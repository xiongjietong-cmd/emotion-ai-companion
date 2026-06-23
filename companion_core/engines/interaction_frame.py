"""Internal interaction-frame extraction for companion replies.

This layer describes what the latest user message is doing in relation to the
previous turns. It must not generate user-facing wording.
"""

from __future__ import annotations

import re
from typing import Any


Message = dict[str, Any]

_ACTIVITIES = (
    "上课",
    "上班",
    "吃饭",
    "写作业",
    "开会",
    "路上",
    "回家",
    "发呆",
    "睡觉",
    "打游戏",
    "看剧",
)

_STYLE_FEEDBACK = (
    "不耐烦",
    "太ai",
    "ai感",
    "模板",
    "机械",
    "怪",
    "不像",
    "不自然",
    "答非所问",
)

_UNSUPPORTED_GUESS_MARKERS = (
    "输得挺惨",
    "偷吃",
    "在发呆",
    "是不是",
    "猜",
    "看起来",
    "听语气",
)


def build_interaction_frame(
    text: str,
    recent_messages: list[Message],
    conversation_state: dict | None = None,
    selected_memories: list[Message] | None = None,
) -> dict[str, Any]:
    """Build a compact internal frame for the next generation step."""

    clean_text = str(text or "").strip()
    recent = _normalize_messages(recent_messages)
    conversation_state = conversation_state or {}
    selected_memories = selected_memories or []

    facts = _known_scene_facts(clean_text, recent, conversation_state)
    pending_guesses = _pending_assistant_guesses(recent)
    last_assistant = _last_message(recent, "assistant")
    repair_debt = _repair_debt(clean_text, recent)

    user_move = _classify_user_move(clean_text, recent, pending_guesses, repair_debt)
    relation = _relation_to_previous(user_move, clean_text, recent, pending_guesses)
    reaction = _user_reaction(user_move, clean_text)
    active_topic = _active_topic(clean_text, facts, recent, selected_memories)

    return {
        "user_move": user_move,
        "relation_to_previous": relation,
        "active_topic": active_topic,
        "last_assistant_move": _assistant_move(last_assistant),
        "known_scene_facts": facts,
        "pending_assistant_guesses": pending_guesses,
        "user_reaction": reaction,
        "repair_debt": repair_debt,
        "generation_direction": _generation_direction(
            user_move=user_move,
            relation=relation,
            active_topic=active_topic,
            facts=facts,
            pending_guesses=pending_guesses,
            repair_debt=repair_debt,
        ),
    }


def _normalize_messages(recent_messages: list[Message]) -> list[Message]:
    normalized = []
    for item in recent_messages or []:
        role = str(item.get("role", "")).strip()
        content = str(item.get("content", "")).strip()
        if role in {"user", "assistant"} and content:
            normalized.append({"role": role, "content": content})
    return normalized[-20:]


def _last_message(messages: list[Message], role: str) -> Message | None:
    for message in reversed(messages):
        if message.get("role") == role:
            return message
    return None


def _known_scene_facts(text: str, recent: list[Message], conversation_state: dict) -> list[dict[str, Any]]:
    facts = []
    for fact in conversation_state.get("situational_facts") or []:
        if not isinstance(fact, dict):
            continue
        if fact.get("kind") == "activity" and str(fact.get("value", "")).strip():
            facts.append({
                "key": "current_activity",
                "value": str(fact.get("value", "")).strip(),
                "source": str(fact.get("source", "conversation_state") or "conversation_state"),
                "confidence": _confidence_number(fact.get("confidence", 0.8)),
                "changeable": bool(fact.get("changeable", True)),
                "evidence": str(fact.get("evidence", "")).strip(),
            })

    for source_text in [message["content"] for message in recent if message["role"] == "user"] + [text]:
        activity = _extract_activity(source_text)
        if not activity:
            continue
        facts = [fact for fact in facts if fact.get("key") != "current_activity"]
        facts.append({
            "key": "current_activity",
            "value": activity,
            "source": "user_stated",
            "confidence": 0.9,
            "changeable": True,
            "evidence": source_text[:48],
        })

    return facts[-5:]


def _confidence_number(value: Any) -> float:
    if isinstance(value, (int, float)):
        return float(value)
    if str(value).lower() == "high":
        return 0.9
    if str(value).lower() == "low":
        return 0.35
    return 0.7


def _extract_activity(text: str) -> str:
    value = str(text or "")
    for pattern in (
        r"我(?:现在)?在(?P<activity>上课|上班|吃饭|写作业|开会|路上|回家|发呆|睡觉|打游戏|看剧)",
        r"我(?:准备|要)(?P<activity>睡觉|吃饭|上课|上班|出门)",
    ):
        match = re.search(pattern, value)
        if match:
            return match.group("activity")
    for activity in _ACTIVITIES:
        if activity in value:
            return activity
    return ""


def _pending_assistant_guesses(recent: list[Message]) -> list[dict[str, Any]]:
    guesses = []
    for message in recent[-4:]:
        if message["role"] != "assistant":
            continue
        content = message["content"]
        marker = _guess_marker(content)
        if not marker:
            continue
        guesses.append({
            "guess": marker,
            "status": "unconfirmed",
            "risk": "unsupported",
            "evidence": content[:80],
        })
    return guesses[-3:]


def _guess_marker(text: str) -> str:
    value = str(text or "")
    if "输得挺惨" in value:
        return "输得挺惨"
    for marker in _UNSUPPORTED_GUESS_MARKERS:
        if marker in value:
            return marker
    return ""


def _classify_user_move(
    text: str,
    recent: list[Message],
    pending_guesses: list[dict[str, Any]],
    repair_debt: str,
) -> str:
    if _is_question_mark_only(text) and pending_guesses:
        return "pushback"
    if _is_question_mark_only(text) and _last_message(recent, "assistant"):
        return "pushback"
    if _is_activity_probe(text):
        return "probe"
    if repair_debt and _has_style_feedback(text):
        return "feedback"
    if repair_debt and ("不说也行" in text or "你说" in text):
        return "correction"
    if _is_correction(text, recent):
        return "correction"
    if _is_playful_confirmation(text):
        return "tease"
    if len(text) <= 2:
        return "silence"
    return "share"


def _relation_to_previous(
    user_move: str,
    text: str,
    recent: list[Message],
    pending_guesses: list[dict[str, Any]],
) -> str:
    if user_move == "pushback":
        return "questions_previous_reply"
    if user_move == "probe":
        return "tests_context_memory"
    if user_move == "correction":
        return "rejects_or_corrects_reply"
    if user_move == "tease" and pending_guesses:
        return "continues_previous_guess"
    if recent:
        return "continues_conversation"
    return "new_topic"


def _user_reaction(user_move: str, text: str) -> str:
    if user_move == "pushback":
        return "confused"
    if _has_style_feedback(text):
        return "annoyed"
    if _is_playful_confirmation(text):
        return "plays_along"
    return "unknown"


def _active_topic(
    text: str,
    facts: list[dict[str, Any]],
    recent: list[Message],
    selected_memories: list[Message],
) -> str:
    if facts:
        latest_fact = facts[-1]
        if latest_fact.get("key") == "current_activity":
            return str(latest_fact.get("value", ""))
    for message in reversed(recent):
        if message["role"] == "user" and len(message["content"]) > 2:
            return message["content"][:32]
    if selected_memories:
        return str(selected_memories[0].get("value", ""))[:32]
    return text[:32] or "current_turn"


def _assistant_move(last_assistant: Message | None) -> str:
    if not last_assistant:
        return "none"
    content = str(last_assistant.get("content", ""))
    if _guess_marker(content):
        return "unsupported_guess"
    if "？" in content or "?" in content:
        return "question"
    return "reply"


def _repair_debt(text: str, recent: list[Message]) -> str:
    combined = "\n".join([message["content"] for message in recent[-4:]] + [text])
    if "不耐烦" in combined and "不说也行" in combined:
        return "用户觉得“不说也行”听起来不耐烦；需要修复语气压力。"
    if _has_style_feedback(combined):
        return "用户指出回复风格不自然；需要直接改善接话方式。"
    return ""


def _generation_direction(
    *,
    user_move: str,
    relation: str,
    active_topic: str,
    facts: list[dict[str, Any]],
    pending_guesses: list[dict[str, Any]],
    repair_debt: str,
) -> str:
    directions = [
        "这是内部对话现场理解，不是固定话术。",
        "先判断用户这句话和上一轮的关系，再自然回复。",
    ]
    if user_move == "correction":
        directions.append("用户在纠正或强调上一轮没接住的点，不要把这句当新话题。")
    if relation == "questions_previous_reply":
        directions.append("用户的问号是在质疑上一句，别把问号当普通在线确认。")
    if relation == "tests_context_memory":
        directions.append("用户在测试上下文连续性，使用上文事实做思考依据，不要无依据乱猜。")
    if pending_guesses:
        directions.append("上轮助手猜测仍未确认，不能当成事实继续发挥。")
    if facts:
        fact_text = "；".join(f"{fact.get('key')}={fact.get('value')}" for fact in facts)
        directions.append(f"可用场景事实：{fact_text}。这些事实可能变化，只能指导理解。")
    if repair_debt:
        directions.append(f"需要修复：{repair_debt} 不要追问用户解释，直接调整接话姿态。")
    if active_topic:
        directions.append(f"当前话题焦点：{active_topic}。")
    return " ".join(directions)


def _is_question_mark_only(text: str) -> bool:
    return str(text or "").strip() in {"?", "？", "??", "？？", "啊？", "嗯？"}


def _is_activity_probe(text: str) -> bool:
    value = str(text or "")
    return any(token in value for token in (
        "我在干什么",
        "我现在在干什么",
        "你知道我在干什么",
        "你知道我现在在干什么",
    ))


def _is_correction(text: str, recent: list[Message]) -> bool:
    value = str(text or "")
    if "我说" in value or "不是" in value or "不对" in value:
        return True
    activity = _extract_activity(value)
    if activity and any(message["role"] == "assistant" for message in recent[-2:]):
        return True
    return False


def _has_style_feedback(text: str) -> bool:
    lowered = str(text or "").lower()
    return any(marker.lower() in lowered for marker in _STYLE_FEEDBACK)


def _is_playful_confirmation(text: str) -> bool:
    return any(token in str(text or "") for token in ("被你发现", "被你看穿", "还真是", "确实"))
