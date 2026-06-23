TOPIC_KEYWORDS = {
    "pet": ["猫", "宠物", "狗", "喵", "猫咪"],
    "job": ["工作", "换工作", "辞职", "上班", "同事", "老板", "职场"],
    "sleep": ["睡", "熬夜", "失眠", "睡不着"],
    "stress": ["压力", "撑不住", "焦虑", "崩溃"],
    "feedback": ["重复", "模板", "太ai", "AI感", "机械", "不像", "油腻", "假"],
    "body": ["肚子疼", "头疼", "胃疼", "不舒服", "窜稀", "拉肚子"],
}

MEMORY_TYPE_TOPICS = {
    "feedback": "feedback",
    "preference": "feedback",
    "boundary": "feedback",
    "health": "body",
    "habit": "sleep",
}


def _contains_any(text: str, words: list[str]) -> bool:
    lowered = text.lower()
    return any(word.lower() in lowered for word in words)


def _matched_topics(text: str) -> set[str]:
    return {
        topic
        for topic, words in TOPIC_KEYWORDS.items()
        if _contains_any(text, words)
    }


def _memory_topics(memory: dict) -> set[str]:
    haystack = " ".join([
        str(memory.get("key", "")),
        str(memory.get("value", "")),
        str(memory.get("type", "")),
    ])
    topics = _matched_topics(haystack)
    mapped = MEMORY_TYPE_TOPICS.get(str(memory.get("type", "")))
    if mapped:
        topics.add(mapped)
    return topics


def _keyword_score(text: str, memory: dict) -> float:
    text_topics = _matched_topics(text)
    if not text_topics:
        return 0.0
    memory_topics = _memory_topics(memory)
    overlap = text_topics & memory_topics
    if not overlap:
        return 0.0
    return float(len(overlap))


def select_memories(text: str, memories: list[dict], relationship: dict, limit: int = 3) -> list[dict]:
    scored = []
    for memory in memories:
        relevance = _keyword_score(text, memory)
        if relevance <= 0:
            continue
        salience = float(memory.get("salience", 0.5))
        trust_boost = float(relationship.get("trust", 0.1)) * 0.1
        scored.append((relevance * 2 + salience + trust_boost, memory))
    scored.sort(key=lambda item: item[0], reverse=True)
    return [memory for _, memory in scored[:limit]]


def extract_memory_candidates(text: str) -> list[dict]:
    candidates = []
    clean = str(text or "")

    if "换工作" in clean or ("工作" in clean and any(word in clean for word in ["考虑", "想", "不敢", "压力", "辞职", "上班"])):
        candidates.append({
            "key": "job_change",
            "value": "用户最近提到工作或换工作的压力",
            "type": "episodic",
            "emotion": "uncertain",
            "salience": 0.82,
        })
    if any(word in clean for word in ["猫", "猫咪", "宠物", "狗"]):
        candidates.append({
            "key": "pet",
            "value": "用户提到家里的宠物",
            "type": "profile",
            "emotion": "warm",
            "salience": 0.7,
        })
    if any(word in clean for word in ["熬夜", "睡不着", "失眠"]):
        candidates.append({
            "key": "sleep_pattern",
            "value": "用户最近睡眠状态不太稳定",
            "type": "habit",
            "emotion": "care",
            "salience": 0.76,
        })
    if _contains_any(clean, TOPIC_KEYWORDS["feedback"]):
        candidates.append({
            "key": "feedback_naturalness",
            "value": "用户反馈回复有重复、模板、机械或AI感时，需要减少策略感和固定话术",
            "type": "feedback",
            "emotion": "friction",
            "salience": 0.9,
        })
    if _contains_any(clean, TOPIC_KEYWORDS["body"]):
        candidates.append({
            "key": "body_discomfort_recent",
            "value": "用户近期提到身体不舒服，需要先接住不适感，避免生硬追问",
            "type": "health",
            "emotion": "care",
            "salience": 0.78,
        })

    unique = []
    seen = set()
    for candidate in candidates:
        marker = (candidate.get("key"), candidate.get("value"))
        if marker in seen:
            continue
        seen.add(marker)
        unique.append(candidate)
    return unique
