RELATIONSHIP_KEYS = {
    "intimacy": 0.1,
    "trust": 0.1,
    "attachment": 0.1,
    "humor": 0.4,
    "activity": 0.5,
    "rationality": 0.5,
    "sensibility": 0.5,
    "safety": 0.2,
    "loneliness": 0.3,
    "expressiveness": 0.4,
}


def clamp(value: float) -> float:
    return max(0.0, min(1.0, round(value, 4)))


def default_relationship() -> dict:
    return dict(RELATIONSHIP_KEYS)


def update_relationship(current: dict | None, text: str, recent_messages: list[dict]) -> dict:
    relationship = {**default_relationship(), **(current or {})}
    emotional_words = ["累", "撑不住", "难受", "烦", "崩溃", "孤独", "想哭", "压力", "焦虑"]
    playful_words = ["哈哈", "笑死", "离谱", "绝了", "摸鱼"]

    if any(word in text for word in emotional_words):
        relationship["trust"] = clamp(relationship["trust"] + 0.04)
        relationship["safety"] = clamp(relationship["safety"] + 0.05)
        relationship["sensibility"] = clamp(relationship["sensibility"] + 0.03)
        relationship["expressiveness"] = clamp(relationship["expressiveness"] + 0.02)

    if any(word in text for word in playful_words):
        relationship["humor"] = clamp(relationship["humor"] + 0.04)
        relationship["activity"] = clamp(relationship["activity"] + 0.02)

    if len(text.strip()) >= 18:
        relationship["intimacy"] = clamp(relationship["intimacy"] + 0.02)
        relationship["expressiveness"] = clamp(relationship["expressiveness"] + 0.02)

    if len(recent_messages) >= 6:
        relationship["attachment"] = clamp(relationship["attachment"] + 0.01)

    return relationship
