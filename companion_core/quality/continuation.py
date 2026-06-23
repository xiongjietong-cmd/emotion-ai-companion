DEAD_END_REPLIES = {"好的", "嗯", "哦", "知道了", "早点休息。", "加油。"}
FORCED_QUESTION_MARKERS = ["为什么", "发生了什么", "详细说说", "具体怎么了"]


def evaluate_continuation(case: dict, user_text: str, reply: str) -> dict:
    scene = case.get("expected_scene", "normal")
    clean_reply = (reply or "").strip()
    clean_user = user_text or ""
    score = 0.62
    reasons: list[str] = []

    if clean_reply in DEAD_END_REPLIES:
        score -= 0.35
        reasons.append("dead_end_reply")

    if any(marker in clean_reply for marker in FORCED_QUESTION_MARKERS):
        score -= 0.25
        reasons.append("forced_question")

    if scene in ["memory_boundary", "disengaged"] and ("不说" in clean_reply or "不提" in clean_reply):
        score += 0.18
        reasons.append("boundary_respected")

    if scene in ["low_mood", "ai_feedback"] and 10 <= len(clean_reply) <= 90 and clean_reply not in DEAD_END_REPLIES:
        score += 0.12
        reasons.append("right_sized")

    if "?" in clean_reply or "？" in clean_reply:
        score += 0.06
        reasons.append("has_opening")

    if len(clean_user) <= 4 and len(clean_reply) <= 18:
        score += 0.08
        reasons.append("matches_short_rhythm")

    score = round(max(0.0, min(1.0, score)), 4)
    if score >= 0.9:
        label = "continue_likely"
    elif score >= 0.6:
        label = "continue_possible"
    elif score >= 0.25:
        label = "conversation_stalls"
    else:
        label = "user_likely_annoyed"

    return {"score": score, "label": label, "reasons": reasons}
