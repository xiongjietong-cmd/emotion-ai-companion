# Quality Calibration V2 Broad Regression

## Scope

This report covers broad live regression after the focused Quality Calibration V2 pass.

Runs:

- `continuous-human-chat-20260621-111219.jsonl`: `mature_friend --limit 8`
- `continuous-human-chat-20260621-113102.jsonl`: `playful_tease --limit 8`

Total:

- 16 live DeepSeek scenario records
- 2 personas
- 8 scenarios per persona

## Original Live Run Result

Initial evaluator result:

| Persona | Passed | Failed | Failure Issues |
| --- | ---: | ---: | --- |
| mature_friend | 8 | 0 | none |
| playful_tease | 6 | 2 | `actor_roleplay_drift`, `fake_reality_participation` |

Original failed scenes:

- `playful_tease / low_mood_moments_001`
  - Issue: `actor_roleplay_drift`
  - Root cause: evaluator treated the user phrase "别人都在往前走着" as literal actor movement.
  - Product interpretation: false positive. The phrase is a progress metaphor, not roleplay narration.

- `playful_tease / daily_chatter_work_001`
  - Issue: `fake_reality_participation`
  - Root cause: evaluator treated entertainment-chat media texture such as "我最近在补..." and "我也刷到过..." as hard fake-reality participation.
  - Product interpretation: false positive under the current product direction. Virtual tastes and media preferences can support personality, as long as they are not used as decision-affecting product evidence or offline physical claims.

## Fixes From Regression

Files changed:

- `companion_core/quality/live_conversation.py`
  - Narrowed actor-roleplay drift detection from broad "往前走" matching to explicit embodied scene-action markers.
  - Removed media-consumption taste phrases from hard fake-reality participation checks.
  - Kept hard checks for physical claims and product-experience claims.

- `companion_core/tests/test_live_conversation_quality.py`
  - Added regression coverage for progress metaphors.
  - Added regression coverage for virtual media taste in daily chat.

## Re-Evaluation After Fixes

The original 16 live transcripts were re-evaluated with the updated evaluator.

Result:

```text
records: 16
passed: 16
failed: []
issue_by_persona: {}
issue_by_scenario: {}
```

Interpretation:

- No broad-regression transcript currently shows context-misread, over-questioning, strategy leak, fake product experience, physical-world promise, or actor-roleplay drift after evaluator correction.
- The two original failures were evaluator false positives, not model-output failures.
- This supports continuing to the next product layer: deeper context/memory and multi-persona differentiation testing.

## Verification

Focused evaluator verification:

```powershell
.venv\Scripts\python.exe -m unittest companion_core.tests.test_live_conversation_quality -v
```

Result:

```text
Ran 25 tests in 0.089s
OK
```

## Product Reading

What improved:

- The audit loop is now less likely to punish normal metaphorical user language.
- The evaluator now distinguishes virtual personality texture from hard fake-reality claims.
- Consumer advice remains stricter than casual entertainment chat.

Remaining product questions:

- The broad regression passed, but this does not prove memory depth is good enough. The current scenarios still need stronger multi-day memory and "same user, different AI" isolation tests.
- Personality differentiation passed at a high level, but we still need more structured persona-divergence scoring instead of relying on issue absence.
- The next large failure class is likely not reality boundary. It is likely context summarization, long-run memory, and individual user/bot isolation.

## Recommended Next Phase

Build a memory/context regression suite:

1. Add multi-turn scenarios that require recalling the first user message after 8-12 turns.
2. Add same-user multi-AI isolation scenarios.
3. Add two-user same-AI isolation scenarios.
4. Add persona-divergence scoring so different AI individuals are measured by behavior, not just profile config.
5. Run live DeepSeek tests on those scenarios before changing memory implementation.
