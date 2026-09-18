import unittest

from modules.context_recovery import ConfidenceLevel, ContextRecovery


class FinalEvidenceSafeguardTests(unittest.TestCase):
    def setUp(self):
        self.recovery = ContextRecovery()

    def test_abstains_when_final_score_is_below_threshold(self):
        self.assertTrue(
            self.recovery.should_abstain(ConfidenceLevel.MODERATE, 0.54)
        )

    def test_does_not_abstain_when_final_evidence_is_sufficient(self):
        self.assertFalse(
            self.recovery.should_abstain(ConfidenceLevel.HIGH, 0.70)
        )


if __name__ == "__main__":
    unittest.main()