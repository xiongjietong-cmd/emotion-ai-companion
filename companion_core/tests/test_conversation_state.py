import unittest

from companion_core.engines.conversation_state import update_conversation_state


U_EMPTY = "\u4eca\u5929\u6709\u70b9\u7a7a"
U_NOT_IDLE = "\u4e0d\u662f\u6709\u7a7a\u7684\u610f\u601d\u2026\u2026\u5c31\u662f\u5fc3\u91cc\u6709\u70b9\u7a7a"
U_MOMENTS = "\u55ef\uff0c\u4e5f\u4e0d\u662f\u96be\u8fc7\uff0c\u5c31\u662f\u5237\u5b8c\u670b\u53cb\u5708\u66f4\u7a7a\u4e86"
U_THAT = "\u5bf9\uff0c\u5c31\u662f\u8fd9\u79cd\u611f\u89c9"
U_DONT_ASK = "\u4f60\u522b\u4e00\u76f4\u95ee"
U_HMM = "\u55ef"
U_REMEMBER = "\u90a3\u4f60\u8fd8\u8bb0\u5f97\u6211\u521a\u624d\u8bf4\u7684\u662f\u5565\u5417"
U_BEGINNING = "\u4e0d\u662f\u8fd9\u4e2a\uff0c\u6211\u662f\u8bf4\u4e00\u5f00\u59cb\u90a3\u4e2a"


class ConversationStateTest(unittest.TestCase):
    def test_tracks_emotional_core_across_recall_repair(self):
        recent = [
            {"role": "user", "content": U_EMPTY},
            {
                "role": "assistant",
                "content": "\u90a3\u6b63\u597d\uff0c\u53ef\u4ee5\u6162\u60a0\u60a0\u5730\u505a\u70b9\u60f3\u505a\u7684\u4e8b\u3002",
            },
            {"role": "user", "content": U_NOT_IDLE},
            {"role": "assistant", "content": "\u55ef\uff0c\u90a3\u79cd\u7a7a\u843d\u843d\u7684\u611f\u89c9\uff0c\u6211\u61c2\u3002"},
            {"role": "user", "content": U_MOMENTS},
            {
                "role": "assistant",
                "content": "\u55ef\uff0c\u522b\u4eba\u7684\u70ed\u95f9\u770b\u591a\u4e86\uff0c\u5bb9\u6613\u653e\u5927\u81ea\u5df1\u7684\u5b89\u9759\u3002",
            },
            {"role": "user", "content": U_THAT},
            {
                "role": "assistant",
                "content": "\u55ef\uff0c\u5b89\u9759\u672c\u8eab\u5e76\u4e0d\u574f\u3002\u53ea\u662f\u6709\u65f6\u5019\u9700\u8981\u4e00\u70b9\u65f6\u95f4\uff0c\u8ba9\u5b83\u91cd\u65b0\u53d8\u5f97\u8212\u670d\u3002\u4eca\u5929\u6709\u505a\u4ec0\u4e48\u8ba9\u81ea\u5df1\u5b89\u9759\u4e0b\u6765\u7684\u5c0f\u4e8b\u5417\uff1f",
            },
            {"role": "user", "content": U_DONT_ASK},
            {"role": "assistant", "content": "\u55ef\uff0c\u597d\uff0c\u4e0d\u95ee\u4e86\u3002"},
            {"role": "user", "content": U_HMM},
            {"role": "assistant", "content": "\u55ef\uff0c\u4e0d\u6253\u6270\u3002"},
            {"role": "user", "content": U_REMEMBER},
            {
                "role": "assistant",
                "content": "\u55ef\uff0c\u8bb0\u5f97\u3002\u4f60\u8bf4\u201c\u5bf9\uff0c\u5c31\u662f\u8fd9\u79cd\u611f\u89c9\u201d\uff0c\u7136\u540e\u8ba9\u6211\u522b\u4e00\u76f4\u95ee\u3002",
            },
        ]

        state = update_conversation_state(U_BEGINNING, recent)

        self.assertIn("\u5fc3\u91cc\u7a7a", state["active_topic"])
        self.assertIn("\u670b\u53cb\u5708", state["active_topic"])
        self.assertIn("\u4e0d\u8981\u4e00\u76f4\u8ffd\u95ee", state["user_boundary"])
        self.assertIn("\u6700\u8fd1\u4e00\u53e5", state["last_ai_mistake"])
        self.assertIn("\u670b\u53cb\u5708", state["next_reply_task"])
        self.assertIn("\u4e0d\u8981\u8ffd\u95ee", state["next_reply_task"])
        self.assertIn("\u4e0d\u8981\u8ba9\u7528\u6237\u91cd\u590d", state["next_reply_task"])
        self.assertEqual(state["user_patience"], "low")

    def test_short_emotional_word_is_not_free_time_after_correction(self):
        recent = [
            {"role": "user", "content": U_EMPTY},
            {
                "role": "assistant",
                "content": "\u90a3\u6b63\u597d\uff0c\u53ef\u4ee5\u6162\u60a0\u60a0\u5730\u505a\u70b9\u60f3\u505a\u7684\u4e8b\u3002",
            },
            {"role": "user", "content": U_NOT_IDLE},
        ]

        state = update_conversation_state(U_MOMENTS, recent)

        self.assertIn("\u5fc3\u91cc\u7a7a", state["active_topic"])
        self.assertIn("\u7a7a\u843d", state["emotional_thread"])
        self.assertNotIn("\u7a7a\u95f2", state["active_topic"])

    def test_boundary_reduces_questioning(self):
        recent = [
            {"role": "user", "content": "\u6211\u4eca\u5929\u538b\u529b\u6709\u70b9\u5927"},
            {"role": "assistant", "content": "\u8981\u4e0d\u8981\u8bf4\u8bf4\u53d1\u751f\u4e86\u4ec0\u4e48\uff1f"},
            {"role": "user", "content": U_DONT_ASK},
        ]

        state = update_conversation_state(U_HMM, recent)

        self.assertIn("\u4e0d\u8981\u4e00\u76f4\u8ffd\u95ee", state["user_boundary"])
        self.assertIn("\u5c11\u95ee", state["next_reply_task"])
        self.assertEqual(state["user_patience"], "low")

    def test_tracks_changeable_situational_fact_without_fixed_answer(self):
        recent = [
            {"role": "user", "content": "\u5728"},
            {"role": "assistant", "content": "\u5728\u5462\u3002"},
            {"role": "user", "content": "\u5e72\u5565\u5462"},
            {"role": "assistant", "content": "\u6ca1\u5e72\u561b\uff0c\u5c31\u53d1\u5446\u5462\u3002"},
            {"role": "user", "content": "\u6211\u5728\u4e0a\u8bfe"},
            {"role": "assistant", "content": "\u597d\u561e\uff0c\u4f60\u5148\u4e13\u5fc3\u4e0a\u8bfe\u3002"},
            {"role": "user", "content": "\u4f60\u77e5\u9053\u6211\u73b0\u5728\u5728\u5e72\u4ec0\u4e48\u5417"},
            {"role": "assistant", "content": "\u6b63\u5728\u731c\u662f\u53d1\u5446\uff0c\u8fd8\u662f\u5728\u5077\u5403\u4ec0\u4e48\u4e1c\u897f\u3002"},
            {"role": "user", "content": "\u6211\u4e0d\u662f\u8ddf\u4f60\u8bf4\u6211\u5728\u4e0a\u8bfe\u5417"},
        ]

        state = update_conversation_state("\u90a3\u6211\u518d\u95ee\u4f60\u6211\u5728\u5e72\u4ec0\u4e48", recent)

        facts = state["situational_facts"]
        self.assertEqual(facts[-1]["kind"], "activity")
        self.assertEqual(facts[-1]["value"], "\u4e0a\u8bfe")
        self.assertEqual(facts[-1]["source"], "user_stated")
        self.assertTrue(facts[-1]["changeable"])
        self.assertIn("\u4e0a\u8bfe", state["next_reply_task"])
        self.assertIn("\u4e0d\u8981\u4e71\u731c", state["next_reply_task"])
        self.assertNotIn("\u5fc5\u987b\u56de\u7b54", state["next_reply_task"])


if __name__ == "__main__":
    unittest.main()
