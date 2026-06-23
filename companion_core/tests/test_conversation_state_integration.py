import unittest
from unittest.mock import AsyncMock, patch

from fastapi.testclient import TestClient

from companion_core.app import app
from companion_core.engines.context_understanding import understand_context
from companion_core.engines.conversation_state import update_conversation_state
from companion_core.engines.prompt_composer import compose_system_prompt


class ConversationStateIntegrationTest(unittest.TestCase):
    def test_recall_repair_prompt_contains_initial_core_and_boundary(self):
        recent = [
            {"role": "user", "content": "\u4eca\u5929\u6709\u70b9\u7a7a"},
            {
                "role": "assistant",
                "content": "\u90a3\u6b63\u597d\uff0c\u53ef\u4ee5\u6162\u60a0\u60a0\u5730\u505a\u70b9\u60f3\u505a\u7684\u4e8b\u3002",
            },
            {"role": "user", "content": "\u4e0d\u662f\u6709\u7a7a\u7684\u610f\u601d\u2026\u2026\u5c31\u662f\u5fc3\u91cc\u6709\u70b9\u7a7a"},
            {"role": "assistant", "content": "\u55ef\uff0c\u90a3\u79cd\u7a7a\u843d\u843d\u7684\u611f\u89c9\uff0c\u6211\u61c2\u3002"},
            {"role": "user", "content": "\u55ef\uff0c\u4e5f\u4e0d\u662f\u96be\u8fc7\uff0c\u5c31\u662f\u5237\u5b8c\u670b\u53cb\u5708\u66f4\u7a7a\u4e86"},
            {
                "role": "assistant",
                "content": "\u55ef\uff0c\u522b\u4eba\u7684\u70ed\u95f9\u770b\u591a\u4e86\uff0c\u5bb9\u6613\u653e\u5927\u81ea\u5df1\u7684\u5b89\u9759\u3002",
            },
            {"role": "user", "content": "\u4f60\u522b\u4e00\u76f4\u95ee"},
            {"role": "assistant", "content": "\u55ef\uff0c\u597d\uff0c\u4e0d\u95ee\u4e86\u3002"},
            {"role": "user", "content": "\u90a3\u4f60\u8fd8\u8bb0\u5f97\u6211\u521a\u624d\u8bf4\u7684\u662f\u5565\u5417"},
            {
                "role": "assistant",
                "content": "\u55ef\uff0c\u8bb0\u5f97\u3002\u4f60\u8bf4\u201c\u5bf9\uff0c\u5c31\u662f\u8fd9\u79cd\u611f\u89c9\u201d\uff0c\u7136\u540e\u8ba9\u6211\u522b\u4e00\u76f4\u95ee\u3002",
            },
        ]
        text = "\u4e0d\u662f\u8fd9\u4e2a\uff0c\u6211\u662f\u8bf4\u4e00\u5f00\u59cb\u90a3\u4e2a"
        context = understand_context(text, recent)
        state = update_conversation_state(
            text=text,
            recent_messages=recent,
            context_understanding=context,
        )
        prompt = compose_system_prompt(
            relationship={},
            persona={},
            attachment={},
            goal={},
            memories=[],
            style_state={},
            preference_profile={},
            persona_plan={},
            context_understanding=context,
            conversation_state=state,
        )

        self.assertIn("\u5fc3\u91cc\u7a7a", prompt)
        self.assertIn("\u670b\u53cb\u5708", prompt)
        self.assertIn("\u4e0d\u8981\u4e00\u76f4\u8ffd\u95ee", prompt)
        self.assertIn("\u4e0d\u8981\u8ba9\u7528\u6237\u91cd\u590d", prompt)
        self.assertIn("internal continuity guide only", prompt)

    def test_reply_endpoint_builds_conversation_state_only_when_enabled(self):
        client = TestClient(app)
        with patch("companion_core.app.generate_reply", new_callable=AsyncMock) as mocked_generate:
            mocked_generate.return_value = "\u662f\u6211\u521a\u624d\u8bb0\u504f\u4e86\uff0c\u4f60\u4e00\u5f00\u59cb\u8bf4\u7684\u662f\u5fc3\u91cc\u6709\u70b9\u7a7a\u3002"
            response = client.post("/v1/reply", json={
                "bot_id": "167",
                "user_key": "wechat-user",
                "channel": "wechat",
                "text": "\u4e0d\u662f\u8fd9\u4e2a\uff0c\u6211\u662f\u8bf4\u4e00\u5f00\u59cb\u90a3\u4e2a",
                "recent_messages": [
                    {"role": "user", "content": "\u4eca\u5929\u6709\u70b9\u7a7a"},
                    {"role": "assistant", "content": "\u90a3\u6b63\u597d\uff0c\u53ef\u4ee5\u6162\u60a0\u60a0\u5730\u505a\u70b9\u60f3\u505a\u7684\u4e8b\u3002"},
                    {"role": "user", "content": "\u4e0d\u662f\u6709\u7a7a\u7684\u610f\u601d\u2026\u2026\u5c31\u662f\u5fc3\u91cc\u6709\u70b9\u7a7a"},
                    {"role": "user", "content": "\u55ef\uff0c\u4e5f\u4e0d\u662f\u96be\u8fc7\uff0c\u5c31\u662f\u5237\u5b8c\u670b\u53cb\u5708\u66f4\u7a7a\u4e86"},
                    {"role": "user", "content": "\u4f60\u522b\u4e00\u76f4\u95ee"},
                    {"role": "assistant", "content": "\u55ef\uff0c\u8bb0\u5f97\u3002\u4f60\u8bf4\u201c\u5bf9\uff0c\u5c31\u662f\u8fd9\u79cd\u611f\u89c9\u201d\uff0c\u7136\u540e\u8ba9\u6211\u522b\u4e00\u76f4\u95ee\u3002"},
                ],
                "memories": [],
                "relationship": {},
                "features": {"context_understanding": True, "conversation_state": True},
            })

        self.assertEqual(response.status_code, 200)
        first_kwargs = mocked_generate.await_args_list[0].kwargs
        state = first_kwargs["conversation_state"]
        self.assertIn("\u5fc3\u91cc\u7a7a", state["active_topic"])
        self.assertIn("\u670b\u53cb\u5708", state["active_topic"])
        self.assertIn("\u4e0d\u8981\u4e00\u76f4\u8ffd\u95ee", state["user_boundary"])
        self.assertIn("\u4e0d\u8981\u8ba9\u7528\u6237\u91cd\u590d", state["next_reply_task"])

    def test_reply_endpoint_passes_changeable_activity_fact_to_generation(self):
        client = TestClient(app)
        with patch("companion_core.app.generate_reply", new_callable=AsyncMock) as mocked_generate:
            mocked_generate.return_value = "\u90a3\u6211\u8fd9\u6b21\u4e0d\u4e71\u731c\u4e86\u3002"
            response = client.post("/v1/reply", json={
                "bot_id": "167",
                "user_key": "wechat-user",
                "channel": "wechat",
                "text": "\u90a3\u6211\u518d\u95ee\u4f60\u6211\u5728\u5e72\u4ec0\u4e48",
                "recent_messages": [
                    {"role": "user", "content": "\u6211\u5728\u4e0a\u8bfe"},
                    {"role": "assistant", "content": "\u597d\u561e\uff0c\u4f60\u5148\u4e13\u5fc3\u4e0a\u8bfe\u3002"},
                    {"role": "user", "content": "\u4f60\u77e5\u9053\u6211\u73b0\u5728\u5728\u5e72\u4ec0\u4e48\u5417"},
                    {"role": "assistant", "content": "\u6b63\u5728\u731c\u662f\u53d1\u5446\uff0c\u8fd8\u662f\u5728\u5077\u5403\u4ec0\u4e48\u4e1c\u897f\u3002"},
                    {"role": "user", "content": "\u6211\u4e0d\u662f\u8ddf\u4f60\u8bf4\u6211\u5728\u4e0a\u8bfe\u5417"},
                ],
                "memories": [],
                "relationship": {},
                "features": {"context_understanding": True, "conversation_state": True},
            })

        self.assertEqual(response.status_code, 200)
        first_kwargs = mocked_generate.await_args_list[0].kwargs
        context = first_kwargs["context_understanding"]
        state = first_kwargs["conversation_state"]
        self.assertEqual(context["scene"], "situational_probe")
        self.assertIn("\u4e0a\u8bfe", context["active_topic"])
        self.assertEqual(state["situational_facts"][-1]["value"], "\u4e0a\u8bfe")
        self.assertTrue(state["situational_facts"][-1]["changeable"])
        self.assertIn("\u4e0d\u8981\u4e71\u731c", state["next_reply_task"])


if __name__ == "__main__":
    unittest.main()
