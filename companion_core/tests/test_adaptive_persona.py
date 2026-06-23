import unittest

from companion_core.engines.persona_scheduler import schedule_persona
from companion_core.engines.personality_compiler import compile_personality_config
from companion_core.engines.preference_profile import build_preference_profile
from companion_core.engines.prompt_composer import compose_system_prompt
from companion_core.engines.style_guardrails import classify_user_state


class AdaptivePersonaTest(unittest.TestCase):
    def test_preference_profile_detects_short_reply_and_dislikes_long_explanations(self):
        recent = [
            {"role": "user", "content": "\u55ef"},
            {"role": "assistant", "content": "\u4f60\u53ef\u4ee5\u628a\u6211\u5f53\u6210\u4e00\u4e2a\u804a\u5929\u642d\u5b50\u3002"},
            {"role": "user", "content": "\u522b\u8bf4\u90a3\u4e48\u591a"},
            {"role": "user", "content": "\u592a\u957f\u4e86"},
            {"role": "user", "content": "\u54e6"},
        ]

        profile = build_preference_profile(recent)

        self.assertIn("short_reply", profile["communication_style"])
        self.assertIn("long_explanation", profile["disliked_patterns"])
        self.assertEqual(profile["chat_rhythm"], "slow_blank_space")

    def test_three_minimal_inputs_force_minimal_persona(self):
        recent = [
            {"role": "user", "content": "\uff1f"},
            {"role": "assistant", "content": "\u6211\u5728\u3002"},
            {"role": "user", "content": "\u55ef"},
            {"role": "assistant", "content": "\u90a3\u5c31\u5148\u7f13\u7f13\u3002"},
        ]
        state = classify_user_state("\u54e6", recent)
        profile = build_preference_profile(recent + [{"role": "user", "content": "\u54e6"}])

        plan = schedule_persona(profile, state, recent)

        self.assertEqual(plan["persona"], "minimal_sync")
        self.assertTrue(plan["forced"])
        self.assertLessEqual(plan["max_reply_chars"], 18)
        self.assertFalse(plan["allow_question"])

    def test_playful_context_switches_to_playful_without_long_formality(self):
        recent = [{"role": "user", "content": "\u54c8\u54c8\u54c8\u4f60\u4e5f\u592a\u79bb\u8c31\u4e86"}]
        state = classify_user_state("\u6478\u9c7c\u88ab\u6293\u5305\u4e86\u54c8\u54c8", recent)
        profile = build_preference_profile(recent)

        plan = schedule_persona(profile, state, recent)

        self.assertEqual(plan["persona"], "playful_tease")
        self.assertIn("\u53e3\u8bed", plan["prompt_rules"])
        self.assertNotIn("\u5206\u70b9", plan["prompt_rules"])

    def test_prompt_composer_keeps_ai_identity_boundary_and_persona_rules(self):
        profile = {
            "communication_style": ["short_reply"],
            "base_persona": "minimal_sync",
            "disliked_patterns": ["long_explanation", "over_questioning"],
            "emotional_needs": ["quiet_company"],
            "chat_rhythm": "slow_blank_space",
        }
        state = {"kind": "minimal_input", "emotion_intensity": "low", "allow_question": False}
        plan = schedule_persona(profile, state, [])

        prompt = compose_system_prompt(
            relationship={},
            persona={},
            attachment={},
            goal={"primary_goal": "emotion_ack"},
            memories=[],
            style_state=state,
            preference_profile=profile,
            persona_plan=plan,
            rewrite=False,
        )

        self.assertIn("\u8eab\u4efd\u81ea\u77e5", prompt)
        self.assertIn("\u65e5\u5e38\u804a\u5929\u4e0d\u8981\u4e3b\u52a8\u5f3a\u8c03\u8eab\u4efd", prompt)
        self.assertIn("\u6781\u7b80\u9ed8\u5951", prompt)
        self.assertIn("\u7981\u6b62\u957f\u7bc7", prompt)
        self.assertNotIn("\u4f60\u662f\u771f\u4eba", prompt)

    def test_prompt_composer_injects_user_personality_as_primary_individuality(self):
        preference = {
            "communication_style": ["short_reply"],
            "base_persona": "warm_heal",
            "disliked_patterns": [],
            "emotional_needs": ["quiet_company"],
            "chat_rhythm": "steady",
        }
        state = {"kind": "casual", "emotion_intensity": "low", "allow_question": True}
        plan = schedule_persona(preference, state, [])
        identity_profile = compile_personality_config({
            "name": "\u963f\u8a00",
            "speakingStyle": "\u5634\u786c\u4f46\u4f1a\u7ad9\u5728\u6211\u8fd9\u8fb9\uff0c\u77ed\u53e5",
            "customPersona": "\u6e05\u51b7\uff0c\u4f46\u9760\u5f97\u4f4f",
            "speechExamples": ["\u884c\uff0c\u4eca\u5929\u5148\u522b\u8ddf\u81ea\u5df1\u8f83\u52b2\u3002"],
            "avoidStyle": "\u4e0d\u8981\u5ba2\u670d\u611f",
        })

        prompt = compose_system_prompt(
            relationship={},
            persona={},
            attachment={},
            goal={"primary_goal": "natural_continue"},
            memories=[],
            style_state=state,
            preference_profile=preference,
            persona_plan=plan,
            identity_profile=identity_profile,
            rewrite=False,
        )

        self.assertIn("\u7528\u6237\u4e2a\u6027\u5316\u4eba\u683c\u8bbe\u5b9a", prompt)
        self.assertIn("\u4f18\u5148\u7ea7\u9ad8\u4e8e\u9ed8\u8ba4\u4eba\u8bbe", prompt)
        self.assertIn("\u963f\u8a00", prompt)
        self.assertIn("\u5634\u786c", prompt)
        self.assertIn("\u4e0d\u8981\u5ba2\u670d\u611f", prompt)
        self.assertIn("\u4e0d\u662f\u56fa\u5b9a\u8bdd\u672f", prompt)
        self.assertIn("\u4e0d\u8981\u7167\u6284", prompt)


if __name__ == "__main__":
    unittest.main()
