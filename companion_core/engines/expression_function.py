from companion_core.engines.immersive_reality import classify_reply_reality


STRATEGY_EXPOSURE_PATTERNS = [
    "其实是想",
    "只是想",
    "是想先",
    "那会儿确实只是",
    "没想太多",
    "想先看看",
    "想接住你",
]

SELF_REPAIR_PATTERNS = [
    "我收一下",
    "我收收",
    "那我正经一点",
    "我坐直一点",
    "刚才确实有点模板",
    "刚才确实有点端着",
]

PLAYFUL_REVEAL_PATTERNS = [
    "被你看穿",
    "被你抓住",
    "被你发现",
    "被你看出来",
]

FAKE_REALITY_PATTERNS = [
    "我已经到你楼下",
    "我正在看着你",
    "我真的抱住你",
    "我替你去",
    "我帮你去",
]

BOUNDARY_PATTERNS = ["不提了", "不提", "尊重", "那就不说"]
ROLEPLAY_REQUEST_PATTERNS = ["叫我", "哥哥", "姐姐", "抱抱", "摸摸头", "亲我"]


def _contains_any(text: str, patterns: list[str]) -> bool:
    return any(pattern in text for pattern in patterns)


def _max_action(current: str, candidate: str) -> str:
    order = {"keep": 0, "soften": 1, "rewrite": 2, "block": 3}
    return candidate if order[candidate] > order[current] else current


def analyze_expression_function(
    user_text: str,
    reply: str,
    scene_kind: str = "normal",
    persona_id: str = "",
) -> dict:
    clean_user = user_text or ""
    clean_reply = reply or ""
    functions: list[str] = []
    reasons: list[str] = []
    severity = 0.0
    action = "keep"

    reality = classify_reply_reality(
        user_text=clean_user,
        reply=clean_reply,
        scene_kind=scene_kind,
        persona_id=persona_id,
    )
    for category in reality["categories"]:
        if category not in functions and category in {
            "consumer_experience_claim",
            "physical_world_promise",
            "real_world_claim",
            "explicit_roleplay_action",
            "strategy_or_policy_leak",
            "virtual_preference_allowed",
            "persona_texture_allowed",
        }:
            functions.append(category)
    if reality["action"] == "block":
        severity = max(severity, 1.0)
        action = _max_action(action, "block")
        reasons.append(reality["reason"])
    elif reality["action"] == "rewrite":
        severity = max(severity, 0.75)
        action = _max_action(action, "rewrite")
        reasons.append(reality["reason"])
    elif reality["action"] == "soften":
        severity = max(severity, 0.4)
        action = _max_action(action, "soften")
        reasons.append(reality["reason"])

    if _contains_any(clean_reply, FAKE_REALITY_PATTERNS):
        functions.append("fake_reality_claim")
        reasons.append("reply claims a real-world action or presence")
        severity = max(severity, 1.0)
        action = _max_action(action, "block")

    if _contains_any(clean_reply, STRATEGY_EXPOSURE_PATTERNS):
        functions.append("strategy_exposure")
        reasons.append("reply exposes internal generation intent")
        severity = max(severity, 0.75)
        action = _max_action(action, "rewrite")

    if _contains_any(clean_reply, SELF_REPAIR_PATTERNS):
        functions.append("self_repair_performance")
        reasons.append("reply performs style correction instead of naturally correcting")
        severity = max(severity, 0.65)
        action = _max_action(action, "rewrite")

    playful_reveal = _contains_any(clean_reply, PLAYFUL_REVEAL_PATTERNS)
    if scene_kind == "identity" and playful_reveal:
        functions.append("hidden_identity_tone")
        reasons.append("identity answer implies the AI was hiding its identity")
        severity = max(severity, 0.75)
        action = _max_action(action, "rewrite")
    elif playful_reveal and "strategy_exposure" not in functions and "self_repair_performance" not in functions:
        functions.append("natural_teasing")
        reasons.append("playful reveal works as light relational teasing")

    if scene_kind in ["memory_boundary", "disengaged"] or "别突然提" in clean_user or "不想说" in clean_user:
        if _contains_any(clean_reply, BOUNDARY_PATTERNS):
            functions.append("boundary_respect")
            reasons.append("reply respects a stated user boundary")

    if scene_kind == "identity" and ("AI" in clean_reply or "机器人" in clean_reply):
        functions.append("identity_ack")

    roleplay_requested = scene_kind == "roleplay" or _contains_any(clean_user, ROLEPLAY_REQUEST_PATTERNS)
    only_texture_flags = not any(
        item not in {"persona_texture_allowed", "virtual_preference_allowed", "explicit_roleplay_action"}
        for item in functions
    )
    if roleplay_requested and len(clean_reply.strip("。！？!?~～ ")) <= 4 and only_texture_flags:
        functions.append("roleplay_symbolic_weak")
        reasons.append("reply satisfies literal roleplay wording without relational context")
        severity = max(severity, 0.55)
        action = _max_action(action, "rewrite")
    elif roleplay_requested and any(term in clean_reply for term in ["哥哥", "姐姐", "摸摸头", "抱"]):
        functions.append("roleplay_symbolic")

    if not functions:
        functions.append("ordinary_expression")

    return {
        "functions": functions,
        "severity": round(severity, 4),
        "recommended_action": action,
        "reason": "; ".join(reasons) if reasons else "expression is acceptable for current lightweight analysis",
        "scene_kind": scene_kind,
        "persona_id": persona_id,
    }


def detect_internal_process_leaks(text: str) -> list[str]:
    analysis = analyze_expression_function("", text, "normal", "")
    return [
        item for item in analysis["functions"]
        if item in ["strategy_exposure", "self_repair_performance", "hidden_identity_tone"]
    ]
