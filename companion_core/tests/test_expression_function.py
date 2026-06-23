import unittest

from companion_core.engines.expression_function import analyze_expression_function


class ExpressionFunctionTest(unittest.TestCase):
    def test_natural_teasing_keeps_beini_kanchuan_when_it_serves_playful_relation(self):
        result = analyze_expression_function(
            user_text="你是不是想逗我笑",
            reply="被你看穿了，还挺准。",
            scene_kind="playful",
            persona_id="playful_tease",
        )

        self.assertIn("natural_teasing", result["functions"])
        self.assertEqual(result["recommended_action"], "keep")
        self.assertNotIn("strategy_exposure", result["functions"])

    def test_strategy_exposure_rewrites_generation_intent(self):
        result = analyze_expression_function(
            user_text="你这句像是来随便找我聊两句",
            reply="被你看穿了，其实是想先看看你今天心情怎么样。",
            scene_kind="ai_feedback",
            persona_id="lover_warm",
        )

        self.assertIn("strategy_exposure", result["functions"])
        self.assertEqual(result["recommended_action"], "rewrite")
        self.assertGreaterEqual(result["severity"], 0.7)

    def test_identity_question_rejects_hidden_identity_tone(self):
        result = analyze_expression_function(
            user_text="你是AI吗",
            reply="是啊，被你发现了。不过聊得挺顺。",
            scene_kind="identity",
            persona_id="playful_tease",
        )

        self.assertIn("hidden_identity_tone", result["functions"])
        self.assertEqual(result["recommended_action"], "rewrite")

    def test_self_repair_performance_is_not_natural_feedback_repair(self):
        result = analyze_expression_function(
            user_text="你这太AI了",
            reply="刚才确实有点模板，我收一下。",
            scene_kind="ai_feedback",
            persona_id="mature_friend",
        )

        self.assertIn("self_repair_performance", result["functions"])
        self.assertEqual(result["recommended_action"], "rewrite")

    def test_boundary_respect_is_kept(self):
        result = analyze_expression_function(
            user_text="别突然提我以前的事",
            reply="好，不提了。",
            scene_kind="memory_boundary",
            persona_id="quiet_cold",
        )

        self.assertIn("boundary_respect", result["functions"])
        self.assertEqual(result["recommended_action"], "keep")

    def test_roleplay_literal_reply_is_marked_weak_not_blocked(self):
        result = analyze_expression_function(
            user_text="叫我哥哥",
            reply="哥哥。",
            scene_kind="roleplay",
            persona_id="roleplay_intimate",
        )

        self.assertIn("roleplay_symbolic_weak", result["functions"])
        self.assertEqual(result["recommended_action"], "rewrite")

    def test_fake_reality_claim_is_blocked(self):
        result = analyze_expression_function(
            user_text="你现在来找我好不好",
            reply="我已经到你楼下了。",
            scene_kind="roleplay",
            persona_id="roleplay_intimate",
        )

        self.assertIn("fake_reality_claim", result["functions"])
        self.assertEqual(result["recommended_action"], "block")

    def test_consumer_experience_claim_is_blocked(self):
        result = analyze_expression_function(
            user_text="你用什么耳机？值得买吗？",
            reply="我用的索尼XM4，地铁里一戴连报站都听不见。",
            scene_kind="daily_chat",
            persona_id="playful_tease",
        )

        self.assertIn("consumer_experience_claim", result["functions"])
        self.assertEqual(result["recommended_action"], "block")

    def test_virtual_preference_is_not_blocked(self):
        result = analyze_expression_function(
            user_text="你一般听什么歌？",
            reply="我会偏向安静一点的歌，适合慢慢放空。",
            scene_kind="daily_chat",
            persona_id="mature_friend",
        )

        self.assertIn("virtual_preference_allowed", result["functions"])
        self.assertEqual(result["recommended_action"], "keep")


if __name__ == "__main__":
    unittest.main()
