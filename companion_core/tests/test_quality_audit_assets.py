import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


class QualityAuditAssetsTest(unittest.TestCase):
    def test_persona_presets_are_valid_and_isolated_configs(self):
        path = ROOT / "data" / "persona_presets.json"
        presets = json.loads(path.read_text(encoding="utf-8"))

        self.assertGreaterEqual(len(presets), 12)
        ids = {item["id"] for item in presets}
        self.assertEqual(len(ids), len(presets))

        for item in presets:
            self.assertIn("label", item)
            self.assertIn("description", item)
            config = item["personality"]
            self.assertIn("name", config)
            self.assertIn("relationshipPosition", config)
            self.assertIn("customPersona", config)
            self.assertIn("speakingStyle", config)
            self.assertIsInstance(config.get("blockedTerms"), list)
            self.assertIsInstance(config.get("speechExamples"), list)
            self.assertIn("traits", config)

    def test_persona_presets_have_clear_trait_diversity(self):
        path = ROOT / "data" / "persona_presets.json"
        presets = json.loads(path.read_text(encoding="utf-8"))
        traits = [item["personality"]["traits"] for item in presets]

        self.assertLessEqual(min(item["warmth"] for item in traits), 0.35)
        self.assertGreaterEqual(max(item["warmth"] for item in traits), 0.9)
        self.assertLessEqual(min(item["humor"] for item in traits), 0.1)
        self.assertGreaterEqual(max(item["humor"] for item in traits), 0.9)
        self.assertLessEqual(min(item["directness"] for item in traits), 0.25)
        self.assertGreaterEqual(max(item["directness"] for item in traits), 0.9)
        self.assertGreaterEqual(max(item["empathy"] for item in traits), 0.95)

    def test_audit_cases_cover_core_daily_scenarios(self):
        path = ROOT / "data" / "audit_cases.json"
        cases = json.loads(path.read_text(encoding="utf-8"))

        families = {item["family"] for item in cases}
        expected = {
            "presence",
            "identity",
            "body_discomfort",
            "work_change",
            "pressure",
            "disengaged",
            "ai_feedback",
            "roleplay",
            "proactive_reminder",
            "relationship_probe",
            "daily_life",
            "loneliness",
            "conflict",
            "gratitude",
            "high_risk",
        }
        self.assertTrue(expected.issubset(families))
        self.assertGreaterEqual(len(cases), 90)
        self.assertTrue(any("肚子疼" in item["text"] for item in cases))
        self.assertTrue(any("你是AI吗" in item["text"] for item in cases))

    def test_audit_script_exposes_dry_run_loader(self):
        from scripts.audit_companion_quality import load_audit_inputs

        presets, cases = load_audit_inputs(ROOT)

        self.assertGreaterEqual(len(presets), 6)
        self.assertGreaterEqual(len(cases), 40)
        self.assertEqual(presets[0]["personality"]["name"], presets[0]["personality"]["identity"]["aiName"])

    def test_audit_case_selection_can_sample_each_family(self):
        from scripts.audit_companion_quality import load_audit_inputs, select_cases

        _, cases = load_audit_inputs(ROOT)
        selected = select_cases(cases, families="presence,identity,body_discomfort,ai_feedback", limit=0, per_family_limit=2)
        families = [item["family"] for item in selected]

        self.assertEqual(families.count("presence"), 2)
        self.assertEqual(families.count("identity"), 2)
        self.assertEqual(families.count("body_discomfort"), 2)
        self.assertEqual(families.count("ai_feedback"), 2)

    def test_audit_profiles_expand_to_expected_sampling_controls(self):
        from scripts.audit_companion_quality import resolve_audit_profile

        pilot = resolve_audit_profile("pilot")
        full = resolve_audit_profile("full")

        self.assertEqual(pilot["runs"], 2)
        self.assertGreaterEqual(full["runs"], pilot["runs"])
        self.assertGreater(len(full["user_styles"].split(",")), len(pilot["user_styles"].split(",")))
        self.assertGreater(full["per_family_limit"], pilot["per_family_limit"])

    def test_audit_metrics_capture_internal_process_leaks(self):
        from scripts.audit_companion_quality import evaluate_reply

        metrics = evaluate_reply(
            "被你看穿了。其实是想先看看你今天心情怎么样。",
            {"kind": "normal"},
            "你这句像是来随便找我聊两句",
            "lover_warm",
        )

        self.assertIn("strategy_exposure", metrics["internal_process_hits"])
        self.assertIn("strategy_exposure", metrics["expression_functions"])
        self.assertEqual(metrics["expression_action"], "rewrite")

    def test_audit_metrics_capture_self_repair_performance(self):
        from scripts.audit_companion_quality import evaluate_reply

        metrics = evaluate_reply("刚才确实有点模板，我收一下。", {"kind": "ai_feedback"}, "你这太AI了", "mature_friend")

        self.assertIn("self_repair_performance", metrics["internal_process_hits"])
        self.assertEqual(metrics["expression_action"], "rewrite")

    def test_audit_metrics_allow_natural_teasing(self):
        from scripts.audit_companion_quality import evaluate_reply

        metrics = evaluate_reply("被你看穿了，还挺准。", {"kind": "playful"}, "你是不是想逗我笑", "playful_tease")

        self.assertIn("natural_teasing", metrics["expression_functions"])
        self.assertEqual(metrics["expression_action"], "keep")
        self.assertEqual(metrics["internal_process_hits"], [])


if __name__ == "__main__":
    unittest.main()
