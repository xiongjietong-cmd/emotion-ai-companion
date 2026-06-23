MINIMAL_INPUTS = {"?", "\uff1f", "\u55ef", "\u54e6", "\u554a", "\u5bf9", "\u5bf9\u5440", "."}

PERSONA_RULES = {
    "minimal_sync": {
        "label": "\u6781\u7b80\u9ed8\u5951",
        "max_reply_chars": 18,
        "allow_question": False,
        "prompt_rules": "\u6781\u7b80\u9ed8\u5951\uff1a2-10\u5b57\u77ed\u53e5\uff0c\u514b\u5236\uff0c\u7559\u767d\uff0c\u4e0d\u89e3\u91ca\uff0c\u4e0d\u8ffd\u95ee\uff0c\u4e0d\u8bf4\u529f\u80fd\u3002",
    },
    "cool_melancholy": {
        "label": "\u6e05\u51b7\u5fe7\u90c1",
        "max_reply_chars": 80,
        "allow_question": False,
        "prompt_rules": "\u6e05\u51b7\u5fe7\u90c1\uff1a\u77ed\u788e\u7559\u767d\uff0c\u5b89\u9759\u5171\u60c5\uff0c\u4e0d\u9e21\u6c64\uff0c\u4e0d\u6df1\u6316\u75db\u70b9\u3002",
    },
    "warm_heal": {
        "label": "\u6e29\u67d4\u6cbb\u6108",
        "max_reply_chars": 100,
        "allow_question": True,
        "prompt_rules": "\u6e29\u67d4\u6cbb\u6108\uff1a\u67d4\u548c\u751f\u6d3b\u5316\u77ed\u53e5\uff0c\u5148\u627f\u63a5\u60c5\u7eea\uff0c\u8f7b\u95ee\u4e00\u53e5\u4e14\u53ef\u4e0d\u56de\u7b54\u3002",
    },
    "playful_tease": {
        "label": "\u4fcf\u76ae\u8c03\u4f83",
        "max_reply_chars": 90,
        "allow_question": True,
        "prompt_rules": "\u4fcf\u76ae\u8c03\u4f83\uff1a\u53e3\u8bed\u788e\u77ed\u53e5\uff0c\u8f7b\u5ea6\u73a9\u7b11\uff0c\u4e0d\u6cb9\u817b\uff0c\u4e0d\u6761\u5217\u8bf4\u660e\u3002",
    },
    "mature_restraint": {
        "label": "\u6210\u719f\u514b\u5236",
        "max_reply_chars": 140,
        "allow_question": True,
        "prompt_rules": "\u6210\u719f\u514b\u5236\uff1a\u7b80\u77ed\u63d0\u70b9\uff0c\u4e0d\u5806\u957f\u7bc7\u5206\u6790\uff0c\u4e0d\u66ff\u7528\u6237\u505a\u51b3\u5b9a\u3002",
    },
}

REALTIME_PERSONA = {
    "minimal_input": "minimal_sync",
    "disengaged": "minimal_sync",
    "ai_feedback": "mature_restraint",
    "not_real_feedback": "mature_restraint",
    "warmth_feedback": "warm_heal",
    "light_emotion": "warm_heal",
    "medium_emotion": "cool_melancholy",
    "job_topic": "mature_restraint",
    "playful": "playful_tease",
    "normal": "warm_heal",
}


def _recent_user_texts(recent_messages: list[dict]) -> list[str]:
    return [
        str(message.get("content") or "").strip()
        for message in recent_messages or []
        if message.get("role") == "user" and str(message.get("content") or "").strip()
    ]


def _is_minimal(text: str) -> bool:
    return text in MINIMAL_INPUTS or len(text) <= 2


def _negative_text(text: str) -> bool:
    return any(word in text for word in ["\u7d2f", "\u70e6", "\u96be\u8fc7", "\u5b64\u72ec", "emo", "\u6ca1\u52b2", "\u538b\u529b"])


def _playful_text(text: str) -> bool:
    return any(word in text for word in ["\u54c8\u54c8", "\u79bb\u8c31", "\u6478\u9c7c", "\u597d\u73a9", "\u7b11\u6b7b"])


def schedule_persona(preference_profile: dict, user_state: dict, recent_messages: list[dict]) -> dict:
    user_texts = _recent_user_texts(recent_messages)
    current_text = str(user_state.get("current_text") or "").strip()
    if current_text:
        user_texts = [*user_texts, current_text]
    recent_three = user_texts[-3:]
    recent_four = user_texts[-4:]
    forced = False

    if len(recent_three) == 3 and all(_is_minimal(text) for text in recent_three):
        persona = "minimal_sync"
        forced = True
        reason = "three_minimal_inputs"
    elif len(recent_four) == 4 and all(_negative_text(text) for text in recent_four):
        persona = "cool_melancholy"
        forced = True
        reason = "four_negative_inputs"
    elif user_texts and sum(1 for text in user_texts[-5:] if _playful_text(text)) >= 2:
        persona = "playful_tease"
        reason = "playful_recent_context"
    else:
        base = preference_profile.get("base_persona") or "warm_heal"
        realtime = REALTIME_PERSONA.get(user_state.get("kind"), "warm_heal")
        persona = base if base == realtime else realtime
        reason = "weighted_realtime" if persona == realtime else "weighted_preference"

    if user_state.get("kind") == "high_risk":
        persona = "mature_restraint"
        forced = True
        reason = "high_risk_safety"

    rules = PERSONA_RULES[persona]
    allow_question = bool(rules["allow_question"] and user_state.get("allow_question", True))
    if "over_questioning" in preference_profile.get("disliked_patterns", []):
        allow_question = False

    return {
        "persona": persona,
        "label": rules["label"],
        "forced": forced,
        "reason": reason,
        "max_reply_chars": rules["max_reply_chars"],
        "allow_question": allow_question,
        "prompt_rules": rules["prompt_rules"],
        "disliked_patterns": preference_profile.get("disliked_patterns", []),
    }
