# Digital Companion Phase 1 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Route web chat and WeChat messages through a runnable Python `companion_core` sidecar that behaves like a digital companion, while preserving the existing Node fallback path if the sidecar is unavailable.

**Architecture:** Keep Node/Express as the SaaS and WeChat delivery layer. Add Python `companion_core` on `127.0.0.1:3105` for relationship, memory selection, persona evolution, conversation direction, reply judging, and final reply generation. Node loads/persists product state and calls Python for companion behavior.

**Tech Stack:** Node.js ESM, Express, better-sqlite3, Python 3, FastAPI, Uvicorn, unittest, DeepSeek through the existing OpenAI-compatible Node/Python model settings.

---

## Scope

Phase 1 includes:

- Python sidecar scaffold and `/v1/reply`.
- Deterministic engine implementations for tests.
- Node database support for per-user companion relationship, companion memories, and reply judgement records.
- Node client for calling the Python sidecar.
- Node `/api/chat/:botId` and `/api/webhook/:botId` integration.
- Fallback to existing Node reply path if Python is unavailable.
- Local scripts to test the complete path.

Phase 1 excludes:

- Automatic proactive WeChat sending.
- Admin UI for low-score replies.
- Full production deployment.
- Sophisticated vector search.

## File Structure

Create:

- `companion_core/requirements.txt` - Python runtime dependencies.
- `companion_core/app.py` - FastAPI app and `/v1/reply`.
- `companion_core/models.py` - Pydantic request/response models.
- `companion_core/model_client.py` - model generation wrapper with deterministic test mode.
- `companion_core/engines/memory.py` - memory selection and candidate extraction.
- `companion_core/engines/relationship.py` - relationship update rules.
- `companion_core/engines/personality.py` - persona state derivation.
- `companion_core/engines/attachment.py` - attachment signal builder.
- `companion_core/engines/director.py` - conversation goal selection.
- `companion_core/engines/judge.py` - reply scoring and rewrite decision.
- `companion_core/tests/test_engines.py` - engine unit tests.
- `companion_core/tests/test_api.py` - API behavior tests.
- `server/companion-client.js` - Node client for the Python sidecar.
- `scripts/check-companion-core.mjs` - starts Python sidecar and verifies `/v1/reply`.
- `scripts/check-companion-db.mjs` - verifies DB schema/functions.
- `scripts/check-companion-integration.mjs` - verifies Node chat/webhook route through sidecar and fallback.

Modify:

- `server/database.js` - add companion tables and helper functions.
- `server/index.js` - route chat/webhook through sidecar with fallback.
- `daemon.js` - start Python sidecar with Node services.
- `package.json` - add check/start scripts.
- `PROJECT_STATUS.md` - document Phase 1 state.

Do not modify:

- `multi-wechat-bridge.js` except if an integration test proves bridge response shape changed.
- `openclaw-skill/scripts/reply.mjs` in Phase 1.

## Task 1: Python Sidecar Scaffold

**Files:**

- Create: `companion_core/requirements.txt`
- Create: `companion_core/__init__.py`
- Create: `companion_core/engines/__init__.py`
- Create: `companion_core/models.py`
- Create: `companion_core/app.py`
- Create: `companion_core/tests/test_api.py`

- [ ] **Step 1: Write the failing API test**

Create `companion_core/tests/test_api.py`:

```python
import unittest
from fastapi.testclient import TestClient

from companion_core.app import app


class CompanionApiTest(unittest.TestCase):
    def test_reply_endpoint_returns_companion_contract(self):
        client = TestClient(app)
        response = client.post("/v1/reply", json={
            "bot_id": "1",
            "user_key": "web-user",
            "channel": "web",
            "text": "今天有点累",
            "recent_messages": [],
            "memories": [{"key": "job_change", "value": "用户最近在考虑换工作", "type": "episodic", "salience": 0.8}],
            "relationship": {}
        })
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertTrue(body["reply"])
        self.assertIn("relationship_delta", body)
        self.assertIn("memory_candidates", body)
        self.assertIn("director_goal", body)
        self.assertIn("judge", body)
        self.assertGreaterEqual(body["judge"]["score"], 0)
        self.assertLessEqual(body["judge"]["score"], 1)
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```powershell
python -m unittest companion_core.tests.test_api
```

Expected: fail because `companion_core.app` does not exist.

- [ ] **Step 3: Create dependencies**

Create `companion_core/requirements.txt`:

```text
fastapi==0.115.6
uvicorn==0.32.1
pydantic==2.10.4
httpx==0.28.1
```

- [ ] **Step 4: Create request/response models**

Create `companion_core/models.py`:

```python
from pydantic import BaseModel, Field


class MessageItem(BaseModel):
    role: str
    content: str
    created_at: str | None = None


class MemoryItem(BaseModel):
    key: str
    value: str
    type: str = "episodic"
    emotion: str = ""
    salience: float = 0.5
    last_used_at: str | None = None


class ReplyRequest(BaseModel):
    bot_id: str
    user_key: str
    channel: str = "web"
    text: str
    recent_messages: list[MessageItem] = Field(default_factory=list)
    memories: list[MemoryItem] = Field(default_factory=list)
    relationship: dict = Field(default_factory=dict)


class ReplyResponse(BaseModel):
    reply: str
    relationship_delta: dict
    memory_candidates: list[dict]
    director_goal: dict
    judge: dict
```

- [ ] **Step 5: Create minimal app**

Create `companion_core/app.py` with `/health` and `/v1/reply`. The first implementation can return a deterministic reply assembled from request text and selected memory. It must not call the model yet.

- [ ] **Step 6: Run test to verify it passes**

Run:

```powershell
python -m unittest companion_core.tests.test_api
```

Expected: pass.

## Task 2: Deterministic Engine Unit Tests

**Files:**

- Create: `companion_core/tests/test_engines.py`
- Create: `companion_core/engines/memory.py`
- Create: `companion_core/engines/relationship.py`
- Create: `companion_core/engines/personality.py`
- Create: `companion_core/engines/attachment.py`
- Create: `companion_core/engines/director.py`
- Create: `companion_core/engines/judge.py`

- [ ] **Step 1: Write failing engine tests**

Create tests covering:

```python
import unittest

from companion_core.engines.memory import select_memories, extract_memory_candidates
from companion_core.engines.relationship import update_relationship, default_relationship
from companion_core.engines.personality import evolve_personality
from companion_core.engines.director import decide_conversation_goal
from companion_core.engines.judge import judge_reply


class EngineTest(unittest.TestCase):
    def test_memory_selects_relevant_high_salience_memory(self):
        memories = [
            {"key": "cat", "value": "用户家里有只猫", "type": "profile", "salience": 0.9},
            {"key": "food", "value": "用户喜欢辣", "type": "preference", "salience": 0.3},
        ]
        selected = select_memories("你家猫最近怎么样", memories, default_relationship())
        self.assertEqual(selected[0]["key"], "cat")

    def test_relationship_updates_from_emotional_message(self):
        before = default_relationship()
        after = update_relationship(before, "今天真的有点撑不住", [])
        self.assertGreater(after["safety"], before["safety"])
        self.assertGreater(after["trust"], before["trust"])

    def test_personality_changes_for_lonely_user(self):
        rel = {**default_relationship(), "loneliness": 0.85}
        persona = evolve_personality(rel, [])
        self.assertGreater(persona["initiative"], 0.6)
        self.assertGreater(persona["clinginess"], 0.4)

    def test_director_avoids_advice_for_tired_message(self):
        goal = decide_conversation_goal("今天有点累", default_relationship(), [], {})
        self.assertIn(goal["primary_goal"], ["gentle_probe", "emotion_ack"])
        self.assertIn("direct_advice", goal["avoid"])

    def test_judge_rejects_dead_end_reply(self):
        result = judge_reply("今天有点累", "早点休息。", default_relationship(), [], {})
        self.assertFalse(result["passed"])
        self.assertLess(result["score"], 0.72)
```

- [ ] **Step 2: Run tests to verify failure**

Run:

```powershell
python -m unittest companion_core.tests.test_engines
```

Expected: fail because engine modules do not exist.

- [ ] **Step 3: Implement deterministic engines**

Rules:

- `default_relationship()` returns all required relationship dimensions.
- `update_relationship()` clamps values to `0.0-1.0`.
- `select_memories()` scores memory by simple keyword overlap plus salience.
- `evolve_personality()` derives `tone`, `clinginess`, `teasing`, `directness`, `empathy`, `initiative`, `question_depth`.
- `decide_conversation_goal()` returns `primary_goal`, `secondary_goals`, `avoid`, `next_turn_hook`.
- `judge_reply()` rejects short dead-end replies and customer-service style replies.

- [ ] **Step 4: Run tests to verify pass**

Run:

```powershell
python -m unittest companion_core.tests.test_engines
```

Expected: pass.

## Task 3: Compose `/v1/reply` from Engines

**Files:**

- Modify: `companion_core/app.py`
- Create: `companion_core/model_client.py`
- Modify: `companion_core/tests/test_api.py`

- [ ] **Step 1: Extend API test for memory use and judge**

Add assertions:

```python
self.assertIn(body["director_goal"]["primary_goal"], ["gentle_probe", "emotion_ack", "memory_recall"])
self.assertTrue(body["judge"]["passed"])
self.assertGreaterEqual(body["judge"]["score"], 0.72)
```

- [ ] **Step 2: Implement deterministic model client**

Create `model_client.py`:

```python
async def generate_reply(text, memories, relationship, persona, attachment, goal, rewrite=False):
    memory_hint = ""
    if memories:
        memory_hint = f"我还记得{memories[0]['value']}。"
    if "累" in text or "撑不住" in text:
        return f"{memory_hint}你这句听起来不像只是普通的累，更像是被事情磨了一下。是今天发生了什么，还是那种说不上来的没电？"
    return f"{memory_hint}我听见你这句话里有点想继续说的东西。你刚刚想到的第一件事是什么？"
```

- [ ] **Step 3: Compose app from engines**

`/v1/reply` must:

1. update relationship
2. select memories
3. evolve persona
4. build attachment signal
5. decide director goal
6. generate reply
7. judge reply
8. rewrite once if judge fails
9. extract memory candidates
10. return `ReplyResponse`

- [ ] **Step 4: Run Python tests**

Run:

```powershell
python -m unittest discover companion_core/tests
```

Expected: all Python tests pass.

## Task 4: Node Companion Database Support

**Files:**

- Modify: `server/database.js`
- Create: `scripts/check-companion-db.mjs`

- [ ] **Step 1: Write failing DB check**

Create `scripts/check-companion-db.mjs`:

```js
import assert from "node:assert/strict";
import {
  initDatabase,
  getDb,
  getCompanionRelationship,
  updateCompanionRelationship,
  setCompanionMemory,
  getCompanionMemories,
  recordReplyJudgement,
} from "../server/database.js";

initDatabase();

const botId = 1;
const userKey = "companion-db-test";

const initial = getCompanionRelationship(botId, userKey);
assert.equal(initial.bot_id, botId);
assert.equal(initial.user_key, userKey);

updateCompanionRelationship(botId, userKey, { intimacy: 0.2, trust: 0.1 });
const updated = getCompanionRelationship(botId, userKey);
assert.ok(updated.intimacy > initial.intimacy);
assert.ok(updated.trust > initial.trust);

setCompanionMemory(botId, userKey, {
  key: "job_change",
  value: "用户最近在考虑换工作",
  type: "episodic",
  emotion: "stress",
  salience: 0.8,
});
const memories = getCompanionMemories(botId, userKey);
assert.ok(memories.some((m) => m.key === "job_change"));

recordReplyJudgement(botId, userKey, null, {
  score: 0.82,
  details: { topic_momentum: 0.8 },
});
const judgement = getDb().prepare("SELECT * FROM reply_judgements WHERE user_key = ? ORDER BY id DESC").get(userKey);
assert.equal(judgement.score, 0.82);

console.log("companion db check passed");
```

- [ ] **Step 2: Run DB check to verify failure**

Run:

```powershell
node scripts/check-companion-db.mjs
```

Expected: fail because functions/tables do not exist.

- [ ] **Step 3: Add tables**

Add to `initDatabase()`:

- `companion_relationships`
- `companion_memories`
- `reply_judgements`

Use the SQL from `docs/superpowers/specs/2026-06-18-digital-companion-architecture.md`.

- [ ] **Step 4: Add helper functions**

Add exports:

- `getCompanionRelationship(botId, userKey)`
- `updateCompanionRelationship(botId, userKey, delta)`
- `getCompanionMemories(botId, userKey, limit = 20)`
- `setCompanionMemory(botId, userKey, memory)`
- `recordReplyJudgement(botId, userKey, messageId, judgement)`

- [ ] **Step 5: Run DB check**

Run:

```powershell
node scripts/check-companion-db.mjs
```

Expected: pass.

## Task 5: Node Client for Python Sidecar

**Files:**

- Create: `server/companion-client.js`
- Create: `scripts/check-companion-client.mjs`
- Modify: `package.json`

- [ ] **Step 1: Write failing client check**

Create a check script that starts a tiny HTTP server on `3115`, points `COMPANION_CORE_URL` to it, and calls `createCompanionReply()`.

Expected response:

```js
{
  ok: true,
  reply: "sidecar reply",
  relationshipDelta: { intimacy: 0.01 },
  memoryCandidates: [],
  directorGoal: { primary_goal: "emotion_ack" },
  judge: { score: 0.9, passed: true }
}
```

- [ ] **Step 2: Run check to verify failure**

Run:

```powershell
node scripts/check-companion-client.mjs
```

Expected: fail because `server/companion-client.js` does not exist.

- [ ] **Step 3: Implement client**

`server/companion-client.js` exports:

- `getCompanionCoreUrl()`
- `callCompanionCore(payload, options = {})`
- `isCompanionUnavailable(error)`

Behavior:

- URL defaults to `http://127.0.0.1:3105`.
- Timeout defaults to 8000 ms.
- Non-2xx response throws an error with `code = "COMPANION_CORE_ERROR"`.
- Network/timeout failure throws `code = "COMPANION_CORE_UNAVAILABLE"`.

- [ ] **Step 4: Run check**

Run:

```powershell
node scripts/check-companion-client.mjs
```

Expected: pass.

## Task 6: Integrate Node Chat and Webhook with Sidecar

**Files:**

- Modify: `server/index.js`
- Modify: `server/database.js`
- Create: `scripts/check-companion-integration.mjs`

- [ ] **Step 1: Write failing integration check**

The script must:

1. start a fake companion sidecar on `3116`
2. set `COMPANION_CORE_URL=http://127.0.0.1:3116`
3. start Node server on `3117`
4. register a user
5. create a bot
6. call `/api/chat/:botId`
7. assert response reply equals fake sidecar reply
8. assert relationship and judgement were persisted
9. stop fake sidecar
10. call `/api/chat/:botId` again
11. assert Node fallback still returns a controlled error or fallback response instead of crashing

- [ ] **Step 2: Run integration check to verify failure**

Run:

```powershell
node scripts/check-companion-integration.mjs
```

Expected: fail because Node still uses internal `processMessage()` only.

- [ ] **Step 3: Extract payload builder**

In `server/index.js`, create helper:

```js
function buildCompanionPayload({ bot, text, source, senderId }) {
  const userKey = senderId || source + "-user";
  return {
    bot_id: String(bot.id),
    user_key: userKey,
    channel: source,
    text,
    recent_messages: getRecentMessages(bot.id, 12),
    memories: getCompanionMemories(bot.id, userKey),
    relationship: getCompanionRelationship(bot.id, userKey)
  };
}
```

- [ ] **Step 4: Add sidecar-first reply path**

In `processMessage()`:

1. save user message
2. try `callCompanionCore(payload)`
3. save assistant reply
4. persist relationship delta, memory candidates, judgement
5. record stats
6. return reply

If sidecar unavailable:

1. use existing Node generation path
2. preserve current `AI_NOT_READY` behavior
3. keep bridge fallback behavior unchanged

- [ ] **Step 5: Run integration check**

Run:

```powershell
node scripts/check-companion-integration.mjs
```

Expected: pass.

## Task 7: Start Scripts and Daemon

**Files:**

- Modify: `package.json`
- Modify: `daemon.js`
- Create: `scripts/check-companion-runtime.mjs`

- [ ] **Step 1: Add package scripts**

Add:

```json
{
  "companion:install": "python -m pip install -r companion_core/requirements.txt",
  "companion:start": "python -m uvicorn companion_core.app:app --host 127.0.0.1 --port 3105",
  "check:companion-core": "node scripts/check-companion-core.mjs",
  "check:companion-db": "node scripts/check-companion-db.mjs",
  "check:companion-client": "node scripts/check-companion-client.mjs",
  "check:companion-integration": "node scripts/check-companion-integration.mjs"
}
```

- [ ] **Step 2: Update daemon**

`daemon.js` should start:

- `server/index.js`
- `qr-server.js`
- `multi-wechat-bridge.js`
- `python -m uvicorn companion_core.app:app --host 127.0.0.1 --port 3105`

It should write logs to `_logs/companion-core.log` and `_logs/companion-core.err.log`.

- [ ] **Step 3: Add runtime check**

`scripts/check-companion-runtime.mjs` should verify:

- `GET http://127.0.0.1:3105/health`
- `POST http://127.0.0.1:3105/v1/reply`

- [ ] **Step 4: Run runtime check**

Run:

```powershell
cmd /c npm run check:companion-core
```

Expected: pass.

## Task 8: Full Verification

**Files:**

- Modify: `PROJECT_STATUS.md`
- Append: `E:\Workspace\_logs\踩坑日志.md`

- [ ] **Step 1: Run Python tests**

```powershell
python -m unittest discover companion_core/tests
```

Expected: all tests pass.

- [ ] **Step 2: Run companion checks**

```powershell
node scripts/check-companion-db.mjs
node scripts/check-companion-client.mjs
node scripts/check-companion-integration.mjs
```

Expected: all checks pass.

- [ ] **Step 3: Run existing checks**

```powershell
cmd /c npm run check:core
cmd /c npm run check:api
cmd /c npm run check:plan
cmd /c npm run check:qr
cmd /c npm run check:bridge
cmd /c npm run check:ui
cmd /c npm run check:admin
cmd /c npm run check:admin-ui
cmd /c npm run check:memory
cmd /c npm run check:unique-admin
```

Expected: all existing checks still pass.

- [ ] **Step 4: Manual smoke test**

1. Start companion sidecar on `3105`.
2. Start Node service on `3000`.
3. Open `http://127.0.0.1:3000`.
4. Log in with `admin@emotion.local`.
5. Send “今天有点累”.
6. Confirm the reply contains emotional acknowledgement and a next-turn hook.

- [ ] **Step 5: Update docs**

Update `PROJECT_STATUS.md`:

- Add Phase 1 completed items.
- Add new start command for companion core.
- Add known gap: proactive messages are candidate-only and not auto-sent.

Append `E:\Workspace\_logs\踩坑日志.md`:

- Record that companion behavior now lives in Python sidecar.
- Record fallback rule: Node must continue replying or fail gracefully if Python is down.

## Completion Criteria

Phase 1 is complete only when:

- Python `/v1/reply` returns the contract from the architecture spec.
- Node `/api/chat/:botId` and `/api/webhook/:botId` can use Python sidecar.
- Existing WeChat bridge still receives `{ text: reply }`.
- Sidecar failure does not crash Node or bridge.
- Per-user relationship, memory candidates, and judge score are persisted.
- All new companion checks pass.
- All existing checks pass.
