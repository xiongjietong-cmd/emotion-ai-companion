def evolve_personality(relationship: dict, recent_messages: list[dict]) -> dict:
    loneliness = float(relationship.get("loneliness", 0.3))
    humor = float(relationship.get("humor", 0.4))
    rationality = float(relationship.get("rationality", 0.5))
    sensibility = float(relationship.get("sensibility", 0.5))
    trust = float(relationship.get("trust", 0.1))

    tone = "warm"
    if humor > 0.65:
        tone = "playful"
    if loneliness > 0.7:
        tone = "steady_closeness"

    return {
        "tone": tone,
        "clinginess": min(1.0, 0.25 + loneliness * 0.35 + trust * 0.15),
        "teasing": min(1.0, humor * 0.8),
        "directness": min(1.0, rationality * 0.75),
        "empathy": min(1.0, 0.35 + sensibility * 0.55),
        "initiative": min(1.0, 0.35 + loneliness * 0.45 + trust * 0.1),
        "question_depth": min(1.0, 0.3 + trust * 0.5),
    }
