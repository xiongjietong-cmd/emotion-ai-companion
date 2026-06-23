import assert from "node:assert/strict";

import { initDatabase } from "../server/database.js";

initDatabase();

const baseUrl = process.env.SAAS_URL || "http://127.0.0.1:3000";
const suffix = `${Date.now()}-${Math.random().toString(16).slice(2)}`;
const email = `codex-plan-${suffix}@local.test`;
const password = "CodexPlan123!";

async function request(path, options = {}, expectedStatus = 200) {
  const response = await fetch(`${baseUrl}${path}`, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      ...(options.headers || {}),
    },
  });
  const body = await response.json().catch(() => ({}));
  assert.equal(response.status, expectedStatus, `${path} expected ${expectedStatus}, got ${response.status}: ${JSON.stringify(body)}`);
  return body;
}

const registered = await request("/api/auth/register", {
  method: "POST",
  body: JSON.stringify({ email, password }),
});
const token = registered.token;
assert.ok(token, "register must return a token");

const usage = await request("/api/me/usage", {
  headers: { Authorization: `Bearer ${token}` },
});
assert.equal(usage.plan.code, "free", "new users should default to free plan");
assert.equal(usage.limits.botLimit, 2, "free plan should allow 2 active bots");
assert.equal(usage.limits.wechatLimit, 1, "free plan should allow 1 wechat binding");
assert.equal(usage.limits.monthlyMessageLimit, 200, "free plan should allow 200 monthly user messages");

const bot1 = await request("/api/bots", {
  method: "POST",
  headers: { Authorization: `Bearer ${token}` },
  body: JSON.stringify({ name: "Plan Bot 1" }),
});
const bot2 = await request("/api/bots", {
  method: "POST",
  headers: { Authorization: `Bearer ${token}` },
  body: JSON.stringify({ name: "Plan Bot 2" }),
});
await request("/api/bots", {
  method: "POST",
  headers: { Authorization: `Bearer ${token}` },
  body: JSON.stringify({ name: "Plan Bot 3" }),
}, 403);

await request(`/api/bots/${bot1.botId}/wechat-bind`, {
  method: "POST",
  headers: { Authorization: `Bearer ${token}` },
  body: JSON.stringify({
    token: `codex-plan-${suffix}-1@im.bot`,
    baseUrl: "https://ilinkai.weixin.qq.com",
    wxUserId: "codex-plan-1",
  }),
});
await request(`/api/bots/${bot2.botId}/wechat-bind`, {
  method: "POST",
  headers: { Authorization: `Bearer ${token}` },
  body: JSON.stringify({
    token: `codex-plan-${suffix}-2@im.bot`,
    baseUrl: "https://ilinkai.weixin.qq.com",
    wxUserId: "codex-plan-2",
  }),
}, 403);

const after = await request("/api/me/usage", {
  headers: { Authorization: `Bearer ${token}` },
});
assert.equal(after.usage.botCount, 2);
assert.equal(after.usage.wechatCount, 1);
assert.equal(after.remaining.bots, 0);
assert.equal(after.remaining.wechat, 0);

console.log("plan behavior check passed");
