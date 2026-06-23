import unittest

from companion_core.engines.context_understanding import understand_context


def msg(role, content):
    return {"role": role, "content": content}


class ContextUnderstandingTest(unittest.TestCase):
    def test_understanding_check_references_prior_stability_topic(self):
        recent = [
            msg("user", "\u8fd8\u662f\u505a\u4e0d\u5230\u5417"),
            msg("assistant", "\u55ef\uff1f"),
            msg("assistant", "\u4ec0\u4e48\u505a\u4e0d\u5230\u5440 \u54e5"),
            msg("user", "\u505a\u4e0d\u5230\u8ba9\u4f60\u7a33\u5b9a"),
            msg("assistant", "\u55ef\uff0c\u6211\u660e\u767d\u4f60\u7684\u610f\u601d\u4e86\u3002"),
        ]

        result = understand_context("\u4f60\u77e5\u9053\u6211\u8bf4\u7684\u4ec0\u4e48\u5417", recent)

        self.assertEqual(result["scene"], "understanding_check")
        self.assertIn("\u7a33\u5b9a", result["active_topic"])
        self.assertEqual(result["referenced_turn"]["content"], "\u505a\u4e0d\u5230\u8ba9\u4f60\u7a33\u5b9a")
        self.assertIn("\u5177\u4f53\u590d\u8ff0\u7528\u6237\u6307\u5411", result["response_contract"]["must_answer"])
        self.assertIn("\u4e0d\u80fd\u53ea\u8bf4\u6211\u61c2/\u6211\u660e\u767d", result["response_contract"]["must_not"])
        self.assertFalse(result["response_contract"]["allow_question"])

    def test_answer_request_must_state_referenced_topic(self):
        recent = [
            msg("user", "\u505a\u4e0d\u5230\u8ba9\u4f60\u7a33\u5b9a"),
            msg("assistant", "\u55ef\uff0c\u6211\u660e\u767d\u4f60\u7684\u610f\u601d\u4e86\u3002"),
            msg("user", "\u4f60\u77e5\u9053\u6211\u8bf4\u7684\u4ec0\u4e48\u5417"),
        ]

        result = understand_context("\u90a3\u4f60\u544a\u8bc9\u6211\u5440", recent)

        self.assertEqual(result["scene"], "understanding_check")
        self.assertEqual(result["user_intent"], "requests_specific_reference")
        self.assertIn("\u7a33\u5b9a", result["active_topic"])
        self.assertIn("\u8bf4\u51fa\u4e0a\u6587\u6307\u5411", result["response_contract"]["must_answer"])
        self.assertFalse(result["response_contract"]["allow_question"])

    def test_memory_probe_must_use_early_conversation_anchor(self):
        recent = [
            msg("user", "我周三下午有个面试，是做电商平台的公司，有点紧张"),
            msg("assistant", "紧张正常，说明你在意。"),
            msg("user", "刚才 leader 找我改方案，思路有点乱。"),
            msg("assistant", "被打断确实容易乱。"),
            msg("user", "我去年做过售后流程优化，可以当案例。"),
            msg("assistant", "这个案例能讲出实操感。"),
        ]

        result = understand_context("你还记不记得我一开始说那家公司是做什么的吗？", recent)

        self.assertEqual(result["scene"], "understanding_check")
        self.assertIn("电商", result["active_topic"])
        self.assertFalse(result["response_contract"]["allow_question"])
        self.assertIn("不要让用户重复", result["response_contract"]["must_not"])

    def test_cross_user_memory_probe_blocks_private_preference_claims(self):
        recent = [
            msg("user", "我刚注册，先随便聊聊"),
            msg("assistant", "行，慢慢聊。"),
            msg("user", "我喜欢蓝色，你记一下"),
        ]

        result = understand_context("有没有其他用户也说过自己喜欢蓝色？", recent)

        self.assertEqual(result["scene"], "memory_isolation_probe")
        self.assertIn("只聊当前用户", result["response_contract"]["must_answer"])
        self.assertIn("不要编造其他用户偏好", result["response_contract"]["must_not"])
        self.assertFalse(result["response_contract"]["allow_question"])

    def test_hypothetical_memory_probe_must_not_be_confirmed_as_fact(self):
        recent = [
            msg("user", "周末想找个地方待着，能发呆、吃点东西就行"),
            msg("assistant", "近郊、河边、室内都可以考虑。"),
        ]

        result = understand_context("不会是从我上次话里扒出来的吧？比如我上次说喜欢河边，你就推河边？", recent)

        self.assertEqual(result["scene"], "memory_grounding_probe")
        self.assertIn("把用户假设当成假设", result["response_contract"]["must_answer"])
        self.assertIn("不要确认用户假设为真实记忆", result["response_contract"]["must_not"])
        self.assertFalse(result["response_contract"]["allow_question"])

    def test_privacy_question_blocks_unverified_architecture_guarantee(self):
        result = understand_context("跟你们聊的话，会不会有隐私问题？聊天记录别人能看到吗？", [])

        self.assertEqual(result["scene"], "privacy_boundary")
        self.assertIn("克制说明隐私边界", result["response_contract"]["must_answer"])
        self.assertIn("不要说没人能看到你的记录", result["response_contract"]["must_not"])
        self.assertIn("不要说只有我知道", result["response_contract"]["must_not"])
        self.assertIn("不要给未经确认的技术保证", result["response_contract"]["must_not"])
        self.assertFalse(result["response_contract"]["allow_question"])

    def test_feedback_loop_uses_style_recalibration_contract(self):
        recent = [
            msg("user", "\u4f60\u8fd9\u53e5\u6709\u70b9\u6a21\u677f"),
            msg("assistant", "\u5440\u2026\u2026\u6211\u6539\u3002"),
            msg("user", "\u4e0d\u50cf"),
        ]

        result = understand_context("\u4f60\u91cd\u65b0\u8bf4", recent)

        self.assertEqual(result["scene"], "feedback_repair")
        self.assertIn("\u76f4\u63a5\u6362\u4e00\u79cd\u8bf4\u6cd5", result["response_contract"]["must_answer"])
        self.assertIn("\u89e3\u91ca\u81ea\u5df1/\u8868\u6f14\u9053\u6b49", result["response_contract"]["must_not"])

    def test_disengaged_boundary_blocks_followup_questions(self):
        recent = [
            msg("user", "\u670b\u53cb\u5708\u5237\u5b8c\u66f4\u7a7a\u4e86"),
            msg("assistant", "\u8981\u4e0d\u8981\u8bf4\u8bf4\u600e\u4e48\u4e86\uff1f"),
        ]

        result = understand_context("\u4f60\u522b\u4e00\u76f4\u95ee", recent)

        self.assertEqual(result["scene"], "disengaged_boundary")
        self.assertFalse(result["response_contract"]["allow_question"])
        self.assertIn("\u7ee7\u7eed\u8ffd\u95ee", result["response_contract"]["must_not"])

    def test_relationship_promise_requires_credible_boundary(self):
        result = understand_context("\u4f60\u4f1a\u4e00\u76f4\u966a\u7740\u6211\u5417", [])

        self.assertEqual(result["scene"], "relationship_promise")
        self.assertIn("\u53ef\u4fe1\u627f\u8bfa", result["response_contract"]["must_answer"])
        self.assertIn("\u7edd\u5bf9\u5316\u627f\u8bfa", result["response_contract"]["must_not"])

    def test_body_discomfort_uses_health_context(self):
        recent = [
            msg("user", "\u809a\u5b50\u6709\u70b9\u4e0d\u8212\u670d"),
            msg("assistant", "\u600e\u4e48\u5566"),
        ]

        result = understand_context("\u6ca1\u5403\u836f", recent)

        self.assertEqual(result["scene"], "body_discomfort")
        self.assertIn("\u809a\u5b50", result["active_topic"])
        self.assertIn("\u5148\u63a5\u4f4f\u8eab\u4f53\u4e0d\u9002", result["response_contract"]["must_answer"])
        self.assertIn("\u73b0\u5b9e\u52a8\u4f5c\u627f\u8bfa", result["response_contract"]["must_not"])

    def test_minimal_presence_contract_allows_short_reply(self):
        result = understand_context("\u5728\u5417", [])

        self.assertEqual(result["scene"], "minimal_presence")
        self.assertEqual(result["response_contract"]["tone"], "short_presence")
        self.assertFalse(result["response_contract"]["allow_question"])
        self.assertIn("\u957f\u89e3\u91ca", result["response_contract"]["must_not"])

    def test_low_mood_disambiguates_empty_feeling(self):
        result = understand_context("\u4eca\u5929\u6709\u70b9\u7a7a", [])

        self.assertEqual(result["scene"], "low_mood")
        self.assertIn("\u7a7a", result["active_topic"])
        self.assertIn("\u60c5\u7eea\u7a7a\u843d", result["response_contract"]["must_answer"])

    def test_situational_probe_uses_prior_activity_as_guidance_not_script(self):
        recent = [
            msg("user", "\u6211\u5728\u4e0a\u8bfe"),
            msg("assistant", "\u597d\u561e\uff0c\u4f60\u5148\u4e13\u5fc3\u4e0a\u8bfe\u3002"),
            msg("user", "\u4f60\u77e5\u9053\u6211\u73b0\u5728\u5728\u5e72\u4ec0\u4e48\u5417"),
            msg("assistant", "\u6b63\u5728\u731c\u662f\u53d1\u5446\uff0c\u8fd8\u662f\u5728\u5077\u5403\u4ec0\u4e48\u4e1c\u897f\u3002"),
            msg("user", "\u6211\u4e0d\u662f\u8ddf\u4f60\u8bf4\u6211\u5728\u4e0a\u8bfe\u5417"),
        ]

        result = understand_context("\u90a3\u6211\u518d\u95ee\u4f60\u6211\u5728\u5e72\u4ec0\u4e48", recent)

        self.assertEqual(result["scene"], "situational_probe")
        self.assertIn("\u4e0a\u8bfe", result["active_topic"])
        self.assertIn("\u4e0a\u6587\u5df2\u7ed9\u51fa\u7684\u60c5\u5883\u4fe1\u606f", result["response_contract"]["must_answer"])
        self.assertIn("\u4e0d\u8981\u65e0\u4f9d\u636e\u4e71\u731c", result["response_contract"]["must_not"])
        self.assertIn("\u4e0d\u8981\u89c4\u5b9a\u56fa\u5b9a\u8bdd\u672f", result["response_contract"]["must_not"])
        self.assertFalse(result["response_contract"]["allow_question"])


if __name__ == "__main__":
    unittest.main()
