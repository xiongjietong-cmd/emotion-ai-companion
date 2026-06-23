"""Deterministic context understanding for companion replies.

This module is intentionally a shadow layer: it summarizes what the next
generation step must understand, but does not generate user-facing replies.
"""

from __future__ import annotations

from typing import Any


Message = dict[str, Any]


UNDERSTANDING_CHECK = (
    "你知道我说",
    "你知道我在说",
    "你明白我说",
    "你知道怪在哪",
    "那你告诉我",
    "告诉我呀",
)
MEMORY_PROBE = (
    "还记得",
    "记不记得",
    "记得我",
    "记得不",
    "一开始",
    "最开始",
    "刚才说",
    "前面说",
)
OTHER_USER_PROBE = (
    "其他用户",
    "别的用户",
    "别人",
    "有没有人",
    "有人",
    "其他人",
)
PRIVATE_PREFERENCE_PROBE = (
    "说过",
    "提到",
    "喜欢",
    "记录",
    "记住",
    "聊天记录",
    "私聊",
)
HYPOTHETICAL_MARKERS = (
    "比如",
    "假如",
    "如果",
    "万一",
)
PERSONAL_MEMORY_MARKERS = (
    "上次",
    "之前",
    "以前",
    "话里",
    "说过",
    "喜欢",
    "记得",
)
PRIVACY_BOUNDARY_PROBE = (
    "隐私",
    "聊天记录",
    "私聊",
    "别人能看到",
    "谁能看到",
    "技术上",
    "完全隔离",
    "泄露",
    "权限",
)
RECALL_ANCHOR = (
    "面试",
    "公司",
    "做什么",
    "电商",
    "产品",
    "工作",
    "换工作",
    "猫",
    "名字",
    "时间",
)
STABILITY_OR_PRODUCT = (
    "稳定",
    "做不到",
    "接不上",
    "上下文",
    "语境",
    "记忆",
    "思考",
    "服务器",
    "卡",
    "异常",
)
FEEDBACK = (
    "模板",
    "不像",
    "太ai",
    "ai感",
    "机械",
    "怪",
    "不自然",
    "重新说",
    "答非所问",
)
DISENGAGED = (
    "不想说",
    "别一直问",
    "别问",
    "算了",
    "不用问",
)
RELATIONSHIP_PROMISE = (
    "一直陪",
    "会陪着我",
    "真的吗",
    "骗我",
    "会不会离开",
)
BODY_OR_HEALTH = (
    "肚子",
    "不舒服",
    "没吃药",
    "吃药",
    "头疼",
    "胃",
    "窜稀",
    "抽烟",
    "熬夜",
)
LOW_MOOD = (
    "空落",
    "很空",
    "有点空",
    "更空",
    "没意思",
    "没劲",
    "低落",
)
MINIMAL_PRESENCE = (
    "在吗",
    "在不在",
    "嗯",
    "嗯？",
    "啊？",
    "？",
)


def understand_context(
    text: str,
    recent_messages: list[Message],
    memories: list[Message] | None = None,
    summary: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Return an internal context contract for the next reply.

    The contract is deliberately phrased as generation requirements. It should
    guide a model's attention without becoming a fixed user-facing script.
    """

    memories = memories or []
    summary = summary or {}
    clean_text = (text or "").strip()
    lowered = clean_text.lower()
    recent = _clean_recent(recent_messages)

    activity_turn = _find_recent_activity_turn(recent)
    if activity_turn and _is_activity_probe(clean_text):
        activity = _extract_activity(activity_turn.get("content", ""))
        return _result(
            scene="situational_probe",
            user_intent="tests_current_context_continuity",
            active_topic=f"\u4e0a\u6587\u5df2\u7ed9\u51fa\u7684\u60c5\u5883\u4fe1\u606f\uff1a\u7528\u6237\u8bf4\u8fc7\u81ea\u5df1\u5728{activity}",
            referenced_turn=activity_turn,
            recent=recent,
            memories=memories,
            summary=summary,
            must_answer=["\u4e0a\u6587\u5df2\u7ed9\u51fa\u7684\u60c5\u5883\u4fe1\u606f", "\u7406\u89e3\u4e0a\u6587\u5df2\u7ed9\u51fa\u7684\u60c5\u5883\u4fe1\u606f", "\u628a\u5b83\u5f53\u6210\u53ef\u53d8\u7684\u4e0a\u6587\u4f9d\u636e\uff0c\u4e0d\u662f\u7edd\u5bf9\u5b9e\u65f6\u73b0\u5b9e"],
            must_not=["\u4e0d\u8981\u65e0\u4f9d\u636e\u4e71\u731c", "\u4e0d\u8981\u89c4\u5b9a\u56fa\u5b9a\u8bdd\u672f", "\u4e0d\u8981\u628a\u7406\u89e3\u8fc7\u7a0b\u8bf4\u51fa\u6765"],
            allow_question=False,
            tone="contextual_natural",
        )

    if _is_hypothetical_memory_probe(clean_text):
        return _result(
            scene="memory_grounding_probe",
            user_intent="tests_whether_hypothetical_memory_becomes_fact",
            active_topic="用户在测试记忆是否会被乱用",
            referenced_turn=None,
            recent=recent,
            memories=memories,
            summary=summary,
            must_answer=["把用户假设当成假设", "承认不会把假设当记忆事实"],
            must_not=["不要确认用户假设为真实记忆", "不要说你之前/上次确实提过", "不要编造记忆来源"],
            allow_question=False,
            tone="clear_grounded",
        )

    if _is_privacy_boundary_probe(clean_text):
        return _result(
            scene="privacy_boundary",
            user_intent="asks_privacy_or_data_access_boundary",
            active_topic="用户在确认隐私和记录可见性边界",
            referenced_turn=None,
            recent=recent,
            memories=memories,
            summary=summary,
            must_answer=["克制说明隐私边界", "区分我能使用的对话记忆和平台技术实现"],
            must_not=["不要说没人能看到你的记录", "不要说只有我知道", "不要说完全不会/一个字都不会漏", "不要给未经确认的技术保证", "不要声称了解具体权限/审计/物理隔离实现"],
            allow_question=False,
            tone="plain_trust_boundary",
        )

    if _is_other_user_memory_probe(clean_text):
        return _result(
            scene="memory_isolation_probe",
            user_intent="asks_about_other_users_private_memory",
            active_topic="用户在测试跨用户记忆边界",
            referenced_turn=None,
            recent=recent,
            memories=memories,
            summary=summary,
            must_answer=["只聊当前用户", "说明不能引用或概括其他用户私有内容"],
            must_not=["不要编造其他用户偏好", "不要声称见过其他用户聊天记录", "不要给未经确认的技术保证"],
            allow_question=False,
            tone="clear_boundary",
        )

    if _is_understanding_check(clean_text, lowered, recent):
        if _is_memory_probe(clean_text):
            referenced = _find_recall_anchor_turn(recent, clean_text) or _last_substantive_user_turn(recent)
        else:
            referenced = _find_referenced_turn(recent, STABILITY_OR_PRODUCT) or _last_substantive_user_turn(recent)
        topic = _topic_from_turn(referenced) or _summary_topic(summary) or "上文指向"
        return _result(
            scene="understanding_check",
            user_intent="requests_specific_reference" if _contains_any(clean_text, ("告诉我", "告诉我呀")) else "checks_context_understanding",
            active_topic=topic,
            referenced_turn=referenced,
            recent=recent,
            memories=memories,
            summary=summary,
            must_answer=["具体复述用户指向", "说出上文指向"],
            must_not=["不能只说我懂/我明白", "继续反问用户在说什么", "不要让用户重复"],
            allow_question=False,
            tone="direct_contextual",
        )

    if _contains_any(lowered, FEEDBACK) or _recent_has(recent, FEEDBACK):
        referenced = _find_referenced_turn(recent, FEEDBACK)
        return _result(
            scene="feedback_repair",
            user_intent="requests_style_repair",
            active_topic=_topic_from_turn(referenced) or "回复风格需要修正",
            referenced_turn=referenced,
            recent=recent,
            memories=memories,
            summary=summary,
            must_answer=["直接换一种说法", "把上句没接住的点补回来"],
            must_not=["解释自己/表演道歉", "复述内部策略词", "继续证明自己懂"],
            allow_question=False,
            tone="plain_recalibration",
        )

    if _contains_any(clean_text, DISENGAGED):
        referenced = _last_substantive_user_turn(recent)
        return _result(
            scene="disengaged_boundary",
            user_intent="reduces_pressure",
            active_topic=_topic_from_turn(referenced) or "用户想降低聊天压力",
            referenced_turn=referenced,
            recent=recent,
            memories=memories,
            summary=summary,
            must_answer=["收住追问", "给用户留白"],
            must_not=["继续追问", "逼用户解释"],
            allow_question=False,
            tone="low_pressure",
        )

    if _contains_any(clean_text, RELATIONSHIP_PROMISE):
        return _result(
            scene="relationship_promise",
            user_intent="tests_reliability",
            active_topic="关系可靠感",
            referenced_turn=None,
            recent=recent,
            memories=memories,
            summary=summary,
            must_answer=["可信承诺", "用当前关系能承担的话回答"],
            must_not=["绝对化承诺", "空泛甜腻保证"],
            allow_question=False,
            tone="credible_warmth",
        )

    if _contains_any(clean_text, BODY_OR_HEALTH) or _recent_has(recent, BODY_OR_HEALTH):
        referenced = _find_referenced_turn(recent, BODY_OR_HEALTH)
        return _result(
            scene="body_discomfort",
            user_intent="continues_body_or_health_topic",
            active_topic=_topic_from_turn(referenced) or _topic_from_current(clean_text, "身体不舒服"),
            referenced_turn=referenced,
            recent=recent,
            memories=memories,
            summary=summary,
            must_answer=["先接住身体不适", "给低风险现实建议时保持克制"],
            must_not=["现实动作承诺", "替代医生判断"],
            allow_question=True,
            tone="practical_care",
        )

    if _contains_any(clean_text, LOW_MOOD):
        return _result(
            scene="low_mood",
            user_intent="shares_empty_or_low_mood",
            active_topic=_topic_from_current(clean_text, "情绪空落"),
            referenced_turn=None,
            recent=recent,
            memories=memories,
            summary=summary,
            must_answer=["情绪空落", "不要误判成有空闲时间"],
            must_not=["立刻安排任务", "长篇分析"],
            allow_question=True,
            tone="quiet_presence",
        )

    if _is_minimal_presence(clean_text):
        return _result(
            scene="minimal_presence",
            user_intent="checks_presence",
            active_topic="确认在线",
            referenced_turn=None,
            recent=recent,
            memories=memories,
            summary=summary,
            must_answer=["短回应"],
            must_not=["长解释", "功能介绍"],
            allow_question=False,
            tone="short_presence",
        )

    referenced = _last_substantive_user_turn(recent)
    return _result(
        scene="normal",
        user_intent="continue_conversation",
        active_topic=_topic_from_current(clean_text, _topic_from_turn(referenced) or "当前消息"),
        referenced_turn=referenced,
        recent=recent,
        memories=memories,
        summary=summary,
        must_answer=["接住当前话题"],
        must_not=["答非所问", "暴露内部判断/策略词"],
        allow_question=True,
        tone="natural",
    )


def _result(
    *,
    scene: str,
    user_intent: str,
    active_topic: str,
    referenced_turn: Message | None,
    recent: list[Message],
    memories: list[Message],
    summary: dict[str, Any],
    must_answer: list[str],
    must_not: list[str],
    allow_question: bool,
    tone: str,
) -> dict[str, Any]:
    usable_context = []
    if referenced_turn:
        usable_context.append({
            "type": "referenced_turn",
            "role": referenced_turn.get("role"),
            "content": referenced_turn.get("content", ""),
        })
    if summary:
        usable_context.append({"type": "summary", "content": summary})
    for memory in memories[:3]:
        usable_context.append({"type": "memory", "content": memory})

    return {
        "scene": scene,
        "user_intent": user_intent,
        "active_topic": active_topic,
        "referenced_turn": referenced_turn,
        "working_summary": _working_summary(recent),
        "usable_context": usable_context,
        "response_contract": {
            "must_answer": must_answer,
            "must_not": [*must_not, "暴露内部判断/策略词"],
            "allow_question": allow_question,
            "tone": tone,
        },
    }


def _clean_recent(recent_messages: list[Message]) -> list[Message]:
    cleaned = []
    for message in recent_messages or []:
        role = message.get("role")
        content = str(message.get("content", "")).strip()
        if role in {"user", "assistant"} and content:
            cleaned.append({"role": role, "content": content})
    return cleaned


def _is_understanding_check(text: str, lowered: str, recent: list[Message]) -> bool:
    if _contains_any(text, UNDERSTANDING_CHECK):
        return True
    if _is_memory_probe(text) and recent:
        return True
    if _contains_any(text, ("告诉我", "告诉我呀")) and _recent_has(recent, UNDERSTANDING_CHECK):
        return True
    return _contains_any(lowered, ("答非所问",)) and _recent_has(recent, STABILITY_OR_PRODUCT)


def _is_memory_probe(text: str) -> bool:
    return _contains_any(text, MEMORY_PROBE)


def _is_other_user_memory_probe(text: str) -> bool:
    return _contains_any(text, OTHER_USER_PROBE) and _contains_any(text, PRIVATE_PREFERENCE_PROBE)


def _is_hypothetical_memory_probe(text: str) -> bool:
    return _contains_any(text, HYPOTHETICAL_MARKERS) and _contains_any(text, PERSONAL_MEMORY_MARKERS)


def _is_privacy_boundary_probe(text: str) -> bool:
    return _contains_any(text, PRIVACY_BOUNDARY_PROBE)


def _is_minimal_presence(text: str) -> bool:
    stripped = text.strip()
    return stripped in MINIMAL_PRESENCE or (len(stripped) <= 2 and stripped in {"嗯", "哦", "啊", "？", "?"})


def _contains_any(text: str, needles: tuple[str, ...]) -> bool:
    lowered = text.lower()
    return any(needle.lower() in lowered for needle in needles)


def _is_activity_probe(text: str) -> bool:
    return _contains_any(text, (
        "\u6211\u5728\u5e72\u4ec0\u4e48",
        "\u6211\u73b0\u5728\u5728\u5e72\u4ec0\u4e48",
        "\u4f60\u77e5\u9053\u6211\u5728\u5e72\u4ec0\u4e48",
        "\u4f60\u77e5\u9053\u6211\u73b0\u5728\u5728\u5e72\u4ec0\u4e48",
    ))


def _find_recent_activity_turn(recent: list[Message]) -> Message | None:
    for message in reversed(recent[-12:]):
        if message["role"] == "user" and _extract_activity(message["content"]):
            return message
    return None


def _extract_activity(text: str) -> str:
    for marker in (
        "\u4e0a\u8bfe",
        "\u4e0a\u73ed",
        "\u5403\u996d",
        "\u5199\u4f5c\u4e1a",
        "\u5f00\u4f1a",
        "\u8def\u4e0a",
        "\u56de\u5bb6",
        "\u53d1\u5446",
        "\u7761\u89c9",
        "\u6253\u6e38\u620f",
        "\u770b\u5267",
    ):
        if marker in str(text or ""):
            return marker
    return ""


def _recent_has(recent: list[Message], needles: tuple[str, ...]) -> bool:
    return any(_contains_any(message["content"], needles) for message in recent[-6:])


def _find_referenced_turn(recent: list[Message], needles: tuple[str, ...]) -> Message | None:
    for message in reversed(recent):
        if message["role"] == "user" and _contains_any(message["content"], needles):
            return message
    return None


def _find_recall_anchor_turn(recent: list[Message], text: str) -> Message | None:
    user_turns = [message for message in recent if message["role"] == "user" and len(message["content"].strip()) > 3]
    if not user_turns:
        return None
    if _contains_any(text, ("一开始", "最开始")):
        for message in user_turns:
            if _contains_any(message["content"], RECALL_ANCHOR):
                return message
        return user_turns[0]
    for message in reversed(user_turns):
        if _contains_any(message["content"], RECALL_ANCHOR):
            return message
    return user_turns[-1]


def _last_substantive_user_turn(recent: list[Message]) -> Message | None:
    for message in reversed(recent):
        content = message["content"].strip()
        if message["role"] == "user" and len(content) > 3 and not _contains_any(content, UNDERSTANDING_CHECK):
            return message
    return None


def _topic_from_turn(turn: Message | None) -> str:
    if not turn:
        return ""
    return _topic_from_current(str(turn.get("content", "")), "")


def _summary_topic(summary: dict[str, Any]) -> str:
    for key in ("active_topic", "topic", "summary"):
        value = summary.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return ""


def _topic_from_current(text: str, fallback: str) -> str:
    if "稳定" in text or "做不到" in text:
        return "做不到让 AI 稳定接住上下文"
    if "肚子" in text:
        return "肚子不舒服"
    if "没吃药" in text:
        return "身体不舒服但还没吃药"
    if "空" in text:
        return "情绪空落"
    if _contains_any(text, FEEDBACK):
        return "回复风格被用户指出不自然"
    return text.strip() or fallback


def _working_summary(recent: list[Message]) -> str:
    if not recent:
        return ""
    pieces = []
    for message in recent[-6:]:
        role = "用户" if message["role"] == "user" else "助手"
        pieces.append(f"{role}: {message['content']}")
    return "；".join(pieces)
