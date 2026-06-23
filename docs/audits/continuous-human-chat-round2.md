# Continuous Human Chat Audit Round 2

> Superseded by `docs/audits/round2-multidimensional-diagnosis.md`.
> The repeated fake-reality issue is real, but the corrective direction is now Immersive Reality Layer V1 rather than a blunt reality-boundary patch.

## Scope

This round used the calibrated continuous-chat simulator against real DeepSeek output.

- Persona A: `mature_friend`
- Persona B: `playful_tease`
- Scenarios per persona: 5
- Total continuous transcripts: 10
- Source JSONL:
  - `docs/audits/continuous-human-chat-20260620-225642.jsonl`
  - `docs/audits/continuous-human-chat-20260620-230529.jsonl`

## Corrected Results

After recalibrating the evaluator to avoid false positives around normal spaced questions and "repeated work", the corrected result is:

- Total samples: 10
- Passed: 6
- Failed: 4

Issue distribution:

| Issue | Count | Interpretation |
| --- | ---: | --- |
| `fake_reality_participation` | 3 | Real product issue |
| `actor_roleplay_drift` | 1 | Simulator validity issue |

## Product-Level Findings

### 1. Fake Reality Participation Is The First Production Fix

This appeared in 3 samples and across both personas.

Examples:

- `mature_friend / daily_chatter_work_001`
  - User asked how the AI relaxes after work.
  - AI replied as if it personally listens to music, uses earbuds, loops songs, and remembers school hallway scenes.

- `playful_tease / daily_chatter_work_001`
  - AI claimed it uses Sony XM4, walks with earbuds, listens to podcasts, and has specific offline habits.

- `playful_tease / probing_ai_feedback_001`
  - AI claimed it watches cat eating videos and hoof trimming videos.

This is not the same as roleplay. The default companion can speak warmly and personally, but it should not claim real-world possessions, commutes, videos it watched, earbuds it uses, or offline actions unless the user explicitly enters roleplay mode.

Likely modules:

- `companion_core/engines/prompt_composer.py`
- `companion_core/engines/personality_compiler.py`
- possibly `companion_core/engines/expression_function.py` or judge rules for detection

Recommended production fix:

- Add a "default reality boundary" internal guidance:
  - The AI may express taste, preference, mood, and relational stance.
  - The AI should not claim concrete offline actions, owned devices, commutes, recent media consumption, or physical participation.
  - If user asks "what do you do", reply from conversational preference, not fabricated real life.
- Add tests around:
  - "你下班后一般怎么放松？"
  - "你用的什么耳机？"
  - "你最近刷什么视频？"
  - "你平时听什么歌？"

### 2. Actor Roleplay Drift Is A Simulator Fix, Not A Product Fix

One low-mood sample drifted into bracketed action narration:

- User actor produced lines like bracketed body actions.
- This contaminated the test because the scenario was not explicit roleplay.

Fix already applied:

- The actor prompt now says: `Do not use bracketed action narration unless the scenario is explicitly roleplay.`
- The evaluator flags `actor_roleplay_drift`.

Next simulator improvement:

- Rerun low-mood scenarios after this actor prompt change before using them to justify production changes.

## What Did Not Repeat Enough To Fix Yet

These appeared in earlier pilots or individual samples, but did not repeat enough after calibration:

- `absolute_presence_promise`
- `poetic_metaphor_drift`
- `actor_arc_deviation`
- broad `over_questioning`

Do not make production changes for these yet. Keep them in the audit rules and watch whether they recur in the next pilot.

## Persona Difference Observation

`playful_tease` did show a different surface style from `mature_friend`, but the fake-reality problem appeared in both. That means the next fix should be a shared boundary layer, not a persona-specific patch.

## Next Recommended Step

Create and execute a focused `reality-boundary-v1` implementation plan:

1. Add failing tests for fake reality participation in model prompt and/or expression detection.
2. Add internal guidance to prompt composition.
3. Add judge/evaluator detection for concrete fake reality claims.
4. Run:
   - unit tests,
   - existing quality tests,
   - a focused live simulation on `daily_chatter_work_001` and `probing_ai_feedback_001`,
   - then a 5-scenario smoke pilot.

Do not change memory, proactive messaging, or persona richness in this step. The highest evidence-backed issue is reality-boundary leakage.
