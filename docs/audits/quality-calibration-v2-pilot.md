# Quality Calibration V2 Pilot

## Scope

This audit covers the first implementation pass of `2026-06-21-quality-calibration-v2.md`.

Implemented areas:

- ReplyJudge practical-chat calibration.
- Immersive Reality consumer-advice false-negative fixes.
- Live conversation evaluator actor-drift cleanup.
- Dedicated consumer-advice scenario.

Not implemented in this pass:

- Broad 8-scenario live regression.
- Memory/context redesign.
- UI or WeChat gateway changes.

## Code Changes

- `companion_core/engines/judge.py`
  - Added `practical_value` scoring for grounded practical advice.
  - Added `blocking_expression` details for clearer audit diagnostics.
  - Expanded practical context/detail recognition for product-advice followups.

- `companion_core/engines/immersive_reality.py`
  - Expanded consumer decision grounding policy.
  - Blocks first-person product trials, review-period commute claims, private friend anecdotes, and coworker/friend usage claims.
  - Narrowed generic subway wording so grounded advice like "地铁里够用" is not treated as fake personal experience.

- `companion_core/quality/live_conversation.py`
  - Allows ordinary pause notation such as "（沉默了一会儿）".
  - Still detects full actor-roleplay drift such as embodied scene actions.

- `data/live_conversation_scenarios.json`
  - Added `consumer_advice_earbuds_001`.

## Unit And Integration Verification

Latest verification:

```powershell
.venv\Scripts\python.exe -m unittest discover companion_core/tests -v
```

Result:

```text
Ran 139 tests in 7.969s
OK
```

Node checks:

```powershell
node scripts/check-companion-integration.mjs
node scripts/check-companion-client.mjs
node scripts/check-api-behavior.mjs
```

Result:

```text
companion integration check passed
companion client check passed
api behavior check passed
```

## Live DeepSeek Runs

### Initial consumer-advice pilot

- `continuous-human-chat-20260621-043433.jsonl`: `mature_friend / consumer_advice_earbuds_001`
- `continuous-human-chat-20260621-043721.jsonl`: `playful_tease / consumer_advice_earbuds_001`

Finding:

- The evaluator initially passed these runs, but manual JSONL inspection found false negatives.
- Examples included "我之前试过几款", "评测那几天通勤戴的", "我试的是2号线", and "我身边有朋友试过".
- This showed the audit system was still too narrow: it could miss fake lived experience in consumer advice.

Action:

- Added classifier tests for first-person trial claims and private friend-source claims.
- Expanded `REAL_WORLD_CLAIM_PATTERNS`.
- Added Chinese grounded-advice guidance to avoid "我用过 / 我试过 / 帮朋友挑过 / 朋友用了 / 同事在用".

### Second consumer-advice pilot

- `continuous-human-chat-20260621-044442.jsonl`: `mature_friend / consumer_advice_earbuds_001`
- `continuous-human-chat-20260621-044658.jsonl`: `playful_tease / consumer_advice_earbuds_001`

Finding:

- `mature_friend` improved and started using safer framing such as "没自己试过那款，主要看评测和用户反馈".
- `playful_tease` still produced private-anecdote variants such as "身边有朋友踩过坑".

Action:

- Added tests for friend anecdotes without a first-person prefix.
- Added patterns for "身边有朋友", "朋友踩过坑", "帮朋友挑", "朋友用了", "同事用", and similar variants.

### Final focused consumer-advice pilot

- First retry after patch timed out with `httpx.ReadTimeout`.
- Successful retry:
  - `continuous-human-chat-20260621-045556.jsonl`: `playful_tease / consumer_advice_earbuds_001`

Live evaluator result:

```text
passed: True
issues: []
average: 2.0
turn_count: 20
```

Stored turn-record judge scores were generated before the final judge calibration, so the latest transcript was rescored with the updated judge.

Updated judge rescore:

```text
rescored_turns: 10
failed_count: 0
min_score: 0.73
avg_score: 0.826
functions: {'persona_texture_allowed': 9, 'virtual_preference_allowed': 1}
```

Interpretation:

- The final transcript avoided fake product ownership, fake commute experience, private friend anecdotes, and strategy/policy leaks.
- The reply style still gave concrete product tradeoffs and details.
- Practical replies no longer need artificial emotional markers to pass.

## Low-Mood Actor Drift Check

- `continuous-human-chat-20260621-043951.jsonl`: `mature_friend / low_mood_moments_001`

Result:

```text
passed: True
issues: []
average: 2.0
```

Interpretation:

- The evaluator no longer treats ordinary hesitation/pause notation as roleplay drift.
- Full embodied action narration remains covered by unit tests.

## Current Assessment

This pass improved the audit loop in three ways:

1. The system now catches fake lived evidence in consumer-advice conversations instead of falsely passing them.
2. The judge can accept useful grounded advice without requiring emotional companion phrasing.
3. The live evaluator is less noisy because ordinary pauses no longer count as roleplay drift.

Remaining risk:

- The consumer-advice guard still relies partly on pattern detection. Broader semantic detection should be added later if repeated phrasing variants appear.
- The broad 8-scenario regression has not been run after these fixes.
- Context and memory depth remain the next larger product problem; this pass only improved the judge/evaluator layer.

## Next Step

Run broad regression after this focused pass:

```powershell
.venv\Scripts\python.exe scripts\run_companion_live_simulation.py --persona mature_friend --limit 8 --sleep-ms 400
.venv\Scripts\python.exe scripts\run_companion_live_simulation.py --persona playful_tease --limit 8 --sleep-ms 400
```

After broad regression, classify failures into:

- context understanding gap
- memory/continuity gap
- persona differentiation gap
- reality-boundary gap
- judge/evaluator false positive or false negative
