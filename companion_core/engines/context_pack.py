"""Build prioritized context for companion generation.

Inspired by lorebook / memory-layer systems: recent scene facts and the
current interaction frame outrank stale rolling summaries.
"""

from __future__ import annotations

import re
from typing import Any


Message = dict[str, Any]

_ACTION_PATTERNS = (
    (r"我要去(?P<activity>吃饭饭|吃饭|上课|上班|睡觉|洗漱|打游戏)", "planned_activity"),
    (r"我(?:刚起床)?准备去(?P<activity>上课|上班|吃饭|洗漱)", "planned_activity"),
    (r"我(?:现在)?在(?P<activity>打游戏|上课|上班|吃饭|写作业|开会|看剧|发呆)", "current_activity"),
)


def build_context_pack(
    *,
    text: str,
    recent_messages: list[Message],
    conversation_summary: dict | None,
    conversation_state: dict | None,
    interaction_frame: dict | None,
    selected_memories: list[Message] | None,
) -> dict[str, Any]:
    recent = _normalize_messages(recent_messages)
    summary = conversation_summary or {}
    state = conversation_state or {}
    frame = interaction_frame or {}
    memories = selected_memories or []

    facts = _active_scene_facts(text, recent, state, frame)
    focus = _current_reply_focus(text, facts)
    high_priority = _build_high_priority_context(text, recent, facts, frame, focus)
    low_priority = _build_low_priority_background(summary, memories)

    return {
        "summary_policy": "rolling_summary 只能当背景；当前消息、最近真实消息、scene facts、interaction frame 优先。",
        "current_reply_focus": focus,
        "active_scene_facts": facts,
        "high_priority_context": high_priority,
        "low_priority_background": low_priority,
        "recent_window": recent[-10:],
    }


def _normalize_messages(recent_messages: list[Message]) -> list[Message]:
    messages = []
    for item in recent_messages or []:
        role = str(item.get("role", "")).strip()
        content = str(item.get("content", "")).strip()
        if role in {"user", "assistant"} and content:
            messages.append({"role": role, "content": content})
    return messages[-20:]


def _active_scene_facts(
    text: str,
    recent: list[Message],
    state: dict,
    frame: dict,
) -> list[dict[str, Any]]:
    facts: list[dict[str, Any]] = []
    for fact in state.get("situational_facts") or []:
        if isinstance(fact, dict) and str(fact.get("value", "")).strip():
            facts.append({
                "kind": str(fact.get("kind") or "fact"),
                "key": str(fact.get("key") or fact.get("kind") or "fact"),
                "value": _normalize_activity(str(fact.get("value", "")).strip()),
                "source": str(fact.get("source") or "conversation_state"),
                "confidence": fact.get("confidence", "medium"),
                "changeable": bool(fact.get("changeable", True)),
                "evidence": str(fact.get("evidence", "")).strip(),
            })

    for fact in frame.get("known_scene_facts") or []:
        if isinstance(fact, dict) and str(fact.get("value", "")).strip():
            facts = [item for item in facts if item.get("key") != fact.get("key")]
            facts.append({
                "kind": str(fact.get("kind") or fact.get("key") or "fact"),
                "key": str(fact.get("key") or "fact"),
                "value": _normalize_activity(str(fact.get("value", "")).strip()),
                "source": str(fact.get("source") or "interaction_frame"),
                "confidence": fact.get("confidence", "medium"),
                "changeable": bool(fact.get("changeable", True)),
                "evidence": str(fact.get("evidence", "")).strip(),
            })

    for message in recent:
        if message["role"] != "user":
            continue
        found = _extract_action_fact(message["content"])
        if found:
            facts = _replace_action_fact(facts, found)

    current_found = _extract_action_fact(text)
    if current_found:
        facts = _replace_action_fact(facts, current_found)

    if _mentions_game_name(recent):
        if not any(item.get("value") == "打游戏" for item in facts):
            facts.append({
                "kind": "current_activity",
                "key": "current_activity",
                "value": "打游戏",
                "source": "recent_game_context",
                "confidence": 0.85,
                "changeable": True,
                "evidence": " / ".join(_recent_user_contents(recent)[-4:])[:80],
            })

    return facts[-6:]


def _replace_action_fact(facts: list[dict[str, Any]], fact: dict[str, Any]) -> list[dict[str, Any]]:
    key = "current_activity" if fact["kind"] in {"current_activity", "planned_activity"} else fact["kind"]
    kept = [item for item in facts if item.get("key") != key]
    kept.append({
        **fact,
        "key": key,
        "value": _normalize_activity(str(fact.get("value", ""))),
    })
    return kept


def _extract_action_fact(text: str) -> dict[str, Any] | None:
    value = str(text or "")
    for pattern, kind in _ACTION_PATTERNS:
        match = re.search(pattern, value)
        if match:
            return {
                "kind": kind,
                "key": "current_activity",
                "value": _normalize_activity(match.group("activity")),
                "source": "recent_user_message",
                "confidence": 0.9,
                "changeable": True,
                "evidence": value[:80],
            }
    return None


def _normalize_activity(value: str) -> str:
    if value == "吃饭饭":
        return "吃饭"
    return value


def _mentions_game_name(recent: list[Message]) -> bool:
    joined = "\n".join(_recent_user_contents(recent)[-6:])
    return "和平精英" in joined or "王者荣耀" in joined or "原神" in joined


def _recent_user_contents(recent: list[Message]) -> list[str]:
    return [message["content"] for message in recent if message["role"] == "user"]


def _current_reply_focus(text: str, facts: list[dict[str, Any]]) -> str:
    value = str(text or "")
    latest_activity = ""
    for fact in reversed(facts):
        if fact.get("key") == "current_activity":
            latest_activity = str(fact.get("value") or "")
            break
    if "我要去干什么" in value or "刚才跟你说我要干什么" in value:
        if latest_activity:
            return f"用户刚才说要去{latest_activity}"
        return "用户在问刚才计划去做什么"
    if "我在干什么" in value:
        return "用户在问自己当前/刚才在做什么"
    if latest_activity:
        return f"围绕用户当前/刚才的行动：{latest_activity}"
    return "围绕当前消息自然接话"


def _build_high_priority_context(
    text: str,
    recent: list[Message],
    facts: list[dict[str, Any]],
    frame: dict,
    focus: str,
) -> str:
    lines = [
        "High priority context:",
        f"- latest_user_message: {text}",
        f"- current_reply_focus: {focus}",
    ]
    if facts:
        fact_text = " / ".join(
            f"{fact.get('key')}={fact.get('value')} source={fact.get('source')}"
            for fact in facts
        )
        lines.append(f"- active_scene_facts: {fact_text}")
    if frame:
        lines.append(
            "- interaction_frame: "
            f"user_move={frame.get('user_move')} "
            f"relation={frame.get('relation_to_previous')} "
            f"topic={frame.get('active_topic')}"
        )
    recent_text = " / ".join(f"{m['role']}: {m['content']}" for m in recent[-10:])
    if recent_text:
        lines.append(f"- recent_real_messages: {recent_text}")
    lines.append("- Priority rule: answer from latest_user_message + recent_real_messages + active_scene_facts before old summaries.")
    return "\n".join(lines)


def _build_low_priority_background(summary: dict, memories: list[Message]) -> str:
    lines = ["Low priority background:"]
    rolling = str(summary.get("rollingSummary") or summary.get("rolling_summary") or "").strip()
    if rolling:
        lines.append(f"- rolling_summary_background: {rolling[-700:]}")
    for memory in memories[:3]:
        value = str(memory.get("value", "")).strip()
        if value:
            lines.append(f"- selected_memory_background: {value}")
    if len(lines) == 1:
        lines.append("- none")
    lines.append("- These items can support tone, but must not override recent scene facts.")
    return "\n".join(lines)
