# Pitfalls

## 2026-06-19 - Do Not Disguise Operational Errors As Companion Content

Problem:

When the model, companion core, webhook, or WeChat bridge is unavailable, a local "human-sounding" fallback can appear in the user's chat as a sudden, contextless emotional reply. Users experience this as fake companion behavior, not as a service failure.

Decision:

- Companion core does not generate local emotional fallback replies.
- Missing model key, model request failure, empty model choices, and empty model content raise `ModelUnavailableError`.
- Companion core returns `503 MODEL_UNAVAILABLE`.
- Node converts model/core unavailability into a plain operational message.
- WeChat bridge also uses a plain operational message and must not say things like "I will keep陪 you", "恢复后认真回复", or "继续陪你".

Principle:

Business and infrastructure failures must be visible as failures. The emotional matrix guides real model generation; it must not become a hidden offline template generator.

## 2026-06-20 - Quality Audits Must Vary User Style And Sample Each Scenario Family

Problem:

Only reading one WeChat conversation or taking the first N test cases hides broad failures. An early real-model probe only covered presence and identity cases because `--limit` selected the beginning of the corpus. That made the result look narrower than the product problem.

Decision:

- Keep shared UTF-8 audit assets in `data/persona_presets.json` and `data/audit_cases.json`.
- Run audits across multiple personas, multiple user styles, and at least two runs.
- Use `--per-family-limit` for small probes so each requested scenario family is represented.
- Treat PowerShell inline Chinese probes as unreliable unless the text is loaded from UTF-8 files.

Observed real DeepSeek sample, 2026-06-20:

- 64 records: 2 runs x 2 personas x 2 user styles x 4 scenario families x 2 cases.
- Model failures: 8/64.
- Judge failures: 64/64.
- Average judge score: 0.2177.
- `肚子疼` and `想窜稀` were classified as `normal`, exposing a missing body-discomfort state.
- `不像` repair replies were too short and template-like.
- Minimal replies such as `在呢` were judged as total failures, so ReplyJudge is too strict for minimal/presence contexts.
- Some replies were truncated or empty, so model error diagnostics and retry policy need improvement.

Observed expanded real DeepSeek sample, 2026-06-20:

- 96 records: 2 runs x 2 personas x 3 user styles x 8 scenario families x 1 case.
- Model failures: 18/96.
- Judge passed: 3/96.
- Average judge score: 0.3008.
- Most expanded scenarios were classified as `normal`: loneliness, conflict, memory boundary, relationship probe, and roleplay need explicit states.
- Roleplay was the weakest family: avgScore=0.065. Replies like `哥哥。` satisfy the literal wording but have almost no relational intelligence.
- Memory-boundary cases such as `别突然提我以前的事` sometimes got acceptable short repair, but sometimes empty replies or slightly dismissive responses.
- Relationship requests such as `你能不能更主动一点` frequently produced empty replies, showing the model/prompt path is unstable on relational meta-conversation.
- Some daily-life memory use was good enough to keep testing, for example linking `路上看到一只很可爱的猫` to the stored cat memory. This still needs relevance guardrails so it does not become forced memory proof.

Observed rich-persona DeepSeek sample, 2026-06-20:

- 168 records: 1 run x 7 distinct personas x 3 user styles x 8 scenario families x 1 case.
- Model failures: 41/168.
- Judge passed: 1/168.
- Average judge score: 0.2503.
- Best average personas in this sample: `lover_warm` 0.3225, `protective_anchor` 0.3092.
- Worst average persona: `cool_interrogator` 0.1667. Strongly differentiated traits can collapse if the scheduler still routes most scenarios to `warm_heal`.
- Relationship probe was the weakest non-roleplay family: avgScore=0.1229, with many empty replies.
- Roleplay remained weak: avgScore=0.1514. Replies often satisfied literal wording but lacked relational intelligence.
- Persona differences did appear in wording, but the current classifier/scheduler suppresses them because most scenarios are classified as `normal` and scheduled as `warm_heal`.

Principle:

Persona presets alone are not enough. The classifier and scheduler must preserve user-created individuality and choose scenario-specific strategy before defaulting to a warm generic companion voice.

## 2026-06-20 - Do Not Expose Internal Reply Strategy To Users

Problem:

In real DeepSeek audits, some replies narrated the companion's internal intent or self-repair action:

- `被你抓住啦，是有那么一点。其实是想先看看你今天心情怎么样。`
- `那会儿确实只是想接住你，没想太多。`
- `刚才确实有点模板了。我收一下。`

This can sound human in isolation, but in the product it exposes the machinery of the emotional matrix and makes the companion feel like it is explaining its own generation process.

Decision:

- Treat this as `internal_process_leaks`, not a one-off wording issue.
- The emotional matrix, reply objective, and generation direction are internal guidance only.
- The model should express the resulting stance naturally, not narrate how it chose the stance.
- Judge the expression function, not the literal phrase. For example, "被你看穿了" can be normal teasing, but becomes a leak when it explains hidden strategy or identity.
- The sanitizer removes common leak fragments.
- ReplyJudge records and penalizes internal-process leaks.
- The audit harness records `metrics.internal_process_hits` so future tests can track regressions.

Principle:

Do not patch individual sentences. Preserve the architecture: strategy stays internal, persona and scene shape the outward reply.

Principle:

The audit harness is not a prompt toy. It is the control surface for discovering where the emotional matrix, classifier, prompt composer, model client, and judge disagree.

## 2026-06-22 - Do Not Treat Endpoint Recovery As Product Recovery

Problem:

A simplified rollback restored the old Node chat path and old static admin pages. The server became reachable, but product-level contracts were lost:

- `server/index.js` called the legacy `processMessage()` path instead of `processCompanionMessage()`.
- The companion-core path, per-user companion memory, relationship state, reply judgement, and `replyParts` storage were bypassed.
- `multi-wechat-bridge.js` collapsed webhook replies into one `text/reply` message instead of sending `replyParts` separately.
- `client/admin.html` reverted to a simple table page without collapsible account events, orders, bots, and account actions.

Decision:

- Before calling a crash "fixed", run the contract checks for companion memory, companion integration, companion isolation, bridge behavior, admin UI, and dashboard UI.
- Compare the live route behavior with `PROJECT_STATUS.md`, especially the chat contract: web chat and WeChat must both use companion core and preserve `replyParts`.
- When a regression appears after a restart or rollback, inspect recently touched files and staged diffs first. A reachable `/api/health` is not enough.
- Never stabilize by falling back to the legacy Node prompt path unless the user explicitly asks for a temporary emergency mode.

Principle:

The product is the digital companion runtime, not just an Express server that answers. If companion core, per-user isolation, multi-part WeChat delivery, or admin controls are missing, the project is still broken even if the page loads.

## 2026-06-22 - QR Scan Success Is Not The Same As SaaS Bot Binding

Problem:

WeChat messages reached `multi-wechat-bridge.js`, but they were posted to `/api/webhook/1` and rejected with `404 机器人不存在`.

Root cause:

- QR login created a new OpenClaw account file under `.openclaw-state/openclaw-weixin/accounts`.
- The dashboard did not poll QR status and did not call `/api/bots/:id/wechat-bind` after scan completion.
- The account file did not preserve the target `botId`.
- The bridge silently fell back to `botId=1` when no `wx_bot_<account>` setting existed.

Decision:

- After QR start, the dashboard must poll `/status?session=...` and call the authenticated SaaS bind API when it receives `status=done` and a token.
- QR/account files should include `botId` as a secondary mapping source.
- The bridge must never default to bot 1. If an account has no mapping, skip it and log a clear diagnostic.
- When WeChat receives messages but the SaaS DB has no new conversation rows, inspect bridge logs for `webhook failed status=404` and inspect `settings.wx_bot_*` before changing model logic.

Principle:

Do not treat "OpenClaw connected to WeChat" as "this SaaS bot is bound". The binding contract is only complete when both the account credential and the SaaS bot mapping exist.

## 2026-06-22 - Context State Guides Thinking, Not Wording

Problem:

The companion failed a live WeChat context test:

- User said they were in class.
- Later the user asked what they were doing.
- The assistant guessed random activities instead of using the earlier class context.
- A naive fix would be to force the reply to say "I remember you said..." or always answer "you are in class".

Decision:

- Do not turn context understanding into fixed output scripts.
- Store changeable situational facts such as current activity with source, confidence, evidence, and `changeable=true`.
- Use those facts only as internal guidance for reasoning.
- The model should understand that the user gave an earlier activity clue, avoid random guessing, and express the answer in the current persona's natural style.
- Tests should check whether the prompt/state contains the relevant context and avoids fixed wording requirements, not whether a specific phrase appears.

Principle:

The emotional matrix should improve the model's thinking substrate. It should not become a response-template cage.

## 2026-06-23 - Short Messages Need Interaction Frames, Not Presence Defaults

Problem:

Live WeChat testing exposed a broader continuity failure:

- User said they were playing a game.
- The assistant made an unsupported guess such as "听语气输得挺惨".
- User replied only `？`.
- The assistant treated the question mark as a presence check and replied "嗯，我在", losing the previous turn relation.
- Later playful or corrective messages were read as generic teasing instead of being tied back to the assistant's previous guess.

Root cause:

The system had context summaries and situational facts, but it did not explicitly model the current interaction frame: what the user message is doing in relation to the previous assistant move.

Decision:

- Add `Interaction Frame Engine V1` as an internal layer before prompt composition.
- Classify the latest user move as correction, pushback, probe, tease, silence, share, or feedback.
- Track relation to previous assistant reply, including question marks that challenge the previous reply.
- Keep assistant guesses as unconfirmed until the user confirms or clearly plays along.
- Treat current activity as a changeable scene fact, not an absolute real-time truth.
- Feed the frame into the prompt as internal scene understanding only.

Principle:

Do not default short messages to "presence". A single `？`, `嗯`, or short correction often means "you missed the previous move". The frame guides the model's thinking; it must not force fixed wording such as "我记得你刚才说...".

## 2026-06-23 - Runtime Restart And Payload Field Names Are Part Of The Fix

Problem:

After adding the interaction-frame code, live WeChat tests still behaved like the old version:

- `嗯？` still became `在呢`.
- `我在干什么` after the user said they were gaming still produced a random guess.
- The user correctly felt that "没什么变化".

Root cause:

- The running companion core process had started before `app.py` and `interaction_frame.py` were modified, so WeChat was still hitting the old in-memory code.
- Node sent `personality` and `summary` to `/v1/reply`, while Python expected `personality_config` and `conversation_summary`. Pydantic ignored those legacy field names, so part of the user's personality configuration and rolling summary never reached the companion core.

Decision:

- After changing `companion_core/app.py`, `companion_core/engines/*`, `server/index.js`, or `server/companion-client.js`, restart the affected local services before asking the user to test WeChat.
- Keep Node payload field names aligned with `companion_core.models.ReplyRequest`.
- Add integration assertions for `personality_config` and `conversation_summary`, and assert the legacy `personality` / `summary` fields are not sent to companion core.

Principle:

Do not claim a behavioral fix from file edits alone. For WeChat behavior, proof requires the live service to be restarted and the real bridge -> Node -> companion core payload contract to be verified.

## 2026-06-23 - Rolling Summary Must Not Override Current Scene

Problem:

Live WeChat testing showed the assistant pulling old test topics back into a fresh scene:

- The user had just said they were going to eat.
- A stale rolling summary still contained earlier test wording such as "做不到".
- When the user asked what they were going to do, the assistant answered from the stale summary instead of the recent scene.

Root cause:

- Rolling summaries are useful continuity material, but they are compressed and may contain old, unrelated tests.
- If a rolling summary is placed beside current scene facts without a priority layer, the model can treat old compressed text as equally important or more important than the last few turns.

Decision:

- Add a `Context Pack` layer before prompt composition.
- Extract current scene facts from the recent window, especially current activity, planned activity, and user probes about "what was I doing / what was I going to do".
- Put recent scene facts in high-priority context.
- Keep rolling summaries as low-priority background only.
- Tests must assert that stale summary text does not appear in high-priority context.

Principle:

Recent scene evidence outranks compressed history. Summaries guide continuity, but they must never resurrect stale topics against the user's current conversation.

## 2026-06-23 - Low Pressure Is Not Premature Closure

Problem:

Live WeChat testing exposed a strange comfort reply:

- User said the teacher was strict and they were tired.
- User explicitly asked: "安慰安慰我呗".
- The assistant replied "过来，抱一下。/ 不说话也行。"

Root cause:

- The system had broad low-pressure guidance such as leave space, do not over-question, and allow silence.
- It did not distinguish between a user closing the door and a user actively asking for comfort.
- `ReplyJudge` marked the reply as failed, but the repair layer had no branch for intent mismatch, so the low-quality reply still went out.

Decision:

- Add a `Conversation Act` layer to classify the user's current conversational move.
- Treat "安慰安慰我呗 / 安慰我 / 哄哄我 / 抱一下" as `seeking_comfort`, not `disengaged_boundary`.
- For `seeking_comfort`, reject premature closure phrases such as "不说话也行", "不用说", and "不用回".
- Pass the act into the generation prompt as internal guidance only.
- Add a repair branch that replaces premature closure with actual emotional support.

Principle:

Leaving space is only appropriate when the user asks for space. When the user asks for comfort, the companion should stay with the feeling and offer warmth, not quietly end the turn.

## 2026-06-24 - User Persona Must Be A Kernel, Not A Late Prompt Note

Problem:

Live WeChat testing showed the assistant answering identity questions with the default name even though bot 167 was configured as a different individual:

- Bot setting: name `仝雄杰`, relationship `恋人`, style `温暖，性感，成熟，主动`.
- User asked: `你是谁`.
- Assistant answered as the default companion identity instead of the user-authored individual.

Root cause:

- The user-authored personality was present in the prompt, but it was appended late as a descriptive section.
- Global style rules, emotional matrix guidance, default product persona, and repair logic could effectively dilute or override it.
- Fixing only the visible name would be a symptom patch. The deeper issue is priority architecture.

Decision:

- Add a `Persona Kernel` layer compiled from the user's bot settings.
- Put Persona Kernel at the top of the system prompt, directly below safety boundaries.
- Treat Context Pack, Conversation Act, emotional matrix, and default style as expression shapers only; they must not replace the user's configured identity.
- Add persona consistency evaluation to `ReplyJudge`.
- Repair replies that fall back to default identity names when the user configured a different individual.

Principle:

User-authored AI identity is the core character card. It is not a decorative prompt note. Other systems can adjust the moment, but they cannot overwrite who this specific companion is.
