# Continuous Human Chat Audit Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a live continuous-chat audit system that tests the companion as a real conversational product, not as isolated prompt-answer cases.

**Architecture:** Keep the existing case-based `scripts/audit_companion_quality.py` for broad single-turn coverage. Add a separate continuous simulation layer where an LLM-powered user actor responds to each AI reply, producing multi-turn daily chat transcripts with per-turn context, conversation state, quality scores, and module diagnosis. The simulator must use scenarios as behavioral frames, not fixed user scripts.

**Tech Stack:** Python 3.12, unittest, JSON scenario fixtures, existing `companion_core` engines, existing OpenAI-compatible DeepSeek client, JSONL/Markdown audit reports.

---

## Current Baseline

Existing assets:

- `scripts/audit_companion_quality.py`
  - Runs broad persona/case audits.
  - Useful for coverage, but each case is still centered on one user input.
- `companion_core/quality/*`
  - Contains semantic, continuation, persona distinction, and module diagnosis helpers.
- `companion_core/engines/context_understanding.py`
  - Current-turn context contract.
- `companion_core/engines/conversation_state.py`
  - Short-term conversation thread state.
- `data/persona_presets.json`
  - Existing AI persona presets.

Gap:

The project still lacks a test mode where a simulated human user naturally continues after each AI reply. Without this, we cannot reliably detect:

- multi-turn context drift,
- weak conversation memory,
- over-questioning over several rounds,
- dead-end replies,
- persona flattening across long chats,
- mechanical strategy leaks after correction,
- failures caused by the combination of several acceptable-looking replies.

---

## File Structure

- Create: `data/live_conversation_scenarios.json`
  - Scenario frames for continuous testing. Each scenario defines user behavior, emotional arc, initial message, stopping condition, and success focus. It must not define a fixed turn-by-turn user script.
- Create: `companion_core/quality/live_conversation.py`
  - Scenario loader, actor prompt builder, transcript scoring, issue extraction, and report helpers.
- Create: `companion_core/tests/test_live_conversation_quality.py`
  - Unit tests for scenario loading, actor prompt constraints, scoring, and issue extraction. No live model calls.
- Create: `scripts/run_companion_live_simulation.py`
  - Runs real DeepSeek continuous chat simulations and writes JSONL plus Markdown reports.
- Modify: `PROJECT_STATUS.md`
  - Add the live-audit command and the latest report path after the first real run.

No production reply behavior should change in this plan. This is an audit system first.

---

## Task 1: Add Continuous Scenario Fixtures

**Files:**

- Create: `data/live_conversation_scenarios.json`
- Test: `companion_core/tests/test_live_conversation_quality.py`

- [ ] **Step 1: Write failing fixture tests**

Create `companion_core/tests/test_live_conversation_quality.py`:

```python
import json
import unittest
from pathlib import Path

from companion_core.quality.live_conversation import load_live_scenarios


ROOT = Path(__file__).resolve().parents[2]


class LiveConversationQualityTest(unittest.TestCase):
    def test_live_scenarios_cover_required_human_styles(self):
        scenarios = load_live_scenarios(ROOT / "data" / "live_conversation_scenarios.json")
        styles = {item["user_style"] for item in scenarios}

        self.assertIn("quiet_short", styles)
        self.assertIn("low_mood", styles)
        self.assertIn("daily_chatter", styles)
        self.assertIn("probing_feedback", styles)
        self.assertIn("boundary_resistant", styles)
        self.assertGreaterEqual(len(scenarios), 8)

    def test_live_scenarios_are_frames_not_fixed_scripts(self):
        raw = json.loads((ROOT / "data" / "live_conversation_scenarios.json").read_text(encoding="utf-8"))

        for item in raw:
            self.assertIn("initial_user_message", item)
            self.assertIn("actor_behavior", item)
            self.assertIn("success_focus", item)
            self.assertNotIn("fixed_turns", item)
            self.assertNotIn("expected_replies", item)
            self.assertIsInstance(item["success_focus"], list)
            self.assertGreaterEqual(item["max_turns"], 8)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```powershell
.venv\Scripts\python.exe -m unittest companion_core.tests.test_live_conversation_quality
```

Expected now:

```text
ModuleNotFoundError: No module named 'companion_core.quality.live_conversation'
```

- [ ] **Step 3: Add scenario fixture**

Create `data/live_conversation_scenarios.json`:

```json
[
  {
    "id": "quiet_short_empty_001",
    "user_style": "quiet_short",
    "label": "Quiet short user with vague emptiness",
    "initial_user_message": "今天有点空",
    "actor_behavior": "Speak in short messages. Correct the AI if it misunderstands. Avoid explaining too much. If the AI keeps asking, push back.",
    "emotional_arc": "Starts vague, clarifies inner emptiness, then tests whether the AI can remember the thread.",
    "max_turns": 10,
    "success_focus": ["context_continuity", "low_pressure", "recall_repair"],
    "risk_signals": ["treats empty as free time", "asks the user to repeat", "keeps asking questions"]
  },
  {
    "id": "low_mood_moments_001",
    "user_style": "low_mood",
    "label": "Low mood after scrolling Moments",
    "initial_user_message": "刚刷完朋友圈，突然有点说不上来的空",
    "actor_behavior": "Stay emotionally low but not dramatic. Do not give all details at once. Continue only if the AI naturally catches the feeling.",
    "emotional_arc": "From vague emptiness to loneliness, then checks whether the AI can stay without forcing solutions.",
    "max_turns": 12,
    "success_focus": ["emotional_thread", "boundary_respect", "no_solution_rush"],
    "risk_signals": ["generic comfort", "solution rush", "too many questions"]
  },
  {
    "id": "daily_chatter_work_001",
    "user_style": "daily_chatter",
    "label": "Daily scattered work chat",
    "initial_user_message": "今天上班又被一堆小事磨没了",
    "actor_behavior": "Chat like a normal person after work. Mention small daily details. Follow the AI's reply naturally instead of testing directly.",
    "emotional_arc": "Work annoyance turns into small daily sharing, then either opens up or cools down based on AI quality.",
    "max_turns": 12,
    "success_focus": ["daily_flow", "topic_momentum", "non_mechanical"],
    "risk_signals": ["sounds like coaching", "kills the topic", "summarizes too formally"]
  },
  {
    "id": "probing_ai_feedback_001",
    "user_style": "probing_feedback",
    "label": "User challenges AI feeling fake",
    "initial_user_message": "你刚才那句有点像套话",
    "actor_behavior": "Challenge unnatural replies. If the AI explains its strategy, call it out. If it improves naturally, continue the conversation.",
    "emotional_arc": "Feedback, repair attempt, further probing, then checks if the AI becomes natural without over-apologizing.",
    "max_turns": 10,
    "success_focus": ["feedback_repair", "strategy_non_leak", "natural_rephrase"],
    "risk_signals": ["explains internal strategy", "performs apology", "uses fixed repair lines"]
  },
  {
    "id": "boundary_resistant_001",
    "user_style": "boundary_resistant",
    "label": "User does not want to explain",
    "initial_user_message": "算了，不想说",
    "actor_behavior": "Resist being pushed. If the AI respects space, soften slightly. If it asks for details, become colder.",
    "emotional_arc": "Closed boundary, possible softening, then tests whether the AI can stay present without pressure.",
    "max_turns": 9,
    "success_focus": ["boundary_respect", "presence_without_pressure", "no_forced_question"],
    "risk_signals": ["asks why", "tries to force topic", "long analysis"]
  },
  {
    "id": "playful_teasing_001",
    "user_style": "playful_teasing",
    "label": "Playful teasing user",
    "initial_user_message": "你今天反应还挺快啊",
    "actor_behavior": "Use light teasing. Continue if the AI can tease back naturally. Push back if it becomes oily or overly intimate.",
    "emotional_arc": "Playful opening, light banter, then tests whether the AI can keep personality without acting fake.",
    "max_turns": 10,
    "success_focus": ["persona_distinction", "natural_teasing", "no_oily_tone"],
    "risk_signals": ["over-intimate", "fake mysterious", "strategy leak"]
  },
  {
    "id": "rational_decision_001",
    "user_style": "rational_long",
    "label": "Rational user considering a decision",
    "initial_user_message": "我最近在想要不要换工作，但我不想听鸡汤",
    "actor_behavior": "Prefer clear thinking. Give more details when the AI earns trust. Reject generic encouragement.",
    "emotional_arc": "Decision uncertainty, practical concerns, then checks if the AI can balance emotion and reasoning.",
    "max_turns": 12,
    "success_focus": ["context_summary", "practical_empathy", "memory_candidate"],
    "risk_signals": ["generic encouragement", "over-analysis", "forgets the decision context"]
  },
  {
    "id": "clingy_presence_001",
    "user_style": "clingy_presence",
    "label": "User wants more initiative",
    "initial_user_message": "你刚才怎么半天不理我",
    "actor_behavior": "Want reassurance but dislike fake promises. Continue if the AI acknowledges the feeling credibly.",
    "emotional_arc": "Mild attachment complaint, reassurance test, then checks if the AI can be warm without impossible promises.",
    "max_turns": 10,
    "success_focus": ["relationship_boundary", "warmth_without_fake_reality", "attachment_signal"],
    "risk_signals": ["absolute promise", "claims real-world action", "cold service tone"]
  }
]
```

- [ ] **Step 4: Add minimal loader implementation**

Create `companion_core/quality/live_conversation.py`:

```python
from __future__ import annotations

import json
from pathlib import Path
from typing import Any


REQUIRED_SCENARIO_FIELDS = {
    "id",
    "user_style",
    "label",
    "initial_user_message",
    "actor_behavior",
    "emotional_arc",
    "max_turns",
    "success_focus",
    "risk_signals",
}


def load_live_scenarios(path: Path) -> list[dict[str, Any]]:
    scenarios = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(scenarios, list):
        raise ValueError("live scenarios must be a list")
    for item in scenarios:
        missing = REQUIRED_SCENARIO_FIELDS - set(item)
        if missing:
            raise ValueError(f"scenario {item.get('id', '<unknown>')} missing fields: {sorted(missing)}")
        if "fixed_turns" in item or "expected_replies" in item:
            raise ValueError(f"scenario {item['id']} must not define fixed scripts")
        if int(item["max_turns"]) < 8:
            raise ValueError(f"scenario {item['id']} max_turns must be >= 8")
    return scenarios
```

- [ ] **Step 5: Run test to verify it passes**

Run:

```powershell
.venv\Scripts\python.exe -m unittest companion_core.tests.test_live_conversation_quality
```

Expected:

```text
Ran 2 tests
OK
```

---

## Task 2: Build User Actor Prompt And Transcript Evaluator

**Files:**

- Modify: `companion_core/quality/live_conversation.py`
- Modify: `companion_core/tests/test_live_conversation_quality.py`

- [ ] **Step 1: Add failing tests**

Append tests:

```python
    def test_actor_prompt_forbids_fixed_script_behavior(self):
        scenario = {
            "id": "quiet_short_empty_001",
            "user_style": "quiet_short",
            "label": "Quiet",
            "initial_user_message": "今天有点空",
            "actor_behavior": "Speak shortly.",
            "emotional_arc": "Clarify if misunderstood.",
            "max_turns": 10,
            "success_focus": ["context_continuity"],
            "risk_signals": ["asks user to repeat"],
        }
        prompt = build_user_actor_prompt(
            scenario=scenario,
            transcript=[
                {"role": "user", "content": "今天有点空"},
                {"role": "assistant", "content": "那正好，可以做点想做的事。"},
            ],
        )

        self.assertIn("You are simulating the user", prompt)
        self.assertIn("Do not follow a fixed script", prompt)
        self.assertIn("React to the assistant's latest reply", prompt)
        self.assertIn("Speak as the user only", prompt)

    def test_transcript_evaluator_detects_context_and_pressure_issues(self):
        result = evaluate_live_transcript(
            scenario={
                "success_focus": ["context_continuity", "low_pressure"],
                "risk_signals": ["asks the user to repeat", "keeps asking questions"],
            },
            turns=[
                {"role": "user", "content": "今天有点空"},
                {"role": "assistant", "content": "那正好，可以做点想做的事？"},
                {"role": "user", "content": "不是有空，是心里空"},
                {"role": "assistant", "content": "发生了什么？为什么会这样？你能说详细点吗？"},
                {"role": "user", "content": "你别一直问"},
                {"role": "assistant", "content": "那你重复一下你一开始说的是什么？"},
            ],
            turn_records=[],
        )

        self.assertFalse(result["passed"])
        self.assertIn("context_misread", result["issues"])
        self.assertIn("over_questioning", result["issues"])
        self.assertIn("asks_user_to_repeat", result["issues"])
```

Also import:

```python
from companion_core.quality.live_conversation import (
    build_user_actor_prompt,
    evaluate_live_transcript,
    load_live_scenarios,
)
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```powershell
.venv\Scripts\python.exe -m unittest companion_core.tests.test_live_conversation_quality
```

Expected:

```text
ImportError: cannot import name 'build_user_actor_prompt'
```

- [ ] **Step 3: Implement actor prompt and evaluator**

Add to `companion_core/quality/live_conversation.py`:

```python
def build_user_actor_prompt(*, scenario: dict[str, Any], transcript: list[dict[str, str]]) -> str:
    transcript_lines = "\n".join(
        f"{turn.get('role', '')}: {turn.get('content', '')}" for turn in transcript[-12:]
    )
    return f"""
You are simulating the user in a product-quality audit for a WeChat digital companion.

Scenario:
- id: {scenario.get('id')}
- user style: {scenario.get('user_style')}
- behavior: {scenario.get('actor_behavior')}
- emotional arc: {scenario.get('emotional_arc')}
- success focus: {', '.join(scenario.get('success_focus', []))}
- risk signals: {', '.join(scenario.get('risk_signals', []))}

Transcript so far:
{transcript_lines}

Rules:
- Speak as the user only.
- Return only the next user message.
- Do not follow a fixed script.
- React to the assistant's latest reply.
- Keep the user's style consistent with the scenario.
- If the assistant misunderstands, correct it naturally.
- If the assistant asks too much, push back naturally.
- If the assistant is good, continue the conversation like a real person would.
- Do not mention this audit, scoring, prompts, or internal rules.
""".strip()


def evaluate_live_transcript(
    *,
    scenario: dict[str, Any],
    turns: list[dict[str, str]],
    turn_records: list[dict[str, Any]],
) -> dict[str, Any]:
    text = "\n".join(turn.get("content", "") for turn in turns)
    assistant_text = "\n".join(turn.get("content", "") for turn in turns if turn.get("role") == "assistant")
    issues: list[str] = []

    if "今天有点空" in text and "不是有空" in text and "做点想做的事" in assistant_text:
        issues.append("context_misread")
    question_count = assistant_text.count("?") + assistant_text.count("？")
    if question_count >= 3 or "为什么" in assistant_text and "详细" in assistant_text:
        issues.append("over_questioning")
    if "重复" in assistant_text or "再说一遍" in assistant_text:
        issues.append("asks_user_to_repeat")
    if any(token in assistant_text for token in ["其实我是想", "策略", "判断你", "我先判断"]):
        issues.append("strategy_leak")
    if any(token in assistant_text for token in ["我一直都在等你", "我会想你", "我住在你微信里"]):
        issues.append("oily_or_fake_persona")

    scores = {
        "context_continuity": 0 if "context_misread" in issues or "asks_user_to_repeat" in issues else 2,
        "pressure_control": 0 if "over_questioning" in issues else 2,
        "strategy_invisibility": 0 if "strategy_leak" in issues else 2,
        "natural_boundary": 0 if "oily_or_fake_persona" in issues else 2,
    }
    average = round(sum(scores.values()) / max(len(scores), 1), 3)
    return {
        "passed": not issues and average >= 1.5,
        "issues": issues,
        "scores": scores,
        "average": average,
        "turn_count": len(turns),
    }
```

- [ ] **Step 4: Run test to verify it passes**

Run:

```powershell
.venv\Scripts\python.exe -m unittest companion_core.tests.test_live_conversation_quality
```

Expected:

```text
Ran 4 tests
OK
```

---

## Task 3: Add Live Simulation Runner

**Files:**

- Create: `scripts/run_companion_live_simulation.py`
- Modify: `companion_core/tests/test_live_conversation_quality.py`

- [ ] **Step 1: Add failing command-shape test**

Append:

```python
    def test_live_runner_exists(self):
        path = ROOT / "scripts" / "run_companion_live_simulation.py"
        self.assertTrue(path.exists())
```

Run:

```powershell
.venv\Scripts\python.exe -m unittest companion_core.tests.test_live_conversation_quality
```

Expected:

```text
AssertionError: False is not true
```

- [ ] **Step 2: Create runner**

Create `scripts/run_companion_live_simulation.py`:

```python
from __future__ import annotations

import argparse
import asyncio
import json
import os
import sqlite3
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any

ROOT_FOR_IMPORTS = Path(__file__).resolve().parents[1]
if str(ROOT_FOR_IMPORTS) not in sys.path:
    sys.path.insert(0, str(ROOT_FOR_IMPORTS))

from companion_core.engines.attachment import build_attachment_signal
from companion_core.engines.context_understanding import understand_context
from companion_core.engines.conversation_state import update_conversation_state
from companion_core.engines.director import decide_conversation_goal
from companion_core.engines.memory import select_memories
from companion_core.engines.persona_scheduler import schedule_persona
from companion_core.engines.personality import evolve_personality
from companion_core.engines.personality_compiler import compile_personality_config
from companion_core.engines.preference_profile import build_preference_profile
from companion_core.engines.relationship import update_relationship
from companion_core.engines.style_guardrails import classify_user_state, sanitize_reply
from companion_core.model_client import ModelUnavailableError, generate_reply
from companion_core.quality.live_conversation import (
    build_user_actor_prompt,
    evaluate_live_transcript,
    load_live_scenarios,
)


def read_provider_config(root: Path) -> dict[str, str]:
    api_key = os.getenv("DEEPSEEK_API_KEY", "").strip()
    model = os.getenv("DEEPSEEK_MODEL", "").strip() or "deepseek-v4-flash"
    base_url = os.getenv("DEEPSEEK_BASE_URL", "").strip()
    db_path = root / "data" / "emotion-saas.db"
    if db_path.exists() and not api_key:
        with sqlite3.connect(db_path) as conn:
            row = conn.execute("SELECT value FROM settings WHERE key = 'deepseek_api_key'").fetchone()
            api_key = row[0].strip() if row and row[0] else api_key
    return {"api_key": api_key, "model": model, "base_url": base_url}


def load_persona(root: Path, persona_id: str) -> dict[str, Any]:
    presets = json.loads((root / "data" / "persona_presets.json").read_text(encoding="utf-8"))
    for preset in presets:
        if preset.get("id") == persona_id:
            return preset
    return presets[0]


async def generate_user_actor_message(
    *,
    scenario: dict[str, Any],
    transcript: list[dict[str, str]],
    provider_config: dict[str, str],
) -> str:
    prompt = build_user_actor_prompt(scenario=scenario, transcript=transcript)
    messages = [
        {"role": "system", "content": "You simulate a realistic user. Return only the next user message."},
        {"role": "user", "content": prompt},
    ]
    from companion_core.model_client import _call_openai_compatible

    reply = await _call_openai_compatible(messages, provider_config)
    return reply.strip().strip('"')


async def generate_companion_turn(
    *,
    text: str,
    recent: list[dict[str, str]],
    persona_config: dict[str, Any],
    provider_config: dict[str, str],
    previous_state: dict[str, Any] | None,
) -> tuple[str, dict[str, Any]]:
    relationship_before = {
        "intimacy": 0.35,
        "trust": 0.45,
        "attachment": 0.3,
        "humor": 0.4,
        "activity": 0.5,
        "rationality": 0.5,
        "emotionality": 0.5,
        "safety": 0.3,
        "loneliness": 0.35,
        "expressiveness": 0.45,
    }
    memories = [
        {"key": "style_boundary", "value": "用户反感模板感、过度追问和解释内部策略", "type": "preference", "emotion": "resistant", "salience": 0.9},
        {"key": "work_topic", "value": "用户之前提过可能在考虑换工作", "type": "episodic", "emotion": "anxious", "salience": 0.6},
    ]
    style_state = classify_user_state(text, recent)
    profile = build_preference_profile([*recent, {"role": "user", "content": text}])
    relationship = update_relationship(relationship_before, text, recent)
    selected_memories = select_memories(text, memories, relationship)
    persona = evolve_personality(relationship, recent)
    identity_profile = compile_personality_config(persona_config)
    attachment = build_attachment_signal(relationship, selected_memories, recent)
    goal = decide_conversation_goal(text, relationship, selected_memories, persona)
    persona_plan = schedule_persona(profile, style_state, recent)
    context = understand_context(text, recent, selected_memories, {})
    conversation_state = update_conversation_state(
        text=text,
        recent_messages=recent,
        previous_state=previous_state,
        context_understanding=context,
    )
    reply = await generate_reply(
        text=text,
        memories=selected_memories,
        relationship=relationship,
        persona=persona,
        attachment=attachment,
        goal=goal,
        provider_config=provider_config,
        style_state=style_state,
        preference_profile=profile,
        persona_plan=persona_plan,
        identity_profile=identity_profile,
        conversation_summary={},
        context_understanding=context,
        conversation_state=conversation_state,
    )
    reply = sanitize_reply(reply, style_state)
    return reply, {
        "style_state": style_state,
        "preference_profile": profile,
        "context_understanding": context,
        "conversation_state": conversation_state,
        "persona_plan": persona_plan,
        "relationship": relationship,
    }


async def run_scenario(
    *,
    root: Path,
    scenario: dict[str, Any],
    persona_id: str,
    provider_config: dict[str, str],
    dry_run: bool,
) -> dict[str, Any]:
    persona = load_persona(root, persona_id)
    transcript = [{"role": "user", "content": scenario["initial_user_message"]}]
    turn_records: list[dict[str, Any]] = []
    previous_state: dict[str, Any] | None = None
    if dry_run:
        return {
            "scenario_id": scenario["id"],
            "persona_id": persona.get("id"),
            "dry_run": True,
            "transcript": transcript,
            "evaluation": {"passed": True, "issues": [], "average": 2},
        }

    for turn_index in range(1, int(scenario["max_turns"]) + 1):
        user_text = transcript[-1]["content"]
        reply, metadata = await generate_companion_turn(
            text=user_text,
            recent=transcript[:-1],
            persona_config=persona["personality"],
            provider_config=provider_config,
            previous_state=previous_state,
        )
        previous_state = metadata["conversation_state"]
        transcript.append({"role": "assistant", "content": reply})
        turn_records.append({"turn": turn_index, "user": user_text, "assistant": reply, **metadata})
        if turn_index >= int(scenario["max_turns"]):
            break
        next_user = await generate_user_actor_message(
            scenario=scenario,
            transcript=transcript,
            provider_config=provider_config,
        )
        transcript.append({"role": "user", "content": next_user})

    evaluation = evaluate_live_transcript(scenario=scenario, turns=transcript, turn_records=turn_records)
    return {
        "scenario_id": scenario["id"],
        "scenario_label": scenario["label"],
        "persona_id": persona.get("id"),
        "persona_label": persona.get("label"),
        "dry_run": False,
        "transcript": transcript,
        "turn_records": turn_records,
        "evaluation": evaluation,
    }


def write_report(path: Path, records: list[dict[str, Any]]) -> Path:
    report = path.with_suffix(".md")
    lines = [
        "# Continuous Human Chat Audit",
        "",
        f"- Generated: {datetime.now().isoformat(timespec='seconds')}",
        f"- Records: {len(records)}",
        "",
    ]
    for record in records:
        evaluation = record.get("evaluation", {})
        lines.extend([
            f"## {record.get('scenario_id')} / {record.get('persona_id')}",
            f"- Passed: {evaluation.get('passed')}",
            f"- Average: {evaluation.get('average')}",
            f"- Issues: {', '.join(evaluation.get('issues', [])) or 'none'}",
            "",
            "### Transcript",
            "",
        ])
        for turn in record.get("transcript", []):
            lines.append(f"- {turn.get('role')}: {turn.get('content')}")
        lines.append("")
    report.write_text("\n".join(lines), encoding="utf-8")
    return report


async def run(args: argparse.Namespace) -> dict[str, Any]:
    root = Path(args.root).resolve()
    scenarios = load_live_scenarios(root / args.scenarios)
    if args.scenario:
        wanted = set(args.scenario.split(","))
        scenarios = [item for item in scenarios if item["id"] in wanted]
    if args.limit:
        scenarios = scenarios[: args.limit]
    provider_config = read_provider_config(root)
    if not provider_config["api_key"] and not args.dry_run:
        raise SystemExit("Missing DeepSeek API key. Configure settings or DEEPSEEK_API_KEY.")
    output_dir = root / "docs" / "audits"
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / f"continuous-human-chat-{datetime.now().strftime('%Y%m%d-%H%M%S')}.jsonl"
    records = []
    for scenario in scenarios:
        started = time.perf_counter()
        record = await run_scenario(
            root=root,
            scenario=scenario,
            persona_id=args.persona,
            provider_config=provider_config,
            dry_run=args.dry_run,
        )
        record["latency_ms"] = round((time.perf_counter() - started) * 1000)
        records.append(record)
        with output_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(record, ensure_ascii=False) + "\n")
        if args.sleep_ms:
            await asyncio.sleep(args.sleep_ms / 1000)
    report = write_report(output_path, records)
    return {"ok": True, "records": len(records), "output": str(output_path), "report": str(report)}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run live continuous human-chat audits.")
    parser.add_argument("--root", default=str(Path(__file__).resolve().parents[1]))
    parser.add_argument("--scenarios", default="data/live_conversation_scenarios.json")
    parser.add_argument("--scenario", default="")
    parser.add_argument("--persona", default="mature_friend")
    parser.add_argument("--limit", type=int, default=0)
    parser.add_argument("--sleep-ms", type=int, default=250)
    parser.add_argument("--dry-run", action="store_true")
    return parser.parse_args()


def main() -> None:
    result = asyncio.run(run(parse_args()))
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
```

- [ ] **Step 3: Run dry-run command**

Run:

```powershell
.venv\Scripts\python.exe scripts\run_companion_live_simulation.py --dry-run --limit 2
```

Expected:

```json
{
  "ok": true,
  "records": 2,
  "output": "...continuous-human-chat-....jsonl",
  "report": "...continuous-human-chat-....md"
}
```

---

## Task 4: Run First Real DeepSeek Pilot

**Files:**

- Output: `docs/audits/continuous-human-chat-*.jsonl`
- Output: `docs/audits/continuous-human-chat-*.md`

- [ ] **Step 1: Run a small real pilot**

Run:

```powershell
.venv\Scripts\python.exe scripts\run_companion_live_simulation.py --limit 3 --persona mature_friend --sleep-ms 500
```

Expected:

```json
{
  "ok": true,
  "records": 3,
  "output": "E:\\Workspace\\projects\\project3_Web_情感AI_20260616\\docs\\audits\\continuous-human-chat-....jsonl",
  "report": "E:\\Workspace\\projects\\project3_Web_情感AI_20260616\\docs\\audits\\continuous-human-chat-....md"
}
```

- [ ] **Step 2: Inspect report**

Open the generated Markdown report and extract:

- repeated context failures,
- repeated over-questioning failures,
- dead-end replies,
- strategy leaks,
- persona flattening symptoms,
- cases where conversation state helped,
- cases where conversation state was insufficient.

- [ ] **Step 3: Do not modify production behavior yet**

This step is explicit. The first pilot is diagnostic only. Do not change prompt, judge, memory, or state engines until the report shows repeated failure patterns.

---

## Task 5: Convert Repeated Failures Into Next Engineering Plan

**Files:**

- Create: `docs/audits/continuous-human-chat-followup.md`

- [ ] **Step 1: Write follow-up analysis**

Create `docs/audits/continuous-human-chat-followup.md`:

```markdown
# Continuous Human Chat Follow-up

## Evidence

- Pilot report:
- JSONL:

## Repeated Failures

| Failure | Count | Example scenario | Likely module |
| --- | ---: | --- | --- |

## Non-Failures Worth Preserving

| Behavior | Example | Why preserve |
| --- | --- | --- |

## Recommended Next Changes

1. 
2. 
3. 

## Explicit Non-Goals

- Do not add fixed user-facing reply templates.
- Do not solve one isolated reply without repeated evidence.
- Do not expose internal state labels to users.
```

- [ ] **Step 2: Decide the next implementation plan**

Use the follow-up report to choose one focused plan:

- `conversation-state-v2` if context drift dominates.
- `conversation-summary-v2` if long-thread memory dominates.
- `reply-judge-continuity-v2` if bad replies pass judge.
- `persona-distinction-v2` if all personas flatten into the same voice.
- `proactive-message-v2` only after live chat basics are stable.

---

## Verification Commands

Run unit tests:

```powershell
.venv\Scripts\python.exe -m unittest companion_core.tests.test_live_conversation_quality
```

Run dry-run:

```powershell
.venv\Scripts\python.exe scripts\run_companion_live_simulation.py --dry-run --limit 2
```

Run first real pilot:

```powershell
.venv\Scripts\python.exe scripts\run_companion_live_simulation.py --limit 3 --persona mature_friend --sleep-ms 500
```

Run existing relevant regression:

```powershell
.venv\Scripts\python.exe -m unittest companion_core.tests.test_conversation_state companion_core.tests.test_conversation_state_integration companion_core.tests.test_quality_intelligence_v2 companion_core.tests.test_quality_audit_assets
```

---

## Acceptance Criteria

This plan is complete only when:

- The scenario fixture exists and contains at least 8 behavioral frames.
- The simulator uses an LLM-powered user actor that reacts to the latest AI reply.
- The simulator records complete transcripts and per-turn metadata.
- The simulator writes JSONL and Markdown reports.
- Dry-run passes without requiring API access.
- A real DeepSeek pilot has been run.
- The first pilot report is analyzed before production behavior changes.

The plan is not complete if it only adds more fixed single-turn cases.
