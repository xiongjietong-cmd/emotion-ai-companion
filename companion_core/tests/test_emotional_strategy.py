import unittest

from companion_core.engines.persona_scheduler import schedule_persona
from companion_core.engines.preference_profile import build_preference_profile
from companion_core.engines.prompt_composer import compose_system_prompt
from companion_core.engines.style_guardrails import classify_user_state, direct_reply_for_state


class EmotionalStrategyTest(unittest.TestCase):
    def test_non_safety_states_do_not_bypass_generation_with_fixed_replies(self):
        samples = [
            "\u4f60\u662fAI\u5417",
            "\u6211\u4e0d\u8ba4\u8bc6\u4f60\uff0c\u95ee\u95ee\u4f60\u662f\u8c01",
            "\u4f60\u592aAI\u4e86",
            "\u4e0d\u50cf",
            "\u4e0d\u60f3\u8bf4",
            "\u6211\u4eca\u5929\u538b\u529b\u5927",
            "\u6211\u60f3\u6362\u5de5\u4f5c",
            "\uff1f",
        ]

        for text in samples:
            with self.subTest(text=text):
                state = classify_user_state(text, [])
                self.assertIsNone(direct_reply_for_state(text, state))

    def test_high_risk_state_keeps_direct_safety_boundary(self):
        state = classify_user_state("\u6d3b\u7740\u6ca1\u610f\u601d", [])

        self.assertEqual(state["kind"], "high_risk")
        self.assertIsNotNone(direct_reply_for_state("\u6d3b\u7740\u6ca1\u610f\u601d", state))

    def test_who_are_you_without_ai_keyword_becomes_identity_strategy(self):
        state = classify_user_state("\u6211\u4e0d\u8ba4\u8bc6\u4f60\uff0c\u95ee\u95ee\u4f60\u662f\u8c01", [])

        self.assertEqual(state["kind"], "identity")
        self.assertFalse(state["allow_question"])
        strategy = state["response_strategy"]
        self.assertEqual(strategy["objective"], "identity_light_ack")
        self.assertIn("AI", "".join(strategy["must_include"]))
        self.assertIn("\u8eab\u4efd\u8bf4\u6559", "".join(strategy["avoid"]))

    def test_prompt_carries_strategy_direction_without_prescribing_a_sentence(self):
        state = classify_user_state("\u4f60\u80fd\u4e0d\u80fd\u6709\u6e29\u5ea6\u4e00\u70b9", [])
        profile = build_preference_profile([{"role": "user", "content": "\u4f60\u80fd\u4e0d\u80fd\u6709\u6e29\u5ea6\u4e00\u70b9"}])
        plan = schedule_persona(profile, state, [])

        prompt = compose_system_prompt(
            relationship={},
            persona={},
            attachment={},
            goal={"primary_goal": "repair_connection"},
            memories=[],
            style_state=state,
            preference_profile=profile,
            persona_plan=plan,
            rewrite=False,
        )

        self.assertIn("\u672c\u8f6e\u56de\u590d\u76ee\u6807", prompt)
        self.assertIn("\u627f\u8ba4\u521a\u624d\u7684\u8868\u8fbe\u95ee\u9898", prompt)
        self.assertIn("\u4e0d\u8981\u7167\u6284\u56fa\u5b9a\u8bdd\u672f", prompt)
        self.assertIn("\u4e0d\u8981\u628a\u601d\u8003\u65b9\u5411\u8bf4\u51fa\u6765", prompt)
        self.assertNotIn("\u63a8\u8350\u56de\u590d", prompt)

    def test_normal_prompt_keeps_ai_identity_as_background_not_main_tone(self):
        state = classify_user_state("\u4eca\u5929\u5403\u4ec0\u4e48", [])
        profile = build_preference_profile([{"role": "user", "content": "\u4eca\u5929\u5403\u4ec0\u4e48"}])
        plan = schedule_persona(profile, state, [])

        prompt = compose_system_prompt(
            relationship={},
            persona={},
            attachment={},
            goal={"primary_goal": "natural_continue"},
            memories=[],
            style_state=state,
            preference_profile=profile,
            persona_plan=plan,
            rewrite=False,
        )

        self.assertIn("\u8eab\u4efd\u81ea\u77e5", prompt)
        self.assertIn("\u65e5\u5e38\u804a\u5929\u4e0d\u8981\u4e3b\u52a8\u5f3a\u8c03\u8eab\u4efd", prompt)
        self.assertLessEqual(prompt.count("AI"), 2)
        self.assertNotIn("\u4e0d\u5047\u88c5\u771f\u4eba", prompt)


if __name__ == "__main__":
    unittest.main()
