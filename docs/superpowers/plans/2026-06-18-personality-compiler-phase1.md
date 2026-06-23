# User Personality Compiler Phase 1 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make user-defined AI personality settings become the primary individuality layer for web and WeChat replies without turning them into fixed scripts.

**Architecture:** Node already stores a bot `personality` JSON, but the Python companion sidecar does not receive or compile it. Phase 1 passes that JSON into the sidecar, compiles it into a structured runtime personality profile, and injects it into the prompt as identity, temperament, speech guidance, boundaries, and style references. The compiler must state that examples and settings influence judgment and tone, not fixed wording.

**Tech Stack:** Node.js/Express, SQLite, Python FastAPI sidecar, Pydantic, unittest.

---

### Task 1: Add Personality Compiler Tests

**Files:**
- Create: `companion_core/tests/test_personality_compiler.py`
- Create later: `companion_core/engines/personality_compiler.py`

- [ ] **Step 1: Write failing tests**

```python
import unittest

from companion_core.engines.personality_compiler import compile_personality_config


class PersonalityCompilerTest(unittest.TestCase):
    def test_compiles_user_authored_personality_without_fixed_script(self):
        profile = compile_personality_config({
            "name": "阿言",
            "speakingStyle": "嘴硬但会站在我这边，短句，偶尔吐槽",
            "background": "像一个清冷但可靠的朋友",
            "traits": {"warmth": 0.35, "humor": 0.72, "directness": 0.8, "empathy": 0.55},
            "customPersona": "有点冷淡，不说漂亮话，但会记得我在意的事。",
            "speechExamples": ["行，今天先别跟自己较劲了。", "你这脑子又开十个后台了吧。"],
            "avoidStyle": "不要客服，不要鸡汤，不要太甜。",
        })

        self.assertEqual(profile["name"], "阿言")
        self.assertIn("嘴硬", profile["temperament"])
        self.assertIn("短句", profile["speech_style"])
        self.assertIn("客服", profile["avoid"])
        self.assertIn("不是固定话术", profile["example_policy"])

    def test_empty_config_returns_neutral_companion_profile(self):
        profile = compile_personality_config({})

        self.assertEqual(profile["name"], "小暖")
        self.assertIn("自然", profile["speech_style"])
        self.assertIn("固定话术", profile["example_policy"])
```

- [ ] **Step 2: Run tests to verify RED**

Run: `.venv\Scripts\python -m unittest companion_core.tests.test_personality_compiler`

Expected: import failure because `personality_compiler.py` does not exist.

### Task 2: Implement Personality Compiler

**Files:**
- Create: `companion_core/engines/personality_compiler.py`

- [ ] **Step 1: Implement minimal compiler**

```python
def compile_personality_config(config: dict | None) -> dict:
    raw = config or {}
    traits = raw.get("traits") or {}
    return {
        "name": str(raw.get("name") or "小暖").strip() or "小暖",
        "temperament": " / ".join(filter(None, [
            str(raw.get("customPersona") or "").strip(),
            str(raw.get("background") or "").strip(),
        ])) or "自然、稳定、尊重用户节奏",
        "speech_style": str(raw.get("speakingStyle") or "自然口语，短句优先，不像客服").strip(),
        "relationship_position": str(raw.get("relationshipPosition") or "用户亲手设定的陪伴对象").strip(),
        "avoid": str(raw.get("avoidStyle") or "不要客服感，不要固定话术，不要过度说教").strip(),
        "style_references": [str(item).strip() for item in raw.get("speechExamples") or [] if str(item).strip()][:5],
        "traits": {
            "warmth": float(traits.get("warmth", 0.6) or 0.6),
            "humor": float(traits.get("humor", 0.4) or 0.4),
            "directness": float(traits.get("directness", 0.5) or 0.5),
            "empathy": float(traits.get("empathy", 0.6) or 0.6),
        },
        "example_policy": "样例只用于学习语气和判断方式，不是固定话术，不要照抄。",
    }
```

- [ ] **Step 2: Run compiler tests**

Run: `.venv\Scripts\python -m unittest companion_core.tests.test_personality_compiler`

Expected: PASS.

### Task 3: Pass Personality Config Through Sidecar

**Files:**
- Modify: `companion_core/models.py`
- Modify: `companion_core/app.py`
- Modify: `companion_core/model_client.py`
- Modify: `companion_core/engines/prompt_composer.py`
- Modify tests: `companion_core/tests/test_model_client.py`, `companion_core/tests/test_adaptive_persona.py`

- [ ] **Step 1: Add failing prompt tests**

Add tests proving `compose_system_prompt(..., identity_profile=profile)` includes:
- user personality has higher priority than runtime default persona
- examples are style references, not fixed wording
- prompt contains the configured name and style

- [ ] **Step 2: Implement request field**

Add to `ReplyRequest`:

```python
personality_config: dict = Field(default_factory=dict)
```

- [ ] **Step 3: Compile in app**

In `create_reply`, call:

```python
identity_profile = compile_personality_config(request.personality_config)
```

Pass `identity_profile` into `generate_reply`.

- [ ] **Step 4: Inject into prompt**

In `compose_system_prompt`, add a section:

```text
用户个性化人格设定（优先级高于默认人设）：
- 名字: ...
- 核心气质: ...
- 说话方式: ...
- 避免像: ...
- 样例政策: 样例只用于学习语气，不可照抄。
```

### Task 4: Pass Bot Personality From Node to Sidecar

**Files:**
- Modify: `server/index.js`

- [ ] **Step 1: Add payload field**

In `processCompanionMessage`, include:

```js
personality_config: p,
```

inside `createCompanionReply(...)`.

- [ ] **Step 2: Verify existing integration still passes**

Run:

```powershell
npm.cmd run check:companion-integration
npm.cmd run check:bridge
```

### Task 5: Verification and Restart

**Files:**
- No new files.

- [ ] **Step 1: Run Python tests**

Run:

```powershell
.venv\Scripts\python -W error -m unittest discover companion_core/tests
```

Expected: all tests pass.

- [ ] **Step 2: Run Node checks**

Run:

```powershell
npm.cmd run check:companion-model
npm.cmd run check:companion-integration
npm.cmd run check:bridge
```

Expected: all checks pass.

- [ ] **Step 3: Restart sidecar**

Restart port `3105` and verify:

```powershell
Invoke-RestMethod http://127.0.0.1:3105/health
```

Expected: `{"ok":true}`.

