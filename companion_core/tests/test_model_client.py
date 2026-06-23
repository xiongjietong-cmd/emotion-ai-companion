import asyncio
import json
import os
import threading
import unittest
from http.server import BaseHTTPRequestHandler, HTTPServer

from companion_core.model_client import ModelUnavailableError, generate_reply


class FakeDeepSeekHandler(BaseHTTPRequestHandler):
    requests = []
    replies = ["模型回复：听起来今天确实挺耗人的。先别急着解决，可以先缓一下。"]

    def do_POST(self):
        length = int(self.headers.get("Content-Length", "0"))
        body = json.loads(self.rfile.read(length).decode("utf-8"))
        self.__class__.requests.append({
            "path": self.path,
            "body": body,
            "authorization": self.headers.get("Authorization", ""),
        })
        reply = self.__class__.replies[min(len(self.__class__.requests) - 1, len(self.__class__.replies) - 1)]
        if isinstance(reply, dict):
            payload = reply
        else:
            payload = {"choices": [{"message": {"content": reply}}]}
        encoded = json.dumps(payload).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(encoded)))
        self.end_headers()
        self.wfile.write(encoded)

    def log_message(self, format, *args):
        return


class ModelClientTest(unittest.TestCase):
    def setUp(self):
        self.old_env = {
            "DEEPSEEK_API_KEY": os.environ.get("DEEPSEEK_API_KEY"),
            "DEEPSEEK_BASE_URL": os.environ.get("DEEPSEEK_BASE_URL"),
            "DEEPSEEK_MODEL": os.environ.get("DEEPSEEK_MODEL"),
        }
        for key in self.old_env:
            os.environ.pop(key, None)

    def tearDown(self):
        for key, value in self.old_env.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value

    def test_without_api_key_raises_model_unavailable(self):
        with self.assertRaises(ModelUnavailableError):
            asyncio.run(generate_reply(
                text="今天有点累",
                memories=[],
                relationship={},
                persona={},
                attachment={},
                goal={"primary_goal": "gentle_probe"},
            ))

    def test_with_api_key_calls_openai_compatible_chat_completions(self):
        FakeDeepSeekHandler.requests = []
        server = HTTPServer(("127.0.0.1", 0), FakeDeepSeekHandler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        os.environ["DEEPSEEK_API_KEY"] = "test-key"
        os.environ["DEEPSEEK_BASE_URL"] = f"http://127.0.0.1:{server.server_port}/v1"
        os.environ["DEEPSEEK_MODEL"] = "deepseek-v4-flash"

        try:
            reply = asyncio.run(generate_reply(
                text="今天有点累",
                memories=[{"key": "job_change", "value": "用户最近在考虑换工作", "salience": 0.8}],
                relationship={"trust": 0.3, "intimacy": 0.2},
                persona={"tone": "warm", "empathy": 0.8},
                attachment={"should_recall_memory": True},
                goal={"primary_goal": "gentle_probe", "avoid": ["direct_advice"]},
            ))
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=5)

        self.assertEqual(reply, FakeDeepSeekHandler.replies[0])
        self.assertEqual(FakeDeepSeekHandler.requests[0]["path"], "/v1/chat/completions")
        body = FakeDeepSeekHandler.requests[0]["body"]
        self.assertEqual(body["model"], "deepseek-v4-flash")
        self.assertNotIn("max_tokens", body)
        self.assertEqual(body["messages"][0]["role"], "system")
        all_prompt_text = "\n".join(message["content"] for message in body["messages"])
        self.assertIn("用户最近在考虑换工作", all_prompt_text)
        self.assertIn("用户刚发来：今天有点累", all_prompt_text)

    def test_request_provider_config_can_supply_api_key_without_env(self):
        FakeDeepSeekHandler.requests = []
        server = HTTPServer(("127.0.0.1", 0), FakeDeepSeekHandler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()

        try:
            reply = asyncio.run(generate_reply(
                text="今天有点累",
                memories=[],
                relationship={},
                persona={},
                attachment={},
                goal={"primary_goal": "gentle_probe"},
                provider_config={
                    "api_key": "request-key",
                    "base_url": f"http://127.0.0.1:{server.server_port}/v1",
                    "model": "request-model",
                },
            ))
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=5)

        self.assertEqual(reply, FakeDeepSeekHandler.replies[0])
        self.assertEqual(FakeDeepSeekHandler.requests[0]["authorization"], "Bearer request-key")
        self.assertEqual(FakeDeepSeekHandler.requests[0]["body"]["model"], "request-model")

    def test_empty_content_response_retries_without_leaking_reasoning(self):
        FakeDeepSeekHandler.requests = []
        FakeDeepSeekHandler.replies = [
            {
                "choices": [{
                    "message": {
                        "content": "",
                        "reasoning_content": "internal reasoning must not be returned",
                    },
                    "finish_reason": "length",
                }]
            },
            "第二次正常回复",
        ]
        server = HTTPServer(("127.0.0.1", 0), FakeDeepSeekHandler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()

        try:
            reply = asyncio.run(generate_reply(
                text="嗯？",
                memories=[],
                relationship={},
                persona={},
                attachment={},
                goal={"primary_goal": "minimal_presence"},
                provider_config={
                    "api_key": "request-key",
                    "base_url": f"http://127.0.0.1:{server.server_port}/v1",
                    "model": "request-model",
                },
            ))
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=5)
            FakeDeepSeekHandler.replies = ["model reply"]

        self.assertEqual(reply, "\u7b2c\u4e8c\u6b21\u6b63\u5e38\u56de\u590d")
        self.assertEqual(len(FakeDeepSeekHandler.requests), 2)

    def test_identity_profile_is_sent_in_system_prompt(self):
        FakeDeepSeekHandler.requests = []
        server = HTTPServer(("127.0.0.1", 0), FakeDeepSeekHandler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()

        try:
            asyncio.run(generate_reply(
                text="在吗",
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
                    "label": "温和",
                    "prompt_rules": "自然口语",
                    "max_reply_chars": 80,
                    "reason": "test",
                    "allow_question": True,
                },
                identity_profile={
                    "name": "阿言",
                    "relationship_position": "用户设定的朋友",
                    "temperament": "清冷但靠得住",
                    "speech_style": "嘴硬，短句",
                    "avoid": "不要客服感",
                    "style_references": ["行，今天先别较劲。"],
                    "traits": {"warmth": 0.3, "humor": 0.6, "directness": 0.8, "empathy": 0.5},
                    "example_policy": "样例只用于学习语气，不是固定话术，不要照抄。",
                },
            ))
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=5)

        system_prompt = FakeDeepSeekHandler.requests[0]["body"]["messages"][0]["content"]
        self.assertIn("用户个性化人格设定", system_prompt)
        self.assertIn("阿言", system_prompt)
        self.assertIn("嘴硬", system_prompt)
        self.assertIn("不要照抄", system_prompt)

    def test_immersive_reality_policy_is_sent_in_system_prompt(self):
        FakeDeepSeekHandler.requests = []
        server = HTTPServer(("127.0.0.1", 0), FakeDeepSeekHandler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()

        try:
            asyncio.run(generate_reply(
                text="你用什么耳机？值得买吗？",
                memories=[],
                relationship={},
                persona={},
                attachment={},
                goal={"primary_goal": "daily_chat"},
                provider_config={
                    "api_key": "request-key",
                    "base_url": f"http://127.0.0.1:{server.server_port}/v1",
                    "model": "request-model",
                },
                style_state={"kind": "daily_chat", "emotion_intensity": "low"},
                preference_profile={
                    "communication_style": [],
                    "base_persona": "playful_tease",
                    "disliked_patterns": [],
                    "emotional_needs": [],
                    "chat_rhythm": "steady",
                },
                persona_plan={
                    "label": "俏皮损友",
                    "prompt_rules": "自然口语",
                    "max_reply_chars": 120,
                    "reason": "test",
                    "allow_question": True,
                },
                immersive_reality={
                    "mode": "grounded_advice",
                    "prompt_guidance": "- Internal only\n- Do not claim owned devices",
                },
            ))
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=5)

        system_prompt = FakeDeepSeekHandler.requests[0]["body"]["messages"][0]["content"]
        self.assertIn("Immersive reality policy", system_prompt)
        self.assertIn("grounded_advice", system_prompt)
        self.assertIn("Do not claim owned devices", system_prompt)
