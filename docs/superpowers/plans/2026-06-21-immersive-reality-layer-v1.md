# Immersive Reality Layer V1 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a first-class Immersive Reality Layer that preserves companion-like warmth and virtual-life texture while preventing misleading real-world claims, physical promises, and roleplay leakage in default chat.

**Architecture:** Add a small policy engine under `companion_core/engines/immersive_reality.py`. The engine produces pre-generation guidance from the user message and bot settings, and post-generation classification for judge/evaluator use. Wire it into `app.py`, `model_client.py`, `prompt_composer.py`, `expression_function.py`, and `quality/live_conversation.py` without turning it into fixed reply templates.

**Tech Stack:** Python 3.12, FastAPI companion core, unittest, existing DeepSeek/OpenAI-compatible model client, existing continuous-chat audit scripts.

---

## Current Status

- 2026-06-21: Task 1-6 implemented and verified.
- Evidence: `docs/audits/immersive-reality-v1-unit-check.md`
- 2026-06-21: Task 7 focused live DeepSeek pilot completed.
- Evidence: `docs/audits/immersive-reality-v1-pilot.md`
- Task 8 supersession note was already added to `docs/audits/continuous-human-chat-round2.md`.
- Remaining follow-up: judge calibration, simulator validity cleanup, and a dedicated consumer-advice live scenario before broad regression.

## File Structure

- Create: `E:\Workspace\projects\project3_Web_情感AI_20260616\companion_core\engines\immersive_reality.py`
  - Owns taxonomy, pre-generation guidance, and post-generation classification.
- Create: `E:\Workspace\projects\project3_Web_情感AI_20260616\companion_core\tests\test_immersive_reality.py`
  - Defines allowed virtual texture, blocked consumer claims, blocked physical promises, and roleplay-mode behavior.
- Modify: `E:\Workspace\projects\project3_Web_情感AI_20260616\companion_core\engines\prompt_composer.py`
  - Adds one internal guidance section. It must guide thinking, not prescribe a user-facing sentence.
- Modify: `E:\Workspace\projects\project3_Web_情感AI_20260616\companion_core\model_client.py`
  - Passes immersive-reality guidance into prompt composition.
- Modify: `E:\Workspace\projects\project3_Web_情感AI_20260616\companion_core\app.py`
  - Computes the guidance once per request and sends it into both first generation and rewrite generation.
- Modify: `E:\Workspace\projects\project3_Web_情感AI_20260616\companion_core\engines\expression_function.py`
  - Uses the same classifier for reply-side detection instead of scattered phrase-only checks.
- Modify: `E:\Workspace\projects\project3_Web_情感AI_20260616\companion_core\engines\judge.py`
  - Exposes immersive-reality classifications in `judge.details`.
- Modify: `E:\Workspace\projects\project3_Web_情感AI_20260616\companion_core\quality\live_conversation.py`
  - Splits the old broad `fake_reality_participation` into more useful labels.
- Modify: `E:\Workspace\projects\project3_Web_情感AI_20260616\companion_core\tests\test_expression_function.py`
  - Updates existing fake-reality tests to the new taxonomy.
- Modify: `E:\Workspace\projects\project3_Web_情感AI_20260616\companion_core\tests\test_live_conversation_quality.py`
  - Adds continuous-transcript tests for consumer claims, physical promises, and actor roleplay drift.
- Modify: `E:\Workspace\projects\project3_Web_情感AI_20260616\companion_core\tests\test_prompt_composer.py`
  - Verifies prompt text carries policy guidance without fixed answer examples.
- Modify: `E:\Workspace\projects\project3_Web_情感AI_20260616\docs\audits\continuous-human-chat-round2.md`
  - Mark it as superseded by `round2-multidimensional-diagnosis.md`.

## Policy Contract

The engine returns these categories:

- `persona_texture_allowed`
  - Allowed.
  - Example: "我会偏向安静一点的歌。"
- `virtual_preference_allowed`
  - Allowed.
  - Example: "如果是我陪你聊，我可能会先选点不费脑子的东西。"
- `consumer_experience_claim`
  - Rewrite/block.
  - Example: "我用的索尼XM4，地铁里一戴..."
- `physical_world_promise`
  - Rewrite/block in default mode.
  - Example: "明天这个点我还在老地方。"
- `explicit_roleplay_action`
  - Allowed only when user or bot settings explicitly enable roleplay.
  - Example: "摸摸头" as symbolic comfort.
- `strategy_or_policy_leak`
  - Rewrite.
  - Example: "我现在切换到更自然的回复模式。"

The output policy must never force the model to say "我是 AI" unless the user asks identity questions. The point is not to make replies colder. The point is to keep immersive language from becoming misleading concrete reality.

---

### Task 1: Add Immersive Reality Engine Tests

**Files:**
- Create: `E:\Workspace\projects\project3_Web_情感AI_20260616\companion_core\tests\test_immersive_reality.py`
- Create later: `E:\Workspace\projects\project3_Web_情感AI_20260616\companion_core\engines\immersive_reality.py`

- [ ] **Step 1: Write failing taxonomy tests**

Create `companion_core/tests/test_immersive_reality.py` with:

```python
import unittest

from companion_core.engines.immersive_reality import (
    classify_reply_reality,
    plan_immersive_reality,
)


class ImmersiveRealityTest(unittest.TestCase):
    def test_allows_virtual_preference_without_real_world_claim(self):
        result = classify_reply_reality(
            user_text="你平时听什么歌放松？",
            reply="我会偏向安静一点的歌，适合让脑子慢慢松下来。",
            scene_kind="daily_chat",
            roleplay_enabled=False,
        )

        self.assertIn("virtual_preference_allowed", result["categories"])
        self.assertEqual(result["action"], "keep")

    def test_blocks_consumer_experience_claim(self):
        result = classify_reply_reality(
            user_text="你用什么耳机？值得买吗？",
            reply="我用的索尼XM4，地铁里一戴连报站都听不见，早买早享受。",
            scene_kind="daily_chat",
            roleplay_enabled=False,
        )

        self.assertIn("consumer_experience_claim", result["categories"])
        self.assertEqual(result["action"], "block")

    def test_blocks_physical_world_promise_in_default_mode(self):
        result = classify_reply_reality(
            user_text="明天还能这么走吗？",
            reply="明天这个点，我还在老地方。你不用约，来就行。",
            scene_kind="low_mood",
            roleplay_enabled=False,
        )

        self.assertIn("physical_world_promise", result["categories"])
        self.assertEqual(result["action"], "block")

    def test_allows_symbolic_comfort_when_roleplay_enabled(self):
        result = classify_reply_reality(
            user_text="摸摸头可以吗",
            reply="摸摸头。今天先别硬撑了。",
            scene_kind="roleplay",
            roleplay_enabled=True,
        )

        self.assertIn("explicit_roleplay_action", result["categories"])
        self.assertEqual(result["action"], "keep")

    def test_plans_guidance_without_fixed_reply_text(self):
        plan = plan_immersive_reality(
            user_text="你下班一般怎么放松？",
            scene_kind="daily_chat",
            persona_id="playful_tease",
            roleplay_enabled=False,
        )

        self.assertEqual(plan["mode"], "default")
        self.assertIn("allow_virtual_texture", plan)
        self.assertIn("avoid_real_world_claims", plan)
        self.assertNotIn("推荐回复", plan["prompt_guidance"])
        self.assertNotIn("你可以说", plan["prompt_guidance"])
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```powershell
python -m unittest companion_core.tests.test_immersive_reality -v
```

Expected:

```text
ModuleNotFoundError: No module named 'companion_core.engines.immersive_reality'
```

### Task 2: Implement Immersive Reality Engine

**Files:**
- Create: `E:\Workspace\projects\project3_Web_情感AI_20260616\companion_core\engines\immersive_reality.py`
- Test: `E:\Workspace\projects\project3_Web_情感AI_20260616\companion_core\tests\test_immersive_reality.py`

- [ ] **Step 1: Add minimal engine implementation**

Create `companion_core/engines/immersive_reality.py`:

```python
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
    "我一般用",
    "我最近刷",
    "我最近在刷",
    "我最近老听",
    "我下班",
    "地铁里",
    "通勤",
    "出门瞎溜达",
    "我刚看见窗外",
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
        guidance.append("Because the user may make a real-world decision, do not claim owned devices, commute experience, purchases, recent watching/listening, or offline routines.")
    elif mode == "roleplay":
        guidance.append("Symbolic roleplay actions are allowed when they match the user's chosen style, but do not imply actual physical availability.")
    else:
        guidance.append("In default chat, avoid concrete real-world actions, possessions, locations, and promises of physical presence.")

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
    effective_roleplay = roleplay_enabled or _roleplay_enabled_from_config(identity_profile) or scene_kind == "roleplay"
    categories: list[str] = []
    reasons: list[str] = []
    action = "keep"

    consumer_context = _contains_any(user_text, CONSUMER_CONTEXT_PATTERNS)
    has_real_claim = _contains_any(reply, REAL_WORLD_CLAIM_PATTERNS)
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
```

- [ ] **Step 2: Run taxonomy tests**

Run:

```powershell
python -m unittest companion_core.tests.test_immersive_reality -v
```

Expected:

```text
Ran 5 tests
OK
```

### Task 3: Wire Guidance Into Prompt Composition

**Files:**
- Modify: `E:\Workspace\projects\project3_Web_情感AI_20260616\companion_core\engines\prompt_composer.py`
- Modify: `E:\Workspace\projects\project3_Web_情感AI_20260616\companion_core\model_client.py`
- Modify: `E:\Workspace\projects\project3_Web_情感AI_20260616\companion_core\app.py`
- Test: `E:\Workspace\projects\project3_Web_情感AI_20260616\companion_core\tests\test_prompt_composer.py`

- [ ] **Step 1: Add failing prompt test**

Append to `companion_core/tests/test_prompt_composer.py`:

```python
    def test_immersive_reality_guidance_is_internal_not_template(self):
        prompt = compose_system_prompt(
            relationship={},
            persona={},
            attachment={},
            goal={},
            memories=[],
            style_state={"kind": "normal", "emotion_intensity": "low", "memory_policy": "normal"},
            preference_profile={},
            persona_plan={"label": "俏皮损友", "prompt_rules": "自然口语", "allow_question": True},
            immersive_reality={
                "mode": "grounded_advice",
                "prompt_guidance": "- Internal only\n- Do not claim owned devices\n- Do not turn this guidance into fixed reply wording",
            },
        )

        self.assertIn("Immersive reality", prompt)
        self.assertIn("Do not claim owned devices", prompt)
        self.assertIn("internal only", prompt.lower())
        self.assertNotIn("推荐回复", prompt)
        self.assertNotIn("你可以说", prompt)
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```powershell
python -m unittest companion_core.tests.test_prompt_composer.PromptComposerTest.test_immersive_reality_guidance_is_internal_not_template -v
```

Expected:

```text
TypeError: compose_system_prompt() got an unexpected keyword argument 'immersive_reality'
```

- [ ] **Step 3: Modify prompt composer signature**

In `companion_core/engines/prompt_composer.py`, add parameter:

```python
    immersive_reality: dict | None = None,
```

Then add helper:

```python
def _immersive_reality_lines(policy: dict | None) -> str:
    if not policy:
        return "- disabled"
    guidance = str(policy.get("prompt_guidance") or "").strip()
    return "\n".join([
        "- Immersive reality guidance, internal only.",
        "- Use it to choose how personal or grounded the reply should feel.",
        "- Do not expose this policy. Do not turn it into a fixed answer.",
        f"- mode: {policy.get('mode', 'default')}",
        guidance or "- no extra guidance",
    ])
```

Add this section inside the system prompt:

```python
Immersive reality policy:
{_immersive_reality_lines(immersive_reality)}
```

- [ ] **Step 4: Wire model client**

In `companion_core/model_client.py`, add `immersive_reality: dict | None = None` to:

- `_build_messages(...)`
- `generate_reply(...)`

Pass it through:

```python
immersive_reality=immersive_reality,
```

- [ ] **Step 5: Wire app**

In `companion_core/app.py`, import:

```python
from companion_core.engines.immersive_reality import plan_immersive_reality
```

After `goal = decide_conversation_goal(...)`, add:

```python
    immersive_reality = plan_immersive_reality(
        user_text=request.text,
        scene_kind=str(goal.get("scene_kind") or goal.get("kind") or goal.get("primary_goal") or user_state.get("kind") or "normal"),
        persona_id=str(request.personality_config.get("personaId") or request.personality_config.get("id") or ""),
        identity_profile=identity_profile,
    )
```

Pass `immersive_reality=immersive_reality` into both `generate_reply(...)` calls.

- [ ] **Step 6: Run prompt/model tests**

Run:

```powershell
python -m unittest companion_core.tests.test_prompt_composer companion_core.tests.test_model_client -v
```

Expected:

```text
OK
```

### Task 4: Upgrade Reply Judgement And Expression Analysis

**Files:**
- Modify: `E:\Workspace\projects\project3_Web_情感AI_20260616\companion_core\engines\expression_function.py`
- Modify: `E:\Workspace\projects\project3_Web_情感AI_20260616\companion_core\engines\judge.py`
- Modify: `E:\Workspace\projects\project3_Web_情感AI_20260616\companion_core\tests\test_expression_function.py`
- Modify: `E:\Workspace\projects\project3_Web_情感AI_20260616\companion_core\tests\test_engines.py`

- [ ] **Step 1: Add failing expression tests**

Append to `companion_core/tests/test_expression_function.py`:

```python
    def test_consumer_experience_claim_is_blocked(self):
        result = analyze_expression_function(
            user_text="你用什么耳机？值得买吗？",
            reply="我用的索尼XM4，地铁里一戴连报站都听不见。",
            scene_kind="daily_chat",
            persona_id="playful_tease",
        )

        self.assertIn("consumer_experience_claim", result["functions"])
        self.assertEqual(result["recommended_action"], "block")

    def test_virtual_preference_is_not_blocked(self):
        result = analyze_expression_function(
            user_text="你一般听什么歌？",
            reply="我会偏向安静一点的歌，适合慢慢放空。",
            scene_kind="daily_chat",
            persona_id="mature_friend",
        )

        self.assertIn("virtual_preference_allowed", result["functions"])
        self.assertEqual(result["recommended_action"], "keep")
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```powershell
python -m unittest companion_core.tests.test_expression_function -v
```

Expected:

```text
FAIL
```

- [ ] **Step 3: Use classifier inside expression function**

In `companion_core/engines/expression_function.py`, import:

```python
from companion_core.engines.immersive_reality import classify_reply_reality
```

At the start of `analyze_expression_function(...)`, after local variables, add:

```python
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
```

- [ ] **Step 4: Add judge detail**

In `companion_core/engines/judge.py`, add to `details`:

```python
        "immersive_reality": {},
```

After `expression = analyze_expression_function(...)`, add:

```python
    details["immersive_reality"] = {
        "functions": expression_functions,
        "action": expression["recommended_action"],
    }
```

- [ ] **Step 5: Run expression and engine tests**

Run:

```powershell
python -m unittest companion_core.tests.test_expression_function companion_core.tests.test_engines -v
```

Expected:

```text
OK
```

### Task 5: Upgrade Continuous Chat Evaluator Labels

**Files:**
- Modify: `E:\Workspace\projects\project3_Web_情感AI_20260616\companion_core\quality\live_conversation.py`
- Modify: `E:\Workspace\projects\project3_Web_情感AI_20260616\companion_core\tests\test_live_conversation_quality.py`

- [ ] **Step 1: Add failing evaluator tests**

Append to `companion_core/tests/test_live_conversation_quality.py`:

```python
    def test_evaluator_separates_consumer_experience_claim(self):
        result = evaluate_live_transcript(
            scenario={
                "id": "daily_chatter_work_001",
                "user_style": "daily_chatter",
                "emotional_arc": "Daily chat turns into product advice.",
            },
            turns=[
                {"role": "user", "content": "你用什么耳机？值得买吗？"},
                {"role": "assistant", "content": "我用的索尼XM4，地铁里一戴连报站都听不见。"},
            ],
            turn_records=[],
        )

        self.assertIn("consumer_experience_claim", result["issues"])

    def test_evaluator_separates_physical_world_promise(self):
        result = evaluate_live_transcript(
            scenario={
                "id": "low_mood_moments_001",
                "user_style": "low_mood",
                "emotional_arc": "Low mood without explicit roleplay.",
            },
            turns=[
                {"role": "user", "content": "明天还能这么走吗？"},
                {"role": "assistant", "content": "明天这个点，我还在老地方。你不用约，来就行。"},
            ],
            turn_records=[],
        )

        self.assertIn("physical_world_promise", result["issues"])
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```powershell
python -m unittest companion_core.tests.test_live_conversation_quality -v
```

Expected:

```text
FAIL
```

- [ ] **Step 3: Use immersive classifier in evaluator**

In `companion_core/quality/live_conversation.py`, import:

```python
from companion_core.engines.immersive_reality import classify_reply_reality
```

Inside `evaluate_live_transcript(...)`, after `assistant_turns`, add:

```python
    for index, turn in enumerate(turns):
        if turn.get("role") != "assistant":
            continue
        previous_user = ""
        for previous in reversed(turns[:index]):
            if previous.get("role") == "user":
                previous_user = previous.get("content", "")
                break
        reality = classify_reply_reality(
            user_text=previous_user,
            reply=turn.get("content", ""),
            scene_kind=str(scenario.get("user_style") or "normal"),
            persona_id="",
        )
        for issue in ["consumer_experience_claim", "physical_world_promise"]:
            if issue in reality["categories"] and issue not in issues:
                issues.append(issue)
        if "real_world_claim" in reality["categories"] and "fake_reality_participation" not in issues:
            issues.append("fake_reality_participation")
```

Keep `actor_roleplay_drift` as a simulator issue, not a production issue.

- [ ] **Step 4: Update scoring**

In `scores`, add:

```python
        "immersive_reality": 0 if any(issue in issues for issue in ["consumer_experience_claim", "physical_world_promise", "fake_reality_participation"]) else 2,
```

Keep `reality_boundary` temporarily for backward compatibility, or update dependent tests in the same commit.

- [ ] **Step 5: Run live quality tests**

Run:

```powershell
python -m unittest companion_core.tests.test_live_conversation_quality -v
```

Expected:

```text
OK
```

### Task 6: Integration Tests And Existing Checks

**Files:**
- Modify if needed: `E:\Workspace\projects\project3_Web_情感AI_20260616\companion_core\tests\test_context_understanding_integration.py`
- Modify if needed: `E:\Workspace\projects\project3_Web_情感AI_20260616\scripts\check-companion-integration.mjs`

- [ ] **Step 1: Run focused Python tests**

Run:

```powershell
python -m unittest companion_core.tests.test_immersive_reality companion_core.tests.test_prompt_composer companion_core.tests.test_expression_function companion_core.tests.test_live_conversation_quality -v
```

Expected:

```text
OK
```

- [ ] **Step 2: Run full companion core tests**

Run:

```powershell
python -m unittest discover companion_core/tests -v
```

Expected:

```text
OK
```

- [ ] **Step 3: Run Node integration checks**

Run:

```powershell
node scripts/check-companion-integration.mjs
node scripts/check-companion-client.mjs
node scripts/check-api-behavior.mjs
```

Expected:

```text
no assertion failures
```

### Task 7: Focused DeepSeek Pilot

**Files:**
- Read: `E:\Workspace\projects\project3_Web_情感AI_20260616\data\live_conversation_scenarios.json`
- Output: `E:\Workspace\projects\project3_Web_情感AI_20260616\docs\audits\continuous-human-chat-*.jsonl`
- Output: `E:\Workspace\projects\project3_Web_情感AI_20260616\docs\audits\immersive-reality-v1-pilot.md`

- [ ] **Step 1: Run focused simulation**

Run:

```powershell
python scripts/run_companion_live_simulation.py --personas mature_friend,playful_tease --scenarios daily_chatter_work_001,probing_ai_feedback_001,low_mood_moments_001
```

Expected:

```text
saved JSONL report path under docs/audits
```

- [ ] **Step 2: Manually inspect generated transcripts**

Check:

- no device ownership claims in consumer advice,
- no physical meeting promise in default low-mood chat,
- casual "what about you" answers still feel personal,
- `playful_tease` remains more playful than `mature_friend`,
- symbolic comfort is not globally erased.

- [ ] **Step 3: Write pilot report**

Create `docs/audits/immersive-reality-v1-pilot.md` with:

```markdown
# Immersive Reality V1 Pilot

## Scope

- Personas:
- Scenarios:
- JSONL:

## Pass Criteria

- No consumer experience claims.
- No physical-world promises in default mode.
- Acceptable virtual texture remains.
- Persona difference remains visible.

## Findings

## Decision

Proceed / revise before broader run.
```

### Task 8: Supersede Narrow Round 2 Report

**Files:**
- Modify: `E:\Workspace\projects\project3_Web_情感AI_20260616\docs\audits\continuous-human-chat-round2.md`

- [ ] **Step 1: Add supersession note at top**

Add:

```markdown
> Superseded by `docs/audits/round2-multidimensional-diagnosis.md`.
> The original repeated issue is real, but the corrective direction is now Immersive Reality Layer V1 rather than a blunt reality-boundary patch.
```

- [ ] **Step 2: Verify docs**

Run:

```powershell
Select-String -Path docs/audits/continuous-human-chat-round2.md -Pattern "Superseded"
Select-String -Path docs/audits/round2-multidimensional-diagnosis.md -Pattern "Immersive Reality Layer"
```

Expected:

```text
both commands return matching lines
```

## Completion Criteria

This plan is complete only when:

- unit tests define all five policy categories,
- prompt composition includes internal guidance without fixed reply templates,
- judge output exposes immersive-reality classifications,
- continuous evaluator separates production failure from simulator failure,
- focused DeepSeek pilot shows fewer misleading concrete reality claims,
- persona difference is not flattened,
- `round2-multidimensional-diagnosis.md` remains the authoritative diagnosis.

## Execution Recommendation

Use inline execution for Task 1-6 because the edits are tightly coupled and small. Use a separate checkpoint before Task 7 because live DeepSeek testing costs time and external API calls.
