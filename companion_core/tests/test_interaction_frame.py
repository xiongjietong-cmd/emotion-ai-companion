import unittest

from companion_core.engines.interaction_frame import build_interaction_frame


class InteractionFrameTest(unittest.TestCase):
    def test_correction_keeps_current_activity(self):
        recent = [
            {"role": "user", "content": "在干嘛"},
            {"role": "assistant", "content": "刚在看窗外，发了一会儿呆。你呢"},
            {"role": "user", "content": "打游戏呢"},
            {"role": "assistant", "content": "挺好，专注的时候舒服。"},
        ]

        frame = build_interaction_frame(
            text="我在打游戏我说",
            recent_messages=recent,
            conversation_state={},
            selected_memories=[],
        )

        self.assertEqual(frame["user_move"], "correction")
        self.assertEqual(frame["relation_to_previous"], "rejects_or_corrects_reply")
        self.assertEqual(frame["known_scene_facts"][-1]["key"], "current_activity")
        self.assertEqual(frame["known_scene_facts"][-1]["value"], "打游戏")
        self.assertIn("不要把这句当新话题", frame["generation_direction"])

    def test_question_mark_after_guess_is_pushback_not_presence(self):
        recent = [
            {"role": "user", "content": "我在打游戏我说"},
            {"role": "assistant", "content": "打游戏呢？听语气输得挺惨。"},
        ]

        frame = build_interaction_frame("？", recent, {}, [])

        self.assertEqual(frame["user_move"], "pushback")
        self.assertEqual(frame["relation_to_previous"], "questions_previous_reply")
        self.assertEqual(frame["user_reaction"], "confused")
        self.assertEqual(frame["pending_assistant_guesses"][-1]["status"], "unconfirmed")
        self.assertIn("别把问号当普通在线确认", frame["generation_direction"])

    def test_question_mark_after_odd_reply_is_pushback_not_presence(self):
        recent = [
            {"role": "user", "content": "对呀"},
            {"role": "assistant", "content": "嗯，那就踏实了。"},
        ]

        frame = build_interaction_frame("嗯？", recent, {}, [])

        self.assertEqual(frame["user_move"], "pushback")
        self.assertEqual(frame["relation_to_previous"], "questions_previous_reply")
        self.assertEqual(frame["user_reaction"], "confused")
        self.assertIn("别把问号当普通在线确认", frame["generation_direction"])

    def test_activity_probe_uses_recent_activity_without_fixed_phrase(self):
        recent = [
            {"role": "user", "content": "我在上课"},
            {"role": "assistant", "content": "好嘞，你先专心上课。"},
        ]

        frame = build_interaction_frame("你知道我现在在干什么吗", recent, {}, [])

        self.assertEqual(frame["user_move"], "probe")
        self.assertEqual(frame["relation_to_previous"], "tests_context_memory")
        self.assertEqual(frame["known_scene_facts"][-1]["value"], "上课")
        self.assertNotIn("我记得你刚才说", frame["generation_direction"])

    def test_style_feedback_creates_repair_debt(self):
        recent = [
            {"role": "assistant", "content": "你是不是也想放空一下。不说也行。"},
            {"role": "user", "content": "感觉你很不耐烦"},
        ]

        frame = build_interaction_frame("你说不说也行", recent, {}, [])

        self.assertEqual(frame["user_move"], "correction")
        self.assertIn("不耐烦", frame["repair_debt"])
        self.assertIn("不要追问用户解释", frame["generation_direction"])


if __name__ == "__main__":
    unittest.main()
