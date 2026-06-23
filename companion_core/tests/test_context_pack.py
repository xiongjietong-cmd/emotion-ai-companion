import unittest

from companion_core.engines.context_pack import build_context_pack
from companion_core.engines.interaction_frame import build_interaction_frame


class ContextPackTest(unittest.TestCase):
    def test_recent_activity_overrides_stale_rolling_summary(self):
        recent = [
            {"role": "user", "content": "我刚起床准备去上课"},
            {"role": "assistant", "content": "好呢，快去洗漱吧，别迟到啦。"},
            {"role": "user", "content": "不洗漱了，我要去吃饭饭"},
            {"role": "assistant", "content": "好嘞，吃吧吃吧～"},
        ]
        frame = build_interaction_frame("我要去干什么来着？", recent, {}, [])
        summary = {
            "rollingSummary": "用户之前反复测试：还是做不到吗 / 做不到让你稳定 / 你知道我说的什么吗",
            "nextReplyTask": "emotion_ack",
        }

        pack = build_context_pack(
            text="我要去干什么来着？",
            recent_messages=recent,
            conversation_summary=summary,
            conversation_state={},
            interaction_frame=frame,
            selected_memories=[],
        )

        self.assertEqual(pack["active_scene_facts"][-1]["value"], "吃饭")
        self.assertEqual(pack["current_reply_focus"], "用户刚才说要去吃饭")
        self.assertIn("吃饭", pack["high_priority_context"])
        self.assertNotIn("做不到", pack["high_priority_context"])
        self.assertIn("做不到", pack["low_priority_background"])
        self.assertIn("只能当背景", pack["summary_policy"])

    def test_current_activity_probe_uses_latest_game_context(self):
        recent = [
            {"role": "user", "content": "我在打游戏"},
            {"role": "assistant", "content": "打什么游戏呀，我也想看看。"},
            {"role": "user", "content": "和平精英"},
            {"role": "assistant", "content": "哦 在打和平精英啊？"},
            {"role": "user", "content": "对呀"},
            {"role": "assistant", "content": "真好"},
        ]
        frame = build_interaction_frame("所以我问你我在干什么", recent, {}, [])

        pack = build_context_pack(
            text="所以我问你我在干什么",
            recent_messages=recent,
            conversation_summary={"rollingSummary": "旧话题：还是做不到稳定"},
            conversation_state={},
            interaction_frame=frame,
            selected_memories=[],
        )

        self.assertEqual(pack["active_scene_facts"][-1]["value"], "打游戏")
        self.assertIn("和平精英", pack["high_priority_context"])
        self.assertNotIn("稳定", pack["high_priority_context"])
        self.assertEqual(pack["current_reply_focus"], "用户在问自己当前/刚才在做什么")


if __name__ == "__main__":
    unittest.main()
