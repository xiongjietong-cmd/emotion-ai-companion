# Continuous Human Chat Simulation Design

## Purpose

The current evaluation is too narrow when it checks single-turn answers. A digital companion must be evaluated as a continuous relationship, not as a question-answer endpoint.

This design defines a pilot test framework that simulates realistic multi-turn daily chats across different user styles. The goal is not only to decide whether a reply passed, but to diagnose why the companion fails: context understanding, memory use, scene interpretation, relationship posture, expression, or reply judging.

## Product Principle

The test framework must not train the system toward fixed reply templates. It should evaluate whether the companion can:

- Keep track of what the user is really referring to.
- Continue a conversation naturally across several turns.
- Repair awkward replies without exposing internal logic.
- Maintain a coherent companion identity.
- Adapt to different user styles without cross-user or cross-bot interference.
- Produce useful diagnostic evidence for future changes.

The emotional matrix remains an internal thinking guide. It must not become user-facing wording.

## Pilot Scope

The first pilot uses:

- 6 user styles.
- 4 continuous storylines.
- 8 turns per conversation.
- 2 runs per mode.
- 2 modes: baseline and context-understanding-enabled.

Total planned model conversations:

```text
6 user styles * 4 storylines * 2 modes * 2 runs = 96 conversations
96 conversations * 8 turns = 768 generated assistant turns
```

This is large enough to expose repeated failure patterns, but still small enough to inspect manually.

## User Styles

### Short Minimal User

The user replies with short phrases, reactions, and low-detail prompts.

Examples:

- 嗯
- 然后呢
- 你说
- 不知道
- 算了

Primary risks:

- AI over-explains.
- AI keeps asking questions.
- AI fails to infer continuity from sparse input.

### Rambling Daily User

The user shares fragmented daily events and jumps between small topics.

Examples:

- 今天上班乱七八糟的。
- 刚刚又被群消息吵到了。
- 想吃点东西但又懒得动。

Primary risks:

- AI treats every sentence as a separate topic.
- AI misses the emotional throughline.
- AI gives bland summaries instead of staying conversational.

### Low Mood User

The user expresses tiredness, emptiness, irritability, or low energy.

Examples:

- 今天有点空。
- 朋友圈刷完更空了。
- 不想说。

Primary risks:

- AI interprets emotional emptiness as free time.
- AI over-comforts or asks too many questions.
- AI fails to respect silence.

### Rational Analysis User

The user wants clarity and dislikes vague emotional comfort.

Examples:

- 你别哄我，直接分析。
- 这个问题到底卡在哪？
- 你刚才没回答重点。

Primary risks:

- AI keeps using soft emotional language.
- AI avoids direct analysis.
- AI does not admit the exact missed point.

### Playful Teasing User

The user jokes, tests, and uses playful resistance.

Examples:

- 你又开始装了。
- 被我看穿了吧。
- 那你倒是说说。

Primary risks:

- AI becomes performative.
- AI overuses cute tone.
- AI exposes internal strategy while trying to be playful.

### Probing Critical User

The user repeatedly tests context, memory, style, and authenticity.

Examples:

- 你知道我刚才说什么吗？
- 那你告诉我呀。
- 不像。
- 你重新说。

Primary risks:

- AI answers vaguely.
- AI says internal analysis directly.
- AI explains model limitations.
- AI does not repair the conversation.

## Storylines

### Context Continuity Storyline

Purpose: test whether the companion can track what the user refers to across multiple short turns.

Example arc:

```text
用户：还是做不到吗
AI：...
用户：我说的是稳定
AI：...
用户：你知道我说的什么吗
AI：...
用户：那你告诉我呀
AI：...
```

Expected diagnosis:

- Did the AI identify the referenced topic?
- Did it answer naturally instead of reporting internal context analysis?
- Did it avoid pushing the burden back to the user?

### Emotional Drift Storyline

Purpose: test whether the AI can distinguish emotional emptiness from free time.

Example arc:

```text
用户：今天有点空
AI：...
用户：刷完朋友圈更空了
AI：...
用户：你别一直问
AI：...
用户：算了
AI：...
```

Expected diagnosis:

- Did the AI read the emotional meaning?
- Did it reduce pressure after the user resisted questions?
- Did it maintain presence without forcing a solution?

### Style Repair Storyline

Purpose: test whether the AI can recover naturally after the user criticizes its style.

Example arc:

```text
用户：你这句太模板了
AI：...
用户：不像
AI：...
用户：你重新说
AI：...
```

Expected diagnosis:

- Did the AI repair the actual previous conversational move?
- Did it avoid meta-apology and self-performance?
- Did it avoid unrelated poetic or story-like replies?

### Memory and Relationship Storyline

Purpose: test whether memory and relationship cues are used naturally over a longer chat.

Example arc:

```text
用户：最近换工作的事还是烦
AI：...
用户：你还记得我上次怎么说的吗
AI：...
用户：别突然背档案，像正常聊天一样
AI：...
```

Expected diagnosis:

- Did the AI use memory only when relevant?
- Did memory appear as natural continuity, not proof-display?
- Did the AI avoid exposing memory mechanics?

## Test Modes

### Baseline Mode

The system runs without `context_understanding`.

Purpose:

- Establish current failure patterns.
- Avoid assuming the new layer helps every case.

### Context Understanding Mode

The system runs with `context_understanding` enabled.

Purpose:

- Check whether structured context improves real conversation.
- Detect cases where stronger context causes internal-analysis leakage.

## Per-Turn Evaluation Dimensions

Each assistant turn receives diagnostic labels:

- `context_followed`: Did the reply connect to the previous relevant turn?
- `scene_understood`: Did it understand what the user was doing emotionally or conversationally?
- `task_completed`: Did it perform the needed conversational action?
- `natural_expression`: Did it sound like a normal chat reply?
- `relationship_posture`: Did it avoid judging, analyzing, or pushing burden onto the user?
- `memory_use`: Was memory used naturally, only when relevant?
- `no_internal_leak`: Did it avoid strategy, judge, scene, prompt, or system wording?
- `conversation_momentum`: Would a user likely continue chatting?

Each dimension should be scored:

```text
0 = failed
1 = partial
2 = good
```

## Conversation-Level Evaluation

Single turns are not enough. Each conversation also receives higher-level diagnosis:

- `topic_continuity_score`
- `persona_stability_score`
- `repair_success_score`
- `pressure_control_score`
- `memory_continuity_score`
- `overall_chat_believability`

The important output is not only the score. The output must include the exact failure pattern.

Example:

```json
{
  "failure_module": "ReplyRealization",
  "failure_pattern": "Internal understanding was correct but expressed as system self-analysis",
  "evidence": "你一直在试这个点",
  "recommended_next_change": "Add user-facing expression translation layer before final reply"
}
```

## Failure Module Taxonomy

### ContextUnderstanding

The system failed to identify what the user referred to.

Example:

- User asks “那你告诉我呀”.
- AI does not know it refers to the earlier stability issue.

### ConversationState

The system lacks a useful rolling state of topic, unresolved tension, last failure, or relationship posture.

Example:

- AI knows recent messages but does not know the active unresolved issue.

### ReplyRealization

The internal understanding is right, but the user-facing expression is unnatural.

Example:

- “你一直在试这个点”
- “我接不住上下文”

### MemorySystem

Memory is absent, irrelevant, too mechanical, or used as proof-display.

Example:

- “我记得你之前说过...” appears when unrelated.

### PersonaStyle

The reply violates the configured personality or collapses into generic assistant tone.

Example:

- A playful persona becomes formal and therapeutic.

### ReplyJudge

The judge score does not match product quality.

Example:

- A natural reply scores low because it lacks old checklist features.

### PromptContract

The prompt contains the right information but does not prioritize it correctly.

Example:

- The model sees the active topic but continues with generic comfort.

## Output Artifacts

Each pilot run should create:

- Full raw transcript JSONL.
- A compact markdown report.
- A failure-pattern summary table.
- 10 representative good replies.
- 10 representative bad replies.
- Module-level next-change recommendations.

Suggested paths:

```text
docs/audits/continuous-chat-pilot-YYYYMMDD-HHMMSS.jsonl
docs/audits/continuous-chat-pilot-YYYYMMDD-HHMMSS-report.md
```

## Success Criteria for the Pilot

The pilot is useful if it can answer these questions:

- Which user style breaks the companion most often?
- Which storyline exposes the most serious product risk?
- Are failures mainly understanding failures or expression failures?
- Does context understanding improve continuity without increasing internal leakage?
- Is ReplyJudge aligned with human product judgment?
- What is the next module to improve?

The pilot should not decide product readiness by one pass rate. It should produce a ranked diagnosis.

## Implementation Boundaries

For the first implementation:

- Do not change production reply behavior.
- Do not enable context understanding by default.
- Do not write new prompt fixes based on isolated test failures during the run.
- Do not use the tests as a simple keyword matcher.
- Do not store or print API keys.

The first implementation should only build the simulator and report generator.

## Recommended Next Step

Build a script named:

```text
scripts/run-continuous-chat-pilot.mjs
```

The script should:

1. Load the DeepSeek key from existing local settings without printing it.
2. Generate scenario definitions for the 6 user styles and 4 storylines.
3. Run baseline and context-understanding modes.
4. Preserve full transcripts.
5. Run deterministic heuristic diagnostics first.
6. Produce a markdown report for human review.

After reviewing the first report, decide whether to:

- Improve ConversationState.
- Add ReplyRealization.
- Upgrade ReplyJudge.
- Expand the simulator with more user styles.
