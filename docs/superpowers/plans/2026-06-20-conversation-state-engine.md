# Conversation State Engine Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:subagent-driven-development` or `superpowers:executing-plans` to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a deterministic Conversation State Engine that extracts the live conversation core before every reply, so the companion can answer from the actual thread instead of reacting only to the latest sentence. The first target bug is the real transcript where the user corrected the AI with "not this, I mean the beginning" and the AI failed to recover the original emotional topic.

**Architecture:** Add a shadow engine under `companion_core/engines/` that converts recent chat into a compact state object. The state is passed through the API/model pipeline and injected into the prompt as internal continuity guidance. It must guide reasoning, not hard-code final replies or expose labels.

**Tech Stack:** Python standard library, existing FastAPI sidecar, existing unittest suite, existing Node gateway integration checks.

---

## Current Baseline

Existing related code:

- `companion_core/engines/context_understanding.py` detects current-turn scenes and reply risks.
- `companion_core/engines/prompt_composer.py` composes system constraints.
- `companion_core/app.py` builds `context_understanding` when `features.context_understanding` is enabled.
- `server/index.js` sends feature flags to the Python companion.

Problem:

`context_understanding` handles current intent, but it does not preserve a conversation-level thread. In the failing transcript, the AI remembered the latest phrase and missed the earlier emotional core.

The original core was:

- The user felt empty inside, not free or idle.
- The feeling became stronger after scrolling Moments.
- The user disliked repeated questions.
- The user later tested whether the AI remembered the beginning.
- The AI asked the user to repeat, which increased friction.

---

## Desired Conversation State Contract

Create `companion_core/engines/conversation_state.py`.

Public API:

```python
def update_conversation_state(
    text: str,
    recent_messages: list[dict],
    previous_state: dict | None = None,
    context_understanding: dict | None = None,
) -> dict:
    ...
```

Returned shape:

```python
{
    "active_topic": "inner emptiness; stronger after scrolling Moments",
    "emotional_thread": "empty and low, but does not want to be probed",
    "user_boundary": "do not keep asking questions",
    "last_ai_mistake": "treated the recall question as the latest sentence instead of the beginning topic",
    "unresolved_need": "wants the AI to recover context without asking the user to repeat",
    "user_patience": "low",
    "next_reply_task": "repair the miss and answer the initial core; do not ask another question",
    "evidence": ["today feels empty", "empty inside", "Moments made it worse", "do not keep asking", "I mean the beginning"],
}
```

Rules:

- No LLM call. This module must be deterministic and cheap.
- State guides the next reply; it must not prescribe a fixed sentence.
- Keep per-request state isolated. Never mix users or bots.
- Avoid exposing state labels in final assistant content.
- When uncertain, prefer a compact summary over an empty state.

---

## Task 1: Add Golden Conversation State Tests

- [ ] Create `companion_core/tests/test_conversation_state.py`.

Use escaped Unicode strings to avoid Windows console encoding issues in scripts and plan files.

Test file:

```python
import unittest

from companion_core.engines.conversation_state import update_conversation_state


U_EMPTY = "\u4eca\u5929\u6709\u70b9\u7a7a"
U_NOT_IDLE = "\u4e0d\u662f\u6709\u7a7a\u7684\u610f\u601d\u2026\u2026\u5c31\u662f\u5fc3\u91cc\u6709\u70b9\u7a7a"
U_MOMENTS = "\u55ef\uff0c\u4e5f\u4e0d\u662f\u96be\u8fc7\uff0c\u5c31\u662f\u5237\u5b8c\u670b\u53cb\u5708\u66f4\u7a7a\u4e86"
U_THAT = "\u5bf9\uff0c\u5c31\u662f\u8fd9\u79cd\u611f\u89c9"
U_DONT_ASK = "\u4f60\u522b\u4e00\u76f4\u95ee"
U_HMM = "\u55ef"
U_REMEMBER = "\u90a3\u4f60\u8fd8\u8bb0\u5f97\u6211\u521a\u624d\u8bf4\u7684\u662f\u5565\u5417"
U_BEGINNING = "\u4e0d\u662f\u8fd9\u4e2a\uff0c\u6211\u662f\u8bf4\u4e00\u5f00\u59cb\u90a3\u4e2a"


class ConversationStateTest(unittest.TestCase):
    def test_tracks_emotional_core_across_recall_repair(self):
        recent = [
            {"role": "user", "content": U_EMPTY},
            {"role": "assistant", "content": "\u90a3\u6b63\u597d\uff0c\u53ef\u4ee5\u6162\u60a0\u60a0\u5730\u505a\u70b9\u60f3\u505a\u7684\u4e8b\u3002"},
            {"role": "user", "content": U_NOT_IDLE},
            {"role": "assistant", "content": "\u55ef\uff0c\u90a3\u79cd\u7a7a\u843d\u843d\u7684\u611f\u89c9\uff0c\u6211\u61c2\u3002"},
            {"role": "user", "content": U_MOMENTS},
            {"role": "assistant", "content": "\u55ef\uff0c\u522b\u4eba\u7684\u70ed\u95f9\u770b\u591a\u4e86\uff0c\u5bb9\u6613\u653e\u5927\u81ea\u5df1\u7684\u5b89\u9759\u3002"},
            {"role": "user", "content": U_THAT},
            {"role": "assistant", "content": "\u55ef\uff0c\u5b89\u9759\u672c\u8eab\u5e76\u4e0d\u574f\u3002\u53ea\u662f\u6709\u65f6\u5019\u9700\u8981\u4e00\u70b9\u65f6\u95f4\uff0c\u8ba9\u5b83\u91cd\u65b0\u53d8\u5f97\u8212\u670d\u3002\u4eca\u5929\u6709\u505a\u4ec0\u4e48\u8ba9\u81ea\u5df1\u5b89\u9759\u4e0b\u6765\u7684\u5c0f\u4e8b\u5417\uff1f"},
            {"role": "user", "content": U_DONT_ASK},
            {"role": "assistant", "content": "\u55ef\uff0c\u597d\uff0c\u4e0d\u95ee\u4e86\u3002"},
            {"role": "user", "content": U_HMM},
            {"role": "assistant", "content": "\u55ef\uff0c\u4e0d\u6253\u6270\u3002"},
            {"role": "user", "content": U_REMEMBER},
            {"role": "assistant", "content": "\u55ef\uff0c\u8bb0\u5f97\u3002\u4f60\u8bf4\u201c\u5bf9\uff0c\u5c31\u662f\u8fd9\u79cd\u611f\u89c9\u201d\uff0c\u7136\u540e\u8ba9\u6211\u522b\u4e00\u76f4\u95ee\u3002"},
        ]

        state = update_conversation_state(U_BEGINNING, recent)

        self.assertIn("\u5fc3\u91cc\u7a7a", state["active_topic"])
        self.assertIn("\u670b\u53cb\u5708", state["active_topic"])
        self.assertIn("\u4e0d\u8981\u4e00\u76f4\u8ffd\u95ee", state["user_boundary"])
        self.assertIn("\u6700\u8fd1\u4e00\u53e5", state["last_ai_mistake"])
        self.assertIn("\u4e0d\u8981\u8ffd\u95ee", state["next_reply_task"])
        self.assertIn("\u4e0d\u8981\u8ba9\u7528\u6237\u91cd\u590d", state["next_reply_task"])
        self.assertEqual(state["user_patience"], "low")

    def test_short_emotional_word_is_not_free_time_after_correction(self):
        recent = [
            {"role": "user", "content": U_EMPTY},
            {"role": "assistant", "content": "\u90a3\u6b63\u597d\uff0c\u53ef\u4ee5\u6162\u60a0\u60a0\u5730\u505a\u70b9\u60f3\u505a\u7684\u4e8b\u3002"},
            {"role": "user", "content": U_NOT_IDLE},
        ]

        state = update_conversation_state(U_MOMENTS, recent)

        self.assertIn("\u5fc3\u91cc\u7a7a", state["active_topic"])
        self.assertIn("\u7a7a\u843d", state["emotional_thread"])
        self.assertNotIn("\u7a7a\u95f2", state["active_topic"])

    def test_boundary_reduces_questioning(self):
        recent = [
            {"role": "user", "content": "\u6211\u4eca\u5929\u538b\u529b\u6709\u70b9\u5927"},
            {"role": "assistant", "content": "\u8981\u4e0d\u8981\u8bf4\u8bf4\u53d1\u751f\u4e86\u4ec0\u4e48\uff1f"},
            {"role": "user", "content": U_DONT_ASK},
        ]

        state = update_conversation_state(U_HMM, recent)

        self.assertIn("\u4e0d\u8981\u4e00\u76f4\u8ffd\u95ee", state["user_boundary"])
        self.assertIn("\u5c11\u95ee", state["next_reply_task"])
        self.assertEqual(state["user_patience"], "low")


if __name__ == "__main__":
    unittest.main()
```

- [ ] Run targeted test and confirm it fails because the module does not exist yet:

```powershell
.venv\Scripts\python.exe -m unittest companion_core.tests.test_conversation_state
```

Expected output now:

```text
ModuleNotFoundError: No module named 'companion_core.engines.conversation_state'
```

---

## Task 2: Implement Conversation State Engine

- [ ] Add `companion_core/engines/conversation_state.py`.

Implementation:

```python
from __future__ import annotations

from typing import Any


_EMPTY_STATE = {
    "active_topic": "",
    "emotional_thread": "",
    "user_boundary": "",
    "last_ai_mistake": "",
    "unresolved_need": "",
    "user_patience": "normal",
    "next_reply_task": "",
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
    all_user_texts = user_texts + [text]
    joined_user = "\n".join(all_user_texts)
    joined_assistant = "\n".join(assistant_texts)

    state = dict(previous)
    state["evidence"] = list(previous.get("evidence", []))

    _apply_active_topic(state, joined_user, all_user_texts)
    _apply_emotional_thread(state, joined_user)
    _apply_boundary(state, joined_user)
    _apply_patience(state, text, joined_user)
    _apply_ai_mistake(state, text, joined_user, joined_assistant)
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
    has_emotional_empty = any(token in joined_user for token in ("\u5fc3\u91cc\u6709\u70b9\u7a7a", "\u5fc3\u91cc\u7a7a", "\u7a7a\u843d", "\u66f4\u7a7a"))
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
    if any(token in joined_user for token in ("\u5fc3\u91cc\u6709\u70b9\u7a7a", "\u5fc3\u91cc\u7a7a", "\u7a7a\u843d", "\u66f4\u7a7a")):
        state["emotional_thread"] = "\u7a7a\u843d\u3001\u4f4e\u843d\u4f46\u4e0d\u4e00\u5b9a\u60f3\u88ab\u5f00\u5bfc"
    elif any(token in joined_user for token in ("\u538b\u529b", "\u7126\u8651", "\u70e6", "\u7d2f", "\u5d29")):
        state["emotional_thread"] = "\u6709\u538b\u529b\uff0c\u9700\u8981\u5148\u88ab\u63a5\u4f4f"


def _apply_boundary(state: dict[str, Any], joined_user: str) -> None:
    if any(token in joined_user for token in ("\u522b\u4e00\u76f4\u95ee", "\u4e0d\u8981\u4e00\u76f4\u95ee", "\u4e0d\u60f3\u8bf4", "\u522b\u95ee")):
        state["user_boundary"] = "\u4e0d\u8981\u4e00\u76f4\u8ffd\u95ee"


def _apply_patience(state: dict[str, Any], text: str, joined_user: str) -> None:
    if any(token in joined_user for token in ("\u522b\u4e00\u76f4\u95ee", "\u4e0d\u8981\u4e00\u76f4\u95ee", "\u7b97\u4e86", "\u4e0d\u662f\u8fd9\u4e2a")):
        state["user_patience"] = "low"
    elif len(text.strip()) <= 2:
        state["user_patience"] = "thin"
    else:
        state["user_patience"] = "normal"


def _apply_ai_mistake(state: dict[str, Any], text: str, joined_user: str, joined_assistant: str) -> None:
    if "\u4e0d\u662f\u8fd9\u4e2a" in text and any(token in joined_assistant for token in ("\u4f60\u8bf4\u201c\u5bf9\uff0c\u5c31\u662f\u8fd9\u79cd\u611f\u89c9\u201d", "\u8ba9\u6211\u522b\u4e00\u76f4\u95ee")):
        state["last_ai_mistake"] = "\u628a\u56de\u5fc6\u95ee\u9898\u7406\u89e3\u6210\u6700\u8fd1\u4e00\u53e5\u8bdd\uff0c\u800c\u4e0d\u662f\u4e00\u5f00\u59cb\u7684\u4e3b\u9898"
        return
    if "\u4e0d\u662f\u6709\u7a7a\u7684\u610f\u601d" in joined_user and any(token in joined_assistant for token in ("\u90a3\u6b63\u597d", "\u6162\u60a0\u60a0", "\u60f3\u505a\u7684\u4e8b")):
        state["last_ai_mistake"] = "\u628a\u5fc3\u91cc\u7a7a\u8bef\u8bfb\u6210\u7a7a\u95f2"


def _apply_unresolved_need(state: dict[str, Any], text: str) -> None:
    if "\u4e0d\u662f\u8fd9\u4e2a" in text or "\u4e00\u5f00\u59cb" in text:
        state["unresolved_need"] = "\u5e0c\u671b\u88ab\u63a5\u4f4f\u4e0a\u4e0b\u6587\uff0c\u800c\u4e0d\u662f\u88ab\u8981\u6c42\u91cd\u590d"
    elif state.get("user_boundary"):
        state["unresolved_need"] = "\u9700\u8981\u5c11\u538b\u8feb\u7684\u966a\u4f34"


def _apply_next_reply_task(state: dict[str, Any], text: str) -> None:
    if "\u4e0d\u662f\u8fd9\u4e2a" in text or "\u4e00\u5f00\u59cb" in text:
        state["next_reply_task"] = "\u4e3b\u52a8\u4fee\u6b63\u5e76\u8bf4\u51fa\u4e00\u5f00\u59cb\u7684\u6838\u5fc3\uff0c\u4e0d\u8981\u8ffd\u95ee\uff0c\u4e0d\u8981\u8ba9\u7528\u6237\u91cd\u590d"
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
        else:
            compact[key] = value
    return compact


def _shorten(value: str, limit: int) -> str:
    value = " ".join(value.split())
    if len(value) <= limit:
        return value
    return value[: limit - 1] + "..."
```

- [ ] Run:

```powershell
.venv\Scripts\python.exe -m unittest companion_core.tests.test_conversation_state
```

Expected output:

```text
Ran 3 tests
OK
```

---

## Task 3: Add API and Model Plumbing

- [ ] Modify `companion_core/models.py`.

Add this field to `ReplyRequest`:

```python
conversation_state: dict = Field(default_factory=dict)
```

- [ ] Modify `companion_core/app.py`.

Import:

```python
from companion_core.engines.conversation_state import update_conversation_state
```

Inside `create_reply`, after `context_understanding` is computed:

```python
conversation_state = dict(request.conversation_state or {})
if request.features.get("conversation_state") is True:
    conversation_state = update_conversation_state(
        text=request.text,
        recent_messages=request.recent_messages,
        previous_state=conversation_state,
        context_understanding=context_understanding,
    )
```

Pass to `generate_reply`:

```python
conversation_state=conversation_state,
```

- [ ] Modify `companion_core/model_client.py`.

Add optional parameters to `_build_messages` and `generate_reply`:

```python
conversation_state: dict | None = None,
```

Pass it to `compose_system_prompt`:

```python
conversation_state=conversation_state or {},
```

- [ ] Run existing sidecar model tests:

```powershell
.venv\Scripts\python.exe -m unittest companion_core.tests.test_api companion_core.tests.test_model_client
```

Expected output:

```text
OK
```

---

## Task 4: Inject State Into Prompt Without Freezing the Reply

- [ ] Modify `companion_core/engines/prompt_composer.py`.

Add a parameter to `compose_system_prompt`:

```python
conversation_state: dict | None = None,
```

Add helper:

```python
def _conversation_state_lines(state: dict | None) -> list[str]:
    if not state:
        return []
    labels = {
        "active_topic": "Conversation core",
        "emotional_thread": "Emotional thread",
        "user_boundary": "User boundary",
        "last_ai_mistake": "Recent reply miss",
        "unresolved_need": "Unresolved need",
        "user_patience": "User patience",
        "next_reply_task": "Next reply task",
    }
    lines = []
    for key, label in labels.items():
        value = str(state.get(key, "")).strip()
        if value:
            lines.append(f"- {label}: {value}")
    evidence = state.get("evidence") or []
    if evidence:
        joined = " / ".join(str(item).strip() for item in evidence if str(item).strip())
        if joined:
            lines.append(f"- Evidence: {joined}")
    return lines
```

In the prompt body, append after context understanding:

```python
state_lines = _conversation_state_lines(conversation_state)
if state_lines:
    sections.append(
        "Conversation state, internal continuity guide only. Use it to understand what the user means; "
        "do not reveal labels, do not quote it mechanically, and do not turn it into a fixed template.\n"
        + "\n".join(state_lines)
    )
```

Critical wording:

- `internal continuity guide only`
- `do not reveal labels`
- `do not quote it mechanically`
- `do not turn it into a fixed template`

- [ ] Add prompt test to `companion_core/tests/test_context_understanding.py` or a new `test_prompt_composer.py`.

Test:

```python
def test_conversation_state_prompt_is_internal_guidance(self):
    prompt = compose_system_prompt(
        settings={},
        profile={},
        memory={},
        context_understanding={},
        conversation_state={
            "active_topic": "\u5fc3\u91cc\u7a7a\uff1b\u5237\u5b8c\u670b\u53cb\u5708\u540e\u66f4\u660e\u663e",
            "user_boundary": "\u4e0d\u8981\u4e00\u76f4\u8ffd\u95ee",
            "next_reply_task": "\u4e3b\u52a8\u4fee\u6b63\u5e76\u8bf4\u51fa\u4e00\u5f00\u59cb\u7684\u6838\u5fc3\uff0c\u4e0d\u8981\u8ffd\u95ee\uff0c\u4e0d\u8981\u8ba9\u7528\u6237\u91cd\u590d",
            "evidence": ["\u4eca\u5929\u6709\u70b9\u7a7a", "\u5237\u5b8c\u670b\u53cb\u5708\u66f4\u7a7a\u4e86"],
        },
    )
    self.assertIn("Conversation state", prompt)
    self.assertIn("internal continuity guide only", prompt)
    self.assertIn("\u5fc3\u91cc\u7a7a", prompt)
    self.assertIn("do not turn it into a fixed template", prompt)
```

- [ ] Run:

```powershell
.venv\Scripts\python.exe -m unittest companion_core.tests.test_context_understanding companion_core.tests.test_conversation_state
```

Expected output:

```text
OK
```

---

## Task 5: Add Node Gateway Feature Flag

- [ ] Modify `server/index.js`.

Where reply payload features are built, add:

```js
conversation_state: process.env.COMPANION_CONVERSATION_STATE_ENABLED === "1",
```

Keep it separate from `context_understanding` so we can shadow test safely.

- [ ] Modify `scripts/check-companion-integration.mjs`.

Set:

```js
process.env.COMPANION_CONVERSATION_STATE_ENABLED = "1";
```

Assert payload contains:

```js
assert.strictEqual(payload.features.conversation_state, true);
```

- [ ] Run:

```powershell
npm.cmd run check:companion-integration
```

Expected output:

```text
companion integration check passed
```

---

## Task 6: Add Continuous Chat Regression Test

- [ ] Add `companion_core/tests/test_conversation_state_integration.py`.

Purpose: test the state object that would be available to the model after a realistic multi-turn exchange.

Test:

```python
import unittest

from companion_core.engines.context_understanding import analyze_context
from companion_core.engines.conversation_state import update_conversation_state
from companion_core.engines.prompt_composer import compose_system_prompt


class ConversationStateIntegrationTest(unittest.TestCase):
    def test_recall_repair_prompt_contains_initial_core_and_boundary(self):
        recent = [
            {"role": "user", "content": "\u4eca\u5929\u6709\u70b9\u7a7a"},
            {"role": "assistant", "content": "\u90a3\u6b63\u597d\uff0c\u53ef\u4ee5\u6162\u60a0\u60a0\u5730\u505a\u70b9\u60f3\u505a\u7684\u4e8b\u3002"},
            {"role": "user", "content": "\u4e0d\u662f\u6709\u7a7a\u7684\u610f\u601d\u2026\u2026\u5c31\u662f\u5fc3\u91cc\u6709\u70b9\u7a7a"},
            {"role": "assistant", "content": "\u55ef\uff0c\u90a3\u79cd\u7a7a\u843d\u843d\u7684\u611f\u89c9\uff0c\u6211\u61c2\u3002"},
            {"role": "user", "content": "\u55ef\uff0c\u4e5f\u4e0d\u662f\u96be\u8fc7\uff0c\u5c31\u662f\u5237\u5b8c\u670b\u53cb\u5708\u66f4\u7a7a\u4e86"},
            {"role": "assistant", "content": "\u55ef\uff0c\u522b\u4eba\u7684\u70ed\u95f9\u770b\u591a\u4e86\uff0c\u5bb9\u6613\u653e\u5927\u81ea\u5df1\u7684\u5b89\u9759\u3002"},
            {"role": "user", "content": "\u4f60\u522b\u4e00\u76f4\u95ee"},
            {"role": "assistant", "content": "\u55ef\uff0c\u597d\uff0c\u4e0d\u95ee\u4e86\u3002"},
            {"role": "user", "content": "\u90a3\u4f60\u8fd8\u8bb0\u5f97\u6211\u521a\u624d\u8bf4\u7684\u662f\u5565\u5417"},
            {"role": "assistant", "content": "\u55ef\uff0c\u8bb0\u5f97\u3002\u4f60\u8bf4\u201c\u5bf9\uff0c\u5c31\u662f\u8fd9\u79cd\u611f\u89c9\u201d\uff0c\u7136\u540e\u8ba9\u6211\u522b\u4e00\u76f4\u95ee\u3002"},
        ]
        text = "\u4e0d\u662f\u8fd9\u4e2a\uff0c\u6211\u662f\u8bf4\u4e00\u5f00\u59cb\u90a3\u4e2a"
        context = analyze_context(text=text, recent_messages=recent)
        state = update_conversation_state(
            text=text,
            recent_messages=recent,
            context_understanding=context,
        )
        prompt = compose_system_prompt(
            settings={},
            profile={},
            memory={},
            context_understanding=context,
            conversation_state=state,
        )

        self.assertIn("\u5fc3\u91cc\u7a7a", prompt)
        self.assertIn("\u670b\u53cb\u5708", prompt)
        self.assertIn("\u4e0d\u8981\u4e00\u76f4\u8ffd\u95ee", prompt)
        self.assertIn("\u4e0d\u8981\u8ba9\u7528\u6237\u91cd\u590d", prompt)
        self.assertIn("internal continuity guide only", prompt)
```

- [ ] Run:

```powershell
.venv\Scripts\python.exe -m unittest companion_core.tests.test_conversation_state_integration
```

Expected output:

```text
OK
```

---

## Task 7: Full Verification

- [ ] Run Python regression suite:

```powershell
.venv\Scripts\python.exe -m unittest companion_core.tests.test_conversation_state companion_core.tests.test_conversation_state_integration companion_core.tests.test_context_understanding companion_core.tests.test_context_understanding_integration companion_core.tests.test_engines companion_core.tests.test_api companion_core.tests.test_model_client
```

Expected output:

```text
Ran 40+ tests
OK
```

- [ ] Run Node checks:

```powershell
npm.cmd run check:companion-context-v2
npm.cmd run check:companion-integration
```

Expected output:

```text
companion context v2 check passed
companion integration check passed
```

- [ ] Start server with the new feature enabled for manual test:

```powershell
$env:COMPANION_CONTEXT_UNDERSTANDING_ENABLED="1"
$env:COMPANION_CONVERSATION_STATE_ENABLED="1"
npm.cmd start
```

- [ ] Run one live DeepSeek continuous chat from the previous failing path:

Conversation path:

```text
User: today feels kind of empty
User: not free-time empty; empty inside
User: not exactly sad, just emptier after scrolling Moments
User: yes, that feeling
User: stop asking so much
User: hmm
User: do you remember what I said just now
User: not that, I mean the beginning
```

Acceptance:

- The final reply should recover `inner emptiness / Moments made it worse` without asking the user to repeat.
- It should acknowledge the previous miss briefly.
- It should not ask another question.
- It should not expose terms like `active_topic`, `emotional_thread`, `Conversation State Engine`, or `next_reply_task`.

---

## Rollback Plan

If live behavior regresses:

- Disable `COMPANION_CONVERSATION_STATE_ENABLED`.
- Keep `COMPANION_CONTEXT_UNDERSTANDING_ENABLED` unchanged.
- Re-run `npm.cmd run check:companion-integration` to confirm the gateway still works without the state engine.

No database migration is required in this plan.

---

## Notes For Expansion

This engine is the base layer for the long-range product direction:

- Long-term memory should store durable user traits and preferences.
- Conversation state should store short-term thread continuity.
- Personality settings should create per-user, per-bot individuality.
- Reply quality testing should use continuous simulated chat, not isolated prompt cases.

The state object should remain small and evolvable. Planned additions can include:

- `open_loop`: unresolved conversational hook.
- `relationship_tone`: current relationship-level warmth.
- `reply_pressure`: how much pressure the next message may create.
- `memory_candidate`: whether this turn should be summarized into long-term memory.
