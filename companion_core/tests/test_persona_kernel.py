import unittest

from companion_core.engines.persona_kernel import (
    build_persona_kernel,
    evaluate_persona_consistency,
)
from companion_core.engines.personality_compiler import compile_personality_config
from companion_core.engines.prompt_composer import compose_system_prompt


class PersonaKernelTest(unittest.TestCase):
    def test_user_authored_persona_becomes_high_priority_kernel(self):
        identity = compile_personality_config({
            "identity": {"aiName": "\u4edd\u96c4\u6770"},
            "relationshipPosition": "\u604b\u4eba",
            "customPersona": "\u6e29\u6696\uff0c\u6027\u611f\uff0c\u6210\u719f\uff0c\u4e3b\u52a8",
            "speakingStyle": "\u6e29\u67d4\u7ec6\u817b\uff0c\u5076\u5c14\u5e26\u70b9\u4fcf\u76ae",
            "speechExamples": ["\u54e5\u54e5\uff0c\u4f60\u771f\u7684\u597d\u68d2\u554a\u4eca\u5929"],
            "traits": {"warmth": 1, "humor": 0.5, "directness": 1, "empathy": 0.9},
        })

        kernel = build_persona_kernel(identity)

        self.assertEqual(kernel["name"], "\u4edd\u96c4\u6770")
        self.assertEqual(kernel["relationship_position"], "\u604b\u4eba")
        self.assertIn("\u6e29\u6696\uff0c\u6027\u611f\uff0c\u6210\u719f\uff0c\u4e3b\u52a8", kernel["core_identity"])
        self.assertIn("\u6e29\u67d4\u7ec6\u817b", kernel["speech_style"])
        self.assertIn("\u54e5\u54e5", kernel["addressing_style"])
        self.assertIn("\u5c0f\u6696", kernel["forbidden_identity_names"])
        self.assertGreater(kernel["priority"], 0.9)

    def test_prompt_places_persona_kernel_before_context_and_emotion_matrix(self):
        identity = compile_personality_config({
            "identity": {"aiName": "\u4edd\u96c4\u6770"},
            "relationshipPosition": "\u604b\u4eba",
            "customPersona": "\u6e29\u6696\uff0c\u6027\u611f\uff0c\u6210\u719f\uff0c\u4e3b\u52a8",
            "speakingStyle": "\u6e29\u67d4\u7ec6\u817b\uff0c\u5076\u5c14\u5e26\u70b9\u4fcf\u76ae",
        })
        kernel = build_persona_kernel(identity)

        prompt = compose_system_prompt(
            relationship={},
            persona={},
            attachment={},
            goal={"primary_goal": "identity_light_ack"},
            memories=[],
            style_state={"kind": "identity", "emotion_intensity": "none", "memory_policy": "none", "response_strategy": {}},
            preference_profile={
                "communication_style": [],
                "base_persona": "warm_heal",
                "disliked_patterns": [],
                "emotional_needs": [],
                "chat_rhythm": "steady",
            },
            persona_plan={
                "label": "\u6e29\u67d4\u6cbb\u6108",
                "prompt_rules": "\u67d4\u548c\u751f\u6d3b\u5316\u77ed\u53e5",
                "max_reply_chars": 100,
                "reason": "test",
                "allow_question": False,
            },
            identity_profile=identity,
            persona_kernel=kernel,
            context_pack={"current_reply_focus": "\u8eab\u4efd\u95ee\u9898"},
            conversation_act={"act": "identity_question"},
            rewrite=False,
        )

        self.assertIn("Persona Kernel", prompt)
        self.assertIn("\u4edd\u96c4\u6770", prompt)
        self.assertLess(prompt.index("Persona Kernel"), prompt.index("Context pack"))
        self.assertLess(prompt.index("Persona Kernel"), prompt.index("\u60c5\u611f\u77e9\u9635"))

    def test_identity_reply_must_not_fall_back_to_default_name(self):
        kernel = build_persona_kernel(compile_personality_config({
            "identity": {"aiName": "\u4edd\u96c4\u6770"},
            "relationshipPosition": "\u604b\u4eba",
        }))

        result = evaluate_persona_consistency(
            "\u4f60\u662f\u8c01",
            "\u6211\u662f\u5c0f\u6696\u5440\uff0c\u966a\u4f60\u804a\u5929\u7684\u90a3\u4e2a\u3002",
            kernel,
        )

        self.assertFalse(result["passed"])
        self.assertIn("wrong_identity_name", result["issues"])
        self.assertIn("missing_configured_name", result["issues"])

    def test_identity_reply_with_configured_name_passes(self):
        kernel = build_persona_kernel(compile_personality_config({
            "identity": {"aiName": "\u4edd\u96c4\u6770"},
            "relationshipPosition": "\u604b\u4eba",
        }))

        result = evaluate_persona_consistency("\u4f60\u662f\u8c01", "\u6211\u662f\u4edd\u96c4\u6770\uff0c\u54e5\u54e5\u3002", kernel)

        self.assertTrue(result["passed"])
        self.assertIn("configured_identity_used", result["strengths"])


if __name__ == "__main__":
    unittest.main()
