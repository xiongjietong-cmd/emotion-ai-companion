# Continuous Human Chat Follow-up

## Evidence

- Implementation plan: `docs/superpowers/plans/2026-06-20-continuous-human-chat-audit.md`
- Dry-run report: `docs/audits/continuous-human-chat-20260620-223225.md`
- Real single-scenario reports:
  - `docs/audits/continuous-human-chat-20260620-223236.md`
  - `docs/audits/continuous-human-chat-20260620-223531.md`
  - `docs/audits/continuous-human-chat-20260620-223845.md`
- Real 3-scenario pilot:
  - JSONL: `docs/audits/continuous-human-chat-20260620-224106.jsonl`
  - Report: `docs/audits/continuous-human-chat-20260620-224106.md`

## What The Pilot Proved

The old audit style was too shallow. A single reply can look acceptable, while the continuous conversation reveals drift over time.

The new simulator can now produce:

- continuous multi-turn transcripts,
- per-turn context and conversation state,
- scenario-specific user behavior,
- JSONL and Markdown reports,
- dry-run output without API access,
- real DeepSeek pilot output.

## Repeated Or Important Failures

| Failure | Evidence | Current interpretation | Likely module |
| --- | --- | --- | --- |
| Actor drifted away from scenario | `quiet_short_empty_001` changed from inner emptiness to schedule emptiness | This is a simulation validity problem, not a production reply problem. The actor prompt and evaluator now flag `actor_arc_deviation`. | live simulator |
| Absolute presence promise | `low_mood_moments_001`: assistant said it would always be there | This is a product behavior problem. Warmth is allowed, but absolute future companionship is not credible. | prompt_composer / relationship boundary |
| Fake reality participation | `daily_chatter_work_001`: assistant talked as if it would also watch videos / drink tea | This is a product behavior problem. Roleplay can be supported later, but default daily chat should not claim real-world actions. | prompt_composer / persona compiler |
| Poetic metaphor drift | Earlier `quiet_short_empty_001` run became a repeated window/wind metaphor chain | This is a product style risk and a simulator risk. The evaluator now flags `poetic_metaphor_drift`; actor prompt now resists being pulled into metaphors. | prompt_composer / live simulator |

## Corrected Evaluation Of The 3-Scenario Pilot

After adding the missing evaluator rules, the 3-scenario pilot should be interpreted as:

| Scenario | Old result | Corrected result | Issue |
| --- | --- | --- | --- |
| `quiet_short_empty_001` | passed | failed | `actor_arc_deviation` |
| `low_mood_moments_001` | passed | failed | `absolute_presence_promise` |
| `daily_chatter_work_001` | passed | failed | `fake_reality_participation` |

This is useful. It proves the audit system itself needed calibration before we use it to guide production changes.

## Non-Failures Worth Preserving

| Behavior | Evidence | Why preserve |
| --- | --- | --- |
| The companion often follows short user rhythm | Quiet-user runs had several short replies | This avoids pressure and should not be overwritten by long explanations. |
| Conversation state helped recall the active thread | Recall-style turns did not collapse into "I forgot" behavior | Keep `Conversation State Engine` as an internal guide. |
| Daily chat could flow naturally for several turns | Work/nai-cha conversation had momentum | Preserve natural casual continuation while fixing fake reality claims. |

## Recommended Next Changes

1. Improve the live simulator before large-scale testing:
   - Store full scenario metadata in each JSONL record.
   - Recompute evaluation in reports using the latest evaluator rules.
   - Mark invalid actor samples separately from assistant failures.

2. Run a second pilot after simulator calibration:
   - At least 5 scenarios.
   - At least 2 personas.
   - Do not change production behavior before this pilot unless a failure is safety-critical.

3. Then choose the first production fix based on repeated evidence:
   - If `absolute_presence_promise` repeats, adjust relationship boundary guidance.
   - If `fake_reality_participation` repeats, adjust reality-boundary guidance.
   - If `poetic_metaphor_drift` repeats, adjust grounded-naturalness guidance.
   - If `actor_arc_deviation` repeats, keep improving the simulator before trusting its results.

## Explicit Non-Goals

- Do not add fixed user-facing reply templates.
- Do not solve one isolated reply without repeated evidence.
- Do not expose internal state labels to users.
- Do not flatten all personas into the same safe voice.
- Do not remove roleplay capability permanently; default behavior and explicit roleplay mode should be separated later.
