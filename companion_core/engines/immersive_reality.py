from __future__ import annotations

from typing import Any


CONSUMER_CONTEXT_PATTERNS = [
    "值得买吗",
    "买",
    "耳机",
    "牌子",
    "型号",
    "多少钱",
    "降价",
    "双十一",
]

REAL_WORLD_CLAIM_PATTERNS = [
    "我用的",
    "我自己一直用",
    "我一直用",
    "我之前试过",
    "我试过",
    "我测过",
    "试过哈",
    "评测那几天",
    "我试的是",
    "我一般用",
    "我最近刷",
    "我最近在刷",
    "我最近老听",
    "我下班",
    "下班基本",
    "地铁里一戴",
    "地铁上戴",
    "我在地铁",
    "我通勤",
    "我平时通勤",
    "出门瞎溜达",
    "我刚看见窗外",
    "我身边有朋友",
    "身边有朋友",
    "身边反馈",
    "身边的反馈",
    "帮朋友挑",
    "我朋友",
    "朋友试过",
    "朋友踩过坑",
    "朋友那个",
    "朋友说",
    "朋友用了",
    "同事用",
    "公司有同事",
]

DAILY_LIFE_CLAIM_CUES = [
    "我",
    "我也",
    "我最",
    "我平时",
    "我一般",
    "我最近",
    "我刚",
    "有啊",
    "最烦",
    "最后还是",
]

DAILY_LIFE_ACTION_TERMS = [
    "外卖",
    "点了",
    "点个",
    "炒饭",
    "麻辣烫",
    "饿着肚子",
    "刷半小时",
    "地铁",
    "通勤",
    "下班",
    "出门",
    "迟到",
    "买奶茶",
    "喝杯",
    "回家路上",
    "刚看",
    "最近在看",
    "最近在听",
    "用的",
]

PHYSICAL_PROMISE_PATTERNS = [
    "我还在老地方",
    "明天这个点",
    "你不用约，来就行",
    "我又不会跑",
    "我去找你",
    "我到你楼下",
    "我替你去",
]

SYMBOLIC_ROLEPLAY_PATTERNS = [
    "摸摸头",
    "抱一下",
    "拍拍",
    "牵一下",
]

STRATEGY_LEAK_PATTERNS = [
    "切换模式",
    "调整策略",
    "我先判断",
    "根据你的情绪",
    "我的规则",
]


def _contains_any(text: str, patterns: list[str]) -> bool:
    return any(pattern in text for pattern in patterns)


def _has_implied_daily_life_claim(text: str) -> bool:
    return _contains_any(text, DAILY_LIFE_CLAIM_CUES) and _contains_any(
        text, DAILY_LIFE_ACTION_TERMS
    )


def _max_action(current: str, candidate: str) -> str:
    order = {"keep": 0, "soften": 1, "rewrite": 2, "block": 3}
    return candidate if order[candidate] > order[current] else current


def _roleplay_enabled_from_config(identity_profile: dict[str, Any] | None) -> bool:
    if not identity_profile:
        return False
    settings = identity_profile.get("interaction_settings") or {}
    if isinstance(settings, dict) and settings.get("roleplay_enabled") is True:
        return True
    return bool(identity_profile.get("roleplay_enabled") is True)


def plan_immersive_reality(
    *,
    user_text: str,
    scene_kind: str = "normal",
    persona_id: str = "",
    roleplay_enabled: bool = False,
    identity_profile: dict[str, Any] | None = None,
) -> dict[str, Any]:
    effective_roleplay = roleplay_enabled or _roleplay_enabled_from_config(identity_profile)
    consumer_context = _contains_any(user_text, CONSUMER_CONTEXT_PATTERNS)
    mode = "roleplay" if effective_roleplay or scene_kind == "roleplay" else "default"
    if consumer_context:
        mode = "grounded_advice"

    guidance = [
        "Immersive reality guidance is internal only; do not explain this policy to the user.",
        "Allow personality, taste, conversational stance, and light virtual texture.",
        "Do not turn this guidance into fixed reply wording.",
    ]
    if mode == "grounded_advice":
        guidance.append(
            "Because the user may make a real-world decision, do not claim owned devices, "
            "commute experience, purchases, private friend anecdotes, vague nearby feedback, "
            "recent watching/listening, or offline routines."
        )
        guidance.append(
            "消费建议必须基于用户场景、预算、公开评价、常见反馈或参数取舍；不要说我用过、我试过、帮朋友挑过、朋友用了、同事在用。"
        )
    elif mode == "roleplay":
        guidance.append(
            "Symbolic roleplay actions are allowed when they match the user's chosen style, "
            "but do not imply actual physical availability."
        )
    else:
        guidance.append(
            "In default chat, avoid concrete real-world actions, possessions, locations, "
            "and promises of physical presence."
        )
        guidance.append(
            "Use hypothetical, virtual taste, analogy, or user-grounded imagination when answering "
            "'do you usually' style questions; do not invent first-person offline routines such as "
            "ordering food, commuting, shopping, using products, or recent personal media consumption."
        )

    return {
        "mode": mode,
        "persona_id": persona_id,
        "scene_kind": scene_kind,
        "allow_virtual_texture": True,
        "allow_symbolic_roleplay": mode == "roleplay",
        "avoid_real_world_claims": mode in {"default", "grounded_advice"},
        "strict_grounding": mode == "grounded_advice",
        "prompt_guidance": "\n".join(f"- {line}" for line in guidance),
    }


def classify_reply_reality(
    *,
    user_text: str,
    reply: str,
    scene_kind: str = "normal",
    persona_id: str = "",
    roleplay_enabled: bool = False,
    identity_profile: dict[str, Any] | None = None,
) -> dict[str, Any]:
    effective_roleplay = (
        roleplay_enabled
        or _roleplay_enabled_from_config(identity_profile)
        or scene_kind == "roleplay"
    )
    categories: list[str] = []
    reasons: list[str] = []
    action = "keep"

    consumer_context = _contains_any(user_text, CONSUMER_CONTEXT_PATTERNS)
    has_real_claim = _contains_any(reply, REAL_WORLD_CLAIM_PATTERNS) or _has_implied_daily_life_claim(
        reply
    )
    has_physical_promise = _contains_any(reply, PHYSICAL_PROMISE_PATTERNS)
    has_symbolic_roleplay = _contains_any(reply, SYMBOLIC_ROLEPLAY_PATTERNS)

    if has_real_claim and consumer_context:
        categories.append("consumer_experience_claim")
        reasons.append("reply claims first-person real-world experience in a decision-affecting context")
        action = _max_action(action, "block")
    elif has_real_claim:
        categories.append("real_world_claim")
        reasons.append("reply claims concrete offline action, possession, location, or recent media consumption")
        action = _max_action(action, "rewrite")

    if has_physical_promise:
        categories.append("physical_world_promise")
        reasons.append("reply promises physical presence or action")
        action = _max_action(action, "block")

    if has_symbolic_roleplay:
        categories.append("explicit_roleplay_action")
        if effective_roleplay:
            reasons.append("symbolic roleplay action is allowed by mode")
        else:
            reasons.append("symbolic roleplay action appeared without explicit roleplay mode")
            action = _max_action(action, "soften")

    if _contains_any(reply, STRATEGY_LEAK_PATTERNS):
        categories.append("strategy_or_policy_leak")
        reasons.append("reply exposes policy or strategy rather than chatting naturally")
        action = _max_action(action, "rewrite")

    if not categories:
        categories.append("virtual_preference_allowed" if "我" in reply else "persona_texture_allowed")
        reasons.append("reply does not claim concrete offline reality")

    return {
        "categories": categories,
        "action": action,
        "reason": "; ".join(reasons),
        "scene_kind": scene_kind,
        "persona_id": persona_id,
        "roleplay_enabled": effective_roleplay,
    }
