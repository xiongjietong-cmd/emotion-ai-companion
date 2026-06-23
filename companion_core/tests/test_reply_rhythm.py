import unittest

from companion_core.engines.reply_rhythm import decide_reply_rhythm, split_reply_parts


class ReplyRhythmTest(unittest.TestCase):
    def test_lonely_user_allows_more_message_parts(self):
        rhythm = decide_reply_rhythm(
            user_text="\u4eca\u5929\u6709\u70b9\u5b64\u72ec\uff0c\u60f3\u627e\u4eba\u8bf4\u8bf4\u8bdd",
            relationship={"loneliness": 0.8, "attachment": 0.7, "safety": 0.7},
        )

        self.assertEqual(rhythm["profile"], "attached")
        self.assertEqual(rhythm["max_parts"], 4)

    def test_irritated_user_gets_quieter_rhythm(self):
        rhythm = decide_reply_rhythm(
            user_text="\u522b\u70e6\u6211\uff0c\u4e0d\u60f3\u804a",
            relationship={"loneliness": 0.2, "activity": 0.2},
        )

        self.assertEqual(rhythm["profile"], "quiet")
        self.assertEqual(rhythm["max_parts"], 2)

    def test_playful_user_keeps_lively_rhythm(self):
        rhythm = decide_reply_rhythm(
            user_text="\u54c8\u54c8\u54c8\u4f60\u4e5f\u592a\u79bb\u8c31\u4e86",
            relationship={"humor": 0.8, "activity": 0.8},
        )

        self.assertEqual(rhythm["profile"], "playful")
        self.assertEqual(rhythm["max_parts"], 4)

    def test_split_uses_rhythm_max_parts(self):
        reply = (
            "\u6211\u542c\u89c1\u4f60\u8fd9\u53e5\u8bdd\u91cc\u6709\u70b9\u5b64\u5355\u3002"
            "\u4f60\u4eca\u5929\u662f\u4e0d\u662f\u6491\u4e86\u5f88\u4e45\uff1f"
            "\u6211\u60f3\u5148\u966a\u4f60\u5750\u4e00\u4f1a\u513f\u3002"
            "\u4f60\u53ef\u4ee5\u6162\u6162\u8bf4\u3002"
        )

        quiet_parts = split_reply_parts(reply, {"profile": "quiet", "max_parts": 2})
        attached_parts = split_reply_parts(reply, {"profile": "attached", "max_parts": 4})

        self.assertEqual(len(quiet_parts), 2)
        self.assertEqual(len(attached_parts), 4)


if __name__ == "__main__":
    unittest.main()
