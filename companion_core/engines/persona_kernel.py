from __future__ import annotations

from typing import Any


IDENTITY_QUESTION_PATTERNS = [
    "\u4f60\u662f\u8c01",
    "\u4f60\u53eb\u4ec0\u4e48",
    "\u4f60\u53eb\u5565",
    "\u4f60\u7684\u540d\u5b57",
    "\u600e\u4e48\u79f0\u547c",
]

DEFAULT_IDENTITY_NAMES = ["\u5c0f\u6696"]


def _contains_any(text: str, patterns: list[str]) -> bool:
    return any(pattern in text for pattern in patterns)


def _clean(value: Any, default: str = "") -> str:
    text = str(value or "").strip()
    return text or default


def _addressing_style(identity_profile: dict[str, Any]) -> str:
    references = identity_profile.get("style_references") or []
    joined = " / ".join(str(item) for item in references)
    if "\u54e5\u54e5" in joined:
        return "\u54e5\u54e5"
    if "\u59d0\u59d0" in joined:
        return "\u59d0\u59d0"
    if "\u54e5" in joined:
        return "\u54e5"
    return ""


def build_persona_kernel(identity_profile: dict[str, Any] | None) -> dict[str, Any]:
    profile = identity_profile or {}
    name = _clean(profile.get("name"), "\u5c0f\u6696")
    relationship = _clean(profile.get("relationship_position"), "\u966a\u4f34\u5bf9\u8c61")
    core_identity = _clean(profile.get("temperament"), "\u81ea\u7136\u3001\u7a33\u5b9a\u3001\u5c0a\u91cd\u7528\u6237\u8282\u594f")
    speech_style = _clean(profile.get("speech_style"), "\u81ea\u7136\u53e3\u8bed\uff0c\u77ed\u53e5\u4f18\u5148")
    blocked_terms = list(profile.get("blocked_terms") or [])
    forbidden_names = [
        item for item in DEFAULT_IDENTITY_NAMES
        if item != name and item not in blocked_terms
    ]

    return {
        "priority": 0.96,
        "name": name,
        "relationship_position": relationship,
        "core_identity": core_identity,
        "speech_style": speech_style,
        "addressing_style": _addressing_style(profile),
        "blocked_terms": blocked_terms,
        "forbidden_identity_names": forbidden_names,
        "style_references": list(profile.get("style_references") or [])[:3],
        "traits": dict(profile.get("traits") or {}),
        "policy": (
            "\u7528\u6237\u4eb2\u624b\u8bbe\u5b9a\u7684\u4eba\u683c\u5185\u6838\u5fc5\u987b\u4f18\u5148\u4e8e\u9ed8\u8ba4\u4ea7\u54c1\u98ce\u683c\u3001\u60c5\u7eea\u77e9\u9635\u3001"
            "\u957f\u671f\u504f\u597d\u548c\u666e\u901a\u4e0a\u4e0b\u6587\uff1b\u5176\u4ed6\u6a21\u5757\u53ea\u80fd\u56f4\u7ed5\u5b83\u8c03\u6574\u8868\u8fbe\u3002"
        ),
    }


def evaluate_persona_consistency(
    user_text: str,
    reply: str,
    persona_kernel: dict[str, Any] | None,
) -> dict[str, Any]:
    kernel = persona_kernel or {}
    name = _clean(kernel.get("name"))
    clean_user = user_text or ""
    clean_reply = reply or ""
    issues: list[str] = []
    strengths: list[str] = []
    identity_question = _contains_any(clean_user, IDENTITY_QUESTION_PATTERNS)

    for wrong_name in kernel.get("forbidden_identity_names") or []:
        if wrong_name and wrong_name in clean_reply:
            issues.append("wrong_identity_name")

    if identity_question and name:
        if name in clean_reply:
            strengths.append("configured_identity_used")
        else:
            issues.append("missing_configured_name")

    if identity_question and kernel.get("relationship_position") and kernel.get("relationship_position") in clean_reply:
        strengths.append("relationship_position_used")

    return {
        "passed": not issues,
        "issues": issues,
        "strengths": strengths,
        "identity_question": identity_question,
        "name": name,
        "relationship_position": kernel.get("relationship_position", ""),
    }
