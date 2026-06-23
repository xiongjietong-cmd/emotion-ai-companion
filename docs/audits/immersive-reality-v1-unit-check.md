# Immersive Reality V1 Unit And Integration Check

Date: 2026-06-21

## Scope

This checkpoint covers Task 1-6 from:

- `docs/superpowers/plans/2026-06-21-immersive-reality-layer-v1.md`

It does not include the focused live DeepSeek pilot yet.

## What Changed

Added a first-class Immersive Reality Layer:

- `companion_core/engines/immersive_reality.py`

The layer separates:

- `persona_texture_allowed`
- `virtual_preference_allowed`
- `consumer_experience_claim`
- `physical_world_promise`
- `explicit_roleplay_action`
- `strategy_or_policy_leak`

Wired it into:

- `companion_core/engines/prompt_composer.py`
- `companion_core/model_client.py`
- `companion_core/app.py`
- `companion_core/engines/expression_function.py`
- `companion_core/engines/judge.py`
- `companion_core/quality/live_conversation.py`

Added and updated tests:

- `companion_core/tests/test_immersive_reality.py`
- `companion_core/tests/test_prompt_composer.py`
- `companion_core/tests/test_model_client.py`
- `companion_core/tests/test_api.py`
- `companion_core/tests/test_expression_function.py`
- `companion_core/tests/test_engines.py`
- `companion_core/tests/test_live_conversation_quality.py`

## Design Boundary

This is not a blunt "do not act like a person" rule.

The layer allows:

- personal preference,
- conversational taste,
- light virtual texture,
- symbolic comfort in explicit roleplay mode.

It blocks or rewrites:

- advice-affecting fabricated product experience,
- concrete physical-world promises,
- real-world possession/action claims in default chat,
- policy or strategy leaks.

## Verification

Focused Python suite:

```text
.venv\Scripts\python.exe -m unittest companion_core.tests.test_immersive_reality companion_core.tests.test_prompt_composer companion_core.tests.test_model_client companion_core.tests.test_api companion_core.tests.test_expression_function companion_core.tests.test_engines companion_core.tests.test_live_conversation_quality -v
Ran 58 tests in 4.344s
OK
```

Full companion core suite:

```text
.venv\Scripts\python.exe -m unittest discover companion_core/tests -v
Ran 124 tests in 7.787s
OK
```

Node integration checks:

```text
node scripts/check-companion-integration.mjs
companion integration check passed

node scripts/check-companion-client.mjs
companion client check passed

node scripts/check-api-behavior.mjs
api behavior check passed
```

## Old Transcript Re-evaluation

Re-ran the updated evaluator against:

- `docs/audits/continuous-human-chat-20260620-225642.jsonl`
- `docs/audits/continuous-human-chat-20260620-230529.jsonl`

Result:

```text
records 10
passed 5
issues {
  consumer_experience_claim: 2,
  fake_reality_participation: 5,
  physical_world_promise: 1,
  actor_roleplay_drift: 1
}
```

Interpretation:

- The old broad fake-reality label is now partially split into actionable subtypes.
- `daily_chatter_work_001` is the main consumer-claim risk.
- `low_mood_moments_001` still has simulator roleplay contamination, but the assistant's physical promise is now detected separately.
- `probing_ai_feedback_001` still shows general real-world texture leakage and needs live retesting after the new prompt guidance is active.

## Remaining Risk

These tests prove that:

- the policy taxonomy exists,
- the policy reaches the model prompt,
- reply judge can see the classifications,
- live evaluator can separate issue types,
- existing core behavior still passes tests.

They do not prove that real DeepSeek output has improved. That requires Task 7 focused live simulation.

## Next Step

Run the focused DeepSeek pilot from Task 7:

```powershell
.venv\Scripts\python.exe scripts/run_companion_live_simulation.py --personas mature_friend,playful_tease --scenarios daily_chatter_work_001,probing_ai_feedback_001,low_mood_moments_001
```

Then inspect whether:

- consumer product claims disappear,
- physical-world promises disappear in default mode,
- playful and mature personas remain distinct,
- virtual texture does not get flattened into cold assistant language.
