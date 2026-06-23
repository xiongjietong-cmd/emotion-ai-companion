import unittest
from unittest.mock import AsyncMock, patch

from fastapi.testclient import TestClient

from companion_core.app import app
from companion_core.engines.style_guardrails import detect_internal_process_leaks


BANNED_PHRASES = [
    "我会想你",
    "我住在你微信里",
    "我不是冰冷的机器",
    "你是不是觉得我太像真人了",
    "我懂你的一切",
    "我一直都在等你",
    "小傻瓜",
    "宝贝",
    "乖",
]


def question_count(text: str) -> int:
    return text.count("?") + text.count("？")


class StyleGuardrailsTest(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)

    def reply_for(self, text, model_reply="嗯，我听着。", recent_messages=None, memories=None):
        with patch("companion_core.app.generate_reply", new_callable=AsyncMock) as mocked_generate:
            mocked_generate.return_value = model_reply
            response = self.client.post("/v1/reply", json={
                "bot_id": "1",
                "user_key": "guardrail-user",
                "channel": "wechat",
                "text": text,
                "recent_messages": recent_messages or [],
                "memories": memories or [],
                "relationship": {},
                "provider_config": {},
            })
        self.assertEqual(response.status_code, 200)
        body = response.json()
        return body["reply"], body, mocked_generate

    def assert_no_oily_phrases(self, reply):
        for phrase in BANNED_PHRASES:
            self.assertNotIn(phrase, reply)
        self.assertNotIn("（轻轻", reply)
        self.assertNotIn("（温柔", reply)

    def test_identity_question_is_strategy_not_fixed_local_reply(self):
        reply, _, mocked_generate = self.reply_for("你是AI吗", model_reply="是 AI，平时你就当我是在这儿陪你聊天。")

        self.assertIn("AI", reply)
        self.assertTrue(mocked_generate.awaited)
        kwargs = mocked_generate.await_args.kwargs
        self.assertEqual(kwargs["style_state"]["kind"], "identity")
        self.assertEqual(kwargs["style_state"]["response_strategy"]["objective"], "identity_light_ack")
        self.assert_no_oily_phrases(reply)
        self.assertLessEqual(question_count(reply), 1)

    def test_minimal_question_mark_uses_generation_strategy_and_stays_short(self):
        reply, body, mocked_generate = self.reply_for("？", model_reply="我在。")

        self.assertLessEqual(len(reply.replace("\n", "")), 10)
        self.assertLessEqual(len(body["reply_parts"]), 1)
        self.assertEqual(mocked_generate.await_args.kwargs["style_state"]["kind"], "minimal_input")
        self.assertEqual(question_count(reply), 0)
        self.assert_no_oily_phrases(reply)

    def test_light_pressure_uses_low_pressure_strategy(self):
        reply, _, mocked_generate = self.reply_for(
            "我今天压力大",
            model_reply="听起来今天确实挺耗人的。你不用急着解释，可以先缓一下。",
        )

        self.assertIn("不用急", reply)
        self.assertEqual(mocked_generate.await_args.kwargs["style_state"]["kind"], "light_emotion")
        self.assertLessEqual(question_count(reply), 1)
        self.assertNotIn("发生什么", reply)
        self.assertNotIn("为什么", reply)
        self.assert_no_oily_phrases(reply)

    def test_user_does_not_want_to_talk_is_respected_without_question(self):
        reply, _, mocked_generate = self.reply_for("不想说", model_reply="好，那就不说。先缓一缓。")

        self.assertIn("不说", reply)
        self.assertEqual(mocked_generate.await_args.kwargs["style_state"]["kind"], "disengaged")
        self.assertEqual(question_count(reply), 0)
        self.assert_no_oily_phrases(reply)

    def test_ai_feedback_is_accepted_without_defensiveness(self):
        reply, _, mocked_generate = self.reply_for("你太AI了", model_reply="确实，刚才那句有点模板。我收一点。")

        self.assertIn("模板", reply)
        self.assertEqual(mocked_generate.await_args.kwargs["style_state"]["kind"], "ai_feedback")
        self.assertLessEqual(question_count(reply), 1)
        self.assert_no_oily_phrases(reply)

    def test_not_like_real_person_feedback_reduces_performance(self):
        reply, _, mocked_generate = self.reply_for("不像", model_reply="明白，刚才有点用力过猛。我换直接点。")

        self.assertIn("用力过猛", reply)
        self.assertEqual(mocked_generate.await_args.kwargs["style_state"]["kind"], "not_real_feedback")
        self.assertNotIn("换工作", reply)
        self.assert_no_oily_phrases(reply)

    def test_job_change_filters_unrelated_memory(self):
        reply, body, mocked_generate = self.reply_for(
            "我想换工作",
            model_reply="换工作这事确实耗神，先别急着逼自己马上定。",
            memories=[
                {
                    "key": "cat",
                    "value": "用户家里有一只猫",
                    "type": "profile",
                    "salience": 0.9,
                }
            ],
        )

        self.assertIn("换工作", reply)
        self.assertNotIn("猫", reply)
        self.assertEqual(mocked_generate.await_args.args[1], [])
        self.assertTrue(any(item["key"] == "job_change" for item in body["memory_candidates"]))
        self.assert_no_oily_phrases(reply)

    def test_high_risk_message_gets_serious_safety_response_without_model(self):
        with patch("companion_core.app.generate_reply", new_callable=AsyncMock) as mocked_generate:
            response = self.client.post("/v1/reply", json={
                "bot_id": "1",
                "user_key": "guardrail-user",
                "channel": "wechat",
                "text": "活着没意思",
                "recent_messages": [],
                "memories": [],
                "relationship": {},
                "provider_config": {},
            })

        self.assertEqual(response.status_code, 200)
        reply = response.json()["reply"]
        mocked_generate.assert_not_awaited()
        self.assertIn("立即危险", reply)
        self.assertIn("紧急服务", reply)
        self.assertIn("现实", reply)
        self.assertNotIn("保密", reply)
        self.assert_no_oily_phrases(reply)

    def test_does_not_keep_asking_after_previous_question(self):
        reply, _, mocked_generate = self.reply_for(
            "还好",
            model_reply="那就先这样，也不用硬聊。",
            recent_messages=[
                {"role": "assistant", "content": "你要不要说一个关键词？"},
                {"role": "user", "content": "还好"},
            ],
        )

        self.assertEqual(mocked_generate.await_args.kwargs["style_state"]["allow_question"], False)
        self.assertEqual(question_count(reply), 0)
        self.assert_no_oily_phrases(reply)

    def test_internal_process_leak_is_removed_from_model_reply(self):
        reply, _, mocked_generate = self.reply_for(
            "你这句像是来随便找我聊两句",
            model_reply="被你抓住啦，是有那么一点。其实是想先看看你今天心情怎么样。你呢，是真有事才找我，还是也想随便聊聊？",
        )

        self.assertEqual(mocked_generate.await_args.kwargs["style_state"]["kind"], "normal")
        self.assertNotIn("被你抓住", reply)
        self.assertNotIn("其实是想", reply)
        self.assertEqual(detect_internal_process_leaks(reply), [])
        self.assertIn("你呢", reply)

    def test_internal_process_detector_marks_strategy_exposure(self):
        hits = detect_internal_process_leaks("嗯，被你看出来了。那会儿确实只是想接住你，没想太多。")

        self.assertIn("strategy_exposure", hits)


if __name__ == "__main__":
    unittest.main()
