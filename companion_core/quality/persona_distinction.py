def analyze_persona_distinction(records: list[dict]) -> dict:
    if not records:
        return {"distinction_score": 0.0, "flattened": True, "reason": "no records"}

    persona_ids = {item.get("personaId") for item in records}
    plans = [item.get("personaPlan", "") for item in records]
    replies = [item.get("reply", "") for item in records]
    unique_plans = len(set(plans))
    unique_replies = len(set(replies))

    plan_score = unique_plans / max(1, len(persona_ids))
    reply_score = unique_replies / max(1, len(records))
    distinction_score = round((plan_score * 0.55) + (reply_score * 0.45), 4)
    flattened = distinction_score < 0.4 or (unique_plans == 1 and len(persona_ids) >= 3)

    return {
        "distinction_score": distinction_score,
        "flattened": flattened,
        "persona_count": len(persona_ids),
        "unique_persona_plans": unique_plans,
        "unique_replies": unique_replies,
        "reason": "personas collapsed into the same plan/reply" if flattened else "personas show measurable difference",
    }
