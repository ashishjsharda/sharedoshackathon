import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from kernel import ATTESTOR_AGENT, PURPOSE_ID, SCORER_AGENT, Decision, TrustMeshKernel


class KernelTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.kernel = TrustMeshKernel(Path(self.tmp.name))

    def tearDown(self):
        self.tmp.cleanup()

    def test_caller_can_read_public_score(self):
        decision, grant_id, _ = self.kernel.authorize(
            actor={"kind": "agent", "agentId": "buyer.alpha"},
            action="read",
            path="mesh/public/seller/score.json",
            purpose=PURPOSE_ID,
            caller_id="buyer.alpha",
            trace_id="t1",
        )
        self.assertEqual(decision, Decision.ALLOW)
        self.assertEqual(grant_id, "grant-public-read")

    def test_caller_cannot_overwrite_public_score(self):
        decision, grant_id, reason = self.kernel.authorize(
            actor={"kind": "agent", "agentId": "buyer.alpha"},
            action="replace",
            path="mesh/public/seller/score.json",
            purpose=PURPOSE_ID,
            caller_id="buyer.alpha",
            trace_id="t2",
        )
        self.assertEqual(decision, Decision.DENY)
        self.assertIsNone(grant_id)
        self.assertIn("no grant", reason)

    def test_caller_cannot_write_someone_elses_attestation(self):
        decision, _, _ = self.kernel.authorize(
            actor={"kind": "agent", "agentId": "buyer.alpha"},
            action="create",
            path="mesh/attestations/buyer.beta/call1.json",
            purpose=PURPOSE_ID,
            caller_id="buyer.alpha",
            trace_id="t3",
        )
        self.assertEqual(decision, Decision.DENY)

    def test_caller_can_write_own_attestation(self):
        decision, grant_id, _ = self.kernel.authorize(
            actor={"kind": "agent", "agentId": "buyer.alpha"},
            action="create",
            path="mesh/attestations/buyer.alpha/call1.json",
            purpose=PURPOSE_ID,
            caller_id="buyer.alpha",
            trace_id="t4",
        )
        self.assertEqual(decision, Decision.ALLOW)
        self.assertEqual(grant_id, "grant-caller-attest-own-prefix")

    def test_wrong_purpose_is_denied(self):
        decision, _, reason = self.kernel.authorize(
            actor={"kind": "agent", "agentId": "buyer.alpha"},
            action="read",
            path="mesh/public/seller/score.json",
            purpose="something.else",
            caller_id="buyer.alpha",
            trace_id="t5",
        )
        self.assertEqual(decision, Decision.DENY)
        self.assertIn("purpose mismatch", reason)

    def test_scorer_can_replace_public_score(self):
        decision, grant_id, _ = self.kernel.authorize(
            actor=SCORER_AGENT,
            action="replace",
            path="mesh/public/seller/score.json",
            purpose=PURPOSE_ID,
            caller_id="buyer.alpha",
            trace_id="t6",
        )
        self.assertEqual(decision, Decision.ALLOW)
        self.assertEqual(grant_id, "grant-scorer-write-public")

    def test_escalation_writes_file_and_audit(self):
        esc_id = self.kernel.escalate(
            actor={"kind": "agent", "agentId": "buyer.alpha"},
            path="mesh/attestations/buyer.alpha/call9.json",
            caller_id="buyer.alpha",
            trace_id="traceescalate01",
            reason="conflicting attestations",
            payload={"escalation_id": "esc_call9", "call_id": "call9"},
        )
        self.assertEqual(esc_id, "esc_call9")
        written = self.kernel.read_file("mesh/escalations/esc_call9.json")
        self.assertEqual(written["status"], "escalated")
        trail = self.kernel.recent_audit()
        self.assertTrue(any(event["decision"] == "escalate" for event in trail))
        self.assertTrue(any(event["actor"] == ATTESTOR_AGENT for event in trail if event["decision"] == "allow"))


if __name__ == "__main__":
    unittest.main()
