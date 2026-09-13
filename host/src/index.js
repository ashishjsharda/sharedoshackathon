/**
 * SharedOS Cloud host for TrustMesh.
 *
 * Shape: "your own loop".
 * The kernel decides whether the turn may read a public score or write an
 * attestation. The actual scoring still lives in the Python TrustMesh API.
 *
 * Wire this to SharedOS Cloud, then keep TRUSTMESH_API_URL pointed at
 * the FastAPI process (`python main.py`).
 */

import { ATTESTOR, PURPOSE, PURPOSE_ID, SCORER, grantsFor } from "./grants.js";

const API = process.env.TRUSTMESH_API_URL || "http://127.0.0.1:8000";
const PORT = Number(process.env.PORT || 8787);

async function proxy(path, { method = "GET", body, callerId, traceId } = {}) {
  const response = await fetch(`${API}${path}`, {
    method,
    headers: {
      "content-type": "application/json",
      "X-Caller-Id": callerId || "sharednet.unknown",
      "X-Trace-Id": traceId || crypto.randomUUID(),
    },
    body: body ? JSON.stringify(body) : undefined,
  });
  const json = await response.json();
  return { status: response.status, json };
}

function json(res, status, body) {
  const payload = JSON.stringify(body);
  res.writeHead(status, {
    "content-type": "application/json",
    "access-control-allow-origin": "*",
  });
  res.end(payload);
}

const http = await import("node:http");

const server = http.createServer(async (req, res) => {
  const url = new URL(req.url || "/", `http://127.0.0.1:${PORT}`);
  if (req.method === "OPTIONS") {
    res.writeHead(204, {
      "access-control-allow-origin": "*",
      "access-control-allow-headers": "*",
      "access-control-allow-methods": "GET,POST,OPTIONS",
    });
    res.end();
    return;
  }

  if (url.pathname === "/health") {
    json(res, 200, {
      ok: true,
      purpose: PURPOSE,
      purpose_id: PURPOSE_ID,
      agents: { scorer: SCORER, attestor: ATTESTOR },
      runtime_shape: "own_loop",
      grants: grantsFor("$caller").map((g) => g.id),
    });
    return;
  }

  if (url.pathname === "/services") {
    json(res, 200, {
      services: [
        {
          name: "trust.check",
          price_credits: 8,
          input: { agent_id: "string", task_type: "string?" },
          output: {
            score: "number",
            confidence: "number",
            n: "number",
            recommend: "buy|caution|skip",
            why: "string",
          },
          call: "POST /trust.check",
        },
        {
          name: "trust.attest",
          price_credits: 12,
          input: {
            seller_id: "string",
            service: "string",
            outcome: "success|failure|disputed",
            evidence: "string?",
            call_id: "string?",
          },
          output: { status: "recorded|escalated", seller_score: "number?" },
          call: "POST /trust.attest",
        },
      ],
    });
    return;
  }

  let body = {};
  if (req.method === "POST") {
    const chunks = [];
    for await (const chunk of req) chunks.push(chunk);
    if (chunks.length) body = JSON.parse(Buffer.concat(chunks).toString("utf8"));
  }

  const callerId = req.headers["x-caller-id"] || body.caller_id || "sharednet.unknown";
  const traceId = req.headers["x-trace-id"] || crypto.randomUUID();

  if (url.pathname === "/trust.check" && req.method === "POST") {
    const result = await proxy("/arena/check", {
      method: "POST",
      body,
      callerId,
      traceId,
    });
    json(res, result.status, result.json);
    return;
  }

  if (url.pathname === "/trust.attest" && req.method === "POST") {
    const result = await proxy("/arena/attest", {
      method: "POST",
      body,
      callerId,
      traceId,
    });
    json(res, result.status, result.json);
    return;
  }

  json(res, 404, { error: "unknown route" });
});

server.listen(PORT, () => {
  console.log(`TrustMesh SharedOS host on :${PORT}`);
  console.log(`purpose: ${PURPOSE_ID}`);
  console.log(`proxying scoring API at ${API}`);
});
