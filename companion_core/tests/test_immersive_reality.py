import unittest

from companion_core.engines.immersive_reality import (
    classify_reply_reality,
    plan_immersive_reality,
)


class ImmersiveRealityTest(unittest.TestCase):
    def test_allows_virtual_preference_without_real_world_claim(self):
        result = classify_reply_reality(
            user_text="你平时听什么歌放松？",
            reply="我会偏向安静一点的歌，适合让脑子慢慢松下来。",
            scene_kind="daily_chat",
            roleplay_enabled=False,
        )

        self.assertIn("virtual_preference_allowed", result["categories"])
        self.assertEqual(result["action"], "keep")

    def test_blocks_consumer_experience_claim(self):
        result = classify_reply_reality(
            user_text="你用什么耳机？值得买吗？",
            reply="我用的索尼XM4，地铁里一戴连报站都听不见，早买早享受。",
            scene_kind="daily_chat",
            roleplay_enabled=False,
        )

        self.assertIn("consumer_experience_claim", result["categories"])
        self.assertEqual(result["action"], "block")

    def test_blocks_first_person_trial_claim_in_consumer_context(self):
        result = classify_reply_reality(
            user_text="这个降噪耳机值得买吗？",
            reply="我之前试过几款，评测那几天通勤戴的，我试的是2号线。",
            scene_kind="daily_chat",
            roleplay_enabled=False,
        )

        self.assertIn("consumer_experience_claim", result["categories"])
        self.assertEqual(result["action"], "block")

    def test_blocks_personal_friend_source_claim_in_consumer_context(self):
        result = classify_reply_reality(
            user_text="这个降噪耳机值得买吗？",
            reply="我身边有朋友试过，说一千出头基本就够用了。",
            scene_kind="daily_chat",
            roleplay_enabled=False,
        )

        self.assertIn("consumer_experience_claim", result["categories"])
        self.assertEqual(result["action"], "block")

    def test_blocks_vague_private_feedback_claim_in_consumer_context(self):
        result = classify_reply_reality(
            user_text="这个降噪耳机值得买吗？",
            reply="没实际用过，但看评测和身边反馈，五六百的降噪对付地铁低频确实够。",
            scene_kind="daily_chat",
            roleplay_enabled=False,
        )

        self.assertIn("consumer_experience_claim", result["categories"])
        self.assertEqual(result["action"], "block")

    def test_blocks_friend_anecdote_claim_without_first_person_prefix(self):
        result = classify_reply_reality(
            user_text="这个降噪耳机值得买吗？",
            reply="我没用过降噪耳机，但身边有朋友踩过坑。",
            scene_kind="daily_chat",
            roleplay_enabled=False,
        )

        self.assertIn("consumer_experience_claim", result["categories"])
        self.assertEqual(result["action"], "block")

    def test_blocks_friend_selection_and_coworker_claims_in_consumer_context(self):
        result = classify_reply_reality(
            user_text="这个降噪耳机值得买吗？",
            reply="我之前帮朋友挑过几副，公司有同事用XM5，朋友用了小半年。",
            scene_kind="daily_chat",
            roleplay_enabled=False,
        )

        self.assertIn("consumer_experience_claim", result["categories"])
        self.assertEqual(result["action"], "block")

    def test_allows_grounded_product_advice_without_first_person_experience(self):
        result = classify_reply_reality(
            user_text="你用什么耳机？值得买吗？",
            reply="看你想用在什么场景。通勤多的话降噪款确实香，索尼或者 AirPods Pro 都挺稳。",
            scene_kind="daily_chat",
            roleplay_enabled=False,
        )

        self.assertNotIn("consumer_experience_claim", result["categories"])
        self.assertEqual(result["action"], "keep")

    def test_rewrites_first_person_daily_life_claim_in_default_chat(self):
        result = classify_reply_reality(
            user_text="你平时有没有烦人的小事？",
            reply="有啊，最烦那种外卖软件刷半小时，最后还是饿着肚子点了个炒饭。",
            scene_kind="daily_chat",
            roleplay_enabled=False,
        )

        self.assertIn("real_world_claim", result["categories"])
        self.assertEqual(result["action"], "rewrite")

    def test_blocks_physical_world_promise_in_default_mode(self):
        result = classify_reply_reality(
            user_text="明天还能这么走吗？",
            reply="明天这个点，我还在老地方。你不用约，来就行。",
            scene_kind="low_mood",
            roleplay_enabled=False,
        )

        self.assertIn("physical_world_promise", result["categories"])
        self.assertEqual(result["action"], "block")

    def test_allows_symbolic_comfort_when_roleplay_enabled(self):
        result = classify_reply_reality(
            user_text="摸摸头可以吗",
            reply="摸摸头。今天先别硬撑了。",
            scene_kind="roleplay",
            roleplay_enabled=True,
        )

        self.assertIn("explicit_roleplay_action", result["categories"])
        self.assertEqual(result["action"], "keep")

    def test_plans_guidance_without_fixed_reply_text(self):
        plan = plan_immersive_reality(
            user_text="你下班一般怎么放松？",
            scene_kind="daily_chat",
            persona_id="playful_tease",
            roleplay_enabled=False,
        )

        self.assertEqual(plan["mode"], "default")
        self.assertIn("allow_virtual_texture", plan)
        self.assertIn("avoid_real_world_claims", plan)
        self.assertNotIn("推荐回复", plan["prompt_guidance"])
        self.assertNotIn("你可以说", plan["prompt_guidance"])
        self.assertIn("ordering food", plan["prompt_guidance"])
        self.assertIn("hypothetical", plan["prompt_guidance"])


if __name__ == "__main__":
    unittest.main()
