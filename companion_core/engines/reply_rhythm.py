import re


IRRITATED_WORDS = ["\u522b\u70e6", "\u70e6", "\u4e0d\u60f3\u804a", "\u95ed\u5634", "\u7b97\u4e86"]
LONELY_WORDS = ["\u5b64\u72ec", "\u4e00\u4e2a\u4eba", "\u6ca1\u4eba", "\u60f3\u627e\u4eba", "\u96be\u53d7", "\u60f3\u54ed"]
PLAYFUL_WORDS = ["\u54c8\u54c8", "\u7b11\u6b7b", "\u79bb\u8c31", "\u597d\u73a9", "\u54c8\u55bd"]


def _score(relationship: dict, key: str) -> float:
    try:
        return float((relationship or {}).get(key, 0))
    except (TypeError, ValueError):
        return 0.0


def decide_reply_rhythm(user_text: str, relationship: dict | None = None) -> dict:
    text = (user_text or "").strip()
    relationship = relationship or {}

    if any(word in text for word in IRRITATED_WORDS):
        return {
            "profile": "quiet",
            "max_parts": 2,
            "reason": "irritated_or_withdrawing_user",
        }

    if (
        any(word in text for word in LONELY_WORDS)
        or _score(relationship, "loneliness") >= 0.65
        or _score(relationship, "attachment") >= 0.65
    ):
        return {
            "profile": "attached",
            "max_parts": 4,
            "reason": "lonely_or_attached_user",
        }

    if (
        any(word in text for word in PLAYFUL_WORDS)
        or _score(relationship, "humor") >= 0.7
        or _score(relationship, "activity") >= 0.75
    ):
        return {
            "profile": "playful",
            "max_parts": 4,
            "reason": "playful_or_active_user",
        }

    return {
        "profile": "steady",
        "max_parts": 3,
        "reason": "default_conversation_rhythm",
    }


def split_reply_parts(reply: str, rhythm: dict | None = None) -> list[str]:
    text = (reply or "").strip()
    if not text:
        return []

    max_parts = int((rhythm or {}).get("max_parts") or 3)
    max_parts = max(1, min(4, max_parts))

    raw_parts = [
        re.sub(r"[ \t]+", " ", part.strip())
        for part in re.split(r"\r?\n+", text)
        if part.strip()
    ]
    cleaned = re.sub(r"\s+", " ", text)
    if len(raw_parts) <= 1:
        raw_parts = [part.strip() for part in re.split(r"(?<=[\u3002\uff01\uff1f!?])\s*", cleaned) if part.strip()]
    if len(raw_parts) <= 1 and len(cleaned) >= 18:
        raw_parts = [part.strip() for part in re.split(r"[\uff0c,;\uff1b]\s*", cleaned) if part.strip()]

    parts: list[str] = []
    for part in raw_parts:
        if len(parts) < max_parts - 1:
            parts.append(part)
        else:
            parts.append(" ".join(raw_parts[len(parts):]).strip())
            break

    if len(parts) == 1 and len(parts[0]) >= 28 and max_parts > 1:
        single = parts[0]
        midpoint = len(single) // 2
        split_at = max(single.rfind("\uff0c", 0, midpoint), single.rfind(",", 0, midpoint))
        if split_at <= 0:
            split_at = midpoint
        parts = [single[:split_at + 1].strip(), single[split_at + 1:].strip()]

    return [part for part in parts if part][:max_parts]
