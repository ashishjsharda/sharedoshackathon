export const PURPOSE_ID = "trustmesh.arena";

export const PURPOSE =
  "Maintain portable reputation for SharedNet agents so a caller can decide whether to buy a service, without letting any agent rewrite another agent's history.";

export const OWNER = { kind: "service", serviceId: "trustmesh" };
export const SCORER = { kind: "agent", agentId: "trustmesh.scorer" };
export const ATTESTOR = { kind: "agent", agentId: "trustmesh.attestor" };

export function grantsFor(callerId) {
  return [
    {
      id: "grant-public-read",
      namespaceId: "trustmesh",
      subject: { kind: "agent", agentId: callerId },
      issuer: OWNER,
      capabilities: [
        {
          resource: { namespace: "files", path: ["mesh", "public"], owner: OWNER },
          actions: ["read", "search"],
          scope: "descendants",
        },
      ],
      constraints: { purposes: [PURPOSE_ID] },
      issuedAt: new Date().toISOString(),
    },
    {
      id: "grant-caller-attest-own-prefix",
      namespaceId: "trustmesh",
      subject: { kind: "agent", agentId: callerId },
      issuer: OWNER,
      capabilities: [
        {
          resource: {
            namespace: "files",
            path: ["mesh", "attestations", callerId],
            owner: OWNER,
          },
          actions: ["create", "read"],
          scope: "descendants",
        },
      ],
      constraints: { purposes: [PURPOSE_ID] },
      issuedAt: new Date().toISOString(),
    },
    {
      id: "grant-scorer-write-public",
      namespaceId: "trustmesh",
      subject: SCORER,
      issuer: OWNER,
      capabilities: [
        {
          resource: { namespace: "files", path: ["mesh", "public"], owner: OWNER },
          actions: ["read", "search", "create", "replace"],
          scope: "descendants",
        },
      ],
      constraints: { purposes: [PURPOSE_ID] },
      issuedAt: new Date().toISOString(),
    },
    {
      id: "grant-attestor-write",
      namespaceId: "trustmesh",
      subject: ATTESTOR,
      issuer: OWNER,
      capabilities: [
        {
          resource: { namespace: "files", path: ["mesh", "attestations"], owner: OWNER },
          actions: ["read", "search", "create"],
          scope: "descendants",
        },
        {
          resource: { namespace: "files", path: ["mesh", "escalations"], owner: OWNER },
          actions: ["read", "search", "create"],
          scope: "descendants",
        },
      ],
      constraints: { purposes: [PURPOSE_ID] },
      issuedAt: new Date().toISOString(),
    },
  ];
}
