# Open-Source-Inspired Companion Redesign

Date: 2026-06-23

## 1. Decision

The current companion direction should stop patching isolated reply failures and redesign the companion brain around open-source-proven structures:

- persona cards for user-created companion individuality;
- dynamic lore/memory injection for relevant context;
- short-term conversation state for current scene continuity;
- long-term scoped memory for user and companion personalization;
- dialogue-flow style evaluation for multi-turn behavior;
- expression-function judging for whether the reply works in context.

This does not mean copying an open-source product. The goal is to learn their architecture boundaries and adapt them to a WeChat-native emotional companion SaaS.

## 2. Why The Current Direction Is Failing

Recent live WeChat tests show the same underlying issue in different forms:

- The model sees recent text but does not know what the latest user move is doing. A correction, a challenge, a tease, and a new topic can all look like short messages.
- The current emotional matrix often guides wording too directly. That creates rigid, mechanical replies instead of better internal understanding.
- User-created individuality exists in settings, but the scheduler can flatten many scenes back into a generic warm companion.
- Memory is stored, but it is not consistently separated into current-scene facts, long-term memories, guesses waiting for confirmation, and relationship state.
- Evaluation still finds symptoms after the fact. It does not yet test whether the system understood the conversational move before generating.

The product problem is not "make the reply warmer." The product problem is: the companion needs a stable inner model of the conversation before it speaks.

## 3. Open-Source Lessons To Absorb

### 3.1 SillyTavern: Character Cards And World Info

Useful ideas:

- Character cards separate stable identity/personality from chat history.
- World Info / Lorebooks dynamically insert only relevant information into the prompt.
- User personas let the system know who the user is in the current chat.
- Macros and prompt sections make prompt composition explicit instead of one giant prompt blob.

What we should not copy:

- We should not become a roleplay-only frontend.
- We should not rely on huge static character prompts.
- We should not let user persona text override safety, account isolation, or verified memory scope.

Adaptation:

- Build a companion card per bot.
- Build a user persona profile per user+bot relationship.
- Build a memory/lore selector that inserts only relevant anchors into the model context.

References:

- https://docs.sillytavern.app/usage/core-concepts/characterdesign/
- https://docs.sillytavern.app/usage/core-concepts/worldinfo/
- https://docs.sillytavern.app/usage/core-concepts/personas/

### 3.2 Mem0: Layered Memory

Useful ideas:

- Memory must be scoped and layered, not just stored as raw chat logs.
- Different memory types should be retrieved at different times.
- Long-term personalization should not require sending the whole history.

What we should not copy yet:

- We should not introduce an external memory service before the current local memory contract is stable.
- We should not use vector retrieval as a shortcut for understanding the current turn.

Adaptation:

- Keep SQLite for now.
- Redesign the schema conceptually into memory layers:
  - `scene_state`: current changeable facts, active topic, pending guess, unresolved repair.
  - `episodic_memory`: events the user shared.
  - `semantic_profile`: stable preferences, traits, dislikes, style.
  - `relationship_memory`: trust, intimacy, friction, repair history.
  - `companion_card`: user-authored identity and speaking style for that bot.

References:

- https://github.com/mem0ai/mem0
- https://docs.mem0.ai/core-concepts/memory-types

### 3.3 LangGraph: State, Checkpoints, Short-Term And Long-Term Memory

Useful ideas:

- Short-term memory belongs to the current thread/run state.
- Long-term memory stores user-specific or application-level data across sessions.
- A conversation can be modeled as state transitions rather than one prompt call.

What we should not copy yet:

- We should not introduce LangGraph as a dependency immediately.
- We should not turn the companion into a complicated agent workflow before the state model is clear.

Adaptation:

- Implement our own lightweight state object first.
- If the state contract stabilizes, we can later evaluate LangGraph-like orchestration.

References:

- https://docs.langchain.com/oss/python/langgraph/add-memory
- https://docs.langchain.com/oss/python/langchain/short-term-memory

### 3.4 Rasa: Dialogue Stories And Conversational State Tests

Useful ideas:

- Multi-turn stories are better than isolated prompt tests.
- Dialogue evaluation should care about conversation paths, not just single outputs.
- Slots/entities are a useful mental model for facts the assistant believes are currently active.

What we should not copy:

- We should not build a classic intent-response chatbot.
- We should not replace LLM generation with rigid story flows.

Adaptation:

- Use Rasa-like stories only for tests and diagnostics.
- Keep generation open, but evaluate whether the assistant followed the right conversational move.

References:

- https://rasa.com/docs/rasa/stories/
- https://rasa.com/docs/rasa/

## 4. New Core Architecture

The redesigned companion brain should have five internal layers.

```text
User message
  -> Interaction Frame Engine
  -> Context Pack Builder
  -> Companion Card Compiler
  -> Reply Realization
  -> Quality Judge + Memory Updater
  -> Reply parts to Web / WeChat
```

### 4.1 Interaction Frame Engine

Purpose:

Understand what is happening in the current turn before generating text.

Inputs:

- latest user message;
- previous 6-12 messages;
- last assistant move;
- scoped scene state;
- selected user+bot memories;
- companion personality settings.

Output:

```json
{
  "user_move": "correction | challenge | tease | answer | share | probe | silence | new_topic",
  "relation_to_previous": "answers_question | rejects_reply | continues_joke | tests_memory | shifts_topic | unclear",
  "active_topic": "short natural topic label",
  "known_scene_facts": [
    {
      "key": "current_activity",
      "value": "打游戏",
      "source": "user_stated",
      "confidence": 0.9,
      "changeable": true
    }
  ],
  "pending_assistant_guesses": [
    {
      "guess": "用户可能输得挺惨",
      "status": "unconfirmed",
      "risk": "unsupported"
    }
  ],
  "user_reaction": "accepts | confused | annoyed | plays_along | unknown",
  "repair_debt": "what the assistant should repair or avoid",
  "generation_direction": "internal direction, not wording"
}
```

Key rule:

This layer does not write the final reply. It only gives the model a better mental frame.

### 4.2 Context Pack Builder

Purpose:

Select the right context for this turn without dumping everything into the prompt.

Context priority:

1. Active scene state.
2. Previous assistant move and pending guesses.
3. User-authored companion card.
4. Relevant user+bot relationship memory.
5. Relevant long-term user facts.
6. Recent raw messages.

Important behavior:

- Current-scene facts outrank old memories.
- User corrections update scene state immediately.
- Hypothetical examples must not become memory.
- Memories from another user or another bot must never be selected.

### 4.3 Companion Card Compiler

Purpose:

Turn user-side personalization into a living companion identity.

Card sections:

- public name;
- relationship position;
- user-written personality;
- speaking style examples;
- allowed intimacy / roleplay preference;
- disliked expressions / blocked terms;
- virtual-life texture allowance;
- reality-boundary preference;
- active evolution notes.

The compiler should preserve individuality. It should not reduce every bot to warm, gentle, low-pressure chat.

### 4.4 Reply Realization

Purpose:

Convert the internal frame into a natural reply without exposing the frame.

It should avoid:

- saying "I detected that...";
- saying "my strategy is...";
- saying "I remember you just said..." as a fixed proof phrase;
- turning every repair into a meta-apology;
- unsupported scene invention.

It should allow:

- natural teasing;
- light virtual texture;
- roleplay-style comfort when the user prefers it;
- personality-specific phrasing;
- multi-part WeChat replies when rhythm calls for it.

### 4.5 Quality Judge And Memory Updater

Purpose:

Evaluate the reply as a product experience, then update memory/state.

Judge dimensions:

- Did the reply follow the active scene?
- Did it understand the user's move?
- Did it preserve the companion's individuality?
- Did it avoid unsupported assumptions?
- Did it use memory naturally if relevant?
- Did it avoid internal-process leakage?
- Would the user likely continue?

Memory update rules:

- User-stated facts can update memory.
- Assistant guesses cannot update memory until user confirms or plays along clearly.
- User corrections must update scene state immediately.
- User criticism creates repair debt.
- Per-user and per-bot isolation is mandatory.

## 5. First Implementation Slice

The first slice should not rebuild everything. It should target the live failure class.

### Goal

Fix the foundation for context continuity:

- corrections;
- bare question marks;
- memory probes;
- user current activity;
- unsupported assistant guesses;
- playful confirmation after a guess.

### Files likely involved

- `companion_core/engines/interaction_frame.py` new module.
- `companion_core/engines/prompt_composer.py` integrate frame summary.
- `companion_core/app.py` call frame engine before generation.
- `companion_core/tests/test_interaction_frame.py` deterministic unit tests.
- `companion_core/tests/test_interaction_frame_integration.py` production-path tests.
- `docs/pitfalls.md` add lessons from this redesign after implementation evidence.

### First failing scenarios

```text
用户：在干嘛
AI：刚在发呆。你呢
用户：打游戏呢
AI：...
用户：我在打游戏我说
Expected: treat as correction/emphasis, not a new generic topic.
```

```text
AI：听语气输得挺惨。
用户：？
Expected: treat as confusion/pushback about the previous guess, not presence check.
```

```text
用户：我在上课
...
用户：你知道我现在在干什么吗
Expected: use the current activity clue internally, without forcing a fixed phrase.
```

```text
AI：你是不是也想放空一下，不说也行。
用户：感觉你很不耐烦
Expected: treat as style feedback and repair the posture, not ask the user to explain more.
```

## 6. Testing Plan

### Unit tests

Test the frame engine without DeepSeek:

- classify correction;
- classify pushback question mark;
- carry current activity;
- keep assistant guesses unconfirmed;
- mark repair debt after user criticism;
- distinguish playful confirmation from generic teasing.

### Integration tests

Run through the production companion core path:

- frame summary reaches prompt composer;
- prompt does not contain fixed required wording;
- scoped memory uses user+bot keys;
- reply parts remain available for WeChat splitting.

### Live DeepSeek tests

Use continuous human-style chats, not isolated questions:

- short minimal user;
- playful teasing user;
- rational critical user;
- low-mood user;
- rambling daily user;
- memory-probing user.

The result should be a diagnosis report, not only pass/fail.

## 7. Non-Goals

Not in this first redesign slice:

- full proactive messaging;
- payment;
- voice;
- vector database migration;
- full LangGraph adoption;
- rewriting the frontend personality editor;
- changing OpenClaw binding behavior;
- replacing DeepSeek.

## 8. Success Criteria

The redesign is working when:

- the companion no longer treats every short message as a new topic;
- it can tell whether a user is correcting, questioning, teasing, or continuing;
- it uses current-scene facts as thinking context without forced phrases;
- it stops turning unsupported guesses into facts;
- user-created companion style survives normal, conflict, roleplay, and memory scenes;
- tests produce actionable module-level diagnoses instead of vague "bad reply" labels.

## 9. Recommended Next Step

After this document is approved:

1. Write an implementation plan for `Interaction Frame Engine V1`.
2. Add deterministic failing tests from the latest WeChat transcript.
3. Implement the frame engine without changing final reply style yet.
4. Connect the frame digest into prompt composition as internal guidance.
5. Run unit, integration, and live DeepSeek continuous-chat tests.
6. Only after tests show the frame improves continuity, tune reply realization.

This keeps the product direction open. The system becomes easier to change later because future features can attach to the frame:

- richer persona cards;
- roleplay preference;
- proactive message timing;
- relationship evolution;
- memory retrieval;
- quality evaluation.

