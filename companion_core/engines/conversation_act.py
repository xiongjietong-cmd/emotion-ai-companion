from __future__ import annotations

from typing import Any


COMFORT_REQUEST_PATTERNS = [
    "安慰安慰",
    "安慰我",
    "哄哄我",
    "抱抱",
    "抱一下",
    "陪陪我",
    "心疼心疼",
]

DISENGAGED_PATTERNS = [
    "不想说",
    "算了",
    "不说了",
    "别问了",
    "先这样",
]

MEMORY_PROBE_PATTERNS = [
    "我在干什么",
    "我在干嘛",
    "我要去干什么",
    "我刚才说",
    "我刚才跟你说",
]

PREMATURE_CLOSURE_PATTERNS = [
    "不说话也行",
    "不说也行",
    "不想说也行",
    "不用说",
    "不用回",
    "不用解释",
    "不用非得说",
    "不用急着回",
]

COMFORT_SIGNAL_PATTERNS = [
    "抱",
    "摸摸头",
    "委屈",
    "辛苦",
    "累",
    "撑着",
    "站你这边",
    "陪你",
    "心疼",
]


def _contains_any(text: str, patterns: list[str]) -> bool:
    return any(pattern in text for pattern in patterns)


def classify_conversation_act(text: str, recent_messages: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    clean = (text or "").strip()
    recent_messages = recent_messages or []
    evidence = [clean]

    if _contains_any(clean, COMFORT_REQUEST_PATTERNS):
        return {
            "act": "seeking_comfort",
            "pressure": "open",
            "needs": ["emotional_support", "warmth", "staying_with_user"],
            "avoid": ["premature_closure", "analysis_first", "generic_presence"],
            "confidence": 0.92,
            "evidence": evidence,
        }

    if _contains_any(clean, DISENGAGED_PATTERNS):
        return {
            "act": "disengaged_boundary",
            "pressure": "closed",
            "needs": ["space"],
            "avoid": ["pressure", "followup_question"],
            "confidence": 0.86,
            "evidence": evidence,
        }

    if _contains_any(clean, MEMORY_PROBE_PATTERNS):
        return {
            "act": "context_probe",
            "pressure": "open",
            "needs": ["use_recent_scene", "answer_the_reference"],
            "avoid": ["random_guess", "generic_presence"],
            "confidence": 0.82,
            "evidence": evidence + [
                str(message.get("content") or "")
                for message in recent_messages[-4:]
                if isinstance(message, dict)
            ],
        }

    return {
        "act": "natural_continue",
        "pressure": "open",
        "needs": ["continue_current_topic"],
        "avoid": ["template_reply"],
        "confidence": 0.5,
        "evidence": evidence,
    }


def evaluate_reply_alignment(
    user_text: str,
    reply: str,
    recent_messages: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    act = classify_conversation_act(user_text, recent_messages)
    clean_reply = (reply or "").strip()
    issues: list[str] = []
    strengths: list[str] = []

    if act["act"] == "seeking_comfort":
        if _contains_any(clean_reply, PREMATURE_CLOSURE_PATTERNS):
            issues.append("premature_closure")
        if _contains_any(clean_reply, COMFORT_SIGNAL_PATTERNS):
            strengths.append("comfort_signal")
        else:
            issues.append("missing_comfort_signal")

    if act["act"] == "disengaged_boundary" and not _contains_any(clean_reply, PREMATURE_CLOSURE_PATTERNS):
        strengths.append("respects_open_space")

    return {
        "act": act["act"],
        "pressure": act["pressure"],
        "needs": act["needs"],
        "avoid": act["avoid"],
        "issues": issues,
        "strengths": strengths,
        "passed": not issues,
    }
