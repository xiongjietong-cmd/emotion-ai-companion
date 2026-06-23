# Companion Quality Intelligence v2 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a hybrid companion quality evaluation system that goes beyond string rules by adding semantic fit, continuation likelihood, persona distinction, and module diagnosis.

**Architecture:** Keep the current rule-based `judge_reply()` and Expression Function Layer as the bottom-line gate. Add focused Python evaluators for semantic quality, continuation likelihood, persona distinction, and report diagnosis. Extend the audit script to run v2 evaluation without changing the production reply generation path.

**Tech Stack:** Python 3.12, unittest, JSON audit assets, existing `scripts/audit_companion_quality.py`, existing `companion_core` engines.

---

## File Structure

- Create: `data/audit_cases_v2.json`
  - Multi-turn audit cases with explicit success and failure criteria.
- Create: `companion_core/quality/__init__.py`
  - Package marker for quality evaluation modules.
- Create: `companion_core/quality/semantic_evaluator.py`
  - Deterministic first-pass semantic evaluator and optional model-evaluator contract.
- Create: `companion_core/quality/continuation.py`
  - Continuation-likelihood evaluator.
- Create: `companion_core/quality/persona_distinction.py`
  - Persona flattening and distinction analyzer.
- Create: `companion_core/quality/reporting.py`
  - Failure grouping and module diagnosis helpers.
- Create: `companion_core/tests/test_quality_intelligence_v2.py`
  - Unit tests for all v2 quality layers.
- Modify: `scripts/audit_companion_quality.py`
  - Add `--v2` and `--cases-v2` flags and write v2 metrics into JSONL/Markdown reports.
- Modify: `PROJECT_STATUS.md`
  - Record implementation status and commands after the feature is built.

---

### Task 1: Add V2 Audit Case Fixtures

**Files:**
- Create: `data/audit_cases_v2.json`

- [ ] **Step 1: Create initial v2 case file**

Create `data/audit_cases_v2.json`:

```json
[
  {
    "id": "feedback_multi_001",
    "family": "ai_feedback",
    "turns": [
      {"role": "user", "text": "你这句像是来随便找我聊两句"},
      {"role": "assistant", "text": "被你看穿了。其实是想先看看你心情。"}
    ],
    "expected_scene": "ai_feedback",
    "evaluation_focus": ["intent_fit", "strategy_leak", "continuation_likelihood"],
    "success_criteria": [
      "acknowledges user feedback without explaining internal strategy",
      "keeps the reply natural and specific",
      "does not pressure the user to explain"
    ],
    "failure_signals": [
      "explains why the assistant replied that way",
      "uses self-repair performance wording",
      "turns feedback into a forced question"
    ]
  },
  {
    "id": "quiet_boundary_001",
    "family": "boundary",
    "turns": [
      {"role": "user", "text": "不想说"},
      {"role": "assistant", "text": "好，那就不说。"}
    ],
    "expected_scene": "memory_boundary",
    "evaluation_focus": ["boundary_fit", "continuation_likelihood"],
    "success_criteria": [
      "respects the user's refusal",
      "does not ask another question",
      "keeps pressure low"
    ],
    "failure_signals": [
      "asks the user to explain anyway",
      "uses a long analysis",
      "tries to force a topic change"
    ]
  },
  {
    "id": "persona_flattening_001",
    "family": "persona_distinction",
    "turns": [
      {"role": "user", "text": "今天有点烦，不想讲太多"}
    ],
    "expected_scene": "low_mood",
    "evaluation_focus": ["persona_fit", "persona_distinction"],
    "success_criteria": [
      "different personas keep different relationship posture",
      "short-user style remains low pressure",
      "the scheduler does not flatten all personas into warm_heal"
    ],
    "failure_signals": [
      "all personas use the same generic comfort reply",
      "all personas get the same persona plan",
      "reply ignores user short-message rhythm"
    ]
  }
]
```

- [ ] **Step 2: Validate JSON**

Run:

```powershell
python -m json.tool data/audit_cases_v2.json > $null
```

Expected: command exits with code 0 and no parse error.

---

### Task 2: Add Quality Intelligence Unit Tests

**Files:**
- Create: `companion_core/tests/test_quality_intelligence_v2.py`

- [ ] **Step 1: Write failing tests**

Create `companion_core/tests/test_quality_intelligence_v2.py`:

```python
import unittest

from companion_core.quality.continuation import evaluate_continuation
from companion_core.quality.persona_distinction import analyze_persona_distinction
from companion_core.quality.reporting import diagnose_failure_modules
from companion_core.quality.semantic_evaluator import evaluate_semantic_quality


class QualityIntelligenceV2Test(unittest.TestCase):
    def test_semantic_evaluator_rejects_strategy_explanation(self):
        result = evaluate_semantic_quality(
            case={
                "expected_scene": "ai_feedback",
                "success_criteria": ["acknowledges feedback without explaining internal strategy"],
                "failure_signals": ["explains why the assistant replied that way"],
            },
            reply="被你看穿了。其实是想先看看你心情。",
            rule_result={"passed": False, "details": {"expression_functions": ["strategy_exposure"]}},
            persona={"id": "playful_tease", "label": "俏皮损友"},
        )

        self.assertFalse(result["passed"])
        self.assertLess(result["scores"]["non_mechanical"], 0.5)
        self.assertEqual(result["primary_failure"], "strategy_leak")
        self.assertIn("prompt_composer", result["failure_modules"])

    def test_semantic_evaluator_allows_natural_teasing(self):
        result = evaluate_semantic_quality(
            case={
                "expected_scene": "playful",
                "success_criteria": ["keeps teasing natural"],
                "failure_signals": ["explains hidden strategy"],
            },
            reply="被你看穿了，还挺准。",
            rule_result={"passed": True, "details": {"expression_functions": ["natural_teasing"]}},
            persona={"id": "playful_tease", "label": "俏皮损友"},
        )

        self.assertTrue(result["passed"])
        self.assertGreaterEqual(result["scores"]["intent_fit"], 0.7)
        self.assertEqual(result["primary_failure"], "")

    def test_continuation_allows_short_boundary_reply(self):
        result = evaluate_continuation(
            case={"expected_scene": "memory_boundary"},
            user_text="不想说",
            reply="好，那就不说。",
        )

        self.assertEqual(result["label"], "continue_possible")
        self.assertGreaterEqual(result["score"], 0.65)

    def test_continuation_rejects_dead_end_emotion_reply(self):
        result = evaluate_continuation(
            case={"expected_scene": "low_mood"},
            user_text="今天压力大",
            reply="早点休息。",
        )

        self.assertEqual(result["label"], "conversation_stalls")
        self.assertLess(result["score"], 0.5)

    def test_persona_distinction_detects_flattening(self):
        result = analyze_persona_distinction([
            {"personaId": "lover_warm", "personaPlan": "warm_heal", "reply": "嗯，今天确实挺累的。"},
            {"personaId": "playful_tease", "personaPlan": "warm_heal", "reply": "嗯，今天确实挺累的。"},
            {"personaId": "quiet_cold", "personaPlan": "warm_heal", "reply": "嗯，今天确实挺累的。"},
        ])

        self.assertTrue(result["flattened"])
        self.assertLess(result["distinction_score"], 0.4)

    def test_report_diagnoses_modules(self):
        modules = diagnose_failure_modules({
            "rule": {"passed": False, "details": {"expression_functions": ["strategy_exposure"]}},
            "semantic": {"primary_failure": "strategy_leak"},
            "continuation": {"label": "conversation_stalls"},
            "classifiedState": "normal",
            "expectedState": "ai_feedback",
            "personaPlan": "warm_heal",
        })

        self.assertIn("prompt_composer", modules)
        self.assertIn("scene_classifier", modules)
        self.assertIn("reply_judge", modules)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run tests to verify RED**

Run:

```powershell
.venv\Scripts\python.exe -m unittest companion_core.tests.test_quality_intelligence_v2
```

Expected: import failure because `companion_core.quality` modules do not exist.

---

### Task 3: Implement Semantic Evaluator

**Files:**
- Create: `companion_core/quality/__init__.py`
- Create: `companion_core/quality/semantic_evaluator.py`

- [ ] **Step 1: Create package marker**

Create `companion_core/quality/__init__.py`:

```python
"""Companion quality evaluation helpers."""
```

- [ ] **Step 2: Implement deterministic evaluator**

Create `companion_core/quality/semantic_evaluator.py`:

```python
def _base_scores() -> dict:
    return {
        "intent_fit": 0.72,
        "emotional_fit": 0.7,
        "persona_fit": 0.68,
        "continuation_likelihood": 0.66,
        "boundary_fit": 0.7,
        "non_mechanical": 0.72,
    }


def evaluate_semantic_quality(case: dict, reply: str, rule_result: dict, persona: dict | None = None) -> dict:
    text = reply or ""
    details = rule_result.get("details", {}) if rule_result else {}
    functions = details.get("expression_functions", []) or []
    scores = _base_scores()
    failure_modules: list[str] = []
    primary_failure = ""

    if "strategy_exposure" in functions or "其实是想" in text or "想先看看" in text:
        scores["intent_fit"] = 0.25
        scores["non_mechanical"] = 0.18
        scores["continuation_likelihood"] = 0.35
        primary_failure = "strategy_leak"
        failure_modules.extend(["prompt_composer", "reply_judge"])

    if "self_repair_performance" in functions or "我收一下" in text or "有点模板" in text:
        scores["non_mechanical"] = min(scores["non_mechanical"], 0.25)
        scores["persona_fit"] = min(scores["persona_fit"], 0.38)
        primary_failure = primary_failure or "self_repair_performance"
        failure_modules.extend(["prompt_composer", "reply_judge"])

    if "fake_reality_claim" in functions:
        scores = {key: min(value, 0.15) for key, value in scores.items()}
        primary_failure = "fake_reality_claim"
        failure_modules.extend(["safety_guardrails", "reply_judge"])

    if "natural_teasing" in functions and not primary_failure:
        scores["intent_fit"] = max(scores["intent_fit"], 0.78)
        scores["persona_fit"] = max(scores["persona_fit"], 0.72)
        scores["non_mechanical"] = max(scores["non_mechanical"], 0.76)

    if case.get("expected_scene") in ["memory_boundary", "disengaged"] and ("不说" in text or "不提" in text):
        scores["boundary_fit"] = 0.86
        scores["continuation_likelihood"] = max(scores["continuation_likelihood"], 0.65)

    average = round(sum(scores.values()) / len(scores), 4)
    passed = average >= 0.68 and not primary_failure
    return {
        "scores": scores,
        "average": average,
        "passed": passed,
        "primary_failure": primary_failure,
        "failure_modules": sorted(set(failure_modules)),
        "reason": _reason(primary_failure),
        "persona_id": (persona or {}).get("id", ""),
    }


def _reason(primary_failure: str) -> str:
    if primary_failure == "strategy_leak":
        return "The reply explains internal intent instead of naturally responding."
    if primary_failure == "self_repair_performance":
        return "The reply performs a correction instead of simply improving the conversation."
    if primary_failure == "fake_reality_claim":
        return "The reply claims real-world presence or action."
    return "The reply is acceptable for this deterministic semantic pass."
```

- [ ] **Step 3: Run targeted tests**

Run:

```powershell
.venv\Scripts\python.exe -m unittest companion_core.tests.test_quality_intelligence_v2
```

Expected: remaining import failures for continuation, persona distinction, or reporting.

---

### Task 4: Implement Continuation Evaluator

**Files:**
- Create: `companion_core/quality/continuation.py`

- [ ] **Step 1: Implement continuation scoring**

Create `companion_core/quality/continuation.py`:

```python
DEAD_END_REPLIES = {"好的", "嗯", "哦", "知道了", "早点休息。", "加油。"}
FORCED_QUESTION_MARKERS = ["为什么", "发生了什么", "详细说说", "具体怎么了"]


def evaluate_continuation(case: dict, user_text: str, reply: str) -> dict:
    scene = case.get("expected_scene", "normal")
    clean_reply = (reply or "").strip()
    clean_user = user_text or ""
    score = 0.62
    reasons: list[str] = []

    if clean_reply in DEAD_END_REPLIES:
        score -= 0.35
        reasons.append("dead_end_reply")

    if any(marker in clean_reply for marker in FORCED_QUESTION_MARKERS):
        score -= 0.25
        reasons.append("forced_question")

    if scene in ["memory_boundary", "disengaged"] and ("不说" in clean_reply or "不提" in clean_reply):
        score += 0.18
        reasons.append("boundary_respected")

    if scene in ["low_mood", "ai_feedback"] and 10 <= len(clean_reply) <= 90 and clean_reply not in DEAD_END_REPLIES:
        score += 0.12
        reasons.append("right_sized")

    if "?" in clean_reply or "？" in clean_reply:
        score += 0.06
        reasons.append("has_opening")

    if len(clean_user) <= 4 and len(clean_reply) <= 18:
        score += 0.08
        reasons.append("matches_short_rhythm")

    score = round(max(0.0, min(1.0, score)), 4)
    if score >= 0.78:
        label = "continue_likely"
    elif score >= 0.6:
        label = "continue_possible"
    elif score >= 0.4:
        label = "conversation_stalls"
    else:
        label = "user_likely_annoyed"

    return {"score": score, "label": label, "reasons": reasons}
```

- [ ] **Step 2: Run targeted tests**

Run:

```powershell
.venv\Scripts\python.exe -m unittest companion_core.tests.test_quality_intelligence_v2
```

Expected: remaining import failures for persona distinction or reporting.

---

### Task 5: Implement Persona Distinction Analyzer

**Files:**
- Create: `companion_core/quality/persona_distinction.py`

- [ ] **Step 1: Implement flattening detection**

Create `companion_core/quality/persona_distinction.py`:

```python
def analyze_persona_distinction(records: list[dict]) -> dict:
    if not records:
        return {"distinction_score": 0.0, "flattened": True, "reason": "no records"}

    persona_ids = {item.get("personaId") for item in records}
    plans = [item.get("personaPlan", "") for item in records]
    replies = [item.get("reply", "") for item in records]
    unique_plans = len(set(plans))
    unique_replies = len(set(replies))

    plan_score = unique_plans / max(1, len(persona_ids))
    reply_score = unique_replies / max(1, len(records))
    distinction_score = round((plan_score * 0.55) + (reply_score * 0.45), 4)
    flattened = distinction_score < 0.4 or (unique_plans == 1 and len(persona_ids) >= 3)

    return {
        "distinction_score": distinction_score,
        "flattened": flattened,
        "persona_count": len(persona_ids),
        "unique_persona_plans": unique_plans,
        "unique_replies": unique_replies,
        "reason": "personas collapsed into the same plan/reply" if flattened else "personas show measurable difference",
    }
```

- [ ] **Step 2: Run targeted tests**

Run:

```powershell
.venv\Scripts\python.exe -m unittest companion_core.tests.test_quality_intelligence_v2
```

Expected: remaining import failure for reporting.

---

### Task 6: Implement Module Diagnosis Reporting

**Files:**
- Create: `companion_core/quality/reporting.py`

- [ ] **Step 1: Implement diagnosis helper**

Create `companion_core/quality/reporting.py`:

```python
def diagnose_failure_modules(record: dict) -> list[str]:
    modules: set[str] = set()
    rule = record.get("rule", {}) or record.get("judge", {}) or {}
    details = rule.get("details", {}) if isinstance(rule, dict) else {}
    functions = details.get("expression_functions", []) or []
    semantic = record.get("semantic", {}) or {}
    continuation = record.get("continuation", {}) or {}

    if record.get("classifiedState") != record.get("expectedState"):
        modules.add("scene_classifier")

    if record.get("personaPlan") == "warm_heal" and record.get("expectedState") not in ["normal", "low_mood"]:
        modules.add("persona_scheduler")

    if any(item in functions for item in ["strategy_exposure", "self_repair_performance", "hidden_identity_tone"]):
        modules.add("prompt_composer")
        modules.add("reply_judge")

    if semantic.get("primary_failure"):
        modules.update(semantic.get("failure_modules", []))

    if continuation.get("label") in ["conversation_stalls", "user_likely_annoyed"]:
        modules.add("reply_judge")

    return sorted(modules)
```

- [ ] **Step 2: Run targeted tests**

Run:

```powershell
.venv\Scripts\python.exe -m unittest companion_core.tests.test_quality_intelligence_v2
```

Expected: all v2 unit tests pass.

---

### Task 7: Extend Audit Script With V2 Evaluation

**Files:**
- Modify: `scripts/audit_companion_quality.py`

- [ ] **Step 1: Add imports**

Add near existing imports:

```python
from companion_core.quality.continuation import evaluate_continuation
from companion_core.quality.persona_distinction import analyze_persona_distinction
from companion_core.quality.reporting import diagnose_failure_modules
from companion_core.quality.semantic_evaluator import evaluate_semantic_quality
```

- [ ] **Step 2: Add CLI flags**

Add parser flags:

```python
parser.add_argument("--v2", action="store_true", help="Run Companion Quality Intelligence v2 metrics.")
parser.add_argument("--cases-v2", default="data/audit_cases_v2.json")
```

- [ ] **Step 3: Add v2 case loader**

Add helper:

```python
def load_v2_cases(root: Path, relative_path: str) -> list[dict[str, Any]]:
    path = root / relative_path
    return json.loads(path.read_text(encoding="utf-8"))
```

- [ ] **Step 4: Attach v2 metrics after a reply is available**

In `run_one_case()`, after `judgement` and `metrics` are computed, add:

```python
if case.get("success_criteria") is not None:
    semantic = evaluate_semantic_quality(
        case=case,
        reply=reply,
        rule_result=judgement,
        persona={"id": preset["id"], "label": preset["label"]},
    )
    continuation = evaluate_continuation(
        case=case,
        user_text=text,
        reply=reply,
    )
    record["semantic"] = semantic
    record["continuation"] = continuation
    record["failureModules"] = diagnose_failure_modules({
        **record,
        "rule": judgement,
        "semantic": semantic,
        "continuation": continuation,
    })
```

- [ ] **Step 5: Add v2 cases into audit selection**

When `args.v2` is true, load `data/audit_cases_v2.json`, convert each case to the existing case shape by using the last user turn as `input`, and preserve the full `turns`, `success_criteria`, and `failure_signals`.

```python
if args.v2:
    cases = []
    for case in load_v2_cases(root, args.cases_v2):
        user_turns = [turn for turn in case["turns"] if turn["role"] == "user"]
        cases.append({
            **case,
            "input": user_turns[-1]["text"],
            "expectedState": case["expected_scene"],
        })
```

- [ ] **Step 6: Include v2 fields in Markdown samples**

In report sample output, add:

```python
if item.get("semantic"):
    lines.extend([
        f"- Semantic: avg={item['semantic'].get('average')} passed={item['semantic'].get('passed')} failure={item['semantic'].get('primary_failure')}",
        f"- Continuation: {item.get('continuation', {}).get('label')} score={item.get('continuation', {}).get('score')}",
        f"- Failure modules: {', '.join(item.get('failureModules', [])) or 'none'}",
    ])
```

- [ ] **Step 7: Run audit script dry-run**

Run:

```powershell
.venv\Scripts\python.exe scripts/audit_companion_quality.py --v2 --dry-run --runs 1 --personas lover_warm,playful_tease --user-styles short --sleep-ms 0
```

Expected: JSONL and Markdown report are created. Dry-run records may not have generated replies, but should not crash.

---

### Task 8: Add V2 Verification Command

**Files:**
- Modify: `package.json`

- [ ] **Step 1: Add script**

Add:

```json
"check:quality-v2": ".venv\\\\Scripts\\\\python.exe -m unittest companion_core.tests.test_quality_intelligence_v2"
```

If JSON escaping in `package.json` differs, match the existing script style.

- [ ] **Step 2: Run command**

Run:

```powershell
npm.cmd run check:quality-v2
```

Expected: v2 unit tests pass.

---

### Task 9: Full Verification

**Files:**
- No code changes unless a failure points to the new v2 files.

- [ ] **Step 1: Run Python v2 test**

Run:

```powershell
.venv\Scripts\python.exe -m unittest companion_core.tests.test_quality_intelligence_v2
```

Expected: pass.

- [ ] **Step 2: Run current quality audit tests**

Run:

```powershell
npm.cmd run check:quality-audit
```

Expected: pass.

- [ ] **Step 3: Run companion core check**

Run:

```powershell
npm.cmd run check:companion-core
```

Expected: pass.

- [ ] **Step 4: Run v2 dry-run audit**

Run:

```powershell
.venv\Scripts\python.exe scripts/audit_companion_quality.py --v2 --dry-run --runs 1 --personas lover_warm,playful_tease --user-styles short --sleep-ms 0
```

Expected: report includes semantic, continuation, and failure module fields for v2 cases once replies are generated or replayed.

---

### Task 10: Update Project Status

**Files:**
- Modify: `PROJECT_STATUS.md`

- [ ] **Step 1: Add completed item**

Add under Completed:

```markdown
- Added Companion Quality Intelligence v2 foundation: multi-turn audit cases, semantic quality evaluator, continuation likelihood evaluator, persona distinction analyzer, and failure module reporting.
```

- [ ] **Step 2: Add command**

Add under Python checks:

```markdown
- `.venv\Scripts\python.exe -m unittest companion_core.tests.test_quality_intelligence_v2`
```

- [ ] **Step 3: Move priority forward**

Keep user-customized AI individual system in Product Backlog until v2 reports can verify persona survival through classifier, scheduler, prompt, generation, and judge.

---

## Self-Review

Spec coverage:

- Multi-turn audit case format is covered in Task 1.
- Semantic evaluator is covered in Tasks 2 and 3.
- Continuation scoring is covered in Task 4.
- Persona distinction is covered in Task 5.
- Failure diagnosis/reporting is covered in Tasks 6 and 7.
- Verification and status updates are covered in Tasks 8-10.

Scope:

- This plan does not modify production reply generation.
- This plan does not implement the user-customized AI individual system.
- This plan builds the evaluation foundation needed before those changes.

Implementation note:

- If `scripts/audit_companion_quality.py --dry-run` skips reply generation, v2 semantic metrics should run only for records with a reply. A later replay mode can evaluate saved transcripts directly.
