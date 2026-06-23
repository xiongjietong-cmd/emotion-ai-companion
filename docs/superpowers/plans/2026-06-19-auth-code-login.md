# Auth Code Login Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add email and phone verification-code login, and show latest login method/account in the admin user list.

**Architecture:** Keep the existing `users` table and email-password login. Add user columns for phone and latest login metadata, plus an `auth_verification_codes` table for one-time login codes. The frontend exposes password login, verification-code login, and registration without adding QQ/WeChat OAuth.

**Tech Stack:** Node.js, Express, better-sqlite3, static HTML/JS, existing JWT auth.

---

### Task 1: Verification-Code Behavior Test

**Files:**
- Create: `scripts/check-auth-code-behavior.mjs`
- Modify: `package.json`

- [x] Add a test that starts a temporary server, sends email and phone verification codes, logs in with them, rejects reused codes, and checks admin user rows expose `last_login_method` and `last_login_account`.
- [x] Add `check:auth-code` script.

### Task 2: Database Support

**Files:**
- Modify: `server/database.js`

- [x] Add `users.phone`, `users.last_login_method`, and `users.last_login_account`.
- [x] Add `auth_verification_codes`.
- [x] Add helpers for normalizing auth channel/account, issuing codes, verifying codes, creating verified-login users, and recording latest login metadata.

### Task 3: Auth API

**Files:**
- Modify: `server/index.js`

- [x] Add `POST /api/auth/code/send`.
- [x] Add `POST /api/auth/code/login`.
- [x] Update password login and registration responses to include login metadata.

### Task 4: Login UI

**Files:**
- Modify: `client/index.html`
- Modify: `scripts/check-auth-ui.mjs`

- [x] Add a verification-code login tab with email/phone selector.
- [x] Call `/api/auth/code/send` and `/api/auth/code/login`.
- [x] Keep invite-code registration unchanged.

### Task 5: Admin UI

**Files:**
- Modify: `client/admin.html`
- Modify: `scripts/check-admin-ui.mjs`

- [x] Add phone, login method, and login account columns to the user list.
- [x] Format `email_password`, `email_code`, and `phone_code` as Chinese labels.

### Task 6: Verification

**Commands:**
- [x] `node --check server/database.js`
- [x] `node --check server/index.js`
- [x] `npm.cmd run check:auth-code`
- [x] `npm.cmd run check:auth-ui`
- [x] `npm.cmd run check:admin-ui`
- [x] `npm.cmd run check:admin`
- [x] `npm.cmd run check:invite`
- [x] Browser verification for login page and admin user table headers.
