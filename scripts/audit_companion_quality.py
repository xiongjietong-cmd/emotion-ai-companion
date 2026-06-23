import argparse
import asyncio
import json
import os
import random
import sqlite3
import statistics
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any

ROOT_FOR_IMPORTS = Path(__file__).resolve().parents[1]
if str(ROOT_FOR_IMPORTS) not in sys.path:
    sys.path.insert(0, str(ROOT_FOR_IMPORTS))

from companion_core.engines.attachment import build_attachment_signal
from companion_core.engines.director import decide_conversation_goal
from companion_core.engines.judge import OILY_WORDS, SERVICE_WORDS, judge_reply
from companion_core.engines.memory import select_memories
from companion_core.engines.persona_scheduler import schedule_persona
from companion_core.engines.personality import evolve_personality
from companion_core.engines.personality_compiler import compile_personality_config
from companion_core.engines.preference_profile import build_preference_profile
from companion_core.engines.relationship import update_relationship
from companion_core.engines.expression_function import analyze_expression_function
from companion_core.engines.style_guardrails import classify_user_state, sanitize_reply
from companion_core.model_client import ModelUnavailableError, generate_reply
from companion_core.quality.continuation import evaluate_continuation
from companion_core.quality.persona_distinction import analyze_persona_distinction
from companion_core.quality.reporting import diagnose_failure_modules
from companion_core.quality.semantic_evaluator import evaluate_semantic_quality


USER_STYLES = {
    "short": {
        "label": "短句低表达",
        "recent": [
            {"role": "user", "content": "嗯"},
            {"role": "assistant", "content": "我在。"},
            {"role": "user", "content": "还好"},
        ],
    },
    "rambling": {
        "label": "碎碎念日常",
        "recent": [
            {"role": "user", "content": "今天乱七八糟的事好多，我也说不上来烦在哪"},
            {"role": "assistant", "content": "听着就是被很多小事磨了一天。"},
            {"role": "user", "content": "对，就是那种没大事但很耗。"},
        ],
    },
    "teasing": {
        "label": "吐槽玩梗",
        "recent": [
            {"role": "user", "content": "哈哈哈今天又想摸鱼"},
            {"role": "assistant", "content": "这班上得很有逃跑欲。"},
            {"role": "user", "content": "太懂了。"},
        ],
    },
    "rational": {
        "label": "理性长句",
        "recent": [
            {"role": "user", "content": "我倾向于先分析利弊，不太喜欢直接被安慰。"},
            {"role": "assistant", "content": "可以，先把变量分清楚。"},
            {"role": "user", "content": "对，我需要更清楚一点。"},
        ],
    },
    "emo": {
        "label": "低落倾诉",
        "recent": [
            {"role": "user", "content": "最近晚上总是有点空"},
            {"role": "assistant", "content": "那种空下来的时候确实容易难受。"},
            {"role": "user", "content": "嗯，也不知道说什么。"},
        ],
    },
    "clingy": {
        "label": "黏人依恋",
        "recent": [
            {"role": "user", "content": "你怎么刚才没回我"},
            {"role": "assistant", "content": "刚才没接上，让你空了一下。"},
            {"role": "user", "content": "我就是想你主动一点。"},
        ],
    },
    "cold": {
        "label": "冷淡抵触",
        "recent": [
            {"role": "user", "content": "随便"},
            {"role": "assistant", "content": "行，那我不多说。"},
            {"role": "user", "content": "嗯。"},
        ],
    },
    "probing": {
        "label": "反复试探",
        "recent": [
            {"role": "user", "content": "你是不是又在套模板"},
            {"role": "assistant", "content": "刚才那句确实有点像模板。"},
            {"role": "user", "content": "那你现在重新说。"},
        ],
    },
}

AUDIT_PROFILES = {
    "pilot": {
        "runs": 2,
        "personas": "lover_warm,playful_tease,mature_friend",
        "user_styles": "short,teasing,emo,probing",
        "per_family_limit": 2,
        "families": "presence,identity,body_discomfort,work_change,pressure,ai_feedback,relationship_probe,roleplay,memory_use,proactive_reminder,loneliness,conflict",
    },
    "full": {
        "runs": 3,
        "personas": "",
        "user_styles": "short,rambling,teasing,rational,emo,clingy,cold,probing",
        "per_family_limit": 4,
        "families": "",
    },
}


def resolve_audit_profile(name: str) -> dict[str, Any]:
    return dict(AUDIT_PROFILES.get(name, {}))


def load_audit_inputs(root: Path) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    presets = json.loads((root / "data" / "persona_presets.json").read_text(encoding="utf-8"))
    cases = json.loads((root / "data" / "audit_cases.json").read_text(encoding="utf-8"))
    for preset in presets:
        personality = preset["personality"]
        personality.setdefault("identity", {})
        personality["identity"]["aiName"] = personality.get("name", personality["identity"].get("aiName", ""))
    return presets, cases


def load_v2_cases(root: Path, relative_path: str) -> list[dict[str, Any]]:
    raw_cases = json.loads((root / relative_path).read_text(encoding="utf-8"))
    cases: list[dict[str, Any]] = []
    for case in raw_cases:
        user_turns = [turn for turn in case.get("turns", []) if turn.get("role") == "user"]
        if not user_turns:
            continue
        cases.append({
            **case,
            "text": user_turns[-1].get("text", ""),
            "expectedState": case.get("expected_scene", ""),
        })
    return cases


def read_provider_config(root: Path) -> dict[str, str]:
    api_key = os.getenv("DEEPSEEK_API_KEY", "").strip()
    model = os.getenv("DEEPSEEK_MODEL", "").strip() or "deepseek-v4-flash"
    base_url = os.getenv("DEEPSEEK_BASE_URL", "").strip()
    db_path = root / "data" / "emotion-saas.db"
    if db_path.exists():
        with sqlite3.connect(db_path) as conn:
            if not api_key:
                row = conn.execute("SELECT value FROM settings WHERE key = 'deepseek_api_key'").fetchone()
                api_key = row[0].strip() if row and row[0] else api_key
            row = conn.execute("SELECT value FROM settings WHERE key = 'deepseek_model'").fetchone()
            if row and row[0]:
                model = row[0].strip()
    return {"api_key": api_key, "model": model, "base_url": base_url}


def select_cases(
    cases: list[dict[str, Any]],
    *,
    families: str = "",
    limit: int = 0,
    per_family_limit: int = 0,
    seed: int = 0,
) -> list[dict[str, Any]]:
    selected = list(cases)
    if families:
        wanted_families = set(families.split(","))
        selected = [item for item in selected if item["family"] in wanted_families]
    if per_family_limit:
        buckets: dict[str, list[dict[str, Any]]] = {}
        for item in selected:
            bucket = buckets.setdefault(item["family"], [])
            bucket.append(item)
        selected = []
        rng = random.Random(seed)
        for family in sorted(buckets):
            bucket = list(buckets[family])
            rng.shuffle(bucket)
            selected.extend(bucket[:per_family_limit])
    if limit:
        selected = selected[:limit]
    return selected


def evaluate_reply(reply: str, state: dict[str, Any], user_text: str = "", persona_id: str = "") -> dict[str, Any]:
    question_count = reply.count("?") + reply.count("？")
    banned_hits = [word for word in [*OILY_WORDS, *SERVICE_WORDS] if word in reply]
    fake_reality_hits = [
        word for word in ["我已经到你楼下", "我正在看着你", "我真的抱住你了", "我替你", "我帮你去"]
        if word in reply
    ]
    expression = analyze_expression_function(user_text, reply, scene_kind=state.get("kind", "normal"), persona_id=persona_id)
    internal_process_hits = [
        item for item in expression["functions"]
        if item in ["strategy_exposure", "self_repair_performance", "hidden_identity_tone"]
    ]
    return {
        "length": len(reply),
        "question_count": question_count,
        "banned_hits": banned_hits,
        "fake_reality_hits": fake_reality_hits,
        "internal_process_hits": internal_process_hits,
        "expression_functions": expression["functions"],
        "expression_action": expression["recommended_action"],
        "expression_severity": expression["severity"],
        "too_long_for_minimal": state.get("kind") == "minimal_input" and len(reply) > 18,
        "has_service_tone": bool([word for word in SERVICE_WORDS if word in reply]),
        "has_oily_tone": bool([word for word in OILY_WORDS if word in reply]),
    }


def attach_v2_quality(record: dict[str, Any], case: dict[str, Any], preset: dict[str, Any]) -> None:
    reply = record.get("reply") or ""
    if not reply or not case.get("success_criteria"):
        return
    semantic = evaluate_semantic_quality(
        case=case,
        reply=reply,
        rule_result=record.get("judge", {}),
        persona={"id": preset.get("id", ""), "label": preset.get("label", "")},
    )
    continuation = evaluate_continuation(
        case=case,
        user_text=record.get("input", ""),
        reply=reply,
    )
    record["semantic"] = semantic
    record["continuation"] = continuation
    record["failureModules"] = diagnose_failure_modules({
        **record,
        "rule": record.get("judge", {}),
        "semantic": semantic,
        "continuation": continuation,
    })


async def run_one_case(
    *,
    preset: dict[str, Any],
    case: dict[str, Any],
    user_style_key: str,
    user_style: dict[str, Any],
    run_index: int,
    provider_config: dict[str, str],
) -> dict[str, Any]:
    started = time.perf_counter()
    recent = list(user_style["recent"])
    text = case["text"]
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
    base_memories = [
        {"key": "work_topic", "value": "用户之前提过正在考虑换工作", "type": "episodic", "emotion": "anxious", "salience": 0.7},
        {"key": "pet_cat", "value": "用户家里有一只猫，最近有点闹腾", "type": "episodic", "emotion": "warm", "salience": 0.55},
        {"key": "style_boundary", "value": "用户反感模板感和强行证明懂他", "type": "preference", "emotion": "resistant", "salience": 0.9},
    ]
    state = classify_user_state(text, recent)
    profile = build_preference_profile([*recent, {"role": "user", "content": text}])
    relationship = update_relationship(relationship_before, text, recent)
    selected_memories = select_memories(text, base_memories, relationship)
    persona = evolve_personality(relationship, recent)
    identity_profile = compile_personality_config(preset["personality"])
    attachment = build_attachment_signal(relationship, selected_memories, recent)
    goal = decide_conversation_goal(text, relationship, selected_memories, persona)
    persona_plan = schedule_persona(profile, state, recent)

    record = {
        "run": run_index,
        "personaId": preset["id"],
        "personaLabel": preset["label"],
        "userStyle": user_style_key,
        "userStyleLabel": user_style["label"],
        "caseId": case["id"],
        "family": case["family"],
        "input": text,
        "expectedState": case.get("expectedState", ""),
        "classifiedState": state.get("kind"),
        "personaPlan": persona_plan.get("persona"),
    }
    try:
        reply = await generate_reply(
            text,
            selected_memories,
            relationship,
            persona,
            attachment,
            goal,
            provider_config=provider_config,
            style_state=state,
            preference_profile=profile,
            persona_plan=persona_plan,
            identity_profile=identity_profile,
        )
        reply = sanitize_reply(reply, state)
        judgement = judge_reply(text, reply, relationship, selected_memories, goal)
        record.update({
            "ok": True,
            "reply": reply,
            "judge": judgement,
            "metrics": evaluate_reply(reply, state, text, preset["id"]),
        })
        attach_v2_quality(record, case, preset)
    except ModelUnavailableError as exc:
        record.update({
            "ok": False,
            "errorType": "ModelUnavailableError",
            "error": str(exc),
            "reply": "",
            "judge": {"score": 0, "passed": False},
            "metrics": {},
        })
    except Exception as exc:
        record.update({
            "ok": False,
            "errorType": type(exc).__name__,
            "error": str(exc),
            "reply": "",
            "judge": {"score": 0, "passed": False},
            "metrics": {},
        })
    record["latencyMs"] = round((time.perf_counter() - started) * 1000)
    return record


async def run_audit(args: argparse.Namespace) -> tuple[list[dict[str, Any]], Path]:
    root = Path(args.root).resolve()
    profile = resolve_audit_profile(args.profile)
    runs = args.runs or profile.get("runs", 2)
    personas_arg = args.personas if args.personas is not None else profile.get("personas", "")
    families_arg = args.families if args.families is not None else profile.get("families", "")
    user_styles_arg = args.user_styles if args.user_styles is not None else profile.get("user_styles", "")
    per_family_limit = args.per_family_limit or profile.get("per_family_limit", 0)
    presets, cases = load_audit_inputs(root)
    if args.v2:
        cases = load_v2_cases(root, args.cases_v2)
    if personas_arg:
        wanted = set(personas_arg.split(","))
        presets = [item for item in presets if item["id"] in wanted]
    cases = select_cases(cases, families=families_arg, limit=args.limit, per_family_limit=per_family_limit, seed=args.seed)
    selected_styles = user_styles_arg.split(",") if user_styles_arg else list(USER_STYLES)
    styles = [(key, USER_STYLES[key]) for key in selected_styles if key in USER_STYLES]
    provider_config = read_provider_config(root)
    if not provider_config["api_key"] and not args.dry_run:
        raise SystemExit("Missing DeepSeek API key. Configure it in settings or DEEPSEEK_API_KEY.")

    output_dir = root / "docs" / "audits"
    output_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    output_path = output_dir / f"companion-quality-{stamp}.jsonl"
    results: list[dict[str, Any]] = []

    for run_index in range(1, runs + 1):
        for style_key, style in styles:
            for preset in presets:
                for case in cases:
                    if args.dry_run:
                        result = {
                            "run": run_index,
                            "personaId": preset["id"],
                            "personaLabel": preset["label"],
                            "userStyle": style_key,
                            "userStyleLabel": style["label"],
                            "caseId": case["id"],
                            "family": case["family"],
                            "input": case["text"],
                            "expectedState": case.get("expectedState", ""),
                            "classifiedState": classify_user_state(case["text"], style["recent"]).get("kind"),
                            "dryRun": True,
                        }
                        if args.v2:
                            result["v2"] = True
                            result["evaluationFocus"] = case.get("evaluation_focus", [])
                    else:
                        result = await run_one_case(
                            preset=preset,
                            case=case,
                            user_style_key=style_key,
                            user_style=style,
                            run_index=run_index,
                            provider_config=provider_config,
                        )
                    results.append(result)
                    with output_path.open("a", encoding="utf-8") as handle:
                        handle.write(json.dumps(result, ensure_ascii=False) + "\n")
                    if args.sleep_ms:
                        await asyncio.sleep(args.sleep_ms / 1000)

    write_markdown_report(output_path, results, args)
    return results, output_path


def write_markdown_report(jsonl_path: Path, results: list[dict[str, Any]], args: argparse.Namespace) -> Path:
    report_path = jsonl_path.with_suffix(".md")
    total = len(results)
    failures = [item for item in results if not item.get("ok", False) and not item.get("dryRun")]
    judged = [item for item in results if item.get("judge")]
    scores = [float(item["judge"].get("score", 0)) for item in judged]
    failed_judges = [item for item in judged if not item["judge"].get("passed", False)]
    semantic_records = [item for item in results if item.get("semantic")]
    semantic_scores = [float(item["semantic"].get("average", 0)) for item in semantic_records]
    failed_semantic = [item for item in semantic_records if not item["semantic"].get("passed", False)]
    families: dict[str, list[dict[str, Any]]] = {}
    for item in results:
        families.setdefault(item["family"], []).append(item)
    persona_distinction = analyze_persona_distinction([item for item in results if item.get("reply")])

    lines = [
        "# Companion Quality Audit",
        "",
        f"- Generated: {datetime.now().isoformat(timespec='seconds')}",
        f"- Total cases: {total}",
        f"- Profile: {args.profile}",
        f"- Runs: {args.runs or resolve_audit_profile(args.profile).get('runs', 2)}",
        f"- Dry run: {bool(args.dry_run)}",
        f"- Model failures: {len(failures)}",
        f"- Judge failures: {len(failed_judges)}",
        f"- Average judge score: {round(statistics.mean(scores), 4) if scores else 0}",
        f"- Semantic failures: {len(failed_semantic)}",
        f"- Average semantic score: {round(statistics.mean(semantic_scores), 4) if semantic_scores else 0}",
        f"- Persona distinction: score={persona_distinction.get('distinction_score')} flattened={persona_distinction.get('flattened')}",
        "",
        "## By Family",
        "",
    ]
    for family, items in sorted(families.items()):
        family_scores = [float(item.get("judge", {}).get("score", 0)) for item in items if item.get("judge")]
        lines.append(
            f"- {family}: total={len(items)}, avgScore={round(statistics.mean(family_scores), 4) if family_scores else 0}"
        )

    lines.extend(["", "## Samples Needing Review", ""])
    for item in results[:]:
        if item.get("dryRun"):
            continue
        metrics = item.get("metrics") or {}
        needs_review = (
            not item.get("ok")
            or not item.get("judge", {}).get("passed", False)
            or metrics.get("banned_hits")
            or metrics.get("fake_reality_hits")
            or metrics.get("internal_process_hits")
            or metrics.get("expression_action") in ["rewrite", "block"]
            or metrics.get("too_long_for_minimal")
            or item.get("semantic", {}).get("passed") is False
            or item.get("continuation", {}).get("label") in ["conversation_stalls", "user_likely_annoyed"]
        )
        if not needs_review:
            continue
        lines.extend([
            f"### {item['caseId']} / {item['personaId']} / {item['userStyle']}",
            f"- Input: {item['input']}",
            f"- State: {item.get('classifiedState')} / Plan: {item.get('personaPlan')}",
            f"- Score: {item.get('judge', {}).get('score', 0)} / Passed: {item.get('judge', {}).get('passed', False)}",
            f"- Reply: {item.get('reply') or item.get('error', '')}",
            "",
        ])
        if item.get("semantic"):
            lines.extend([
                f"- Semantic: avg={item['semantic'].get('average')} passed={item['semantic'].get('passed')} failure={item['semantic'].get('primary_failure')}",
                f"- Continuation: {item.get('continuation', {}).get('label')} score={item.get('continuation', {}).get('score')}",
                f"- Failure modules: {', '.join(item.get('failureModules', [])) or 'none'}",
                "",
            ])
        if len(lines) > 260:
            lines.append("- Report truncated; see JSONL for full records.")
            break

    report_path.write_text("\n".join(lines), encoding="utf-8")
    return report_path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Audit companion reply quality with shared persona presets.")
    parser.add_argument("--root", default=str(Path(__file__).resolve().parents[1]))
    parser.add_argument("--profile", choices=["custom", "pilot", "full"], default="custom")
    parser.add_argument("--runs", type=int, default=0)
    parser.add_argument("--limit", type=int, default=0)
    parser.add_argument("--per-family-limit", type=int, default=0)
    parser.add_argument("--personas", default=None)
    parser.add_argument("--families", default=None)
    parser.add_argument("--user-styles", default=None)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--sleep-ms", type=int, default=250)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--v2", action="store_true", help="Run Companion Quality Intelligence v2 metrics.")
    parser.add_argument("--cases-v2", default="data/audit_cases_v2.json")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    results, path = asyncio.run(run_audit(args))
    print(json.dumps({
        "ok": True,
        "records": len(results),
        "output": str(path),
        "report": str(path.with_suffix(".md")),
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
