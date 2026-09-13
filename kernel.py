"""
SharedOS-shaped permission kernel for TrustMesh.

This is the product host's grant layer. It mirrors SharedOS contracts:
deny by default, one purpose string, per-path file capabilities,
re-check every call, escalate instead of silently overwrite.

When you connect SharedOS Cloud, keep these same purpose / addresses /
paths. The Cloud kernel becomes the source of truth; this module stays
as a local stand-in and as the file-layout contract.
"""

from __future__ import annotations

import json
import os
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Optional

PURPOSE = (
    "Maintain portable reputation for SharedNet agents so a caller can "
    "decide whether to buy a service, without letting any agent rewrite "
    "another agent's history."
)

PURPOSE_ID = "trustmesh.arena"

NAMESPACE = "trustmesh"
MESH_ROOT = Path(os.environ.get("TRUSTMESH_MESH_ROOT", "mesh"))

SCORER_AGENT = {"kind": "agent", "agentId": "trustmesh.scorer"}
ATTESTOR_AGENT = {"kind": "agent", "agentId": "trustmesh.attestor"}
OWNER = {"kind": "service", "serviceId": "trustmesh"}


class Decision(str, Enum):
    ALLOW = "allow"
    DENY = "deny"
    ESCALATE = "escalate"


@dataclass
class Grant:
    id: str
    subject: dict
    issuer: dict
    resource_namespace: str
    path_prefix: list[str]
    actions: list[str]
    scope: str = "descendants"
    purposes: list[str] = field(default_factory=lambda: [PURPOSE_ID])


# Deny-by-default grant map. Callers never get write on public scores.
# Callers may only create files under their own attestation prefix.
# The scorer may replace derived public score files.
# The attestor may create attestation files and escalation records.
GRANTS: list[Grant] = [
    Grant(
        id="grant-public-read",
        subject={"kind": "agent", "agentId": "*"},
        issuer=OWNER,
        resource_namespace="files",
        path_prefix=["mesh", "public"],
        actions=["read", "search"],
    ),
    Grant(
        id="grant-scorer-write-public",
        subject=SCORER_AGENT,
        issuer=OWNER,
        resource_namespace="files",
        path_prefix=["mesh", "public"],
        actions=["read", "search", "create", "replace"],
    ),
    Grant(
        id="grant-attestor-write-attestations",
        subject=ATTESTOR_AGENT,
        issuer=OWNER,
        resource_namespace="files",
        path_prefix=["mesh", "attestations"],
        actions=["read", "search", "create"],
    ),
    Grant(
        id="grant-attestor-write-escalations",
        subject=ATTESTOR_AGENT,
        issuer=OWNER,
        resource_namespace="files",
        path_prefix=["mesh", "escalations"],
        actions=["read", "search", "create"],
    ),
    Grant(
        id="grant-caller-attest-own-prefix",
        subject={"kind": "agent", "agentId": "$caller"},
        issuer=OWNER,
        resource_namespace="files",
        path_prefix=["mesh", "attestations", "$caller"],
        actions=["create", "read"],
    ),
]


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _path_parts(path: str | Path) -> list[str]:
    text = str(path).replace("\\", "/")
    parts = [p for p in text.split("/") if p and p != "."]
    return parts


def _matches_prefix(actual: list[str], prefix: list[str], caller_id: str) -> bool:
    resolved = [caller_id if p == "$caller" else p for p in prefix]
    if len(actual) < len(resolved):
        return False
    return actual[: len(resolved)] == resolved


def _subject_matches(grant: Grant, actor: dict, caller_id: str) -> bool:
    if grant.subject.get("agentId") == "*":
        return actor.get("kind") == "agent"
    if grant.subject.get("agentId") == "$caller":
        return actor.get("kind") == "agent" and actor.get("agentId") == caller_id
    return grant.subject == actor


@dataclass
class AuditEvent:
    at: str
    decision: str
    action: str
    path: str
    actor: dict
    purpose: str
    grant_id: Optional[str]
    reason: str
    trace_id: str


class TrustMeshKernel:
    """Deny-by-default authorizer with an append-only audit log."""

    def __init__(self, root: Path | None = None):
        self.root = root or MESH_ROOT
        self.root.mkdir(parents=True, exist_ok=True)
        (self.root / "public").mkdir(exist_ok=True)
        (self.root / "attestations").mkdir(exist_ok=True)
        (self.root / "escalations").mkdir(exist_ok=True)
        (self.root / "audit").mkdir(exist_ok=True)
        self.audit_path = self.root / "audit" / "trail.jsonl"

    def authorize(
        self,
        *,
        actor: dict,
        action: str,
        path: str,
        purpose: str,
        caller_id: str,
        trace_id: str,
    ) -> tuple[Decision, Optional[str], str]:
        if purpose != PURPOSE_ID:
            event = self._record(
                Decision.DENY,
                action,
                path,
                actor,
                purpose,
                None,
                f"purpose mismatch: expected {PURPOSE_ID}",
                trace_id,
            )
            return Decision.DENY, None, event.reason

        parts = _path_parts(path)
        matched: Optional[Grant] = None
        for grant in GRANTS:
            if PURPOSE_ID not in grant.purposes:
                continue
            if not _subject_matches(grant, actor, caller_id):
                continue
            if grant.resource_namespace != "files":
                continue
            if action not in grant.actions:
                continue
            if not _matches_prefix(parts, grant.path_prefix, caller_id):
                continue
            matched = grant
            break

        if not matched:
            event = self._record(
                Decision.DENY,
                action,
                path,
                actor,
                purpose,
                None,
                "no grant covers this actor/action/path",
                trace_id,
            )
            return Decision.DENY, None, event.reason

        event = self._record(
            Decision.ALLOW,
            action,
            path,
            actor,
            purpose,
            matched.id,
            "grant matched",
            trace_id,
        )
        return Decision.ALLOW, matched.id, event.reason

    def escalate(
        self,
        *,
        actor: dict,
        path: str,
        caller_id: str,
        trace_id: str,
        reason: str,
        payload: dict[str, Any],
    ) -> str:
        esc_id = payload.get("escalation_id") or f"esc_{trace_id[:12]}"
        esc_path = f"mesh/escalations/{esc_id}.json"
        decision, grant_id, _ = self.authorize(
            actor=ATTESTOR_AGENT,
            action="create",
            path=esc_path,
            purpose=PURPOSE_ID,
            caller_id=caller_id,
            trace_id=trace_id,
        )
        if decision != Decision.ALLOW:
            raise PermissionError("attestor cannot write escalation file")

        body = {
            "escalation_id": esc_id,
            "status": "escalated",
            "reason": reason,
            "at": utc_now(),
            "actor": actor,
            "path": path,
            "payload": payload,
            "grant_id": grant_id,
            "trace_id": trace_id,
            "purpose": PURPOSE_ID,
        }
        self.write_file(esc_path, body)
        self._record(
            Decision.ESCALATE,
            "create",
            esc_path,
            actor,
            PURPOSE_ID,
            grant_id,
            reason,
            trace_id,
        )
        return esc_id

    def read_file(self, path: str) -> Optional[dict]:
        disk = self._disk_path(path)
        if not disk.exists():
            return None
        return json.loads(disk.read_text(encoding="utf-8"))

    def write_file(self, path: str, body: dict) -> None:
        disk = self._disk_path(path)
        disk.parent.mkdir(parents=True, exist_ok=True)
        disk.write_text(json.dumps(body, indent=2), encoding="utf-8")

    def recent_audit(self, limit: int = 50) -> list[dict]:
        if not self.audit_path.exists():
            return []
        lines = self.audit_path.read_text(encoding="utf-8").splitlines()
        return [json.loads(line) for line in lines[-limit:]]

    def _disk_path(self, path: str) -> Path:
        parts = _path_parts(path)
        if parts and parts[0] == "mesh":
            parts = parts[1:]
        return self.root.joinpath(*parts)

    def _record(
        self,
        decision: Decision,
        action: str,
        path: str,
        actor: dict,
        purpose: str,
        grant_id: Optional[str],
        reason: str,
        trace_id: str,
    ) -> AuditEvent:
        event = AuditEvent(
            at=utc_now(),
            decision=decision.value,
            action=action,
            path=path,
            actor=actor,
            purpose=purpose,
            grant_id=grant_id,
            reason=reason,
            trace_id=trace_id,
        )
        self.audit_path.parent.mkdir(parents=True, exist_ok=True)
        with self.audit_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(asdict(event)) + "\n")
        return event


kernel = TrustMeshKernel()
