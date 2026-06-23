# PROJECT_STATUS

Last updated: 2026-06-20

## Product Goal

Build a user-facing WeChat-native emotional AI companion SaaS.

The product is not a generic chatbot. The target experience is:

- each user can create one or more independent AI companions;
- each companion has its own personality settings, memories, relationship state, and WeChat binding;
- web chat and WeChat chat use the same companion brain;
- admin can monitor users, bots, bindings, orders, message volume, behavior events, and service health.

## Current Architecture

- Main SaaS service: Node.js + Express, port `3000`.
- Database: SQLite through `better-sqlite3`, active file `data/emotion-saas.db`.
- Companion brain: Python FastAPI sidecar, port `3105`.
- WeChat bridge: `multi-wechat-bridge.js`, reading OpenClaw account state.
- QR service: `qr-server.js`, port `3002`.
- Frontend: static pages in `client/`.
- AI provider: DeepSeek OpenAI-compatible API, default model `deepseek-v4-flash`.

```text
WeChat / Web user
  -> Node SaaS
  -> Python companion_core
  -> DeepSeek model
  -> Node persistence and stats
  -> Web UI / WeChat bridge
```

## Current Runtime Contract

`POST /api/chat/:botId` and `POST /api/webhook/:botId` both use `processCompanionMessage()`.

Normal successful path:

1. Node validates bot, quota, user ownership where required.
2. Node stores the user message.
3. Node sends recent messages, selected memories, relationship state, and personality config to `companion_core`.
4. Python sidecar classifies user state, schedules persona, composes prompt, calls the model, sanitizes reply, judges quality, and splits reply rhythm.
5. Node stores assistant reply parts, relationship delta, memory candidates, and reply judgement.
6. WeChat bridge sends `replyParts` as separate messages.

Failure contract:

- Missing model key, model request failure, empty model choices, or empty model reply returns `503 MODEL_UNAVAILABLE` from companion core.
- Node converts companion/model unavailability into: `服务器异常，暂时没连上模型。请稍后再试。`
- WeChat bridge operational fallback is now plain service text: `服务器异常，暂时无法回复。请稍后再试。`
- Runtime no longer generates fake emotional fallback content when the model is unavailable.

## Completed

- User registration and login.
- Email/phone verification-code login in local dev mode.
- Invitation code and referral quota bonus.
- JWT auth and admin middleware.
- User plans, bot quota, WeChat quota, and monthly message quota.
- Bot create/update/delete.
- Per-user, per-bot personality settings.
- Per-user, per-bot companion relationship state.
- Per-user, per-bot companion memory.
- Web chat test UI.
- WeChat binding through OpenClaw state.
- Multi-account WeChat bridge scaffold.
- WeChat status tracking: bound, online, offline, error, unbound.
- Admin stats, users, bots, orders, account events, and analytics panels.
- Admin blacklist, restore, and complete user deletion.
- Complete user deletion removes dependent bots, conversations, memories, relationships, orders, WeChat bindings, and OpenClaw account files.
- Multi-part replies through `replyParts`.
- Reply rhythm engine for quiet, steady, attached, and playful profiles.
- Style guardrails for identity questions, low-pressure emotion handling, AI-feeling feedback, memory relevance, high-risk safety, and over-question control.
- User personality compiler: name, relationship position, custom persona, speaking style, blocked terms, examples, trait weights.
- Cleaned core companion prompt, memory, relationship, director, personality compiler, and reply judge source text.
- Removed emotional local fallback templates from companion core, Node main service, and WeChat bridge.
- Added shared persona presets for user-side personality simulation.
- Added UTF-8 audit corpus for daily chat quality probes.
- Added real DeepSeek quality audit harness with multi-run and multi-user-style sampling.
- Expanded audit corpus to 90+ daily, relational, memory, roleplay, loneliness, conflict, proactive, and risk scenarios.
- Added audit profiles: `pilot` and `full`.
- Expanded persona presets to 14 distinct archetypes for richer DeepSeek persona-difference testing.
- Added internal-process leak detection, sanitization, judge penalty, and audit metrics.
- Added Expression Function Layer to judge what a reply is doing in context, so natural teasing, roleplay signals, strategy leaks, self-repair performance, hidden identity tone, and fake reality claims are handled differently.
- Added Companion Quality Intelligence v2 foundation: multi-turn audit case format, deterministic semantic evaluator, continuation likelihood evaluator, persona distinction analyzer, and failure module reporting in the audit path.

## Current Tests

Node checks:

- `npm run check:bridge`
- `npm run check:companion-core`
- `npm run check:companion-integration`
- `npm run check:core`
- `npm run check:api`
- `npm run check:qr`
- `npm run check:plan`
- `npm run check:ui`
- `npm run check:admin`
- `npm run check:invite`

Python checks:

- `python -m unittest discover companion_core/tests`
- `python -m py_compile companion_core/model_client.py companion_core/app.py`
- `python -m unittest companion_core.tests.test_quality_audit_assets`
- `.venv\Scripts\python.exe -m unittest companion_core.tests.test_quality_intelligence_v2`
- `python scripts/audit_companion_quality.py --dry-run --runs 2 --personas lover_warm,playful_tease --families presence,identity,body_discomfort,ai_feedback --per-family-limit 2 --user-styles short,teasing`
- `python scripts/audit_companion_quality.py --dry-run --profile pilot --sleep-ms 0`

## Known Gaps

1. Old Node chat engine files still exist and should be moved to `legacy/` or removed after route coverage proves they are unused.
2. Proactive messages are not production-ready yet. They need opt-in, quiet hours, frequency caps, and admin visibility.
3. WeChat bridge needs stronger operational monitoring, restart policy, and recent error diagnostics in admin.
4. Payment is still a local order-confirmation flow, not a real payment provider integration.
5. SQLite backup, log rotation, and production secret handling need hardening.
6. Cloud deployment status is not verified from this machine.
7. Real DeepSeek quality audit 2026-06-20 produced 8/64 model failures and 64/64 judge failures in a controlled small sample. Main issues: missing body-discomfort classifier, over-strict judge for minimal replies, weak repair for "不像", empty/truncated model replies.
8. Expanded real DeepSeek quality audit 2026-06-20 produced 18/96 model failures, 3/96 judge passes, and average score 0.3008. Main issues: most relational scenarios classified as normal, roleplay family nearly unusable, memory-boundary handling inconsistent, relationship meta-conversation often empty.
9. Rich-persona DeepSeek audit 2026-06-20 produced 41/168 model failures, 1/168 judge pass, and average score 0.2503. Persona wording differed, but most cases still classified as normal and scheduled as warm_heal, suppressing user-created individuality.
10. Some DeepSeek replies exposed internal strategy or self-repair wording, such as "其实是想..." and "我收一下". These are now tracked through the Expression Function Layer as strategy exposure or self-repair performance, instead of only matching literal banned phrases.
11. The current reply judge is still mostly a rule/string/score gate. It catches obvious failures but does not yet evaluate semantic fit, continuation likelihood, persona distinction, or real user return signals.

## Immediate Priorities

1. Build Companion Quality Intelligence v2: semantic scene evaluation, continuation likelihood, persona distinction scoring, and quality reports that guide future companion changes.
2. Fix audit-discovered companion gaps: body-discomfort state, loneliness/conflict/relationship/roleplay states, preserve custom persona individuality through scheduler, presence/minimal judge scoring, feedback repair, internal-process leakage, memory-boundary handling, empty/truncated model retry diagnostics.
3. Finish removing or isolating the old Node chat engine path.
4. Add admin diagnostics for Node, companion core, DeepSeek, OpenClaw, QR, and WeChat bridge.
5. Add database backup and log rotation.
6. Build proactive message system only after delivery policy and user opt-in are implemented.
7. Expand analytics: retention, channel split, bound-bot conversion, quota exhaustion, model failure rate.

## Product Backlog

1. User-customized AI individual system v1. Learn from external persona-card products at the product-structure level: persona evolution curve, hidden relationship state, memory anchors, scene context, style references, and per-user/per-bot isolation. Do not implement it before Companion Quality Intelligence v2, because better personalization needs a stronger evaluation system first.

## Operational Notes

- Full local startup: `node daemon.js`.
- Main SaaS: `http://127.0.0.1:3000`.
- Admin: `http://127.0.0.1:3000/admin.html`.
- Dashboard: `http://127.0.0.1:3000/dashboard.html`.
- Companion core: `http://127.0.0.1:3105/health`.
- QR service: `http://127.0.0.1:3002`.
- After changing `server/index.js`, `server/companion-client.js`, `multi-wechat-bridge.js`, or `companion_core/*`, restart affected services.
- Do not commit `.openclaw-state/`, `data/*.db*`, `.env`, logs, or runtime sync files.
