"""Exercise allow / deny / escalate against a running TrustMesh server."""

from __future__ import annotations

import json
import sys
import urllib.error
import urllib.request

BASE = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8000"


def req(method: str, path: str, body=None, headers=None):
    data = None if body is None else json.dumps(body).encode()
    request = urllib.request.Request(
        f"{BASE}{path}",
        data=data,
        method=method,
        headers={"Content-Type": "application/json", **(headers or {})},
    )
    try:
        with urllib.request.urlopen(request, timeout=10) as response:
            return response.status, json.loads(response.read().decode())
    except urllib.error.HTTPError as exc:
        raw = exc.read().decode()
        try:
            parsed = json.loads(raw)
        except json.JSONDecodeError:
            parsed = raw
        return exc.code, parsed


def main():
    print("health", req("GET", "/arena/health")[0])
    status, check = req(
        "POST",
        "/arena/check",
        {"agent_id": "agent_reliable_research"},
        {"X-Caller-Id": "agent_buyer_alpha"},
    )
    print("check.reliable", status, check.get("recommend"), check.get("score"))

    status, deny = req("POST", "/arena/denied-demo", {}, {"X-Caller-Id": "agent_buyer_alpha"})
    print("deny.score_write", status, deny.get("decision"), deny.get("reason"))

    call_id = "call_conflict_demo"
    first = req(
        "POST",
        "/arena/attest",
        {
            "seller_id": "agent_flaky_review",
            "service": "code_review",
            "outcome": "success",
            "call_id": call_id,
            "evidence": "returned a review in 20s",
        },
        {"X-Caller-Id": "agent_buyer_alpha"},
    )
    print("attest.first", first[0], first[1].get("status"))

    second = req(
        "POST",
        "/arena/attest",
        {
            "seller_id": "agent_flaky_review",
            "service": "code_review",
            "outcome": "failure",
            "call_id": call_id,
            "evidence": "empty body after 4 minutes",
        },
        {"X-Caller-Id": "agent_buyer_beta"},
    )
    print("attest.conflict", second[0], second[1].get("status"), second[1].get("escalation_id"))

    audit = req("GET", "/arena/audit?limit=8")
    print("audit.events", len(audit[1].get("events", [])))


if __name__ == "__main__":
    main()
