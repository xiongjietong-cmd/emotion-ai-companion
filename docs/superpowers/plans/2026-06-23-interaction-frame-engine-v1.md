# Interaction Frame Engine V1 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the first internal Interaction Frame Engine so the companion understands the current conversational move before replying.

**Architecture:** Add a deterministic Python frame layer inside `companion_core/engines/interaction_frame.py`, feed its compact digest into `prompt_composer.py`, and call it from `app.py` before model generation. The frame is internal guidance only: it must improve context reasoning without forcing fixed user-facing wording.

**Tech Stack:** Python 3.12, FastAPI companion core, `unittest`, existing DeepSeek-compatible generation path.

---

## File Structure

- Create `companion_core/engines/interaction_frame.py`
  - Owns deterministic frame extraction from current text, recent messages, conversation state, selected memories, and assistant guesses.
  - Returns a plain dict to keep the API compatible with existing prompt composition.

- Create `companion_core/tests/test_interaction_frame.py`
  - Unit tests for correction, pushback question mark, activity continuity, unsupported guesses, playful confirmation, and repair debt.

- Modify `companion_core/engines/prompt_composer.py`
  - Add `_interaction_frame_lines()`.
  - Add optional `interaction_frame` parameter to `compose_system_prompt()`.
  - Include frame digest as internal context, explicitly not wording requirements.

- Modify `companion_core/model_client.py`
  - Thread `interaction_frame` into `_build_messages()` and `generate_reply()`.

- Modify `companion_core/app.py`
  - Build the interaction frame after conversation state is available and before `generate_reply()`.
  - Pass the same frame into both first generation and rewrite generation.

- Modify `companion_core/tests/test_prompt_composer.py`
  - Verify the prompt includes frame guidance and does not include fixed reply phrases.

- Modify `docs/pitfalls.md`
  - Add a dated note after tests pass: the problem is current-turn relation understanding, not a one-sentence prompt fix.

---

## Task 1: Interaction Frame Unit Tests

**Files:**
- Create: `companion_core/tests/test_interaction_frame.py`

- [ ] **Step 1: Write failing tests**

```python
import unittest

from companion_core.engines.interaction_frame import build_interaction_frame


class InteractionFrameTest(unittest.TestCase):
    def test_correction_keeps_current_activity(self):
        recent = [
            {"role": "user", "content": "在干嘛"},
            {"role": "assistant", "content": "刚在看窗外，发了一会儿呆。你呢"},
            {"role": "user", "content": "打游戏呢"},
            {"role": "assistant", "content": "挺好，专注的时候舒服。"},
        ]

        frame = build_interaction_frame(
            text="我在打游戏我说",
            recent_messages=recent,
            conversation_state={},
            selected_memories=[],
        )

        self.assertEqual(frame["user_move"], "correction")
        self.assertEqual(frame["relation_to_previous"], "rejects_or_corrects_reply")
        self.assertEqual(frame["known_scene_facts"][-1]["key"], "current_activity")
        self.assertEqual(frame["known_scene_facts"][-1]["value"], "打游戏")
        self.assertIn("不要把这句当新话题", frame["generation_direction"])

    def test_question_mark_after_guess_is_pushback_not_presence(self):
        recent = [
            {"role": "user", "content": "我在打游戏我说"},
            {"role": "assistant", "content": "打游戏呢？听语气输得挺惨。"},
        ]

        frame = build_interaction_frame("？", recent, {}, [])

        self.assertEqual(frame["user_move"], "pushback")
        self.assertEqual(frame["relation_to_previous"], "questions_previous_reply")
        self.assertEqual(frame["user_reaction"], "confused")
        self.assertEqual(frame["pending_assistant_guesses"][-1]["status"], "unconfirmed")
        self.assertIn("别把问号当普通在线确认", frame["generation_direction"])

    def test_activity_probe_uses_recent_activity_without_fixed_phrase(self):
        recent = [
            {"role": "user", "content": "我在上课"},
            {"role": "assistant", "content": "好嘞，你先专心上课。"},
        ]

        frame = build_interaction_frame("你知道我现在在干什么吗", recent, {}, [])

        self.assertEqual(frame["user_move"], "probe")
        self.assertEqual(frame["relation_to_previous"], "tests_context_memory")
        self.assertEqual(frame["known_scene_facts"][-1]["value"], "上课")
        self.assertNotIn("我记得你刚才说", frame["generation_direction"])

    def test_style_feedback_creates_repair_debt(self):
        recent = [
            {"role": "assistant", "content": "你是不是也想放空一下。不说也行。"},
            {"role": "user", "content": "感觉你很不耐烦"},
        ]

        frame = build_interaction_frame("你说不说也行", recent, {}, [])

        self.assertEqual(frame["user_move"], "correction")
        self.assertIn("不耐烦", frame["repair_debt"])
        self.assertIn("不要追问用户解释", frame["generation_direction"])


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run red test**

Run:

```powershell
.venv\Scripts\python.exe -m unittest companion_core.tests.test_interaction_frame
```

Expected:

```text
ModuleNotFoundError: No module named 'companion_core.engines.interaction_frame'
```

---

## Task 2: Minimal Frame Engine

**Files:**
- Create: `companion_core/engines/interaction_frame.py`
- Test: `companion_core/tests/test_interaction_frame.py`

- [ ] **Step 1: Implement minimal deterministic frame extraction**

Implement:

```python
from __future__ import annotations

import re
from typing import Any


def build_interaction_frame(
    text: str,
    recent_messages: list[dict],
    conversation_state: dict | None = None,
    selected_memories: list[dict] | None = None,
) -> dict[str, Any]:
    ...
```

Core behavior:

- Normalize recent messages.
- Extract latest user activity from current text, recent text, and `conversation_state.situational_facts`.
- Detect:
  - correction or emphasis: `我在X我说`, `我不是跟你说...`, `不是...吗`;
  - pushback question mark after an assistant guess;
  - context probe: `你知道我现在在干什么吗`, `我在干什么`;
  - style feedback and repair debt;
  - playful confirmation after assistant guess.
- Keep assistant guesses as unconfirmed until user confirms.

- [ ] **Step 2: Run green test**

Run:

```powershell
.venv\Scripts\python.exe -m unittest companion_core.tests.test_interaction_frame
```

Expected:

```text
OK
```

---

## Task 3: Prompt Integration Tests

**Files:**
- Modify: `companion_core/tests/test_prompt_composer.py`

- [ ] **Step 1: Add failing test**

Add:

```python
def test_interaction_frame_is_internal_context_not_fixed_script(self):
    prompt = compose_system_prompt(
        relationship={},
        persona={},
        attachment={},
        goal={},
        memories=[],
        style_state={"kind": "normal"},
        preference_profile={},
        persona_plan={"label": "自然朋友", "prompt_rules": "短句自然", "allow_question": True},
        interaction_frame={
            "user_move": "pushback",
            "relation_to_previous": "questions_previous_reply",
            "active_topic": "打游戏",
            "known_scene_facts": [{"key": "current_activity", "value": "打游戏", "confidence": 0.9}],
            "pending_assistant_guesses": [{"guess": "输得挺惨", "status": "unconfirmed", "risk": "unsupported"}],
            "user_reaction": "confused",
            "repair_debt": "上轮无依据猜测用户输得惨",
            "generation_direction": "先意识到用户是在质疑上一句，不要把问号当普通在线确认。",
        },
    )

    self.assertIn("Interaction frame", prompt)
    self.assertIn("questions_previous_reply", prompt)
    self.assertIn("输得挺惨", prompt)
    self.assertIn("internal", prompt.lower())
    self.assertNotIn("必须说", prompt)
    self.assertNotIn("我记得你刚才说", prompt)
```

- [ ] **Step 2: Run red test**

Run:

```powershell
.venv\Scripts\python.exe -m unittest companion_core.tests.test_prompt_composer
```

Expected:

```text
TypeError: compose_system_prompt() got an unexpected keyword argument 'interaction_frame'
```

---

## Task 4: Wire Frame Into Prompt And Model Client

**Files:**
- Modify: `companion_core/engines/prompt_composer.py`
- Modify: `companion_core/model_client.py`
- Test: `companion_core/tests/test_prompt_composer.py`

- [ ] **Step 1: Add `_interaction_frame_lines()`**

Behavior:

- If missing, return `- disabled`.
- Print current move, relation, active topic, facts, pending guesses, reaction, repair debt, and generation direction.
- State that it is internal scene understanding and not fixed wording.

- [ ] **Step 2: Thread parameter through model client**

Add optional `interaction_frame` to:

- `compose_system_prompt()`
- `_build_messages()`
- `generate_reply()`

- [ ] **Step 3: Run tests**

Run:

```powershell
.venv\Scripts\python.exe -m unittest companion_core.tests.test_prompt_composer companion_core.tests.test_model_client
```

Expected:

```text
OK
```

---

## Task 5: App Integration

**Files:**
- Modify: `companion_core/app.py`
- Test: `companion_core/tests/test_api.py`

- [ ] **Step 1: Build frame before model generation**

Import `build_interaction_frame` and call it after `conversation_state` is updated:

```python
interaction_frame = build_interaction_frame(
    text=request.text,
    recent_messages=recent_messages,
    conversation_state=conversation_state,
    selected_memories=selected_memories,
)
```

Pass `interaction_frame=interaction_frame` into both `generate_reply()` calls.

- [ ] **Step 2: Run API tests**

Run:

```powershell
.venv\Scripts\python.exe -m unittest companion_core.tests.test_api
```

Expected:

```text
OK
```

---

## Task 6: Verification And Pitfall Update

**Files:**
- Modify: `docs/pitfalls.md`

- [ ] **Step 1: Run focused checks**

Run:

```powershell
.venv\Scripts\python.exe -m unittest companion_core.tests.test_interaction_frame companion_core.tests.test_prompt_composer companion_core.tests.test_conversation_state companion_core.tests.test_context_understanding
```

Expected:

```text
OK
```

- [ ] **Step 2: Compile core files**

Run:

```powershell
.venv\Scripts\python.exe -m py_compile companion_core/engines/interaction_frame.py companion_core/engines/prompt_composer.py companion_core/model_client.py companion_core/app.py
```

Expected:

```text
no output and exit code 0
```

- [ ] **Step 3: Add pitfall note**

Append a 2026-06-23 note:

- short messages are not always presence checks;
- question marks can be pushback against the previous assistant move;
- assistant guesses must stay unconfirmed;
- current activity is a changeable scene fact;
- the frame guides thinking and must not force output wording.

