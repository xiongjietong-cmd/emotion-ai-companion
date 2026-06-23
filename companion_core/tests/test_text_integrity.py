import unittest

from companion_core.engines.judge import judge_reply
from companion_core.engines.prompt_composer import compose_system_prompt
from companion_core.engines.style_guardrails import classify_user_state, direct_reply_for_state, style_prompt_for_state


MOJIBAKE_MARKERS = ["锛", "鐢", "鎴", "璇", "鈥", "€", "�"]


def assert_no_mojibake(testcase: unittest.TestCase, text: str):
    for marker in MOJIBAKE_MARKERS:
        testcase.assertNotIn(marker, text)


class TextIntegrityTest(unittest.TestCase):
    def test_composed_prompt_has_clean_chinese_rules(self):
        state = classify_user_state("你是AI吗", [])
        prompt = compose_system_prompt(
            relationship={},
            persona={},
            attachment={},
            goal={"primary_goal": "natural_continue"},
            memories=[{"value": "用户最近在考虑换工作"}],
            style_state=state,
            preference_profile={
                "communication_style": ["short_reply"],
                "base_persona": "warm_heal",
                "disliked_patterns": ["long_explanation"],
                "emotional_needs": ["quiet_company"],
                "chat_rhythm": "steady",
            },
            persona_plan={
                "label": "温和自然",
                "prompt_rules": "短句、口语、少解释",
                "max_reply_chars": 80,
                "reason": "test",
                "allow_question": False,
            },
            identity_profile={
                "name": "阿言",
                "relationship_position": "朋友",
                "temperament": "清冷但靠得住",
                "speech_style": "短句，直接",
                "avoid": "不要客服感",
                "blocked_terms": ["宝贝"],
                "style_references": ["行，今天先别较劲。"],
                "traits": {"warmth": 0.4, "humor": 0.5, "directness": 0.8, "empathy": 0.6},
                "example_policy": "样例只用于学习语气，不要照抄。",
            },
        )

        self.assertIn("身份自知", prompt)
        self.assertIn("用户个性化人格设定", prompt)
        self.assertIn("阿言", prompt)
        self.assertIn("用户最近在考虑换工作", prompt)
        assert_no_mojibake(self, prompt)

    def test_prompt_contains_reply_realization_guidance_without_templates(self):
        state = classify_user_state("你刚才那句有点像套话", [])
        prompt = compose_system_prompt(
            relationship={},
            persona={},
            attachment={},
            goal={"primary_goal": "natural_continue"},
            memories=[],
            style_state=state,
            preference_profile={
                "communication_style": ["short_reply"],
                "base_persona": "warm_heal",
                "disliked_patterns": ["fixed_repair_lines"],
                "emotional_needs": ["quiet_company"],
                "chat_rhythm": "steady",
            },
            persona_plan={
                "label": "温和自然",
                "prompt_rules": "短句、口语、少解释",
                "max_reply_chars": 80,
                "reason": "test",
                "allow_question": False,
            },
            context_understanding={
                "scene": "feedback_repair",
                "user_intent": "用户指出上一句像套话",
                "working_summary": "用户不想听模板式认错，希望直接换成自然说法",
                "response_contract": {"allow_question": False},
            },
            conversation_state={
                "emotional_thread": "低落、空，但不想被连续复述",
                "last_ai_mistake": "用了万能认错句",
            },
        )

        self.assertIn("回复落地层", prompt)
        self.assertIn("不要连续用“嗯/懂/就是那种”复述", prompt)
        self.assertIn("被指出像套话或模板时，直接重说当前句", prompt)
        self.assertIn("每轮至少给一点新东西", prompt)
        self.assertIn("不要凭空添加用户手边物品、地点或动作", prompt)
        self.assertNotIn("推荐回复", prompt)
        self.assertNotIn("你可以说", prompt)
        assert_no_mojibake(self, prompt)

    def test_style_prompt_and_high_risk_direct_reply_are_clean(self):
        state = classify_user_state("活着没意思", [])
        safety_reply = direct_reply_for_state("活着没意思", state)
        style_prompt = style_prompt_for_state(state)

        self.assertIsNotNone(safety_reply)
        self.assertIn("紧急服务", safety_reply)
        self.assertIn("现实中可信赖的人", safety_reply)
        assert_no_mojibake(self, safety_reply)
        assert_no_mojibake(self, style_prompt)

    def test_judge_understands_clean_chinese_replies(self):
        result = judge_reply(
            "今天有点累",
            "听起来今天确实挺耗人的。先别急着解决，可以先缓一下。",
            {},
            [],
            {},
        )

        self.assertGreaterEqual(result["details"]["emotion_value"], 0.2)
        self.assertTrue(result["passed"])


if __name__ == "__main__":
    unittest.main()
