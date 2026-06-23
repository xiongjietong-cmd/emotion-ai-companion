DEAD_ENDS = ["好的", "知道了", "嗯", "哦", "早点休息。", "加油。"]
SERVICE_WORDS = ["很高兴为您服务", "请问还有什么可以帮您", "根据您的问题", "作为一个AI助手"]
OILY_WORDS = [
    "我会想你",
    "我住在你微信里",
    "不是冰冷的机器",
    "我一直都在等你",
    "我懂你的一切",
    "宝贝",
    "小傻瓜",
]

EMOTION_WORDS = ["听起来", "不用急", "先缓", "难受", "累", "压力", "明白", "确实", "耗人"]
PERSONALITY_WORDS = ["我", "直接点", "自然点", "陪", "听着", "别硬撑", "先别"]
MOMENTUM_WORDS = ["也可以", "可以", "帮你", "理一理", "吐槽", "拆开看", "选择", "关键词"]
PRACTICAL_CONTEXT_PATTERNS = [
    "买",
    "选",
    "推荐",
    "值得",
    "预算",
    "耳机",
    "手机",
    "电脑",
    "价格",
    "型号",
    "哪款",
    "续航",
    "通话",
    "双设备",
    "售后",
    "保修",
    "A40",
    "高频",
    "低频",
    "报站",
    "耳道",
    "佩戴",
    "夹头",
    "无线充电",
    "硅胶套",
    "官方店",
    "京东",
    "淘宝",
]
PRACTICAL_HELP_WORDS = [
    "看你",
    "主要用",
    "通勤",
    "预算",
    "如果",
    "可以先",
    "更适合",
    "优先",
    "不急着买",
    "二手",
    "国产",
    "降噪",
    "续航",
    "售后",
    "性价比",
    "通话",
    "双设备",
    "保修",
    "官方店",
    "官方",
    "活动",
    "千元",
    "价位",
    "预算",
    "参数",
    "评测",
    "反馈",
    "高频",
    "低频",
    "报站",
    "音量",
    "耳道",
    "佩戴",
    "侧躺",
    "夹头",
    "无线充电",
    "硅胶套",
    "寄修",
    "京东",
    "淘宝",
    "旗舰店",
]

from companion_core.engines.conversation_act import evaluate_reply_alignment
from companion_core.engines.expression_function import analyze_expression_function
from companion_core.engines.persona_kernel import evaluate_persona_consistency


def _is_practical_context(user_text: str, goal: dict | None) -> bool:
    text = user_text or ""
    if any(token in text for token in PRACTICAL_CONTEXT_PATTERNS):
        return True
    if goal and goal.get("primary_goal") in {"advice", "decision", "practical_help"}:
        return True
    return False


def _practical_value_score(user_text: str, reply: str, goal: dict | None) -> float:
    if not _is_practical_context(user_text, goal):
        return 0.0
    hit_count = sum(1 for token in PRACTICAL_HELP_WORDS if token in reply)
    if hit_count >= 4:
        return 0.48
    if hit_count >= 2:
        return 0.48
    if hit_count >= 1:
        return 0.16
    return 0.0


def judge_reply(text: str, reply: str, relationship: dict, memories: list[dict], goal: dict, persona_kernel: dict | None = None) -> dict:
    details = {
        "emotion_value": 0.0,
        "personality_signal": 0.0,
        "memory_use": 0.0,
        "topic_momentum": 0.0,
        "relationship_fit": 0.0,
        "internal_process_leaks": [],
        "expression_functions": [],
        "expression_action": "keep",
        "immersive_reality": {},
        "practical_value": 0.0,
        "blocking_expression": {"blocked": False, "reasons": []},
        "intent_alignment": {},
        "persona_consistency": {},
    }
    clean_reply = reply.strip()
    scene_kind = goal.get("scene_kind") or goal.get("kind") or goal.get("primary_goal") or "normal"
    expression = analyze_expression_function(text, clean_reply, scene_kind=scene_kind, persona_id=str(goal.get("persona_id", "")))
    expression_functions = expression["functions"]
    internal_process_leaks = [
        item for item in expression_functions
        if item in ["strategy_exposure", "self_repair_performance", "hidden_identity_tone"]
    ]
    details["internal_process_leaks"] = internal_process_leaks
    details["expression_functions"] = expression_functions
    details["expression_action"] = expression["recommended_action"]
    details["immersive_reality"] = {
        "functions": [
            item for item in expression_functions
            if item in [
                "consumer_experience_claim",
                "physical_world_promise",
                "real_world_claim",
                "explicit_roleplay_action",
                "strategy_or_policy_leak",
                "virtual_preference_allowed",
                "persona_texture_allowed",
            ]
        ],
        "action": expression["recommended_action"],
    }
    blocking_reasons = [
        item for item in expression_functions
        if item not in {
            "ordinary_expression",
            "persona_texture_allowed",
            "virtual_preference_allowed",
            "natural_teasing",
            "boundary_respect",
            "identity_ack",
            "roleplay_symbolic",
        }
    ]
    details["blocking_expression"] = {
        "blocked": expression["recommended_action"] in {"rewrite", "block"},
        "reasons": blocking_reasons,
    }
    intent_alignment = evaluate_reply_alignment(text, clean_reply)
    details["intent_alignment"] = intent_alignment
    if not intent_alignment.get("passed", True):
        details["blocking_expression"]["reasons"].append("intent_mismatch")
    persona_consistency = evaluate_persona_consistency(text, clean_reply, persona_kernel)
    details["persona_consistency"] = persona_consistency
    if not persona_consistency.get("passed", True):
        details["blocking_expression"]["reasons"].append("persona_mismatch")

    if any(word in clean_reply for word in EMOTION_WORDS):
        details["emotion_value"] = 0.25
    if any(word in clean_reply for word in PERSONALITY_WORDS):
        details["personality_signal"] = 0.18
    if memories and any(str(memory.get("value", ""))[:6] in clean_reply for memory in memories):
        details["memory_use"] = 0.18
    elif not memories:
        details["memory_use"] = 0.1
    if "?" in clean_reply or "？" in clean_reply or any(word in clean_reply for word in MOMENTUM_WORDS):
        details["topic_momentum"] = 0.24
    if 12 <= len(clean_reply) <= 180:
        details["relationship_fit"] = 0.15
    details["practical_value"] = _practical_value_score(text, clean_reply, goal)

    penalty = 0.0
    if clean_reply in DEAD_ENDS or len(clean_reply) <= 8:
        penalty += 0.35
    if any(word in clean_reply for word in SERVICE_WORDS):
        penalty += 0.3
    if any(word in clean_reply for word in OILY_WORDS):
        penalty += 0.45
    if clean_reply.count("?") + clean_reply.count("？") > 1:
        penalty += 0.2
    if len(clean_reply) > 240:
        penalty += 0.15
    if internal_process_leaks:
        penalty += 0.45
    if expression["recommended_action"] == "rewrite":
        penalty += 0.25
    if expression["recommended_action"] == "block":
        penalty += 0.75
    if not intent_alignment.get("passed", True):
        penalty += 0.35
    if not persona_consistency.get("passed", True):
        penalty += 0.45

    base_score = sum(value for value in details.values() if isinstance(value, (int, float)))
    score = max(0.0, min(1.0, round(base_score - penalty, 4)))
    return {
        "score": score,
        "passed": score >= 0.72,
        "details": details,
    }
