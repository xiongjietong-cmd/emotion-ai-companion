# Dashboard Individual AI Settings

Date: 2026-06-18

## Goal

Upgrade the user dashboard so each bot can be shaped as a distinct companion. The UI should let the user define who the AI is, how it speaks, what relationship it has with the user, which terms should not be sent, and which example lines represent the desired voice.

## Scope

- Update `client/dashboard.html` settings view.
- Preserve per-bot isolation by saving everything under the selected bot's `personality` JSON.
- Do not create global personality settings.
- Do not share personality, memory, relationship, or style state between users or between bots.
- Keep the existing backend persistence path: `PUT /api/bots/:id`.

## Personality Fields

- Bot display name: dashboard-facing name.
- AI self name: name used in conversation.
- Relationship position: the role this bot should occupy for the user.
- Core persona: user-authored free-form identity and temperament.
- Speaking style: user-authored free-form speech guidance.
- Background: optional story/context.
- Blocked terms: exact words or short phrases this bot should not send.
- Speech examples: sample lines used as style references only, never fixed replies.
- Numeric traits: warmth, humor, directness, empathy.

## UI Rules

- User-authored text fields are primary.
- Sliders are secondary tuning controls.
- Global style guardrails such as avoiding customer-service tone are handled by the system, not by the user-facing blocked-terms field.
- The settings view should be compact and work-focused, not a landing-page style screen.
- Save feedback should be explicit.
- Missing optional fields should not break saving.

## Button Audit Target

The dashboard must expose and wire these actions:

- Create bot
- Save personality
- Load memories
- Add memory
- Delete memory
- Send test chat
- Generate QR
- Cancel QR
- Refresh WeChat status
- Manual reconnect
- Logout
- Switch tabs
- Select bot

## Verification

- `npm.cmd run check:ui` must assert the new fields and key handlers exist.
- Browser validation should load `http://127.0.0.1:3000/dashboard.html`, verify the dashboard is not blank, inspect console health, and exercise the personality save flow when logged in.
