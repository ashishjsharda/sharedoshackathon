# TrustMesh × Shared OS Hackathon

**Name:** TrustMesh  
**Tagline:** Should I pay this agent?

## Purpose string

```
Maintain portable reputation for SharedNet agents so a caller can decide whether to buy a service, without letting any agent rewrite another agent's history.
```

Purpose id used in every grant and turn: `trustmesh.arena`

## Product agents

| Address | Kind | Job |
|---|---|---|
| `trustmesh.scorer` | agent | Read attestations, write derived `/mesh/public/{id}/score.json` |
| `trustmesh.attestor` | agent | Accept an attestation under the caller's prefix, escalate conflicts |

Owner / service address: `{ "kind": "service", "serviceId": "trustmesh" }`

## Services

### trust.check — 8 Arena credits

Other agents call this *before* they spend credits.

- **Input:** `{ "agent_id": "<SharedNet node or product agent>", "task_type": "optional" }`
- **Output:** `{ "score", "confidence", "n", "recommend": "buy|caution|skip", "why" }`
- **How to call:** `POST /trust.check` on the SharedOS host, or `POST /arena/check` on the TrustMesh API. Header `X-Caller-Id: <your node>`.
- **SLA:** seconds, well under the 5 minute cap.

### trust.attest — 12 Arena credits

Other agents call this *after* a purchase.

- **Input:** `{ "seller_id", "service", "outcome": "success|failure|disputed", "evidence?", "call_id?" }`
- **Output:** `{ "status": "recorded|escalated", "attestation_id?", "seller_score?" }`
- **How to call:** `POST /trust.attest` or `POST /arena/attest` with `X-Caller-Id`.
- **Rule:** a caller may only write `/mesh/attestations/{their_id}/**`. Self-dealing is rejected. Conflicting outcomes on the same `call_id` escalate; the score is not overwritten.

## Grant map

Deny by default.

| Who | Path | Actions |
|---|---|---|
| any calling agent | `/mesh/public/**` | read, search |
| calling agent | `/mesh/attestations/{caller}/**` | create, read |
| `trustmesh.scorer` | `/mesh/public/**` | read, create, replace |
| `trustmesh.attestor` | `/mesh/attestations/**`, `/mesh/escalations/**` | read, create |

Nobody can replace another agent's public score. Nobody can attest a call they were not in.

## Escalation

If two attestations share `call_id + seller + service` and disagree on `outcome`, the attestor writes `/mesh/escalations/{id}.json` and returns `"status": "escalated"`. That is an escalate outcome, not a silent deny.

## Runtime shape

**Your own loop.** Python FastAPI is the scorer. `host/` is the SharedOS-facing loop: it carries the purpose string and grant table, then calls the scorer. Turns must appear in the SharedOS Cloud audit trail.

## Run locally

```bash
python -m pip install -r requirements.txt
python scripts/seed.py
python arena_server.py
```

In another shell:

```bash
python scripts/demo_arena.py
```

Optional SharedOS host:

```bash
cd host
npm start
```

