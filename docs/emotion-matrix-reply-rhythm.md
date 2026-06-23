# Emotion Matrix Reply Rhythm

## Goal

The companion should not always split replies into a fixed number of messages. Message count is part of emotional expression. The system should decide reply rhythm from the user's current emotion, relationship state, and reply content.

## First Version Scope

This version only controls how many message parts are allowed after the model has produced text. It does not yet schedule proactive messages or change model generation length.

## Inputs

- User text: detects short, tired, lonely, angry, playful, and high-energy signals.
- Relationship state: uses `loneliness`, `safety`, `activity`, `humor`, `attachment`, and `expressiveness`.
- Reply text: preserves model line breaks first, then splits by sentence or punctuation.

## Rhythm Profiles

- `quiet`: 1-2 parts. Used when the user is angry, impatient, or sending very short low-context messages.
- `steady`: 2-3 parts. Default mode for normal conversation.
- `attached`: 3-4 parts. Used when loneliness, attachment, or emotional disclosure is high.
- `playful`: 2-4 parts. Used when humor/activity is high or the user is joking.

## Rules

1. Never split just to hit a fixed count.
2. Preserve intentional model line breaks before punctuation splitting.
3. If the user's emotional load is high, allow more short parts, because it feels like staying with them.
4. If the user is irritated or cold, keep messages fewer and lighter.
5. The output contract remains `reply_parts`; the WeChat bridge keeps sending each part separately.

## Current Implementation Plan

- Add `companion_core/engines/reply_rhythm.py`.
- Move reply splitting policy from `app.py` into this engine.
- Keep `_split_reply_parts` as a wrapper for compatibility with existing tests.
- Add unit tests for lonely, angry, playful, and neutral rhythm choices.

## Future Work

- Pass rhythm profile into the model prompt so the model writes in the intended cadence.
- Add delay policy per part, for example slower for care mode and faster for playful mode.
- Add proactive message rhythm using the same matrix.
- Store rhythm outcomes for analytics and tuning.
