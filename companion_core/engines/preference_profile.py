SHORT_REPLY_LIMIT = 6
LONG_REPLY_LIMIT = 40
MINIMAL_INPUTS = {"?", "\uff1f", "\u55ef", "\u54e6", "\u554a", "\u5bf9", "\u5bf9\u5440", "."}


def _user_texts(recent_messages: list[dict]) -> list[str]:
    return [
        str(message.get("content") or "").strip()
        for message in recent_messages or []
        if message.get("role") == "user" and str(message.get("content") or "").strip()
    ]


def _contains_any(text: str, patterns: list[str]) -> bool:
    return any(pattern in text for pattern in patterns)


def build_preference_profile(recent_messages: list[dict]) -> dict:
    texts = _user_texts(recent_messages)[-50:]
    communication_style: list[str] = []
    disliked_patterns: list[str] = []
    emotional_needs: list[str] = []

    if texts:
        short_ratio = sum(1 for text in texts if len(text) <= SHORT_REPLY_LIMIT) / len(texts)
        long_ratio = sum(1 for text in texts if len(text) >= LONG_REPLY_LIMIT) / len(texts)
        minimal_ratio = sum(1 for text in texts if text in MINIMAL_INPUTS or len(text) <= 2) / len(texts)
    else:
        short_ratio = 0
        long_ratio = 0
        minimal_ratio = 0

    if short_ratio >= 0.45:
        communication_style.append("short_reply")
    if long_ratio >= 0.3:
        communication_style.append("long_teller")
    if minimal_ratio >= 0.35:
        communication_style.append("intermittent_silence")

    joined = "\n".join(texts)
    if _contains_any(joined, ["\u592a\u957f", "\u522b\u8bf4\u90a3\u4e48\u591a", "\u5570\u55e6", "\u957f\u7bc7"]):
        disliked_patterns.append("long_explanation")
    if _contains_any(joined, ["\u522b\u95ee", "\u522b\u8ffd\u95ee", "\u4e0d\u60f3\u8bf4"]):
        disliked_patterns.append("over_questioning")
    if _contains_any(joined, ["\u592aAI", "\u50cf\u5ba2\u670d", "\u592a\u4e66\u9762", "\u592a\u5047"]):
        disliked_patterns.append("formal_tone")
    if _contains_any(joined, ["\u522b\u8bb2\u9053\u7406", "\u522b\u9e21\u6c64", "\u8bf4\u6559"]):
        disliked_patterns.append("preaching")

    if _contains_any(joined, ["\u65e0\u804a", "\u6478\u9c7c", "\u968f\u4fbf\u804a"]):
        emotional_needs.append("casual_chat")
    if _contains_any(joined, ["\u5b64\u72ec", "\u96be\u8fc7", "emo", "\u6ca1\u4ec0\u4e48\u60f3\u8bf4"]):
        emotional_needs.append("quiet_company")
    if _contains_any(joined, ["\u600e\u4e48\u529e", "\u7ea0\u7ed3", "\u6362\u5de5\u4f5c"]):
        emotional_needs.append("problem_clarity")

    base_persona = "warm_heal"
    if "intermittent_silence" in communication_style:
        base_persona = "minimal_sync"
    elif "casual_chat" in emotional_needs:
        base_persona = "playful_tease"
    elif "quiet_company" in emotional_needs:
        base_persona = "cool_melancholy"
    elif "problem_clarity" in emotional_needs:
        base_persona = "mature_restraint"

    return {
        "communication_style": communication_style,
        "base_persona": base_persona,
        "disliked_patterns": disliked_patterns,
        "emotional_needs": emotional_needs,
        "chat_rhythm": "slow_blank_space" if short_ratio >= 0.45 or minimal_ratio >= 0.35 else "steady",
    }
