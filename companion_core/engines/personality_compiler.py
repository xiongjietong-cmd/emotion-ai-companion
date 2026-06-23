def _clean_text(value, default: str = "") -> str:
    text = str(value or "").strip()
    return text or default


def _clamp_float(value, default: float = 0.5) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError):
        number = default
    return max(0.0, min(1.0, round(number, 4)))


def _string_list(value, limit: int = 5) -> list[str]:
    if not isinstance(value, list):
        return []
    items = []
    for item in value:
        text = str(item or "").strip()
        if text:
            items.append(text)
    return items[:limit]


def _term_list(value, limit: int = 40) -> list[str]:
    if isinstance(value, list):
        raw_items = value
    else:
        text = str(value or "")
        for separator in ["，", "、", "\n", "\r", "\t", ";", "；"]:
            text = text.replace(separator, ",")
        raw_items = text.split(",")
    terms = []
    seen = set()
    for item in raw_items:
        term = str(item or "").strip()
        if term and term not in seen:
            terms.append(term)
            seen.add(term)
    return terms[:limit]


def compile_personality_config(config: dict | None) -> dict:
    raw = config or {}
    identity = raw.get("identity") if isinstance(raw.get("identity"), dict) else {}
    traits = raw.get("traits") or {}
    profile_name = _clean_text(raw.get("name") or identity.get("aiName"), "\u5c0f\u6696")
    custom_persona = _clean_text(raw.get("customPersona"))
    background = _clean_text(raw.get("background"))
    temperament = " / ".join(item for item in [custom_persona, background] if item)
    if not temperament:
        temperament = "自然、稳定、尊重用户节奏"

    return {
        "name": _clean_text(raw.get("name"), "小暖"),
        "name": profile_name,
        "temperament": temperament,
        "speech_style": _clean_text(raw.get("speakingStyle"), "自然口语，短句优先，不像客服"),
        "relationship_position": _clean_text(raw.get("relationshipPosition"), "用户亲手设定的陪伴对象"),
        "avoid": _clean_text(raw.get("avoidStyle"), "不要客服感，不要固定话术，不要过度说教"),
        "blocked_terms": _term_list(raw.get("blockedTerms")),
        "style_references": _string_list(raw.get("speechExamples")),
        "traits": {
            "warmth": _clamp_float(traits.get("warmth"), 0.6),
            "humor": _clamp_float(traits.get("humor"), 0.4),
            "directness": _clamp_float(traits.get("directness"), 0.5),
            "empathy": _clamp_float(traits.get("empathy"), 0.6),
        },
        "example_policy": "样例只用于学习语气、节奏和判断方式，不是固定话术，不要照抄。",
    }
