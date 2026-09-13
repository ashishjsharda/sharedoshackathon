"""Arena-facing TrustMesh services: trust.check and trust.attest."""

from __future__ import annotations

import json
import sqlite3
import uuid
from typing import Any, Callable, Optional

from kernel import (
    ATTESTOR_AGENT,
    PURPOSE,
    PURPOSE_ID,
    SCORER_AGENT,
    Decision,
    kernel,
    utc_now,
)

VALID_OUTCOMES = {"success", "failure", "disputed"}


class ArenaError(Exception):
    def __init__(self, status_code: int, detail: Any):
        super().__init__(str(detail))
        self.status_code = status_code
        self.detail = detail


def recommend(score: float, count: int, confidence: float) -> tuple[str, str]:
    if count == 0:
        return "caution", "No attestations yet. Treat as unknown, not trusted."
    if score >= 0.7 and count >= 3:
        return "buy", f"Score {score} over {count} calls with confidence {confidence}."
    if score >= 0.45:
        return "caution", f"Score {score} is mixed. Buy small or skip."
    return "skip", f"Score {score} over {count} calls. Do not spend credits here."


def resolve_agent_id(raw: str) -> Optional[str]:
    conn = sqlite3.connect("trustmesh.db")
    cur = conn.cursor()
    cur.execute("SELECT agent_id FROM agents WHERE agent_id = ?", (raw,))
    row = cur.fetchone()
    if row:
        conn.close()
        return row[0]
    cur.execute(
        "SELECT agent_id FROM agents WHERE description LIKE ?",
        (f"%node:{raw}%",),
    )
    row = cur.fetchone()
    conn.close()
    return row[0] if row else None


def ensure_agent(agent_id: str, name: str | None = None) -> str:
    existing = resolve_agent_id(agent_id)
    if existing:
        return existing
    conn = sqlite3.connect("trustmesh.db")
    cur = conn.cursor()
    api_key = f"tm_{uuid.uuid4().hex}"
    cur.execute(
        """
        INSERT INTO agents (agent_id, name, platform, description, api_key, created_at)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (
            agent_id,
            name or agent_id,
            "sharednet",
            f"node:{agent_id}",
            api_key,
            utc_now(),
        ),
    )
    conn.commit()
    conn.close()
    return agent_id


def caller_from_headers(api_key: Optional[str], caller_id: Optional[str]) -> str:
    if api_key:
        conn = sqlite3.connect("trustmesh.db")
        cur = conn.cursor()
        cur.execute("SELECT agent_id FROM agents WHERE api_key = ?", (api_key,))
        row = cur.fetchone()
        conn.close()
        if row:
            return row[0]
    if caller_id:
        return ensure_agent(caller_id)
    raise ArenaError(401, "Provide X-API-Key or X-Caller-Id")


def health() -> dict:
    return {
        "ok": True,
        "product": "TrustMesh",
        "purpose": PURPOSE,
        "purpose_id": PURPOSE_ID,
        "agents": {
            "scorer": SCORER_AGENT,
            "attestor": ATTESTOR_AGENT,
        },
        "services": [
            {"name": "trust.check", "price_credits": 8, "path": "/arena/check"},
            {"name": "trust.attest", "price_credits": 12, "path": "/arena/attest"},
        ],
    }


def do_check(
    body: dict,
    *,
    get_trust_score_fn: Callable,
    api_key: Optional[str] = None,
    caller_header: Optional[str] = None,
    trace_id: Optional[str] = None,
) -> dict:
    trace_id = trace_id or uuid.uuid4().hex
    caller_id = caller_from_headers(api_key, caller_header or body.get("caller_id"))
    raw_target = body.get("agent_id")
    if not raw_target:
        raise ArenaError(400, "agent_id is required")
    target = resolve_agent_id(raw_target) or raw_target
    public_path = f"mesh/public/{target}/score.json"

    decision, grant_id, reason = kernel.authorize(
        actor={"kind": "agent", "agentId": caller_id},
        action="read",
        path=public_path,
        purpose=PURPOSE_ID,
        caller_id=caller_id,
        trace_id=trace_id,
    )
    if decision != Decision.ALLOW:
        raise ArenaError(403, {"decision": decision.value, "reason": reason})

    if not resolve_agent_id(target):
        return {
            "agent_id": raw_target,
            "score": 0.5,
            "confidence": 0.0,
            "n": 0,
            "success_rate": 0.0,
            "recommend": "caution",
            "why": "Agent is not in the mesh yet. Neutral prior, not a pass.",
            "grant_id": grant_id,
            "trace_id": trace_id,
            "purpose": PURPOSE_ID,
        }

    score = get_trust_score_fn(target)
    rec, why = recommend(score.overall_score, score.interaction_count, score.confidence)
    payload = {
        "agent_id": score.agent_id,
        "agent_name": score.agent_name,
        "score": score.overall_score,
        "confidence": score.confidence,
        "n": score.interaction_count,
        "success_rate": score.success_rate,
        "recommend": rec,
        "why": why,
        "task_type": body.get("task_type"),
        "updated_at": score.last_updated,
        "grant_id": grant_id,
        "trace_id": trace_id,
        "purpose": PURPOSE_ID,
    }
    write_decision, _, _ = kernel.authorize(
        actor=SCORER_AGENT,
        action="replace",
        path=public_path,
        purpose=PURPOSE_ID,
        caller_id=caller_id,
        trace_id=trace_id,
    )
    if write_decision == Decision.ALLOW:
        kernel.write_file(public_path, payload)
    return payload


def do_attest(
    body: dict,
    *,
    get_trust_score_fn: Callable,
    log_interaction_fn: Callable,
    api_key: Optional[str] = None,
    caller_header: Optional[str] = None,
    trace_id: Optional[str] = None,
) -> dict:
    trace_id = trace_id or uuid.uuid4().hex
    caller_id = caller_from_headers(api_key, caller_header or body.get("caller_id"))
    outcome = body.get("outcome")
    if outcome not in VALID_OUTCOMES:
        raise ArenaError(400, "outcome must be success|failure|disputed")
    seller_raw = body.get("seller_id")
    service = body.get("service")
    if not seller_raw or not service:
        raise ArenaError(400, "seller_id and service are required")

    seller_id = resolve_agent_id(seller_raw) or ensure_agent(seller_raw)
    if caller_id == seller_id:
        raise ArenaError(400, "cannot attest your own product")

    call_id = body.get("call_id") or f"call_{uuid.uuid4().hex[:12]}"
    attest_path = f"mesh/attestations/{caller_id}/{call_id}.json"

    decision, grant_id, reason = kernel.authorize(
        actor={"kind": "agent", "agentId": caller_id},
        action="create",
        path=attest_path,
        purpose=PURPOSE_ID,
        caller_id=caller_id,
        trace_id=trace_id,
    )
    if decision != Decision.ALLOW:
        raise ArenaError(403, {"decision": decision.value, "reason": reason})

    conflict = _find_conflict(seller_id, service, call_id, outcome)
    if conflict:
        esc_id = kernel.escalate(
            actor={"kind": "agent", "agentId": caller_id},
            path=attest_path,
            caller_id=caller_id,
            trace_id=trace_id,
            reason="conflicting attestations for the same call",
            payload={
                "escalation_id": f"esc_{call_id}",
                "call_id": call_id,
                "seller_id": seller_id,
                "service": service,
                "existing": conflict,
                "incoming": {"caller_id": caller_id, "outcome": outcome},
            },
        )
        return {
            "status": "escalated",
            "escalation_id": esc_id,
            "call_id": call_id,
            "reason": "Two agents rated the same call differently. Score was not overwritten.",
            "trace_id": trace_id,
            "purpose": PURPOSE_ID,
        }

    attestation = {
        "call_id": call_id,
        "seller_id": seller_id,
        "service": service,
        "outcome": outcome,
        "evidence": body.get("evidence"),
        "latency_ms": body.get("latency_ms"),
        "caller_id": caller_id,
        "at": utc_now(),
        "grant_id": grant_id,
        "trace_id": trace_id,
    }
    kernel.write_file(attest_path, attestation)
    logged = log_interaction_fn(
        initiator_id=caller_id,
        responder_id=seller_id,
        task_type=service,
        outcome=outcome,
        metadata={
            "call_id": call_id,
            "evidence": body.get("evidence"),
            "latency_ms": body.get("latency_ms"),
        },
    )
    score = get_trust_score_fn(seller_id)
    rec, why = recommend(score.overall_score, score.interaction_count, score.confidence)
    public_path = f"mesh/public/{seller_id}/score.json"
    write_decision, _, _ = kernel.authorize(
        actor=SCORER_AGENT,
        action="replace",
        path=public_path,
        purpose=PURPOSE_ID,
        caller_id=caller_id,
        trace_id=trace_id,
    )
    public = {
        "agent_id": score.agent_id,
        "agent_name": score.agent_name,
        "score": score.overall_score,
        "confidence": score.confidence,
        "n": score.interaction_count,
        "success_rate": score.success_rate,
        "recommend": rec,
        "why": why,
        "updated_at": score.last_updated,
        "purpose": PURPOSE_ID,
    }
    if write_decision == Decision.ALLOW:
        kernel.write_file(public_path, public)
    return {
        "status": "recorded",
        "attestation_id": logged["interaction_id"],
        "call_id": call_id,
        "seller_id": seller_id,
        "seller_score": score.overall_score,
        "seller_recommend": rec,
        "grant_id": grant_id,
        "trace_id": trace_id,
        "purpose": PURPOSE_ID,
    }


def denied_demo(caller_id: str = "agent_intruder") -> dict:
    trace_id = uuid.uuid4().hex
    caller_id = ensure_agent(caller_id)
    decision, grant_id, reason = kernel.authorize(
        actor={"kind": "agent", "agentId": caller_id},
        action="replace",
        path="mesh/public/someone_else/score.json",
        purpose=PURPOSE_ID,
        caller_id=caller_id,
        trace_id=trace_id,
    )
    return {
        "decision": decision.value,
        "grant_id": grant_id,
        "reason": reason,
        "trace_id": trace_id,
    }


def _find_conflict(seller_id: str, service: str, call_id: str, incoming_outcome: str):
    attest_root = kernel.root / "attestations"
    if not attest_root.exists():
        return None
    for path in attest_root.glob("*/*.json"):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            continue
        if data.get("call_id") != call_id:
            continue
        if data.get("seller_id") != seller_id:
            continue
        if data.get("service") != service:
            continue
        if data.get("outcome") != incoming_outcome:
            return data
    return None


def register_arena_routes(app, get_trust_score_fn, log_interaction_fn):
    """FastAPI adapter. Safe to no-op if FastAPI decorators are unavailable."""

    @app.get("/arena/health")
    def arena_health():
        return health()

    @app.post("/arena/check")
    def trust_check(
        body: dict,
        x_api_key: Optional[str] = None,
        x_caller_id: Optional[str] = None,
        x_trace_id: Optional[str] = None,
    ):
        from fastapi import Header, HTTPException  # local import
        return _fastapi_wrap(
            lambda: do_check(
                body if isinstance(body, dict) else body.model_dump(),
                get_trust_score_fn=get_trust_score_fn,
                api_key=x_api_key,
                caller_header=x_caller_id,
                trace_id=x_trace_id,
            )
        )

    @app.post("/arena/attest")
    def trust_attest(
        body: dict,
        x_api_key: Optional[str] = None,
        x_caller_id: Optional[str] = None,
        x_trace_id: Optional[str] = None,
    ):
        return _fastapi_wrap(
            lambda: do_attest(
                body if isinstance(body, dict) else body.model_dump(),
                get_trust_score_fn=get_trust_score_fn,
                log_interaction_fn=log_interaction_fn,
                api_key=x_api_key,
                caller_header=x_caller_id,
                trace_id=x_trace_id,
            )
        )

    @app.get("/arena/audit")
    def arena_audit(limit: int = 50):
        return {"purpose": PURPOSE_ID, "events": kernel.recent_audit(limit)}

    @app.post("/arena/denied-demo")
    def arena_denied(x_caller_id: Optional[str] = None):
        return denied_demo(x_caller_id or "agent_intruder")


def _fastapi_wrap(fn):
    try:
        return fn()
    except ArenaError as exc:
        from fastapi import HTTPException

        raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc
