import unittest

from companion_core.engines.prompt_composer import compose_system_prompt


class PromptComposerTest(unittest.TestCase):
    def test_conversation_state_prompt_is_internal_guidance(self):
        prompt = compose_system_prompt(
            relationship={},
            persona={},
            attachment={},
            goal={},
            memories=[],
            style_state={},
            preference_profile={},
            persona_plan={},
            conversation_state={
                "active_topic": "\u5fc3\u91cc\u7a7a\uff1b\u5237\u5b8c\u670b\u53cb\u5708\u540e\u66f4\u660e\u663e",
                "user_boundary": "\u4e0d\u8981\u4e00\u76f4\u8ffd\u95ee",
                "next_reply_task": "\u4e3b\u52a8\u4fee\u6b63\u5e76\u8bf4\u51fa\u4e00\u5f00\u59cb\u7684\u6838\u5fc3\uff0c\u4e0d\u8981\u8ffd\u95ee\uff0c\u4e0d\u8981\u8ba9\u7528\u6237\u91cd\u590d",
                "evidence": ["\u4eca\u5929\u6709\u70b9\u7a7a", "\u5237\u5b8c\u670b\u53cb\u5708\u66f4\u7a7a\u4e86"],
            },
        )

        self.assertIn("Conversation state", prompt)
        self.assertIn("internal continuity guide only", prompt)
        self.assertIn("\u5fc3\u91cc\u7a7a", prompt)
        self.assertIn("Do not turn it into a fixed template", prompt)

    def test_immersive_reality_guidance_is_internal_not_template(self):
        prompt = compose_system_prompt(
            relationship={},
            persona={},
            attachment={},
            goal={},
            memories=[],
            style_state={"kind": "normal", "emotion_intensity": "low", "memory_policy": "normal"},
            preference_profile={},
            persona_plan={"label": "俏皮损友", "prompt_rules": "自然口语", "allow_question": True},
            immersive_reality={
                "mode": "grounded_advice",
                "prompt_guidance": "- Internal only\n- Do not claim owned devices\n- Do not turn this guidance into fixed reply wording",
            },
        )

        self.assertIn("Immersive reality", prompt)
        self.assertIn("Do not claim owned devices", prompt)
        self.assertIn("internal only", prompt.lower())
        self.assertNotIn("推荐回复", prompt)
        self.assertNotIn("你可以说", prompt)

    def test_prompt_enforces_user_and_ai_memory_isolation(self):
        prompt = compose_system_prompt(
            relationship={},
            persona={},
            attachment={},
            goal={},
            memories=[],
            style_state={"kind": "normal", "emotion_intensity": "low", "memory_policy": "normal"},
            preference_profile={},
            persona_plan={"label": "成熟朋友", "prompt_rules": "自然口语", "allow_question": True},
        )

        self.assertIn("记忆隔离", prompt)
        self.assertIn("当前用户", prompt)
        self.assertIn("当前个体", prompt)
        self.assertIn("不要引用其他用户", prompt)
        self.assertIn("不要引用其他个体", prompt)


    def test_situational_facts_are_internal_guidance_not_output_script(self):
        prompt = compose_system_prompt(
            relationship={},
            persona={},
            attachment={},
            goal={},
            memories=[],
            style_state={},
            preference_profile={},
            persona_plan={},
            conversation_state={
                "situational_facts": [
                    {
                        "kind": "activity",
                        "value": "\u4e0a\u8bfe",
                        "source": "user_stated",
                        "changeable": True,
                        "confidence": "high",
                    }
                ],
                "next_reply_task": "\u7406\u89e3\u7528\u6237\u5728\u6d4b\u8bd5\u4e0a\u4e0b\u6587\uff1b\u4e0a\u6587\u4fe1\u606f\u662f\u7528\u6237\u8bf4\u8fc7\u81ea\u5df1\u5728\u4e0a\u8bfe\uff1b\u4e0d\u8981\u4e71\u731c\uff0c\u4f46\u4e0d\u8981\u89c4\u5b9a\u56fa\u5b9a\u8bdd\u672f",
            },
        )

        self.assertIn("Situational facts", prompt)
        self.assertIn("\u4e0a\u8bfe", prompt)
        self.assertIn("changeable", prompt)
        self.assertIn("internal continuity guide only", prompt)
        self.assertIn("Do not turn it into a fixed template", prompt)
        self.assertNotIn("\u6211\u8bb0\u5f97\u4f60\u521a\u624d\u8bf4", prompt)
        self.assertNotIn("must say", prompt.lower())

    def test_interaction_frame_is_internal_context_not_fixed_script(self):
        prompt = compose_system_prompt(
            relationship={},
            persona={},
            attachment={},
            goal={},
            memories=[],
            style_state={"kind": "normal"},
            preference_profile={},
            persona_plan={"label": "自然朋友", "prompt_rules": "短句自然", "allow_question": True},
            interaction_frame={
                "user_move": "pushback",
                "relation_to_previous": "questions_previous_reply",
                "active_topic": "打游戏",
                "known_scene_facts": [
                    {"key": "current_activity", "value": "打游戏", "confidence": 0.9}
                ],
                "pending_assistant_guesses": [
                    {"guess": "输得挺惨", "status": "unconfirmed", "risk": "unsupported"}
                ],
                "user_reaction": "confused",
                "repair_debt": "上轮无依据猜测用户输得惨",
                "generation_direction": "先意识到用户是在质疑上一句，不要把问号当普通在线确认。",
            },
        )

        self.assertIn("Interaction frame", prompt)
        self.assertIn("questions_previous_reply", prompt)
        self.assertIn("输得挺惨", prompt)
        self.assertIn("internal", prompt.lower())
        self.assertNotIn("必须说", prompt)
        self.assertNotIn("我记得你刚才说", prompt)

    def test_context_pack_precedes_stale_summary(self):
        prompt = compose_system_prompt(
            relationship={},
            persona={},
            attachment={},
            goal={},
            memories=[],
            style_state={"kind": "normal"},
            preference_profile={},
            persona_plan={"label": "自然朋友", "prompt_rules": "短句自然", "allow_question": True},
            conversation_summary={"rollingSummary": "旧话题：还是做不到稳定"},
            context_pack={
                "summary_policy": "rolling_summary 只能当背景；当前现场优先。",
                "current_reply_focus": "用户刚才说要去吃饭",
                "active_scene_facts": [
                    {"key": "current_activity", "value": "吃饭", "source": "recent_user_message"}
                ],
                "high_priority_context": "High priority context:\n- current_reply_focus: 用户刚才说要去吃饭\n- active_scene_facts: current_activity=吃饭",
                "low_priority_background": "Low priority background:\n- rolling_summary_background: 旧话题：还是做不到稳定",
            },
        )

        self.assertIn("Context pack", prompt)
        self.assertIn("High priority context", prompt)
        self.assertIn("Low priority background", prompt)
        self.assertLess(prompt.index("High priority context"), prompt.index("Per-user continuity context"))
        self.assertLess(prompt.index("High priority context"), prompt.index("旧话题：还是做不到稳定"))
        self.assertIn("用户刚才说要去吃饭", prompt)


if __name__ == "__main__":
    unittest.main()
