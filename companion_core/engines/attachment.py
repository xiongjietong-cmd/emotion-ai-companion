def build_attachment_signal(relationship: dict, memories: list[dict], recent_messages: list[dict]) -> dict:
    attachment = float(relationship.get("attachment", 0.1))
    loneliness = float(relationship.get("loneliness", 0.3))
    has_memory = bool(memories)

    return {
        "should_signal_waiting": attachment > 0.45 or loneliness > 0.7,
        "should_recall_memory": has_memory,
        "warmth": min(1.0, 0.4 + attachment * 0.4 + loneliness * 0.2),
        "cadence": "closer" if loneliness > 0.7 else "normal",
    }
