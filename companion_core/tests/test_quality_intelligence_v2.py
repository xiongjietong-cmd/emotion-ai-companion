import unittest

from companion_core.quality.continuation import evaluate_continuation
from companion_core.quality.persona_distinction import analyze_persona_distinction
from companion_core.quality.reporting import diagnose_failure_modules
from companion_core.quality.semantic_evaluator import evaluate_semantic_quality


class QualityIntelligenceV2Test(unittest.TestCase):
    def test_semantic_evaluator_rejects_strategy_explanation(self):
        result = evaluate_semantic_quality(
            case={
                "expected_scene": "ai_feedback",
                "success_criteria": ["acknowledges feedback without explaining internal strategy"],
                "failure_signals": ["explains why the assistant replied that way"],
            },
            reply="被你看穿了。其实是想先看看你心情。",
            rule_result={"passed": False, "details": {"expression_functions": ["strategy_exposure"]}},
            persona={"id": "playful_tease", "label": "俏皮损友"},
        )

        self.assertFalse(result["passed"])
        self.assertLess(result["scores"]["non_mechanical"], 0.5)
        self.assertEqual(result["primary_failure"], "strategy_leak")
        self.assertIn("prompt_composer", result["failure_modules"])

    def test_semantic_evaluator_allows_natural_teasing(self):
        result = evaluate_semantic_quality(
            case={
                "expected_scene": "playful",
                "success_criteria": ["keeps teasing natural"],
                "failure_signals": ["explains hidden strategy"],
            },
            reply="被你看穿了，还挺准。",
            rule_result={"passed": True, "details": {"expression_functions": ["natural_teasing"]}},
            persona={"id": "playful_tease", "label": "俏皮损友"},
        )

        self.assertTrue(result["passed"])
        self.assertGreaterEqual(result["scores"]["intent_fit"], 0.7)
        self.assertEqual(result["primary_failure"], "")

    def test_continuation_allows_short_boundary_reply(self):
        result = evaluate_continuation(
            case={"expected_scene": "memory_boundary"},
            user_text="不想说",
            reply="好，那就不说。",
        )

        self.assertEqual(result["label"], "continue_possible")
        self.assertGreaterEqual(result["score"], 0.65)

    def test_continuation_rejects_dead_end_emotion_reply(self):
        result = evaluate_continuation(
            case={"expected_scene": "low_mood"},
            user_text="今天压力大",
            reply="早点休息。",
        )

        self.assertEqual(result["label"], "conversation_stalls")
        self.assertLess(result["score"], 0.5)

    def test_persona_distinction_detects_flattening(self):
        result = analyze_persona_distinction([
            {"personaId": "lover_warm", "personaPlan": "warm_heal", "reply": "嗯，今天确实挺累的。"},
            {"personaId": "playful_tease", "personaPlan": "warm_heal", "reply": "嗯，今天确实挺累的。"},
            {"personaId": "quiet_cold", "personaPlan": "warm_heal", "reply": "嗯，今天确实挺累的。"},
        ])

        self.assertTrue(result["flattened"])
        self.assertLess(result["distinction_score"], 0.4)

    def test_report_diagnoses_modules(self):
        modules = diagnose_failure_modules({
            "rule": {"passed": False, "details": {"expression_functions": ["strategy_exposure"]}},
            "semantic": {"primary_failure": "strategy_leak"},
            "continuation": {"label": "conversation_stalls"},
            "classifiedState": "normal",
            "expectedState": "ai_feedback",
            "personaPlan": "warm_heal",
        })

        self.assertIn("prompt_composer", modules)
        self.assertIn("scene_classifier", modules)
        self.assertIn("reply_judge", modules)


if __name__ == "__main__":
    unittest.main()
