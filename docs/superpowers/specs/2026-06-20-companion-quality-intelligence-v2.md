# Companion Quality Intelligence v2 Design

## Product Direction

The product is a WeChat-native digital companion, not a generic chatbot. The final quality target is not "the reply has no forbidden phrase". The target is:

- the user feels this companion understands the current moment;
- the reply matches this specific companion's relationship identity;
- the reply creates a natural reason to continue the conversation;
- repeated conversations make the companion feel more individually adapted;
- obvious safety, boundary, fake-reality, and operational failures are blocked before they reach the user.

The current rule-based ReplyJudge remains useful as a bottom-line gate, but it is not the product's final quality system.

## Current Problem

The current judge mostly uses code rules, string patterns, and a numeric threshold. It can catch failures like strategy leaks, fake reality claims, service tone, oily phrases, and very weak dead-end replies. It cannot reliably judge:

- whether the assistant understood the user's real intent;
- whether a reply would make the user want to continue;
- whether two different personas actually feel different;
- whether a short reply is correctly minimal or just empty;
- whether roleplay, emotional support, teasing, and boundary repair are working in context;
- whether the fix improved the product direction or only patched one bad sentence.

## Scope

This v2 system builds the evaluation foundation before more generation changes.

In scope:

- multi-turn audit case format;
- semantic evaluator contract;
- continuation-likelihood scoring;
- persona-distinction scoring;
- rule-gate plus semantic-gate merged report;
- deterministic dry-run mode for development;
- optional DeepSeek-backed semantic evaluation for richer audits;
- report output that names the module likely responsible for each failure.

Out of scope for this phase:

- changing user-facing chat generation;
- implementing the full user-customized AI individual system;
- adding production telemetry storage;
- adding proactive-message delivery;
- replacing the existing rule judge.

## Design Options Considered

### Option A: Keep Expanding RuleJudge

This is fast and deterministic, but it will keep turning product judgment into phrase-level patches. It is useful for bottom-line safety only.

### Option B: Replace RuleJudge With A Model Judge

This can understand more context, but it is unstable, costly, and hard to test. It also risks making every evaluation opaque.

### Option C: Hybrid Evaluation Layer

Recommended. Keep the rule gate for hard failures, add a semantic evaluator for conversational quality, and add audit-level metrics for persona difference and continuation. This gives us deterministic safety plus richer product judgment.

## Architecture

```text
audit case v2
  -> generation path
  -> rule gate
  -> expression function layer
  -> semantic evaluator
  -> continuation simulator
  -> persona distinction aggregator
  -> quality report
```

### 1. Audit Case v2

Each case can represent a multi-turn situation, not only one user message.

Required fields:

- `id`
- `family`
- `turns`
- `expected_scene`
- `evaluation_focus`
- `success_criteria`
- `failure_signals`

Example:

```json
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
    "acknowledges the feedback without explaining internal strategy",
    "keeps the reply natural and specific",
    "does not pressure the user to explain"
  ],
  "failure_signals": [
    "explains why the assistant replied that way",
    "uses self-repair performance wording",
    "turns feedback into a forced question"
  ]
}
```

### 2. Rule Gate

The existing `judge_reply()` and `analyze_expression_function()` stay as the first gate. They continue to detect:

- fake reality claims;
- internal strategy leaks;
- self-repair performance;
- hidden identity tone;
- service tone;
- oily tone;
- over-questioning;
- hard safety failures.

Rule gate output must be preserved because it is explainable and cheap.

### 3. Semantic Evaluator

The semantic evaluator judges meaning and conversational function, not literal banned words.

Input:

- case metadata;
- recent turns;
- generated reply;
- selected persona profile;
- rule-gate result;
- expression-function result.

Output:

```json
{
  "scores": {
    "intent_fit": 0.0,
    "emotional_fit": 0.0,
    "persona_fit": 0.0,
    "continuation_likelihood": 0.0,
    "boundary_fit": 0.0,
    "non_mechanical": 0.0
  },
  "passed": false,
  "primary_failure": "strategy_leak",
  "failure_modules": ["prompt_composer", "reply_judge"],
  "reason": "The reply explains the assistant's hidden intent instead of naturally responding to user feedback."
}
```

For development, the first implementation can use deterministic heuristics. A later mode can use DeepSeek as an evaluator with strict JSON output.

### 4. Continuation Simulator

The question is not "is this reply correct?" but "would a user likely continue?"

The simulator assigns one of:

- `continue_likely`
- `continue_possible`
- `conversation_stalls`
- `user_likely_annoyed`

It should penalize:

- dead-end replies;
- forced questions;
- generic reassurance;
- unexplained topic jumps;
- replies that make the user feel analyzed instead of met.

It should not penalize intentional quiet replies when the scene is silence, boundary respect, or low-pressure companionship.

### 5. Persona Distinction Aggregator

The same scenario should be tested against multiple personas. The report should answer:

- did the personas differ only in wording, or in relationship posture;
- did the scheduler collapse them all into `warm_heal`;
- which personas lost their defining identity;
- which scenes suppress user-authored individuality.

This is required before building richer user-customized AI creation, because personalization is meaningless if the runtime flattens every bot.

### 6. Quality Report

The report should rank failures by module:

- scene classifier;
- persona scheduler;
- prompt composer;
- model client;
- sanitizer;
- reply judge;
- audit data.

It should produce a short action list:

1. Highest-impact failure family.
2. Most likely responsible module.
3. Example records.
4. Recommended next implementation task.

## Data Flow

1. Load v2 audit cases.
2. For each persona and user style, generate or read reply.
3. Run rule gate.
4. Run expression function analysis.
5. Run semantic evaluator.
6. Run continuation simulator.
7. Aggregate persona distinction.
8. Write JSONL and Markdown report.

## Testing Strategy

Unit tests:

- semantic evaluator rejects strategy explanation even if wording is polite;
- semantic evaluator allows natural teasing when it does not expose strategy;
- continuation simulator allows short boundary-respecting replies;
- continuation simulator rejects generic dead ends in emotional scenes;
- persona distinction detects when all personas produce the same plan;
- report groups failures by likely module.

Smoke checks:

- run dry-run v2 audit without model calls;
- run small real DeepSeek audit with two personas and two families;
- verify output includes rule score, semantic score, continuation label, and module diagnosis.

## Success Criteria

The phase is successful when we can answer these questions from one report:

- Which scene families are failing most?
- Are replies failing because of rules, semantics, continuation, or persona flattening?
- Did different personas actually produce different relationship posture?
- Which module should be changed next?
- Are we improving product-level companion quality instead of patching isolated sentences?

## Backlog Dependency

The user-customized AI individual system should wait behind this evaluation layer. Richer user creation is useful, but without v2 quality evaluation, we cannot prove that personalized settings survive scene classification, scheduling, prompt composition, generation, and judging.
