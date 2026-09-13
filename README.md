# TrustMesh

**Should I pay this agent?**

TrustMesh is a reputation service for agents on [SharedOS](https://shared-os-hackathon.devpost.com/). Before a caller spends Arena credits on a stranger, it asks TrustMesh whether that stranger has actually delivered before. After a purchase, the caller can attest to the outcome — and if two callers disagree about the same delivery, TrustMesh escalates instead of letting either one silently overwrite the other's history.

The scoring engine (a time-weighted Bayesian model) already existed in this repo. What's new for SharedOS is the grant map, the purpose string, the two product agents, and the two Arena-callable services described below.

## Purpose string

```
Maintain portable reputation for SharedNet agents so a caller can decide whether to buy a service, without letting any agent rewrite another agent's history.
```

Purpose id used in every grant and turn: `trustmesh.arena`

## Product agents

| Address | Kind | Job |
|---|---|---|
| `trustmesh.scorer` | agent | Reads attestations, writes the derived `/mesh/public/{id}/score.json` |
| `trustmesh.attestor` | agent | Accepts an attestation under the caller's own prefix, escalates conflicts |

Owner / service address: `{ "kind": "service", "serviceId": "trustmesh" }`

## Services

### `trust.check` — 8 Arena credits

Call this *before* spending credits on someone.

- **Input:** `{ "agent_id": "<SharedNet node or product agent>", "task_type": "optional" }`
- **Output:** `{ "score", "confidence", "n", "recommend": "buy|caution|skip", "why" }`
- **Call:** `POST /trust.check` on the SharedOS host, or `POST /arena/check` on the TrustMesh API. Header `X-Caller-Id: <your node>`.
- **SLA:** seconds, well under the 5-minute cap.

### `trust.attest` — 12 Arena credits

Call this *after* a purchase.

- **Input:** `{ "seller_id", "service", "outcome": "success|failure|disputed", "evidence?", "call_id?" }`
- **Output:** `{ "status": "recorded|escalated", "attestation_id?", "seller_score?" }`
- **Call:** `POST /trust.attest` or `POST /arena/attest` with `X-Caller-Id`.
- **Rule:** a caller may only write `/mesh/attestations/{their_id}/**`. Self-dealing is rejected. Conflicting outcomes on the same `call_id` escalate — the score is never overwritten.

## Grant map

Deny by default.

| Who | Path | Actions |
|---|---|---|
| any calling agent | `/mesh/public/**` | read, search |
| calling agent | `/mesh/attestations/{caller}/**` | create, read |
| `trustmesh.scorer` | `/mesh/public/**` | read, create, replace |
| `trustmesh.attestor` | `/mesh/attestations/**`, `/mesh/escalations/**` | read, create |

Nobody can replace another agent's public score. Nobody can attest a call they weren't in.

## Escalation

If two attestations share `call_id + seller + service` and disagree on `outcome`, the attestor writes `/mesh/escalations/{id}.json` and returns `"status": "escalated"`. That's an escalate outcome, not a silent deny — the `mesh/` folder in this repo has a real example of each of the three outcomes (buy, deny, escalate) from an actual local run.

## Run locally

The Arena services (`arena_server.py`, `kernel.py`, `core.py`, `scripts/`) use only the Python standard library — no `pip install` required.

```bash
python scripts/seed.py       # seeds a small SharedNet neighborhood so scores aren't all 0.5
python arena_server.py       # serves trust.check / trust.attest on :8000
```

In another shell:

```bash
python scripts/demo_arena.py
```

You should see three outcomes: a buy recommendation, a denied score overwrite, and an escalated conflicting attestation.

Optional SharedOS host (proxies the two services with the purpose string and grant table attached):

```bash
cd host
npm install
npm start
```

The original reputation API (`main.py` — agent registration, interaction logging, leaderboard) is the pre-existing engine this build wraps. It's included for reference and isn't required to run the Arena demo above; it also binds port 8000, so don't run it at the same time as `arena_server.py`. To run it on its own: `pip install -r requirements.txt && python main.py`.

## Repository layout

```
kernel.py        deny-by-default grant authorizer + append-only audit log
core.py          Bayesian scoring + SQLite helpers (no web framework)
arena.py         trust.check / trust.attest logic
arena_server.py  stdlib HTTP server exposing the Arena services on :8000
host/            SharedOS Cloud-facing loop (Node) that carries the purpose string
scripts/         seed.py (sample data) and demo_arena.py (exercises all 3 outcomes)
mesh/            grant-scoped file store: public/, attestations/, escalations/, audit/
main.py          pre-existing FastAPI reputation API (register, log, leaderboard)
```

## Built with

Python, FastAPI, SQLite, Bayesian Beta-Binomial scoring, SharedOS grants/purpose/audit, SharedNet-callable HTTP services.

## More

- [`ARENA.md`](ARENA.md) — instructions for the personal agent that pitches, critiques, and spends credits on our behalf.
- [`DEVPOST.md`](DEVPOST.md) — submission copy for Devpost.
