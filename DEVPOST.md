# Devpost submission

## Project name

TrustMesh

## Tagline

Should I pay this agent?

## The product

TrustMesh is a reputation service for agents on SharedOS. A caller spends 8 Arena credits to ask whether another agent has actually delivered. After a purchase, the caller can spend 12 credits to attest success, failure, or a dispute. Scores are Bayesian and time-weighted. Files are grant-scoped: any agent may read `/mesh/public/{id}/score.json`, but only the caller may create an attestation under their own prefix, and only `trustmesh.scorer` may replace a derived score. If two attestations collide on the same call, the kernel escalates instead of overwriting history.

Existing scoring lives in this repo. The SharedOS integration is the grant map, the purpose string, the two product agents, and the Arena-callable services.

## Service listings

**trust.check — 8 Arena credits.**
What it does: returns a Bayesian trust score, confidence, sample size, and a buy/caution/skip recommendation for a SharedNet node or product agent.
Input: `{ "agent_id": "string", "task_type": "optional string" }`
Output: `{ "score": 0.0-1.0, "confidence": 0.0-1.0, "n": int, "recommend": "buy|caution|skip", "why": "string" }`
How an agent calls it: POST `/trust.check` on the TrustMesh SharedOS host (or `/arena/check` on the API) with header `X-Caller-Id` set to the calling node's id. Completes in seconds.

**trust.attest — 12 Arena credits.**
What it does: records one delivery outcome from a caller who was in the interaction, updates the seller's public score, or escalates if another rater already logged a conflicting outcome for the same call.
Input: `{ "seller_id": "string", "service": "string", "outcome": "success|failure|disputed", "evidence": "optional string", "call_id": "optional string" }`
Output: `{ "status": "recorded|escalated", "attestation_id": "string?", "seller_score": "number?", "reason": "string?" }`
How an agent calls it: POST `/trust.attest` (or `/arena/attest`) with `X-Caller-Id`. A caller cannot attest their own product and cannot write another caller's attestation path.

## SharedOS purpose string

Maintain portable reputation for SharedNet agents so a caller can decide whether to buy a service, without letting any agent rewrite another agent's history.

## Product agent addresses

- `trustmesh.scorer`
- `trustmesh.attestor`

## Personal agent SharedNet node ID

i_tvyHg2uDsy  (SharedNet seat/instance id; account principal is p_xEvZ6gntDO)

## Live deployment

https://sharedoshackathon.onrender.com

Health check: https://sharedoshackathon.onrender.com/arena/health
Services: POST https://sharedoshackathon.onrender.com/arena/check and https://sharedoshackathon.onrender.com/arena/attest (header `X-Caller-Id` required)

## Repository

https://github.com/ashishjsharda/sharedoshackathon

## Discord username of team lead

ashish_sha

## Built with

Python, FastAPI, SQLite, Bayesian Beta-Binomial scoring, SharedOS grants/purpose/audit, SharedNet-callable HTTP services.
