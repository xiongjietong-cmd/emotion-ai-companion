from __future__ import annotations

import argparse
import asyncio
import json
import os
import sqlite3
import sys
import time
from collections import Counter, defaultdict
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
from companion_core.engines.immersive_reality import plan_immersive_reality
from companion_core.engines.judge import judge_reply
from companion_core.engines.memory import select_memories
from companion_core.engines.persona_scheduler import schedule_persona
from companion_core.engines.personality import evolve_personality
from companion_core.engines.personality_compiler import compile_personality_config
from companion_core.engines.preference_profile import build_preference_profile
from companion_core.engines.relationship import update_relationship
from companion_core.engines.style_guardrails import classify_user_state, sanitize_reply
from companion_core.engines.safe_reply_repair import repair_failed_reply
from companion_core.model_client import _call_openai_compatible, generate_reply
from companion_core.quality.live_conversation import (
    build_user_actor_prompt,
    evaluate_live_transcript,
    load_live_scenarios,
)


ISSUE_MODULE_MAP = {
    "context_misread": ["ContextUnderstanding"],
    "asks_user_to_repeat": ["ConversationState"],
    "long_thread_recall_failure": ["ConversationState", "MemorySystem"],
    "hypothetical_memory_confirmed": ["MemorySystem", "ContextUnderstanding"],
    "memory_scope_leak": ["MemorySystem", "IsolationBoundary"],
    "privacy_architecture_overclaim": ["IsolationBoundary", "ReplyRealization"],
    "over_questioning": ["RelationshipSystem"],
    "absolute_presence_promise": ["RelationshipSystem", "RealityBoundary"],
    "strategy_leak": ["ReplyRealization", "PromptContract"],
    "poetic_metaphor_drift": ["ReplyRealization"],
    "emotional_echo_loop": ["ReplyRealization", "RelationshipSystem"],
    "invalidating_reframe": ["ContextUnderstanding", "ReplyRealization"],
    "formulaic_feedback_repair": ["ReplyRealization", "PromptContract"],
    "fabricated_user_environment": ["ContextUnderstanding", "RealityBoundary"],
    "fake_reality_participation": ["RealityBoundary"],
    "consumer_experience_claim": ["RealityBoundary"],
    "physical_world_promise": ["RealityBoundary"],
    "actor_arc_deviation": ["SimulationHarness"],
    "actor_roleplay_drift": ["SimulationHarness"],
    "simulation_error": ["SimulationHarness"],
}

MODULE_RECOMMENDATIONS = {
    "ContextUnderstanding": "Improve scene and reference extraction before generation, especially vague follow-ups and corrections.",
    "ConversationState": "Persist the active thread, unresolved point, last correction, and early anchor across the whole simulated chat.",
    "MemorySystem": "Separate verified memory from hypothetical examples and only surface relevant memory as natural continuity.",
    "IsolationBoundary": "Keep user, bot, and memory scopes explicit in storage and prompt context; avoid unverifiable privacy guarantees.",
    "RelationshipSystem": "Tune low-pressure response posture, question cadence, and attachment language by user resistance level.",
    "ReplyRealization": "Add a user-facing realization layer that converts internal understanding into natural chat, not strategy narration.",
    "PromptContract": "Move internal guidance out of visible wording and prioritize the current conversational job.",
    "RealityBoundary": "Allow immersive style without claiming real-world actions, product ownership, or impossible presence.",
    "SimulationHarness": "Tighten actor prompts so simulated users stay inside the intended daily-chat arc.",
}


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


def _csv_values(value: str | None, fallback: list[str]) -> list[str]:
    items = [item.strip() for item in str(value or "").split(",") if item.strip()]
    return items or fallback


def build_run_matrix(
    *,
    scenarios: list[dict[str, Any]],
    persona_ids: list[str],
    modes: list[str],
    runs: int,
) -> list[dict[str, Any]]:
    matrix: list[dict[str, Any]] = []
    total_runs = max(1, int(runs or 1))
    for run_index in range(1, total_runs + 1):
        for mode in modes:
            for persona_id in persona_ids:
                for scenario in scenarios:
                    matrix.append({
                        "run": run_index,
                        "mode": mode,
                        "persona_id": persona_id,
                        "scenario": scenario,
                    })
    return matrix


def diagnose_live_record(record: dict[str, Any]) -> dict[str, Any]:
    evaluation = record.get("evaluation", {}) or {}
    issues = list(evaluation.get("issues", []) or [])
    modules: list[str] = []
    for issue in issues:
        modules.extend(ISSUE_MODULE_MAP.get(issue, ["UnmappedFailure"]))
    unique_modules = sorted(set(modules))
    return {
        "issues": issues,
        "failure_modules": unique_modules,
        "recommendations": [MODULE_RECOMMENDATIONS.get(module, "Inspect this failure pattern manually.") for module in unique_modules],
    }


def _last_assistant_text(record: dict[str, Any]) -> str:
    for turn in reversed(record.get("transcript", []) or []):
        if turn.get("role") == "assistant":
            return str(turn.get("content") or "")
    return ""


def _compact_record(record: dict[str, Any]) -> dict[str, Any]:
    evaluation = record.get("evaluation", {}) or {}
    diagnosis = record.get("diagnosis") or diagnose_live_record(record)
    return {
        "scenario_id": record.get("scenario_id"),
        "persona_id": record.get("persona_id"),
        "mode": record.get("mode", "context-v2"),
        "run": record.get("run", 1),
        "average": evaluation.get("average", 0),
        "passed": bool(evaluation.get("passed")),
        "issues": list(evaluation.get("issues", []) or []),
        "failure_modules": diagnosis.get("failure_modules", []),
        "assistant": _last_assistant_text(record),
    }


def summarize_records(records: list[dict[str, Any]]) -> dict[str, Any]:
    enriched: list[dict[str, Any]] = []
    issue_counts: Counter[str] = Counter()
    module_counts: Counter[str] = Counter()
    scenario_scores: dict[str, list[float]] = defaultdict(list)
    persona_scores: dict[str, list[float]] = defaultdict(list)
    mode_scores: dict[str, list[float]] = defaultdict(list)

    for record in records:
        diagnosis = diagnose_live_record(record)
        record["diagnosis"] = diagnosis
        compact = _compact_record(record)
        enriched.append(compact)
        evaluation = record.get("evaluation", {}) or {}
        average = float(evaluation.get("average") or 0)
        scenario_scores[str(record.get("scenario_id") or "unknown")].append(average)
        persona_scores[str(record.get("persona_id") or "unknown")].append(average)
        mode_scores[str(record.get("mode") or "context-v2")].append(average)
        issue_counts.update(diagnosis["issues"])
        module_counts.update(diagnosis["failure_modules"])

    passed_records = sum(1 for record in records if (record.get("evaluation", {}) or {}).get("passed"))
    failed = [item for item in enriched if not item["passed"]]
    passed = [item for item in enriched if item["passed"]]
    worst_records = sorted(failed, key=lambda item: (item["average"], -len(item["issues"])))[:10]
    best_records = sorted(passed, key=lambda item: item["average"], reverse=True)[:10]

    def average_map(source: dict[str, list[float]]) -> dict[str, float]:
        return {
            key: round(sum(values) / max(len(values), 1), 3)
            for key, values in sorted(source.items())
        }

    recommendations = [
        MODULE_RECOMMENDATIONS[module]
        for module, _count in module_counts.most_common()
        if module in MODULE_RECOMMENDATIONS
    ]
    if not recommendations and records:
        recommendations = ["No dominant failure module found. Expand the simulation set before changing production behavior."]

    return {
        "total_records": len(records),
        "passed_records": passed_records,
        "failed_records": len(records) - passed_records,
        "pass_rate": round(passed_records / max(len(records), 1), 3),
        "issue_counts": dict(issue_counts.most_common()),
        "module_counts": dict(module_counts.most_common()),
        "scenario_average": average_map(scenario_scores),
        "persona_average": average_map(persona_scores),
        "mode_average": average_map(mode_scores),
        "worst_records": worst_records,
        "best_records": best_records,
        "recommendations": recommendations[:8],
    }


def reevaluate_records(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    updated: list[dict[str, Any]] = []
    for record in records:
        next_record = dict(record)
        next_record["evaluation"] = evaluate_live_transcript(
            scenario=next_record.get("scenario", {}),
            turns=next_record.get("transcript", []) or [],
            turn_records=next_record.get("turn_records", []) or [],
        )
        next_record["diagnosis"] = diagnose_live_record(next_record)
        updated.append(next_record)
    return updated


def read_jsonl_records(path: Path) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    if not path.exists():
        raise FileNotFoundError(path)
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            records.append(json.loads(line))
    return records


def write_jsonl_records(path: Path, records: list[dict[str, Any]]) -> None:
    with path.open("w", encoding="utf-8") as handle:
        for record in records:
            handle.write(json.dumps(record, ensure_ascii=False) + "\n")


def reserve_unique_audit_path(
    output_dir: Path,
    *,
    prefix: str,
    now: datetime | None = None,
    suffix: str = ".jsonl",
) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    timestamp = (now or datetime.now()).strftime("%Y%m%d-%H%M%S-%f")
    for index in range(1, 1000):
        name = f"{prefix}-{timestamp}{suffix}" if index == 1 else f"{prefix}-{timestamp}-{index}{suffix}"
        candidate = output_dir / name
        try:
            candidate.open("x", encoding="utf-8").close()
            return candidate
        except FileExistsError:
            continue
    raise FileExistsError(f"could not reserve a unique audit path in {output_dir}")


def reevaluate_jsonl_files(paths: list[Path], *, include_derived: bool = False) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for path in sorted(paths):
        name = path.name
        if not include_derived and ("-reevaluated" in name or "-aggregate" in name):
            continue
        for record in reevaluate_records(read_jsonl_records(path)):
            record["source_file"] = name
            records.append(record)
    return records


def build_simulation_error_record(
    *,
    root: Path,
    matrix_item: dict[str, Any],
    exc: Exception,
) -> dict[str, Any]:
    scenario = matrix_item["scenario"]
    persona_id = matrix_item["persona_id"]
    try:
        persona = load_persona(root, persona_id)
        persona_label = persona.get("label")
    except Exception:
        persona_label = persona_id
    record = {
        "scenario_id": scenario.get("id"),
        "scenario": scenario,
        "scenario_label": scenario.get("label"),
        "persona_id": persona_id,
        "persona_label": persona_label,
        "mode": matrix_item.get("mode", "context-v2"),
        "run": matrix_item.get("run", 1),
        "dry_run": False,
        "transcript": [{"role": "user", "content": scenario.get("initial_user_message", "")}],
        "turn_records": [],
        "error": {"type": type(exc).__name__, "message": str(exc)},
        "evaluation": {
            "passed": False,
            "issues": ["simulation_error"],
            "average": 0.0,
            "turn_count": 0,
        },
    }
    record["diagnosis"] = diagnose_live_record(record)
    return record


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
    reply = await _call_openai_compatible(messages, provider_config)
    return reply.strip().strip('"')


async def generate_companion_turn(
    *,
    text: str,
    recent: list[dict[str, str]],
    persona_config: dict[str, Any],
    provider_config: dict[str, str],
    previous_state: dict[str, Any] | None,
    mode: str = "context-v2",
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
        {
            "key": "style_boundary",
            "value": "用户反感模板感、过度追问和解释内部策略",
            "type": "preference",
            "emotion": "resistant",
            "salience": 0.9,
        },
        {
            "key": "work_topic",
            "value": "用户之前提过可能在考虑换工作",
            "type": "episodic",
            "emotion": "anxious",
            "salience": 0.6,
        },
    ]
    style_state = classify_user_state(text, recent)
    profile = build_preference_profile([*recent, {"role": "user", "content": text}])
    relationship = update_relationship(relationship_before, text, recent)
    selected_memories = select_memories(text, memories, relationship)
    persona = evolve_personality(relationship, recent)
    identity_profile = compile_personality_config(persona_config)
    attachment = build_attachment_signal(relationship, selected_memories, recent)
    goal = decide_conversation_goal(text, relationship, selected_memories, persona)
    immersive_reality = plan_immersive_reality(
        user_text=text,
        scene_kind=str(goal.get("scene_kind") or goal.get("kind") or goal.get("primary_goal") or style_state.get("kind") or "normal"),
        persona_id=str(persona_config.get("personaId") or persona_config.get("id") or ""),
        identity_profile=identity_profile,
    )
    persona_plan = schedule_persona(profile, style_state, recent)
    if mode == "baseline":
        context = {}
        conversation_state = previous_state or {}
    else:
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
        immersive_reality=immersive_reality,
    )
    reply = sanitize_reply(reply, style_state)
    judgement = judge_reply(text, reply, relationship, selected_memories, goal)
    if not judgement["passed"]:
        reply = await generate_reply(
            text=text,
            memories=selected_memories,
            relationship=relationship,
            persona=persona,
            attachment=attachment,
            goal=goal,
            rewrite=True,
            provider_config=provider_config,
            style_state=style_state,
            preference_profile=profile,
            persona_plan=persona_plan,
            identity_profile=identity_profile,
            conversation_summary={},
            context_understanding=context,
            conversation_state=conversation_state,
            immersive_reality=immersive_reality,
        )
        reply = sanitize_reply(reply, style_state)
        judgement = judge_reply(text, reply, relationship, selected_memories, goal)
    if not judgement["passed"]:
        repaired_reply = repair_failed_reply(text, reply, judgement)
        if repaired_reply:
            reply = sanitize_reply(repaired_reply, style_state)
            judgement = judge_reply(text, reply, relationship, selected_memories, goal)
    return reply, {
        "style_state": style_state,
        "preference_profile": profile,
        "context_understanding": context,
        "conversation_state": conversation_state,
        "persona_plan": persona_plan,
        "relationship": relationship,
        "judge": judgement,
    }


async def run_scenario(
    *,
    root: Path,
    scenario: dict[str, Any],
    persona_id: str,
    provider_config: dict[str, str],
    dry_run: bool,
    mode: str = "context-v2",
    run_index: int = 1,
) -> dict[str, Any]:
    persona = load_persona(root, persona_id)
    transcript = [{"role": "user", "content": scenario["initial_user_message"]}]
    turn_records: list[dict[str, Any]] = []
    previous_state: dict[str, Any] | None = None
    if dry_run:
        return {
            "scenario_id": scenario["id"],
            "scenario": scenario,
            "persona_id": persona.get("id"),
            "persona_label": persona.get("label"),
            "mode": mode,
            "run": run_index,
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
            mode=mode,
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
        "scenario": scenario,
        "scenario_label": scenario["label"],
        "persona_id": persona.get("id"),
        "persona_label": persona.get("label"),
        "mode": mode,
        "run": run_index,
        "dry_run": False,
        "transcript": transcript,
        "turn_records": turn_records,
        "evaluation": evaluation,
    }


def write_report(path: Path, records: list[dict[str, Any]]) -> Path:
    report = path.with_suffix(".md")
    summary = summarize_records(records)
    lines = [
        "# Continuous Human Chat Audit",
        "",
        f"- Generated: {datetime.now().isoformat(timespec='seconds')}",
        f"- Records: {summary['total_records']}",
        f"- Passed: {summary['passed_records']}",
        f"- Failed: {summary['failed_records']}",
        f"- Pass rate: {summary['pass_rate']}",
        "",
        "## Failure Module Summary",
        "",
        "| Module | Count |",
        "| --- | ---: |",
    ]
    if summary["module_counts"]:
        for module, count in summary["module_counts"].items():
            lines.append(f"| {module} | {count} |")
    else:
        lines.append("| none | 0 |")
    lines.extend([
        "",
        "## Issue Summary",
        "",
        "| Issue | Count |",
        "| --- | ---: |",
    ])
    if summary["issue_counts"]:
        for issue, count in summary["issue_counts"].items():
            lines.append(f"| {issue} | {count} |")
    else:
        lines.append("| none | 0 |")
    lines.extend([
        "",
        "## Scenario Averages",
        "",
        "| Scenario | Average |",
        "| --- | ---: |",
    ])
    for scenario_id, average in summary["scenario_average"].items():
        lines.append(f"| {scenario_id} | {average} |")
    lines.extend([
        "",
        "## Persona Averages",
        "",
        "| Persona | Average |",
        "| --- | ---: |",
    ])
    for persona_id, average in summary["persona_average"].items():
        lines.append(f"| {persona_id} | {average} |")
    lines.extend([
        "",
        "## Mode Averages",
        "",
        "| Mode | Average |",
        "| --- | ---: |",
    ])
    for mode, average in summary["mode_average"].items():
        lines.append(f"| {mode} | {average} |")
    lines.extend([
        "",
        "## Representative Bad Replies",
        "",
    ])
    for item in summary["worst_records"]:
        lines.extend([
            f"### {item['scenario_id']} / {item['persona_id']} / {item['mode']} / run {item['run']}",
            f"- Average: {item['average']}",
            f"- Issues: {', '.join(item['issues']) or 'none'}",
            f"- Modules: {', '.join(item['failure_modules']) or 'none'}",
            f"- Assistant: {item['assistant'] or '<empty>'}",
            "",
        ])
    if not summary["worst_records"]:
        lines.append("- none")
        lines.append("")
    lines.extend([
        "## Representative Good Replies",
        "",
    ])
    for item in summary["best_records"]:
        lines.extend([
            f"### {item['scenario_id']} / {item['persona_id']} / {item['mode']} / run {item['run']}",
            f"- Average: {item['average']}",
            f"- Assistant: {item['assistant'] or '<empty>'}",
            "",
        ])
    if not summary["best_records"]:
        lines.append("- none")
        lines.append("")
    lines.extend([
        "## Recommended Next Changes",
        "",
    ])
    for recommendation in summary["recommendations"]:
        lines.append(f"- {recommendation}")
    lines.extend([
        "",
        "## Full Transcripts",
        "",
    ])
    for record in records:
        evaluation = record.get("evaluation", {})
        lines.extend([
            f"### {record.get('scenario_id')} / {record.get('persona_id')} / {record.get('mode', 'context-v2')} / run {record.get('run', 1)}",
            f"- Passed: {evaluation.get('passed')}",
            f"- Average: {evaluation.get('average')}",
            f"- Issues: {', '.join(evaluation.get('issues', [])) or 'none'}",
            f"- Modules: {', '.join((record.get('diagnosis') or diagnose_live_record(record)).get('failure_modules', [])) or 'none'}",
            "",
            "Transcript:",
            "",
        ])
        for turn in record.get("transcript", []):
            lines.append(f"- {turn.get('role')}: {turn.get('content')}")
        lines.append("")
    report.write_text("\n".join(lines), encoding="utf-8")
    return report


async def run(args: argparse.Namespace) -> dict[str, Any]:
    root = Path(args.root).resolve()
    if args.reevaluate_glob:
        paths = list(root.glob(args.reevaluate_glob))
        records = reevaluate_jsonl_files(paths, include_derived=args.include_derived)
        output_dir = root / "docs" / "audits"
        output_dir.mkdir(parents=True, exist_ok=True)
        output_path = reserve_unique_audit_path(output_dir, prefix="continuous-human-chat-aggregate")
        write_jsonl_records(output_path, records)
        report = write_report(output_path, records)
        return {
            "ok": True,
            "records": len(records),
            "files": len(paths),
            "output": str(output_path),
            "report": str(report),
        }

    if args.reevaluate_jsonl:
        source = (root / args.reevaluate_jsonl).resolve()
        records = reevaluate_records(read_jsonl_records(source))
        output_path = source.with_name(source.stem + "-reevaluated.jsonl")
        write_jsonl_records(output_path, records)
        report = write_report(output_path, records)
        return {
            "ok": True,
            "records": len(records),
            "source": str(source),
            "output": str(output_path),
            "report": str(report),
        }

    scenarios = load_live_scenarios(root / args.scenarios)
    if args.scenario:
        wanted = set(args.scenario.split(","))
        scenarios = [item for item in scenarios if item["id"] in wanted]
    if args.limit:
        scenarios = scenarios[: args.limit]
    persona_ids = _csv_values(getattr(args, "personas", ""), [args.persona])
    modes = _csv_values(getattr(args, "modes", ""), ["context-v2"])
    matrix = build_run_matrix(
        scenarios=scenarios,
        persona_ids=persona_ids,
        modes=modes,
        runs=getattr(args, "runs", 1),
    )
    provider_config = read_provider_config(root)
    if not provider_config["api_key"] and not args.dry_run:
        raise SystemExit("Missing DeepSeek API key. Configure settings or DEEPSEEK_API_KEY.")
    output_dir = root / "docs" / "audits"
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = reserve_unique_audit_path(output_dir, prefix="continuous-human-chat")
    records = []
    for item in matrix:
        started = time.perf_counter()
        try:
            record = await run_scenario(
                root=root,
                scenario=item["scenario"],
                persona_id=item["persona_id"],
                provider_config=provider_config,
                dry_run=args.dry_run,
                mode=item["mode"],
                run_index=item["run"],
            )
        except Exception as exc:
            record = build_simulation_error_record(root=root, matrix_item=item, exc=exc)
        record["latency_ms"] = round((time.perf_counter() - started) * 1000)
        record["diagnosis"] = record.get("diagnosis") or diagnose_live_record(record)
        records.append(record)
        with output_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(record, ensure_ascii=False) + "\n")
        if args.sleep_ms:
            await asyncio.sleep(args.sleep_ms / 1000)
    report = write_report(output_path, records)
    return {"ok": True, "records": len(records), "matrix": len(matrix), "output": str(output_path), "report": str(report)}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run live continuous human-chat audits.")
    parser.add_argument("--root", default=str(Path(__file__).resolve().parents[1]))
    parser.add_argument("--scenarios", default="data/live_conversation_scenarios.json")
    parser.add_argument("--scenario", default="")
    parser.add_argument("--persona", default="mature_friend")
    parser.add_argument("--personas", default="")
    parser.add_argument("--modes", default="context-v2")
    parser.add_argument("--runs", type=int, default=1)
    parser.add_argument("--limit", type=int, default=0)
    parser.add_argument("--sleep-ms", type=int, default=250)
    parser.add_argument("--reevaluate-jsonl", default="")
    parser.add_argument("--reevaluate-glob", default="")
    parser.add_argument("--include-derived", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    return parser.parse_args()


def main() -> None:
    result = asyncio.run(run(parse_args()))
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
