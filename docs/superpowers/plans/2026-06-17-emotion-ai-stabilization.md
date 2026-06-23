# Emotion AI Stabilization Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Stabilize the original emotion AI project as the working baseline, improve WeChat reply reliability, and merge the useful Reasonix product features into the original project.

**Architecture:** Keep `project3_Web_情感AI_20260616` as the single source of truth. Treat Reasonix as a reference branch only. Add focused verification scripts for bridge behavior, quota behavior, QR behavior, and API behavior before changing production code.

**Tech Stack:** Node.js ESM, Express, better-sqlite3, OpenAI-compatible DeepSeek API, OpenClaw WeChat bridge, static HTML/CSS/JS frontend.

---

### Task 1: WeChat Bridge Reliability

**Files:**
- Modify: `multi-wechat-bridge.js`
- Create: `scripts/check-bridge-behavior.mjs`
- Modify: `package.json`

- [ ] Step 1: Add a failing bridge behavior check that imports helper functions from `multi-wechat-bridge.js`.
- [ ] Step 2: Verify the check fails because helpers are not exported yet.
- [ ] Step 3: Extract bridge helpers for account mapping, webhook reply parsing, and human fallback text.
- [ ] Step 4: Make the bridge log webhook status/body when no reply is sent.
- [ ] Step 5: Run `npm run check:bridge`.

### Task 2: QR Operations UX

**Files:**
- Modify: `qr-server.js`
- Modify: `client/dashboard.html`
- Modify: `scripts/check-qr-behavior.mjs`

- [ ] Step 1: Extend QR check to cover `/cancel`.
- [ ] Step 2: Add dashboard cancel QR and manual reconnect controls from Reasonix.
- [ ] Step 3: Verify `npm run check:qr`.

### Task 3: User Quota and Plan Surface

**Files:**
- Modify: `client/dashboard.html`
- Modify: `scripts/check-plan-behavior.mjs`

- [ ] Step 1: Add usage display for current plan, bot count, WeChat count, and monthly messages.
- [ ] Step 2: Keep backend quota enforcement unchanged unless tests show a gap.
- [ ] Step 3: Verify `npm run check:plan`.

### Task 4: Admin Analytics and Orders

**Files:**
- Modify: `server/database.js`
- Modify: `server/index.js`
- Modify: `client/admin.html`
- Create or modify: API check script

- [ ] Step 1: Add or verify order tables and plan upgrade functions.
- [ ] Step 2: Add `/api/orders`, `/api/orders/:id/confirm`, `/api/admin/orders`, and `/api/admin/analytics`.
- [ ] Step 3: Show plan distribution and order summary in admin.
- [ ] Step 4: Verify admin endpoints with a script.

### Task 5: Final Verification and Notes

**Files:**
- Modify: `PROJECT_STATUS.md`
- Append: `E:\Workspace\_logs\踩坑日志.md`

- [ ] Step 1: Run all local check scripts.
- [ ] Step 2: Start the original project services on ports 3000 and 3002.
- [ ] Step 3: Verify the browser loads the original project, not Reasonix.
- [ ] Step 4: Record the project takeover decision and WeChat pitfalls.
