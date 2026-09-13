/**
 * Drop-in SharedOS Cloud wiring.
 *
 * 1. npm install @aicoo/sharedos
 * 2. Point this file at your Cloud namespace
 * 3. Keep purpose + grants identical to host/src/grants.js
 *
 * This file is an example against the public SharedOS quickstart API:
 * https://sharedos.ai/docs/quickstart
 */

import {
  CapabilityAuthorizer,
  SharedOSKernel,
  registerStandardOsTools,
} from "@aicoo/sharedos";
import { PURPOSE_ID, grantsFor, OWNER } from "./grants.js";

export function createTrustMeshKernel({ files }) {
  const issued = [];

  const kernel = new SharedOSKernel({
    grantSource: {
      async load(access) {
        return issued.filter(
          (candidate) =>
            candidate.namespaceId === access.namespaceId &&
            JSON.stringify(candidate.subject) === JSON.stringify(access.actor)
        );
      },
    },
    authorizer: new CapabilityAuthorizer(),
  });

  registerStandardOsTools(kernel, { files });

  return {
    kernel,
    purpose: PURPOSE_ID,
    issueForCaller(callerId) {
      const batch = grantsFor(callerId).map((grant) => ({
        ...grant,
        issuer: OWNER,
      }));
      issued.push(...batch);
      return batch;
    },
  };
}
