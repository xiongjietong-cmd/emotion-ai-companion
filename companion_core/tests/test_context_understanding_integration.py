import asyncio
import json
import threading
import unittest
from http.server import BaseHTTPRequestHandler, HTTPServer
from unittest.mock import AsyncMock, patch

from fastapi.testclient import TestClient

from companion_core.app import app
from companion_core.model_client import generate_reply


class PromptCaptureHandler(BaseHTTPRequestHandler):
    requests = []

    def do_POST(self):
        length = int(self.headers.get("Content-Length", "0"))
        body = json.loads(self.rfile.read(length).decode("utf-8"))
        self.__class__.requests.append(body)
        payload = {"choices": [{"message": {"content": "\u6211\u77e5\u9053\uff0c\u4f60\u8bf4\u7684\u662f\u521a\u624d\u6211\u6ca1\u6709\u7a33\u5b9a\u63a5\u4f4f\u4e0a\u4e0b\u6587\u8fd9\u4ef6\u4e8b\u3002"}}]}
        encoded = json.dumps(payload).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(encoded)))
        self.end_headers()
        self.wfile.write(encoded)

    def log_message(self, format, *args):
        return


class ContextUnderstandingIntegrationTest(unittest.TestCase):
    def test_prompt_receives_context_understanding_contract(self):
        PromptCaptureHandler.requests = []
        server = HTTPServer(("127.0.0.1", 0), PromptCaptureHandler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()

        try:
            asyncio.run(generate_reply(
                text="\u90a3\u4f60\u544a\u8bc9\u6211\u5440",
                memories=[],
                relationship={},
                persona={},
                attachment={},
                goal={"primary_goal": "natural_continue"},
                provider_config={
                    "api_key": "request-key",
                    "base_url": f"http://127.0.0.1:{server.server_port}/v1",
                    "model": "request-model",
                },
                style_state={"kind": "casual", "emotion_intensity": "low"},
                preference_profile={
                    "communication_style": [],
                    "base_persona": "warm_heal",
                    "disliked_patterns": [],
                    "emotional_needs": [],
                    "chat_rhythm": "steady",
                },
                persona_plan={
                    "label": "warm",
                    "prompt_rules": "natural",
                    "max_reply_chars": 80,
                    "reason": "test",
                    "allow_question": True,
                },
                context_understanding={
                    "scene": "understanding_check",
                    "user_intent": "requests_specific_reference",
                    "active_topic": "\u505a\u4e0d\u5230\u8ba9 AI \u7a33\u5b9a\u63a5\u4f4f\u4e0a\u4e0b\u6587",
                    "referenced_turn": {"role": "user", "content": "\u505a\u4e0d\u5230\u8ba9\u4f60\u7a33\u5b9a"},
                    "response_contract": {
                        "must_answer": ["\u8bf4\u51fa\u4e0a\u6587\u6307\u5411"],
                        "must_not": ["\u4e0d\u80fd\u53ea\u8bf4\u6211\u61c2/\u6211\u660e\u767d"],
                        "allow_question": False,
                        "tone": "direct_contextual",
                    },
                },
            ))
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=5)

        system_prompt = PromptCaptureHandler.requests[0]["messages"][0]["content"]
        self.assertIn("Internal context understanding contract", system_prompt)
        self.assertIn("understanding_check", system_prompt)
        self.assertIn("\u505a\u4e0d\u5230\u8ba9 AI \u7a33\u5b9a\u63a5\u4f4f\u4e0a\u4e0b\u6587", system_prompt)
        self.assertIn("\u8bf4\u51fa\u4e0a\u6587\u6307\u5411", system_prompt)
        self.assertIn("\u4e0d\u8981\u628a\u672c\u6bb5\u5951\u7ea6\u5185\u5bb9\u8bf4\u7ed9\u7528\u6237", system_prompt)

    def test_reply_endpoint_builds_context_understanding_only_when_enabled(self):
        client = TestClient(app)
        with patch("companion_core.app.generate_reply", new_callable=AsyncMock) as mocked_generate:
            mocked_generate.return_value = "\u4f60\u8bf4\u7684\u662f\u521a\u624d\u6211\u6ca1\u6709\u7a33\u5b9a\u63a5\u4f4f\u4e0a\u4e0b\u6587\u3002"
            response = client.post("/v1/reply", json={
                "bot_id": "167",
                "user_key": "wechat-user",
                "channel": "wechat",
                "text": "\u90a3\u4f60\u544a\u8bc9\u6211\u5440",
                "recent_messages": [
                    {"role": "user", "content": "\u505a\u4e0d\u5230\u8ba9\u4f60\u7a33\u5b9a"},
                    {"role": "assistant", "content": "\u55ef\uff0c\u6211\u660e\u767d\u4f60\u7684\u610f\u601d\u4e86\u3002"},
                    {"role": "user", "content": "\u4f60\u77e5\u9053\u6211\u8bf4\u7684\u4ec0\u4e48\u5417"},
                ],
                "memories": [],
                "relationship": {},
                "features": {"context_understanding": True},
            })

        self.assertEqual(response.status_code, 200)
        first_kwargs = mocked_generate.await_args_list[0].kwargs
        contract = first_kwargs["context_understanding"]
        self.assertEqual(contract["scene"], "understanding_check")
        self.assertIn("\u7a33\u5b9a", contract["active_topic"])
        self.assertFalse(contract["response_contract"]["allow_question"])

    def test_reply_endpoint_leaves_context_understanding_off_by_default(self):
        client = TestClient(app)
        with patch("companion_core.app.generate_reply", new_callable=AsyncMock) as mocked_generate:
            mocked_generate.return_value = "\u5728\u3002"
            response = client.post("/v1/reply", json={
                "bot_id": "167",
                "user_key": "wechat-user",
                "channel": "wechat",
                "text": "\u5728\u5417",
                "recent_messages": [],
                "memories": [],
                "relationship": {},
            })

        self.assertEqual(response.status_code, 200)
        first_kwargs = mocked_generate.await_args_list[0].kwargs
        self.assertIsNone(first_kwargs["context_understanding"])

    def test_understanding_check_contract_is_promoted_to_top_reply_task(self):
        PromptCaptureHandler.requests = []
        server = HTTPServer(("127.0.0.1", 0), PromptCaptureHandler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()

        try:
            asyncio.run(generate_reply(
                text="\u90a3\u4f60\u544a\u8bc9\u6211\u5440",
                memories=[],
                relationship={},
                persona={},
                attachment={},
                goal={"primary_goal": "natural_continue"},
                provider_config={
                    "api_key": "request-key",
                    "base_url": f"http://127.0.0.1:{server.server_port}/v1",
                    "model": "request-model",
                },
                style_state={"kind": "casual", "emotion_intensity": "low"},
                preference_profile={
                    "communication_style": [],
                    "base_persona": "warm_heal",
                    "disliked_patterns": [],
                    "emotional_needs": [],
                    "chat_rhythm": "steady",
                },
                persona_plan={
                    "label": "warm",
                    "prompt_rules": "natural",
                    "max_reply_chars": 80,
                    "reason": "test",
                    "allow_question": True,
                },
                context_understanding={
                    "scene": "understanding_check",
                    "user_intent": "requests_specific_reference",
                    "active_topic": "\u505a\u4e0d\u5230\u8ba9 AI \u7a33\u5b9a\u63a5\u4f4f\u4e0a\u4e0b\u6587",
                    "referenced_turn": {"role": "user", "content": "\u505a\u4e0d\u5230\u8ba9\u4f60\u7a33\u5b9a"},
                    "response_contract": {
                        "must_answer": ["\u8bf4\u51fa\u4e0a\u6587\u6307\u5411"],
                        "must_not": ["\u4e0d\u80fd\u53ea\u8bf4\u6211\u61c2/\u6211\u660e\u767d"],
                        "allow_question": False,
                        "tone": "direct_contextual",
                    },
                },
            ))
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=5)

        system_prompt = PromptCaptureHandler.requests[0]["messages"][0]["content"]
        self.assertIn("Highest priority reply task", system_prompt)
        self.assertIn("First state the referenced topic", system_prompt)
        self.assertIn("Do not explain memory limitations", system_prompt)
        self.assertIn("Do not ask the user what they mean", system_prompt)
        self.assertIn("Use active_topic and referenced_turn as the concrete answer", system_prompt)
        self.assertIn("Do not replace it with generic remembering", system_prompt)
        self.assertIn("Do not tell the user to provide more context", system_prompt)

    def test_low_mood_contract_blocks_free_time_interpretation(self):
        PromptCaptureHandler.requests = []
        server = HTTPServer(("127.0.0.1", 0), PromptCaptureHandler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()

        try:
            asyncio.run(generate_reply(
                text="\u4eca\u5929\u6709\u70b9\u7a7a",
                memories=[],
                relationship={},
                persona={},
                attachment={},
                goal={"primary_goal": "emotion_ack"},
                provider_config={
                    "api_key": "request-key",
                    "base_url": f"http://127.0.0.1:{server.server_port}/v1",
                    "model": "request-model",
                },
                style_state={"kind": "low_mood", "emotion_intensity": "medium"},
                preference_profile={
                    "communication_style": [],
                    "base_persona": "warm_heal",
                    "disliked_patterns": [],
                    "emotional_needs": [],
                    "chat_rhythm": "steady",
                },
                persona_plan={
                    "label": "quiet",
                    "prompt_rules": "natural",
                    "max_reply_chars": 80,
                    "reason": "test",
                    "allow_question": True,
                },
                context_understanding={
                    "scene": "low_mood",
                    "user_intent": "shares_empty_or_low_mood",
                    "active_topic": "\u60c5\u7eea\u7a7a\u843d",
                    "referenced_turn": None,
                    "response_contract": {
                        "must_answer": ["\u60c5\u7eea\u7a7a\u843d"],
                        "must_not": ["\u7acb\u523b\u5b89\u6392\u4efb\u52a1"],
                        "allow_question": True,
                        "tone": "quiet_presence",
                    },
                },
            ))
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=5)

        system_prompt = PromptCaptureHandler.requests[0]["messages"][0]["content"]
        self.assertIn("Treat this as emotional emptiness, not free time", system_prompt)
        self.assertIn("Do not say it is good to have free time", system_prompt)

    def test_feedback_repair_contract_requires_revised_reply_not_meta_reset(self):
        PromptCaptureHandler.requests = []
        server = HTTPServer(("127.0.0.1", 0), PromptCaptureHandler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()

        try:
            asyncio.run(generate_reply(
                text="\u4f60\u91cd\u65b0\u8bf4",
                memories=[],
                relationship={},
                persona={},
                attachment={},
                goal={"primary_goal": "natural_continue"},
                provider_config={
                    "api_key": "request-key",
                    "base_url": f"http://127.0.0.1:{server.server_port}/v1",
                    "model": "request-model",
                },
                style_state={"kind": "casual", "emotion_intensity": "low"},
                preference_profile={
                    "communication_style": [],
                    "base_persona": "warm_heal",
                    "disliked_patterns": [],
                    "emotional_needs": [],
                    "chat_rhythm": "steady",
                },
                persona_plan={
                    "label": "plain",
                    "prompt_rules": "natural",
                    "max_reply_chars": 80,
                    "reason": "test",
                    "allow_question": False,
                },
                context_understanding={
                    "scene": "feedback_repair",
                    "user_intent": "requests_style_repair",
                    "active_topic": "\u56de\u590d\u98ce\u683c\u88ab\u7528\u6237\u6307\u51fa\u4e0d\u81ea\u7136",
                    "referenced_turn": {"role": "user", "content": "\u4e0d\u50cf"},
                    "working_summary": "\u7528\u6237: \u4f60\u8fd9\u53e5\u6709\u70b9\u6a21\u677f\uff1b\u52a9\u624b: \u5440\u2026\u2026\u6211\u6539\u3002\uff1b\u7528\u6237: \u4e0d\u50cf",
                    "response_contract": {
                        "must_answer": ["\u76f4\u63a5\u6362\u4e00\u79cd\u8bf4\u6cd5"],
                        "must_not": ["\u89e3\u91ca\u81ea\u5df1/\u8868\u6f14\u9053\u6b49"],
                        "allow_question": False,
                        "tone": "plain_recalibration",
                    },
                },
            ))
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=5)

        system_prompt = PromptCaptureHandler.requests[0]["messages"][0]["content"]
        self.assertIn("Produce the revised reply directly", system_prompt)
        self.assertIn("Do not merely say you will restart", system_prompt)
        self.assertIn("Do not perform an apology", system_prompt)
        self.assertIn("working_summary", system_prompt)
        self.assertIn("\u5440\u2026\u2026\u6211\u6539", system_prompt)
        self.assertIn("Do not switch to an unrelated poetic line", system_prompt)


if __name__ == "__main__":
    unittest.main()
