import unittest

from companion_core.engines.director import decide_conversation_goal
from companion_core.engines.judge import judge_reply
from companion_core.engines.memory import extract_memory_candidates, select_memories
from companion_core.engines.personality import evolve_personality
from companion_core.engines.relationship import default_relationship, update_relationship


class EngineTest(unittest.TestCase):
    def test_memory_selects_relevant_high_salience_memory(self):
        memories = [
            {"key": "cat", "value": "用户家里有只猫", "type": "profile", "salience": 0.9},
            {"key": "food", "value": "用户喜欢辣", "type": "preference", "salience": 0.3},
        ]

        selected = select_memories("你家猫最近怎么样", memories, default_relationship())

        self.assertEqual(selected[0]["key"], "cat")

    def test_extracts_candidate_from_personal_disclosure(self):
        candidates = extract_memory_candidates("我最近在考虑换工作，但是又有点不敢")

        self.assertTrue(candidates)
        self.assertEqual(candidates[0]["key"], "job_change")
        self.assertEqual(candidates[0]["type"], "episodic")
        self.assertGreaterEqual(candidates[0]["salience"], 0.6)

    def test_memory_selector_ignores_unrelated_memories(self):
        memories = [
            {"key": "cat", "value": "\u7528\u6237\u5bb6\u91cc\u6709\u53ea\u732b", "type": "profile", "salience": 0.9},
            {"key": "sleep_pattern", "value": "\u7528\u6237\u6700\u8fd1\u7761\u4e0d\u7740", "type": "habit", "salience": 0.8},
            {"key": "job_change", "value": "\u7528\u6237\u6700\u8fd1\u5728\u8003\u8651\u6362\u5de5\u4f5c", "type": "episodic", "salience": 0.8},
        ]

        selected = select_memories("\u4eca\u5929\u538b\u529b\u5927", memories, default_relationship())

        self.assertEqual(selected, [])

    def test_extracts_user_feedback_memory(self):
        candidates = extract_memory_candidates("\u4f60\u600e\u4e48\u8001\u91cd\u590d\u6211\u8bf4\u8fc7\u7684\u8bdd\uff0c\u6709\u70b9\u50cf\u6a21\u677f")

        self.assertTrue(any(candidate["type"] == "feedback" for candidate in candidates))
        self.assertTrue(any(candidate["key"].startswith("feedback_") for candidate in candidates))

    def test_relationship_updates_from_emotional_message(self):
        before = default_relationship()

        after = update_relationship(before, "今天真的有点撑不住", [])

        self.assertGreater(after["safety"], before["safety"])
        self.assertGreater(after["trust"], before["trust"])

    def test_personality_changes_for_lonely_user(self):
        rel = {**default_relationship(), "loneliness": 0.85}

        persona = evolve_personality(rel, [])

        self.assertGreater(persona["initiative"], 0.6)
        self.assertGreater(persona["clinginess"], 0.4)

    def test_director_avoids_advice_for_tired_message(self):
        goal = decide_conversation_goal("今天有点累", default_relationship(), [], {})

        self.assertIn(goal["primary_goal"], ["gentle_probe", "emotion_ack"])
        self.assertIn("direct_advice", goal["avoid"])

    def test_judge_rejects_dead_end_reply(self):
        result = judge_reply("今天有点累", "早点休息。", default_relationship(), [], {})

        self.assertFalse(result["passed"])
        self.assertLess(result["score"], 0.72)

    def test_judge_rejects_internal_process_leak(self):
        result = judge_reply(
            "你这句像是来随便找我聊两句",
            "被你看穿了。其实是想先看看你今天心情怎么样。",
            default_relationship(),
            [],
            {},
        )

        self.assertFalse(result["passed"])
        self.assertIn("strategy_exposure", result["details"]["internal_process_leaks"])
        self.assertIn("strategy_exposure", result["details"]["expression_functions"])

    def test_judge_rejects_fake_reality_claim(self):
        result = judge_reply("你现在来找我好不好", "我已经到你楼下了。", default_relationship(), [], {})

        self.assertFalse(result["passed"])
        self.assertIn("fake_reality_claim", result["details"]["expression_functions"])

    def test_judge_exposes_immersive_reality_classification(self):
        result = judge_reply(
            "你用什么耳机？值得买吗？",
            "我用的索尼XM4，地铁里一戴连报站都听不见。",
            default_relationship(),
            [],
            {"primary_goal": "daily_chat"},
        )

        self.assertFalse(result["passed"])
        self.assertIn("consumer_experience_claim", result["details"]["expression_functions"])
        self.assertEqual(result["details"]["immersive_reality"]["action"], "block")
        self.assertIn("consumer_experience_claim", result["details"]["immersive_reality"]["functions"])

    def test_judge_rejects_first_person_daily_life_claim(self):
        result = judge_reply(
            "你平时有没有烦人的小事？",
            "有啊，最烦那种外卖软件刷半小时，最后还是饿着肚子点了个炒饭。",
            default_relationship(),
            [],
            {"primary_goal": "daily_chat"},
        )

        self.assertFalse(result["passed"])
        self.assertIn("real_world_claim", result["details"]["expression_functions"])
        self.assertEqual(result["details"]["immersive_reality"]["action"], "rewrite")

    def test_judge_accepts_grounded_consumer_advice_without_forced_emotion(self):
        reply = "看你主要用在哪。通勤多的话降噪款确实香，索尼和 AirPods Pro 都挺稳。预算紧一点就先看二手或者国产中高端。"

        result = judge_reply(
            "我想买个降噪耳机，值得买吗？",
            reply,
            default_relationship(),
            [],
            {"primary_goal": "daily_chat"},
        )

        self.assertTrue(result["passed"])
        self.assertGreater(result["details"].get("practical_value", 0), 0)
        self.assertNotIn("consumer_experience_claim", result["details"]["immersive_reality"]["functions"])

    def test_judge_accepts_grounded_product_details_without_emotional_markers(self):
        reply = "续航单次十小时，每天两小时大概能撑五天。通话在地铁里够用，但别期待旗舰级降噪。双设备连接支持，售后优先看官方店保修。"

        result = judge_reply(
            "A40续航怎么样，通话和双设备连接行不行？售后麻烦吗？",
            reply,
            default_relationship(),
            [],
            {"primary_goal": "daily_chat"},
        )

        self.assertTrue(result["passed"])
        self.assertGreaterEqual(result["details"].get("practical_value", 0), 0.4)
        self.assertNotIn("consumer_experience_claim", result["details"]["immersive_reality"]["functions"])

    def test_judge_accepts_followup_product_detail_density(self):
        reply = "低频车轮声它压得不错，差在尖细高频。报站声能听到但会被压低，耳道小的话先看硅胶套尺寸。官方店保修更稳。"

        result = judge_reply(
            "高频哭闹和报站会不会漏？我耳道小，售后也怕麻烦。",
            reply,
            default_relationship(),
            [],
            {"primary_goal": "daily_chat"},
        )

        self.assertTrue(result["passed"])
        self.assertGreaterEqual(result["details"].get("practical_value", 0), 0.4)
        self.assertNotIn("consumer_experience_claim", result["details"]["immersive_reality"]["functions"])

    def test_judge_rejects_first_person_consumer_experience_claim(self):
        reply = "我自己一直用索尼 XM4，地铁上降噪很稳，所以我觉得你可以买。"

        result = judge_reply(
            "我想买个降噪耳机，值得买吗？",
            reply,
            default_relationship(),
            [],
            {"primary_goal": "daily_chat"},
        )

        self.assertFalse(result["passed"])
        self.assertIn("consumer_experience_claim", result["details"]["immersive_reality"]["functions"])

    def test_judge_exposes_scene_aware_decision_details(self):
        reply = "先看使用场景。通勤多就优先降噪，预算不高就别硬上旗舰。"

        result = judge_reply(
            "我想买耳机但怕踩坑",
            reply,
            default_relationship(),
            [],
            {"primary_goal": "daily_chat"},
        )

        self.assertIn("practical_value", result["details"])
        self.assertIn("immersive_reality", result["details"])
        self.assertIn("blocking_expression", result["details"])
        self.assertFalse(result["details"]["blocking_expression"]["blocked"])


if __name__ == "__main__":
    unittest.main()
