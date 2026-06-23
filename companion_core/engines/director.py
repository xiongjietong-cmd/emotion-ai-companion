def decide_conversation_goal(text: str, relationship: dict, memories: list[dict], persona: dict) -> dict:
    avoid = ["direct_advice", "customer_service_tone", "dead_end_reply"]
    tired_words = ["累", "撑不住", "压力", "烦", "难受", "焦虑"]
    short_text = text.strip()

    if short_text in ["你好", "嗨", "哈喽", "hello", "Hello"]:
        primary = "warm_open"
        secondary = ["light_observation", "invite_context"]
        hook = "ask_what_brought_user_here"
    elif short_text in ["什么", "啊", "啊？", "啊！", "嗯？", "?"]:
        primary = "playful_clarify"
        secondary = ["repair_context", "light_tease"]
        hook = "ask_what_happened"
    elif memories and any(word in text for word in ["最近", "怎么样", "工作", "猫", "睡"]):
        primary = "memory_recall"
        secondary = ["emotion_ack", "gentle_probe"]
        hook = "connect_memory_to_present"
    elif any(word in text for word in tired_words):
        primary = "gentle_probe"
        secondary = ["emotion_ack", "care"]
        hook = "lower_pressure_first"
    else:
        primary = "emotion_ack"
        secondary = ["observation", "topic_expand"]
        hook = "ask_for_inner_context"

    return {
        "primary_goal": primary,
        "secondary_goals": secondary,
        "avoid": avoid,
        "next_turn_hook": hook,
    }
