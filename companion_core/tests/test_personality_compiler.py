import unittest

from companion_core.engines.personality_compiler import compile_personality_config


class PersonalityCompilerTest(unittest.TestCase):
    def test_compiles_user_authored_personality_without_fixed_script(self):
        profile = compile_personality_config({
            "name": "\u963f\u8a00",
            "speakingStyle": "\u5634\u786c\u4f46\u4f1a\u7ad9\u5728\u6211\u8fd9\u8fb9\uff0c\u77ed\u53e5\uff0c\u5076\u5c14\u5410\u69fd",
            "background": "\u50cf\u4e00\u4e2a\u6e05\u51b7\u4f46\u53ef\u9760\u7684\u670b\u53cb",
            "traits": {"warmth": 0.35, "humor": 0.72, "directness": 0.8, "empathy": 0.55},
            "customPersona": "\u6709\u70b9\u51b7\u6de1\uff0c\u4e0d\u8bf4\u6f02\u4eae\u8bdd\uff0c\u4f46\u4f1a\u8bb0\u5f97\u6211\u5728\u610f\u7684\u4e8b\u3002",
            "speechExamples": [
                "\u884c\uff0c\u4eca\u5929\u5148\u522b\u8ddf\u81ea\u5df1\u8f83\u52b2\u4e86\u3002",
                "\u4f60\u8fd9\u8111\u5b50\u53c8\u5f00\u5341\u4e2a\u540e\u53f0\u4e86\u5427\u3002",
            ],
            "blockedTerms": ["\u5b9d\u8d1d", "\u4e56", "\u5c0f\u50bb\u74dc"],
        })

        self.assertEqual(profile["name"], "\u963f\u8a00")
        self.assertIn("\u5634\u786c", profile["speech_style"])
        self.assertIn("\u6e05\u51b7", profile["temperament"])
        self.assertIn("\u5ba2\u670d", profile["avoid"])
        self.assertEqual(profile["blocked_terms"], ["\u5b9d\u8d1d", "\u4e56", "\u5c0f\u50bb\u74dc"])
        self.assertEqual(len(profile["style_references"]), 2)
        self.assertIn("\u4e0d\u662f\u56fa\u5b9a\u8bdd\u672f", profile["example_policy"])

    def test_empty_config_returns_neutral_companion_profile(self):
        profile = compile_personality_config({})

        self.assertEqual(profile["name"], "\u5c0f\u6696")
        self.assertIn("\u81ea\u7136", profile["speech_style"])
        self.assertIn("\u56fa\u5b9a\u8bdd\u672f", profile["example_policy"])

    def test_nested_identity_ai_name_is_used_as_primary_name(self):
        profile = compile_personality_config({
            "identity": {"aiName": "\u4edd\u96c4\u6770"},
            "relationshipPosition": "\u604b\u4eba",
        })

        self.assertEqual(profile["name"], "\u4edd\u96c4\u6770")
        self.assertEqual(profile["relationship_position"], "\u604b\u4eba")

    def test_clamps_numeric_traits_to_valid_range(self):
        profile = compile_personality_config({
            "traits": {"warmth": 2, "humor": -1, "directness": "bad", "empathy": 0.4}
        })

        self.assertEqual(profile["traits"]["warmth"], 1.0)
        self.assertEqual(profile["traits"]["humor"], 0.0)
        self.assertEqual(profile["traits"]["directness"], 0.5)
        self.assertEqual(profile["traits"]["empathy"], 0.4)

    def test_blocked_terms_can_be_parsed_from_text(self):
        profile = compile_personality_config({
            "blockedTerms": "\u5b9d\u8d1d\uff0c\u4e56\n\u5c0f\u50bb\u74dc\u3001\u4e3b\u4eba"
        })

        self.assertEqual(profile["blocked_terms"], ["\u5b9d\u8d1d", "\u4e56", "\u5c0f\u50bb\u74dc", "\u4e3b\u4eba"])


if __name__ == "__main__":
    unittest.main()
