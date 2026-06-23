import unittest
from unittest.mock import AsyncMock, patch

from fastapi.testclient import TestClient

from companion_core.app import app, _split_reply_parts


class CompanionApiTest(unittest.TestCase):
    def test_split_reply_parts_preserves_model_line_breaks(self):
        parts = _split_reply_parts("first line.\nsecond line still counts.\nthird line?")
        self.assertEqual(parts, ["first line.", "second line still counts.", "third line?"])

    def test_split_reply_parts_breaks_medium_single_line_reply(self):
        reply = "这会儿正瘫在沙发上刷手机呢，顺手点开了你的消息"
        parts = _split_reply_parts(reply)
        self.assertGreaterEqual(len(parts), 2)
        self.assertNotEqual(parts, [reply])

    def test_reply_endpoint_returns_companion_contract_with_model(self):
        client = TestClient(app)
        with patch("companion_core.app.generate_reply", new_callable=AsyncMock) as mocked_generate:
            mocked_generate.return_value = "听起来今天确实挺耗人的。用户最近在考虑换工作这件事，也可以先缓一下。"
            response = client.post("/v1/reply", json={
                "bot_id": "1",
                "user_key": "web-user",
                "channel": "web",
                "text": "今天有点累，还在考虑换工作",
                "recent_messages": [],
                "memories": [
                    {
                        "key": "job_change",
                        "value": "用户最近在考虑换工作",
                        "type": "episodic",
                        "salience": 0.8,
                    }
                ],
                "relationship": {},
            })

        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertTrue(body["reply"])
        self.assertIn("relationship_delta", body)
        self.assertIn("memory_candidates", body)
        self.assertIn("director_goal", body)
        self.assertIn("judge", body)
        self.assertIn("reply_parts", body)
        self.assertGreaterEqual(body["judge"]["score"], 0)
        self.assertLessEqual(body["judge"]["score"], 1)
        self.assertIn(body["director_goal"]["primary_goal"], ["gentle_probe", "emotion_ack", "memory_recall"])
        self.assertIn("safety", body["relationship_delta"])
        self.assertTrue(body["judge"]["passed"])
        self.assertGreaterEqual(body["judge"]["score"], 0.72)
        self.assertGreaterEqual(len(body["reply_parts"]), 2)
        self.assertEqual(body["reply"], "\n".join(body["reply_parts"]))
        self.assertEqual(mocked_generate.await_count, 1)

    def test_reply_endpoint_ignores_relationship_metadata(self):
        client = TestClient(app)
        with patch("companion_core.app.generate_reply", new_callable=AsyncMock) as mocked_generate:
            mocked_generate.return_value = "听起来今天确实挺耗人的，也可以先缓一下。"
            response = client.post("/v1/reply", json={
                "bot_id": "1",
                "user_key": "web-user",
                "channel": "web",
                "text": "今天有点累",
                "recent_messages": [],
                "memories": [],
                "relationship": {
                    "id": 1,
                    "bot_id": 1,
                    "user_key": "web-user",
                    "trust": 0.1,
                    "safety": 0.2,
                    "updated_at": "2026-06-18 00:00:00",
                },
            })

        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertIn("trust", body["relationship_delta"])
        self.assertNotIn("user_key", body["relationship_delta"])
        self.assertNotIn("updated_at", body["relationship_delta"])
        self.assertEqual(mocked_generate.await_count, 1)

    def test_reply_endpoint_returns_503_when_model_is_unavailable(self):
        client = TestClient(app)
        with patch.dict("os.environ", {"DEEPSEEK_API_KEY": ""}):
            response = client.post("/v1/reply", json={
                "bot_id": "1",
                "user_key": "web-user",
                "channel": "web",
                "text": "今天有点累",
                "recent_messages": [],
                "memories": [],
                "relationship": {},
                "provider_config": {},
            })

        self.assertEqual(response.status_code, 503)
        body = response.json()
        self.assertFalse(body["ok"])
        self.assertEqual(body["code"], "MODEL_UNAVAILABLE")

    def test_reply_endpoint_compiles_personality_config_for_generation(self):
        client = TestClient(app)
        with patch("companion_core.app.generate_reply", new_callable=AsyncMock) as mocked_generate:
            mocked_generate.return_value = "行，今天先别跟自己较劲。"
            response = client.post("/v1/reply", json={
                "bot_id": "1",
                "user_key": "web-user",
                "channel": "web",
                "text": "在吗",
                "recent_messages": [],
                "memories": [],
                "relationship": {},
                "personality_config": {
                    "name": "阿言",
                    "speakingStyle": "嘴硬，短句",
                    "customPersona": "清冷但靠得住",
                    "avoidStyle": "不要客服感",
                },
            })

        self.assertEqual(response.status_code, 200)
        kwargs = mocked_generate.await_args.kwargs
        self.assertIn("identity_profile", kwargs)
        self.assertEqual(kwargs["identity_profile"]["name"], "阿言")
        self.assertIn("嘴硬", kwargs["identity_profile"]["speech_style"])

    def test_reply_endpoint_passes_immersive_reality_policy_for_generation(self):
        client = TestClient(app)
        with patch("companion_core.app.generate_reply", new_callable=AsyncMock) as mocked_generate:
            mocked_generate.return_value = "这个我会更建议你先看预算，别被参数带着跑。"
            response = client.post("/v1/reply", json={
                "bot_id": "1",
                "user_key": "web-user",
                "channel": "web",
                "text": "你用什么耳机？值得买吗？",
                "recent_messages": [],
                "memories": [],
                "relationship": {},
                "personality_config": {"id": "playful_tease"},
            })

        self.assertEqual(response.status_code, 200)
        kwargs = mocked_generate.await_args.kwargs
        self.assertIn("immersive_reality", kwargs)
        self.assertEqual(kwargs["immersive_reality"]["mode"], "grounded_advice")
        self.assertTrue(kwargs["immersive_reality"]["strict_grounding"])

    def test_reply_endpoint_builds_context_pack_before_generation(self):
        client = TestClient(app)
        with patch("companion_core.app.generate_reply", new_callable=AsyncMock) as mocked_generate:
            mocked_generate.return_value = "吃饭呢，刚刚自己说的。"
            response = client.post("/v1/reply", json={
                "bot_id": "167",
                "user_key": "wechat-user",
                "channel": "wechat",
                "text": "我要去干什么来着？",
                "recent_messages": [
                    {"role": "user", "content": "我刚起床准备去上课"},
                    {"role": "assistant", "content": "好呢，快去洗漱吧，别迟到啦。"},
                    {"role": "user", "content": "不洗漱了，我要去吃饭饭"},
                    {"role": "assistant", "content": "好嘞，吃吧吃吧～"},
                ],
                "memories": [],
                "relationship": {},
                "conversation_summary": {
                    "rollingSummary": "旧话题：还是做不到 / 做不到让你稳定",
                    "nextReplyTask": "emotion_ack",
                },
            })

        self.assertEqual(response.status_code, 200)
        kwargs = mocked_generate.await_args.kwargs
        self.assertIn("context_pack", kwargs)
        context_pack = kwargs["context_pack"]
        self.assertEqual(context_pack["current_reply_focus"], "用户刚才说要去吃饭")
        self.assertIn("吃饭", context_pack["high_priority_context"])
        self.assertNotIn("做不到", context_pack["high_priority_context"])
        self.assertIn("做不到", context_pack["low_priority_background"])

    def test_reply_endpoint_passes_conversation_act_for_comfort_request(self):
        client = TestClient(app)
        with patch("companion_core.app.generate_reply", new_callable=AsyncMock) as mocked_generate:
            mocked_generate.return_value = "来，抱一下。你已经绷着够久了。"
            response = client.post("/v1/reply", json={
                "bot_id": "167",
                "user_key": "wechat-user",
                "channel": "wechat",
                "text": "安慰安慰我呗",
                "recent_messages": [
                    {"role": "user", "content": "我上课呢"},
                    {"role": "assistant", "content": "好，那你先专心上课。"},
                    {"role": "user", "content": "这个老师特别严格"},
                    {"role": "assistant", "content": "哎呀，那肯定挺累的。"},
                ],
                "memories": [],
                "relationship": {},
            })

        self.assertEqual(response.status_code, 200)
        kwargs = mocked_generate.await_args.kwargs
        self.assertIn("conversation_act", kwargs)
        self.assertEqual(kwargs["conversation_act"]["act"], "seeking_comfort")
        self.assertIn("premature_closure", kwargs["conversation_act"]["avoid"])

    def test_reply_endpoint_repairs_default_identity_when_persona_kernel_disagrees(self):
        client = TestClient(app)
        with patch("companion_core.app.generate_reply", new_callable=AsyncMock) as mocked_generate:
            mocked_generate.side_effect = [
                "我是小暖呀，陪你聊天的那个。",
                "我是小暖呀，陪你聊天的那个。",
            ]
            response = client.post("/v1/reply", json={
                "bot_id": "167",
                "user_key": "wechat-user",
                "channel": "wechat",
                "text": "你是谁",
                "recent_messages": [],
                "memories": [],
                "relationship": {},
                "personality_config": {
                    "identity": {"aiName": "仝雄杰"},
                    "relationshipPosition": "恋人",
                    "customPersona": "温暖，性感，成熟，主动",
                    "speakingStyle": "温柔细腻，偶尔带点俏皮",
                    "speechExamples": ["哥哥，你真的好棒啊今天"],
                },
            })

        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertIn("仝雄杰", body["reply"])
        self.assertNotIn("小暖", body["reply"])
        self.assertIn("persona_consistency", body["judge"]["details"])
        self.assertTrue(body["judge"]["details"]["persona_consistency"]["passed"])

    def test_reply_endpoint_uses_safe_repair_when_rewrite_still_fails(self):
        client = TestClient(app)
        failing_reply = "我下班就胡乱听点播客，或者放空发呆。短视频刷完像吃了一袋膨化食品。"
        with patch("companion_core.app.generate_reply", new_callable=AsyncMock) as mocked_generate:
            mocked_generate.side_effect = [failing_reply, failing_reply]
            response = client.post("/v1/reply", json={
                "bot_id": "1",
                "user_key": "web-user",
                "channel": "web",
                "text": "你平时下班路上会干嘛？我最近老刷短视频，刷完又觉得空虚。",
                "recent_messages": [],
                "memories": [],
                "relationship": {},
            })

        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertNotIn("我下班", body["reply"])
        self.assertIn("短视频", body["reply"])
        self.assertTrue(body["judge"]["passed"])
        self.assertEqual(mocked_generate.await_count, 2)


if __name__ == "__main__":
    unittest.main()
