from __future__ import annotations

import re
from typing import Any


_EMPTY_STATE = {
    "active_topic": "",
    "emotional_thread": "",
    "user_boundary": "",
    "last_ai_mistake": "",
    "unresolved_need": "",
    "user_patience": "normal",
    "next_reply_task": "",
    "situational_facts": [],
    "evidence": [],
}


def update_conversation_state(
    text: str,
    recent_messages: list[dict],
    previous_state: dict | None = None,
    context_understanding: dict | None = None,
) -> dict:
    previous = _normalize_state(previous_state)
    messages = _normalize_messages(recent_messages)
    user_texts = [m["content"] for m in messages if m["role"] == "user"]
    assistant_texts = [m["content"] for m in messages if m["role"] == "assistant"]
    all_user_texts = user_texts + [str(text or "").strip()]
    joined_user = "\n".join(all_user_texts)
    joined_assistant = "\n".join(assistant_texts)

    state = dict(previous)
    state["evidence"] = list(previous.get("evidence", []))

    _apply_active_topic(state, joined_user, all_user_texts)
    _apply_emotional_thread(state, joined_user)
    _apply_boundary(state, joined_user)
    _apply_patience(state, text, joined_user)
    _apply_ai_mistake(state, text, joined_user, joined_assistant)
    _apply_situational_facts(state, all_user_texts)
    _apply_unresolved_need(state, text)
    _apply_next_reply_task(state, text)
    _append_evidence(state, all_user_texts)

    if context_understanding:
        _merge_context_understanding(state, context_understanding)

    return _compact_state(state)


def _normalize_state(previous_state: dict | None) -> dict:
    state = dict(_EMPTY_STATE)
    if previous_state:
        for key in state:
            if key in previous_state:
                state[key] = previous_state[key]
    if not isinstance(state.get("evidence"), list):
        state["evidence"] = []
    if not isinstance(state.get("situational_facts"), list):
        state["situational_facts"] = []
    return state


def _normalize_messages(recent_messages: list[dict]) -> list[dict]:
    normalized = []
    for item in recent_messages or []:
        role = str(item.get("role", "")).strip()
        content = str(item.get("content", "")).strip()
        if role in {"user", "assistant"} and content:
            normalized.append({"role": role, "content": content})
    return normalized[-20:]


def _apply_active_topic(state: dict[str, Any], joined_user: str, user_texts: list[str]) -> None:
    has_emotional_empty = any(
        token in joined_user
        for token in ("\u5fc3\u91cc\u6709\u70b9\u7a7a", "\u5fc3\u91cc\u7a7a", "\u7a7a\u843d", "\u66f4\u7a7a")
    )
    has_moments = "\u670b\u53cb\u5708" in joined_user
    if has_emotional_empty and has_moments:
        state["active_topic"] = "\u5fc3\u91cc\u7a7a\uff1b\u5237\u5b8c\u670b\u53cb\u5708\u540e\u66f4\u660e\u663e"
        return
    if has_emotional_empty:
        state["active_topic"] = "\u5fc3\u91cc\u7a7a\uff0c\u4e0d\u662f\u7a7a\u95f2"
        return
    if "\u538b\u529b" in joined_user or "\u70e6" in joined_user or "\u7d2f" in joined_user:
        state["active_topic"] = "\u5f53\u524d\u538b\u529b\u6216\u75b2\u60eb"
        return
    if not state.get("active_topic") and user_texts:
        state["active_topic"] = _shorten(user_texts[-1], 36)


def _apply_emotional_thread(state: dict[str, Any], joined_user: str) -> None:
    if any(
        token in joined_user
        for token in ("\u5fc3\u91cc\u6709\u70b9\u7a7a", "\u5fc3\u91cc\u7a7a", "\u7a7a\u843d", "\u66f4\u7a7a")
    ):
        state["emotional_thread"] = "\u7a7a\u843d\u3001\u4f4e\u843d\u4f46\u4e0d\u4e00\u5b9a\u60f3\u88ab\u5f00\u5bfc"
    elif any(token in joined_user for token in ("\u538b\u529b", "\u7126\u8651", "\u70e6", "\u7d2f", "\u5d29")):
        state["emotional_thread"] = "\u6709\u538b\u529b\uff0c\u9700\u8981\u5148\u88ab\u63a5\u4f4f"


def _apply_boundary(state: dict[str, Any], joined_user: str) -> None:
    if any(
        token in joined_user
        for token in ("\u522b\u4e00\u76f4\u95ee", "\u4e0d\u8981\u4e00\u76f4\u95ee", "\u4e0d\u60f3\u8bf4", "\u522b\u95ee")
    ):
        state["user_boundary"] = "\u4e0d\u8981\u4e00\u76f4\u8ffd\u95ee"


def _apply_patience(state: dict[str, Any], text: str, joined_user: str) -> None:
    if any(
        token in joined_user
        for token in ("\u522b\u4e00\u76f4\u95ee", "\u4e0d\u8981\u4e00\u76f4\u95ee", "\u7b97\u4e86", "\u4e0d\u662f\u8fd9\u4e2a")
    ):
        state["user_patience"] = "low"
    elif len(str(text or "").strip()) <= 2:
        state["user_patience"] = "thin"
    else:
        state["user_patience"] = "normal"


def _apply_ai_mistake(state: dict[str, Any], text: str, joined_user: str, joined_assistant: str) -> None:
    current = str(text or "")
    if "\u4e0d\u662f\u8fd9\u4e2a" in current and any(
        token in joined_assistant for token in ("\u4f60\u8bf4\u201c\u5bf9\uff0c\u5c31\u662f\u8fd9\u79cd\u611f\u89c9\u201d", "\u8ba9\u6211\u522b\u4e00\u76f4\u95ee")
    ):
        state["last_ai_mistake"] = (
            "\u628a\u56de\u5fc6\u95ee\u9898\u7406\u89e3\u6210\u6700\u8fd1\u4e00\u53e5\u8bdd\uff0c"
            "\u800c\u4e0d\u662f\u4e00\u5f00\u59cb\u7684\u4e3b\u9898"
        )
        return
    if "\u4e0d\u662f\u6709\u7a7a\u7684\u610f\u601d" in joined_user and any(
        token in joined_assistant for token in ("\u90a3\u6b63\u597d", "\u6162\u60a0\u60a0", "\u60f3\u505a\u7684\u4e8b")
    ):
        state["last_ai_mistake"] = "\u628a\u5fc3\u91cc\u7a7a\u8bef\u8bfb\u6210\u7a7a\u95f2"


def _apply_situational_facts(state: dict[str, Any], user_texts: list[str]) -> None:
    facts = list(state.get("situational_facts") or [])
    for item in user_texts:
        activity = _extract_user_activity(item)
        if not activity:
            continue
        fact = {
            "kind": "activity",
            "value": activity,
            "source": "user_stated",
            "confidence": "high",
            "changeable": True,
            "evidence": _shorten(item, 48),
        }
        facts = [old for old in facts if old.get("kind") != "activity"]
        facts.append(fact)
    state["situational_facts"] = facts[-5:]


def _apply_unresolved_need(state: dict[str, Any], text: str) -> None:
    current = str(text or "")
    if "\u4e0d\u662f\u8fd9\u4e2a" in current or "\u4e00\u5f00\u59cb" in current:
        state["unresolved_need"] = "\u5e0c\u671b\u88ab\u63a5\u4f4f\u4e0a\u4e0b\u6587\uff0c\u800c\u4e0d\u662f\u88ab\u8981\u6c42\u91cd\u590d"
    elif state.get("user_boundary"):
        state["unresolved_need"] = "\u9700\u8981\u5c11\u538b\u8feb\u7684\u966a\u4f34"


def _apply_next_reply_task(state: dict[str, Any], text: str) -> None:
    current = str(text or "")
    activity_fact = _latest_fact(state, "activity")
    if activity_fact and _is_activity_probe(current):
        value = str(activity_fact.get("value", "")).strip()
        state["next_reply_task"] = (
            "\u7406\u89e3\u7528\u6237\u5728\u6d4b\u8bd5\u4e0a\u4e0b\u6587\uff1b"
            f"\u4e0a\u6587\u4fe1\u606f\u662f\u7528\u6237\u8bf4\u8fc7\u81ea\u5df1\u5728{value}\uff1b"
            "\u8fd9\u662f\u53ef\u80fd\u53d8\u5316\u7684\u60c5\u5883\u4fe1\u606f\uff0c"
            "\u4e0d\u8981\u5f53\u6210\u7edd\u5bf9\u73b0\u5b9e\uff0c\u4e5f\u4e0d\u8981\u4e71\u731c\uff1b"
            "\u4e0d\u8981\u89c4\u5b9a\u56fa\u5b9a\u8bdd\u672f\uff0c\u7528\u5f53\u524d\u4eba\u683c\u81ea\u7136\u63a5"
        )
        return
    if "\u4e0d\u662f\u8fd9\u4e2a" in current or "\u4e00\u5f00\u59cb" in current:
        active_topic = str(state.get("active_topic", ""))
        if "\u670b\u53cb\u5708" in active_topic:
            state["next_reply_task"] = (
                "\u4e3b\u52a8\u4fee\u6b63\u5e76\u8bf4\u51fa\u4e00\u5f00\u59cb\u7684\u6574\u6761\u6838\u5fc3\uff1a"
                "\u5fc3\u91cc\u7a7a\uff0c\u5237\u5b8c\u670b\u53cb\u5708\u540e\u66f4\u660e\u663e\uff1b"
                "\u4e0d\u8981\u8ffd\u95ee\uff0c\u4e0d\u8981\u8ba9\u7528\u6237\u91cd\u590d"
            )
        else:
            state["next_reply_task"] = (
                "\u4e3b\u52a8\u4fee\u6b63\u5e76\u8bf4\u51fa\u4e00\u5f00\u59cb\u7684\u6838\u5fc3\uff0c"
                "\u4e0d\u8981\u8ffd\u95ee\uff0c\u4e0d\u8981\u8ba9\u7528\u6237\u91cd\u590d"
            )
        return
    if state.get("user_boundary"):
        state["next_reply_task"] = "\u5c11\u95ee\uff0c\u77ed\u4e00\u70b9\uff0c\u5148\u627f\u63a5\u5f53\u4e0b\u60c5\u7eea"
        return
    if state.get("active_topic"):
        state["next_reply_task"] = "\u56f4\u7ed5\u5f53\u524d\u8bdd\u9898\u81ea\u7136\u63a5\u8bdd"


def _append_evidence(state: dict[str, Any], user_texts: list[str]) -> None:
    evidence = list(state.get("evidence", []))
    for item in user_texts[-8:]:
        compact = _shorten(item, 40)
        if compact and compact not in evidence:
            evidence.append(compact)
    state["evidence"] = evidence[-8:]


def _merge_context_understanding(state: dict[str, Any], context_understanding: dict) -> None:
    scene = str(context_understanding.get("scene", "")).strip()
    task = str(context_understanding.get("next_reply_task", "")).strip()
    if task and not state.get("next_reply_task"):
        state["next_reply_task"] = task
    if scene == "feedback_repair" and not state.get("unresolved_need"):
        state["unresolved_need"] = "\u7528\u6237\u5728\u7ea0\u6b63\u56de\u590d\u65b9\u5411\uff0c\u9700\u8981\u5148\u4fee\u6b63"


def _compact_state(state: dict[str, Any]) -> dict:
    compact = {}
    for key in _EMPTY_STATE:
        value = state.get(key, _EMPTY_STATE[key])
        if isinstance(value, str):
            compact[key] = _shorten(value.strip(), 80)
        elif key == "evidence":
            compact[key] = [_shorten(str(item).strip(), 40) for item in value if str(item).strip()][-8:]
        elif key == "situational_facts":
            compact[key] = [_compact_fact(item) for item in value if isinstance(item, dict)][-5:]
        else:
            compact[key] = value
    return compact


def _extract_user_activity(text: str) -> str:
    value = str(text or "").strip()
    patterns = [
        r"\u6211(?:\u73b0\u5728)?\u5728(?P<activity>\u4e0a\u8bfe|\u4e0a\u73ed|\u5403\u996d|\u5199\u4f5c\u4e1a|\u5f00\u4f1a|\u8def\u4e0a|\u56de\u5bb6|\u53d1\u5446|\u7761\u89c9|\u6253\u6e38\u620f|\u770b\u5267)",
        r"\u6211(?:\u51c6\u5907|\u8981)(?P<activity>\u7761\u89c9|\u5403\u996d|\u4e0a\u8bfe|\u4e0a\u73ed|\u51fa\u95e8)",
    ]
    for pattern in patterns:
        match = re.search(pattern, value)
        if match:
            return match.group("activity")
    return ""


def _is_activity_probe(text: str) -> bool:
    value = str(text or "")
    return any(token in value for token in (
        "\u6211\u5728\u5e72\u4ec0\u4e48",
        "\u6211\u73b0\u5728\u5728\u5e72\u4ec0\u4e48",
        "\u4f60\u77e5\u9053\u6211\u73b0\u5728\u5728\u5e72\u4ec0\u4e48",
        "\u4f60\u77e5\u9053\u6211\u5728\u5e72\u4ec0\u4e48",
    ))


def _latest_fact(state: dict[str, Any], kind: str) -> dict:
    for fact in reversed(state.get("situational_facts") or []):
        if isinstance(fact, dict) and fact.get("kind") == kind:
            return fact
    return {}


def _compact_fact(fact: dict) -> dict:
    return {
        "kind": _shorten(str(fact.get("kind", "")).strip(), 24),
        "value": _shorten(str(fact.get("value", "")).strip(), 32),
        "source": _shorten(str(fact.get("source", "")).strip(), 24),
        "confidence": _shorten(str(fact.get("confidence", "")).strip(), 16),
        "changeable": bool(fact.get("changeable", True)),
        "evidence": _shorten(str(fact.get("evidence", "")).strip(), 48),
    }


def _shorten(value: str, limit: int) -> str:
    value = " ".join(value.split())
    if len(value) <= limit:
        return value
    return value[: limit - 1] + "..."
