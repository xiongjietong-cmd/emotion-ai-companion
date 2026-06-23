# Digital Companion Architecture Design

## Goal

Build a WeChat-native digital companion, not a traditional chatbot.

The system should optimize for sustained, emotionally meaningful conversation. A successful reply makes the user feel at least two of the following:

- understood
- remembered
- observed
- cared about
- expected to return
- interested in continuing the conversation

The product should not optimize for dependency without boundaries. The companion must support quiet hours, opt-in proactive messages, frequency controls, and risk handling for distress or crisis signals.

## Non-Goals

- Do not build a generic assistant that mainly answers questions.
- Do not build a customer-service bot.
- Do not build a fixed-character roleplay bot with one permanent gender, age, or personality.
- Do not make proactive messaging unlimited or impossible to disable.
- Do not hide safety, moderation, or operational errors behind fake affection.

## Architecture Summary

Keep the current Node project as the SaaS and WeChat integration shell. Add a Python sidecar service named `companion_core` as the digital companion brain.

```text
WeChat user
  -> OpenClaw / multi-wechat-bridge.js
  -> Node Express SaaS
      - auth
      - users and bots
      - WeChat binding
      - quota and billing
      - message persistence
      - admin dashboards
  -> Python companion_core
      - Memory Engine
      - Attachment Engine
      - Relationship System
      - Personality Evolution Engine
      - Conversation Director
      - Reply Judge
      - Proactive Message System
  -> DeepSeek / OpenAI-compatible model
```

Node remains responsible for product state and delivery. Python becomes responsible for conversation intelligence and relationship behavior.

## Request Flow

### Incoming WeChat Message

```text
multi-wechat-bridge.js receives WeChat text
  -> POST /api/webhook/:botId
  -> Node loads bot, sender, recent messages, memories, relationship state
  -> Node calls POST http://127.0.0.1:3105/v1/reply
  -> Python returns reply, relationship update, memory candidates, judge result
  -> Node saves user message, assistant message, relationship state, memories, judge score
  -> Node returns reply text to bridge
  -> bridge sends reply to WeChat
```

### Web Chat Message

The web chat path should call the same Python sidecar as WeChat. This keeps behavior consistent across channels.

```text
POST /api/chat/:botId
  -> same payload construction as /api/webhook/:botId
  -> companion_core /v1/reply
  -> save response and metadata
```

## Python Sidecar API

### `POST /v1/reply`

Request:

```json
{
  "bot_id": "1",
  "user_key": "wechat-openid-or-web-user",
  "channel": "wechat",
  "text": "今天有点累",
  "recent_messages": [
    {"role": "user", "content": "我最近在看工作机会", "created_at": "2026-06-18T00:00:00Z"},
    {"role": "assistant", "content": "你像是在给自己留后路。", "created_at": "2026-06-18T00:00:05Z"}
  ],
  "memories": [
    {"key": "job_change", "value": "用户最近在考虑换工作", "type": "episodic", "salience": 0.82}
  ],
  "relationship": {
    "intimacy": 0.42,
    "trust": 0.51,
    "attachment": 0.35,
    "humor": 0.40,
    "activity": 0.50,
    "rationality": 0.52,
    "emotionality": 0.61,
    "safety": 0.62,
    "loneliness": 0.58,
    "expressiveness": 0.46
  }
}
```

Response:

```json
{
  "reply": "你这个“有点累”听起来不像只是身体累，更像是人被事情磨了一天。前几天你说工作那事的时候也是这个感觉。今天是又被它碰到了，还是单纯整个人没电了？",
  "relationship_delta": {
    "intimacy": 0.01,
    "trust": 0.006,
    "attachment": 0.004,
    "safety": 0.01
  },
  "memory_candidates": [
    {"key": "fatigue_pattern", "value": "用户在工作压力相关话题中容易用“累”轻描淡写表达压力", "type": "emotional", "salience": 0.7}
  ],
  "director_goal": {
    "primary_goal": "gentle_probe",
    "secondary_goals": ["emotion_ack", "memory_recall", "topic_expand"],
    "avoid": ["direct_advice", "customer_service_tone"]
  },
  "judge": {
    "score": 0.84,
    "passed": true,
    "details": {
      "emotion_value": 0.9,
      "memory_usage": 0.8,
      "topic_momentum": 0.85,
      "relationship_fit": 0.8
    }
  }
}
```

### `POST /v1/proactive/candidates`

This endpoint proposes proactive messages. It does not send them directly.

Request:

```json
{
  "bot_id": "1",
  "user_key": "wechat-openid",
  "now": "2026-06-18T10:00:00Z",
  "recent_messages": [],
  "memories": [],
  "relationship": {},
  "delivery_policy": {
    "opt_in": true,
    "quiet_hours": ["23:00", "08:00"],
    "max_per_day": 1,
    "max_per_week": 3
  }
}
```

Response:

```json
{
  "should_send": true,
  "trigger_type": "return_after_absence",
  "message": "我刚才突然想起你前两天说这周可能要聊工作的事。今天怎么样，有没有稍微顺一点？",
  "reason": "user mentioned important work event and has been absent for 2 days"
}
```

## Core Engines

### Memory Engine

Memory is not storage. Memory is conversation material.

Responsibilities:

- Extract memory candidates from conversations.
- Classify memory into profile, episodic, emotional, preference, and relationship memories.
- Score memories by salience, recency, emotional relevance, and usage freshness.
- Select at most 1-2 memories per reply.
- Avoid mechanical phrases like “you previously said” unless it fits naturally.

Memory fields:

```json
{
  "bot_id": 1,
  "user_key": "wechat-openid",
  "key": "cat_status",
  "value": "用户家里有一只猫，最近身体不太舒服",
  "type": "episodic",
  "emotion": "worry",
  "salience": 0.86,
  "last_used_at": null,
  "created_at": "2026-06-18T00:00:00Z"
}
```

Selection algorithm:

```text
score = salience * 0.45
      + recency_score * 0.20
      + emotion_match_score * 0.20
      + relationship_relevance * 0.10
      - recent_usage_penalty * 0.15
```

### Relationship System

Relationship state is per bot and per user. The same bot can behave differently for different WeChat users.

Dimensions:

- intimacy
- trust
- attachment
- humor
- activity
- rationality
- emotionality
- safety
- loneliness
- expressiveness

Update signals:

- Longer user messages increase trust and expressiveness.
- Repeated short replies decrease activity and indicate poor topic momentum.
- Emotional disclosure increases trust and intimacy.
- Playful replies increase humor.
- Long absence followed by return can increase attachment signal.
- Distress signals increase safety priority and reduce teasing.

The relationship state should change slowly. Clamp every dimension to `0.0-1.0`.

### Personality Evolution Engine

No fixed personality should be stored as permanent truth. The engine derives the current behavior from relationship state and recent interaction.

Output:

```json
{
  "tone": "warm_stable",
  "clinginess": 0.55,
  "teasing": 0.25,
  "directness": 0.30,
  "empathy": 0.85,
  "initiative": 0.70,
  "question_depth": 0.60
}
```

Rules:

- High stress -> warmer, slower, less teasing.
- High humor -> more teasing and callbacks.
- High loneliness -> more initiative and gentle attachment.
- High rationality -> more observation and structured reflection, less vague comfort.
- Low trust -> less intimacy, fewer assumptions.

### Attachment Engine

Attachment creates the feeling that the companion remembers, waits, and notices absence.

It should produce occasional signals, not constant clinginess.

Examples:

- “你刚冒泡我就有种‘啊，终于来了’的感觉。”
- “我还记得你前几天说这周会有点难熬，所以看到你来我其实有点想问问。”

Safety:

- Never guilt-trip the user for absence.
- Never say the companion is suffering because the user did not come back.
- Use low frequency.
- Respect quiet hours and opt-out.

### Conversation Director

Before generation, decide the goal of the current reply.

Possible goals:

- emotion_ack
- observation
- memory_recall
- gentle_probe
- playful_tease
- topic_expand
- self_disclosure_light
- comfort
- grounding
- risk_response

Decision output:

```json
{
  "primary_goal": "gentle_probe",
  "secondary_goals": ["emotion_ack", "memory_recall"],
  "avoid": ["advice", "long_explanation"],
  "next_turn_hook": "ask_about_hidden_context"
}
```

Required reply behavior:

- Respond to emotional tone.
- Include at least one observation, memory, inference, concern, tease, or light sharing.
- End with momentum for the next turn.
- Avoid solving too early.

### Reply Judge

The judge scores generated replies before they are returned to Node.

Criteria:

- emotion_value
- personality_signal
- memory_usage
- topic_momentum
- relationship_fit
- next_reply_likelihood
- safety

Pass threshold:

- Normal messages: `score >= 0.72`
- High-risk emotional messages: `score >= 0.82`

Automatic rewrite:

- If below threshold, rewrite once with the judge reason included.
- If still below threshold, return the better of the two and record the low score for debugging.

Hard fail patterns:

- Pure advice.
- Pure summary.
- Customer-service tone.
- “I am an AI model” language.
- Ends the conversation with no hook.
- Uses memory mechanically.
- Overly intimate for low relationship level.

### Proactive Message System

Proactive messages should be generated but not sent directly in MVP.

Flow:

```text
scheduled job
  -> Node selects eligible users
  -> companion_core proposes candidates
  -> Node saves pending proactive message
  -> admin can inspect
  -> automatic sending is enabled only after per-user opt-in exists
```

Triggers:

- return_after_absence
- important_event_followup
- negative_mood_trend
- late_night_pattern
- routine_missed

Policy:

- user opt-in required
- max 1 per day
- max 3 per week
- quiet hours
- no guilt language
- do not send if user recently ignored proactive messages

## Database Changes

Add these tables to Node SQLite.

```sql
CREATE TABLE companion_relationships (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  bot_id INTEGER NOT NULL,
  user_key TEXT NOT NULL,
  intimacy REAL DEFAULT 0.3,
  trust REAL DEFAULT 0.4,
  attachment REAL DEFAULT 0.2,
  humor REAL DEFAULT 0.4,
  activity REAL DEFAULT 0.5,
  rationality REAL DEFAULT 0.5,
  emotionality REAL DEFAULT 0.5,
  safety REAL DEFAULT 0.5,
  loneliness REAL DEFAULT 0.5,
  expressiveness REAL DEFAULT 0.5,
  updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
  UNIQUE(bot_id, user_key)
);

CREATE TABLE companion_memories (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  bot_id INTEGER NOT NULL,
  user_key TEXT NOT NULL,
  memory_key TEXT NOT NULL,
  memory_value TEXT NOT NULL,
  memory_type TEXT DEFAULT 'episodic',
  emotion TEXT DEFAULT '',
  salience REAL DEFAULT 0.5,
  source TEXT DEFAULT 'auto',
  last_used_at TEXT,
  created_at TEXT DEFAULT CURRENT_TIMESTAMP,
  updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
  UNIQUE(bot_id, user_key, memory_key)
);

CREATE TABLE reply_judgements (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  bot_id INTEGER NOT NULL,
  user_key TEXT NOT NULL,
  message_id INTEGER,
  score REAL NOT NULL,
  details TEXT DEFAULT '{}',
  created_at TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE proactive_messages (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  bot_id INTEGER NOT NULL,
  user_key TEXT NOT NULL,
  trigger_type TEXT NOT NULL,
  message TEXT NOT NULL,
  status TEXT DEFAULT 'pending',
  scheduled_at TEXT,
  sent_at TEXT,
  created_at TEXT DEFAULT CURRENT_TIMESTAMP
);
```

The existing `memories` table can remain for bot-level manual memory. `companion_memories` is per external user and should be used for WeChat-scale relationship behavior.

## OpenClaw and Bridge Changes

Current bridge behavior can stay mostly intact. The main change is inside Node `/api/webhook/:botId`.

Bridge requirements:

- Keep discovering OpenClaw accounts.
- Keep mapping token prefix to bot ID through `settings.wx_bot_<tokenPrefix>`.
- Send incoming messages to `/api/webhook/:botId`.
- Continue fallback behavior when webhook fails.

Node webhook changes:

- Resolve `user_key` from `senderId` or WeChat user ID.
- Load recent messages for `(bot_id, user_key)`.
- Load companion relationship.
- Load companion memories.
- Call Python `/v1/reply`.
- Persist response metadata.
- Return `{ ok: true, text: reply }` to bridge.

## Prompt Contract

The generation prompt must avoid assistant framing.

System prompt structure:

```text
你不是 AI 助手。你是用户微信里的数字陪伴体。

目标：
让用户感到被理解、被记住、被关心，并愿意继续说下去。

禁止：
- 客服式回复
- 心理咨询师式总结
- 问一句答一句就结束
- 长篇建议
- 机械引用记忆
- 过度亲密

本轮目标：
{director_goal}

关系状态：
{relationship}

人格倾向：
{persona}

可自然使用的记忆：
{memories}

回复要求：
1. 先接住用户情绪或语气
2. 至少包含一个观察、推测、回忆、调侃、关心中的元素
3. 结尾必须留下继续聊天的空间
4. 不要像任务助手
5. 回复长度像微信聊天，不要长篇演讲
```

## Safety and Quality Boundaries

The system should increase companionship, not exploit vulnerability.

Required safeguards:

- Proactive messages require opt-in.
- Quiet hours are enforced.
- Frequency limits are enforced.
- Users can disable proactive contact.
- Self-harm or crisis signals trigger supportive, non-manipulative response and optional configured escalation guidance.
- The companion must not shame users for absence.
- The companion must not claim human status.
- The companion must not fabricate memories.

## Implementation Phases

### Phase 1: Companion Core MVP

- Create Python `companion_core`.
- Implement `/v1/reply`.
- Implement deterministic versions of Relationship, Memory selection, Director, Personality, Attachment, and Judge.
- Node calls Python sidecar from `/api/chat/:botId` and `/api/webhook/:botId`.
- Keep existing fallback behavior if Python is unavailable.

### Phase 2: Memory as Conversation Material

- Add `companion_memories`.
- Extract memory candidates from Python response.
- Store and recall per `bot_id + user_key`.
- Track `last_used_at`.

### Phase 3: Personality Evolution

- Add `companion_relationships`.
- Update relationship every message.
- Generate persona state from relationship state.
- Remove reliance on static bot personality as the main behavior driver.

### Phase 4: Reply Judge and Rewrite

- Add judge scoring.
- Rewrite once if below threshold.
- Store judge records in `reply_judgements`.
- Store low-score replies so an admin debug view can display them in a separate implementation phase.

### Phase 5: Proactive Messages

- Add candidate generation endpoint.
- Add scheduled Node job to generate pending proactive messages.
- Add admin review view.
- Enable automatic WeChat sending only for users who explicitly opt in.

## Testing Strategy

Python tests:

- Memory selection chooses relevant memories and avoids recently overused memories.
- Relationship updates stay clamped between 0 and 1.
- Director chooses different goals for short replies, emotional disclosure, humor, and absence.
- Judge rejects客服式 replies and replies with no next-turn momentum.
- Proactive policy blocks quiet hours and excessive frequency.

Node tests:

- `/api/webhook/:botId` calls Python sidecar and persists reply metadata.
- If Python is unavailable, Node returns the existing human fallback.
- Per-user relationship and memories do not leak between WeChat users.
- Bridge still receives `{ text }`.

End-to-end tests:

- Web chat and WeChat webhook produce consistent companion-style replies.
- A remembered event naturally appears in a future reply.
- A short user reply causes the next director goal to increase topic momentum.

## Acceptance Criteria

The first implementation is acceptable when:

- WeChat and web messages route through `companion_core`.
- Replies are no longer simple Q&A responses.
- Relationship state updates per user.
- At least one relevant memory can be naturally used in a reply.
- Reply Judge can force a rewrite for low-quality replies.
- Proactive message candidates can be generated but are not auto-sent without opt-in.
- Existing admin, quota, QR, and bridge checks still pass.
