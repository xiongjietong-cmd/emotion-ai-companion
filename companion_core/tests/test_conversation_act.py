import unittest

from companion_core.engines.conversation_act import classify_conversation_act
from companion_core.engines.judge import judge_reply
from companion_core.engines.prompt_composer import compose_system_prompt
from companion_core.engines.relationship import default_relationship
from companion_core.engines.safe_reply_repair import repair_failed_reply


class ConversationActTest(unittest.TestCase):
    def test_comfort_request_is_not_disengaged_boundary(self):
        recent = [
            {"role": "user", "content": "我上课呢"},
            {"role": "assistant", "content": "好，那你先专心上课。"},
            {"role": "user", "content": "我跟你说这个老师特别严格"},
            {"role": "assistant", "content": "哎呀，那肯定挺累的。"},
            {"role": "user", "content": "你在我也累呀"},
        ]

        act = classify_conversation_act("安慰安慰我呗", recent)

        self.assertEqual(act["act"], "seeking_comfort")
        self.assertEqual(act["pressure"], "open")
        self.assertIn("emotional_support", act["needs"])
        self.assertIn("premature_closure", act["avoid"])

    def test_judge_rejects_closing_space_when_user_asks_for_comfort(self):
        reply = "过来，抱一下。\n不说话也行。"

        result = judge_reply("安慰安慰我呗", reply, default_relationship(), [], {})

        self.assertFalse(result["passed"])
        self.assertIn("intent_alignment", result["details"])
        self.assertIn("premature_closure", result["details"]["intent_alignment"]["issues"])
        self.assertIn("intent_mismatch", result["details"]["blocking_expression"]["reasons"])

    def test_repair_replaces_premature_closure_with_actual_comfort(self):
        reply = "过来，抱一下。\n不说话也行。"
        judgement = judge_reply("安慰安慰我呗", reply, default_relationship(), [], {})

        repaired = repair_failed_reply("安慰安慰我呗", reply, judgement)

        self.assertIsNotNone(repaired)
        self.assertNotIn("不说话也行", repaired)
        self.assertNotIn("不用回", repaired)
        self.assertTrue(any(token in repaired for token in ["抱", "站你这边", "撑着", "委屈"]))

    def test_prompt_carries_conversation_act_without_fixed_sentence(self):
        act = classify_conversation_act("安慰安慰我呗", [])

        prompt = compose_system_prompt(
            relationship={},
            persona={},
            attachment={},
            goal={"primary_goal": "emotion_ack"},
            memories=[],
            style_state={"kind": "normal", "emotion_intensity": "none", "memory_policy": "relevant", "response_strategy": {}},
            preference_profile={
                "communication_style": [],
                "base_persona": "warm_heal",
                "disliked_patterns": [],
                "emotional_needs": [],
                "chat_rhythm": "steady",
            },
            persona_plan={
                "label": "温柔治愈",
                "prompt_rules": "自然短句",
                "max_reply_chars": 100,
                "reason": "test",
                "allow_question": False,
            },
            conversation_act=act,
            rewrite=False,
        )

        self.assertIn("Conversation act", prompt)
        self.assertIn("seeking_comfort", prompt)
        self.assertIn("premature_closure", prompt)
        self.assertIn("not a fixed script", prompt)
        self.assertNotIn("推荐回复", prompt)


if __name__ == "__main__":
    unittest.main()
