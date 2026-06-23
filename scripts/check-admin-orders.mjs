import assert from "node:assert/strict";
import { spawn } from "node:child_process";
import { existsSync } from "node:fs";
import { join } from "node:path";

import { getDb, initDatabase } from "../server/database.js";

initDatabase();

const port = Number(process.env.ADMIN_CHECK_PORT || 3103);
const baseUrl = `http://127.0.0.1:${port}`;
const suffix = `${Date.now()}-${Math.random().toString(16).slice(2)}`;
const email = `codex-admin-${suffix}@local.test`;
const password = "CodexAdmin123!";
const targetEmail = `codex-target-${suffix}@local.test`;
const targetPassword = "CodexTarget123!";
const targetWechatToken = `codex-target-${suffix}@im.bot`;

function accountFileForToken(token) {
  const accountId = token.split("@")[0] + "@im.bot";
  return join(process.cwd(), ".openclaw-state", "openclaw-weixin", "accounts", accountId + ".json");
}

const child = spawn(process.execPath, ["server/index.js"], {
  cwd: new URL("..", import.meta.url),
  env: { ...process.env, PORT: String(port) },
  stdio: ["ignore", "pipe", "pipe"],
});

let stdout = "";
let stderr = "";
child.stdout.on("data", (chunk) => { stdout += chunk.toString(); });
child.stderr.on("data", (chunk) => { stderr += chunk.toString(); });

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

try {
  await waitForServer();

  await request("/api/auth/register", {
    method: "POST",
    body: JSON.stringify({ email, password }),
  });

  getDb().prepare("UPDATE users SET role = 'admin' WHERE email = ?").run(email);

  const loggedIn = await request("/api/auth/login", {
    method: "POST",
    body: JSON.stringify({ email, password }),
  });
  const token = loggedIn.token;
  assert.ok(token, "admin login must return a token");

  const targetRegistered = await request("/api/auth/register", {
    method: "POST",
    body: JSON.stringify({ email: targetEmail, password: targetPassword }),
  });
  assert.ok(targetRegistered.user?.id, "target user should be created for account-control checks");
  const targetUserId = targetRegistered.user.id;

  const blacklisted = await request(`/api/admin/users/${targetUserId}/blacklist`, {
    method: "POST",
    headers: { Authorization: `Bearer ${token}` },
    body: JSON.stringify({ reason: "integration check" }),
  });
  assert.equal(blacklisted.ok, true, "admin should be able to blacklist user");

  await request("/api/auth/login", {
    method: "POST",
    body: JSON.stringify({ email: targetEmail, password: targetPassword }),
  }, 403);

  const restored = await request(`/api/admin/users/${targetUserId}/restore`, {
    method: "POST",
    headers: { Authorization: `Bearer ${token}` },
  });
  assert.equal(restored.ok, true, "admin should be able to restore user");

  const relogged = await request("/api/auth/login", {
    method: "POST",
    body: JSON.stringify({ email: targetEmail, password: targetPassword }),
  });
  assert.ok(relogged.token, "restored user should be able to log in");
  const targetToken = relogged.token;

  const targetBot = await request("/api/bots", {
    method: "POST",
    headers: { Authorization: `Bearer ${targetToken}` },
    body: JSON.stringify({
      name: "Codex Target Deleted User Bot",
      personality: { identity: { aiName: "Target Bot" } },
    }),
  });
  assert.ok(targetBot.botId, "target user should be able to create a bot before account deletion");

  await request(`/api/bots/${targetBot.botId}/wechat-bind`, {
    method: "POST",
    headers: { Authorization: `Bearer ${targetToken}` },
    body: JSON.stringify({
      token: targetWechatToken,
      baseUrl: "https://ilinkai.weixin.qq.com",
      wxUserId: "codex-target",
    }),
  });
  const targetBinding = getDb()
    .prepare("SELECT * FROM wechat_accounts WHERE bot_id = ? AND is_connected = 1")
    .get(targetBot.botId);
  assert.ok(targetBinding, "target user bot should start with an active wechat binding before account deletion");
  assert.equal(existsSync(accountFileForToken(targetWechatToken)), true, "target user wechat bind should write an OpenClaw account file");

  const targetOrder = await request("/api/orders", {
    method: "POST",
    headers: { Authorization: `Bearer ${targetToken}` },
    body: JSON.stringify({ plan: "starter" }),
  });
  assert.ok(targetOrder.orderId, "target user should have removable order data before account deletion");

  const deletedUser = await request(`/api/admin/users/${targetUserId}`, {
    method: "DELETE",
    headers: { Authorization: `Bearer ${token}` },
  });
  assert.equal(deletedUser.ok, true, "admin should be able to hard-delete user");
  assert.equal(deletedUser.deletedUserId, targetUserId, "delete response should identify the removed user");

  await request("/api/auth/login", {
    method: "POST",
    body: JSON.stringify({ email: targetEmail, password: targetPassword }),
  }, 401);

  await request("/api/bots", {
    headers: { Authorization: `Bearer ${targetToken}` },
  }, 401);

  await request(`/api/chat/${targetBot.botId}`, {
    method: "POST",
    headers: { Authorization: `Bearer ${targetToken}` },
    body: JSON.stringify({ text: "deleted account should not chat" }),
  }, 401);

  const deletedTargetUser = getDb()
    .prepare("SELECT * FROM users WHERE id = ?")
    .get(targetUserId);
  assert.equal(deletedTargetUser, undefined, "hard-deleting a user should remove the user row");

  const targetOrders = getDb()
    .prepare("SELECT COUNT(*) AS count FROM orders WHERE user_id = ?")
    .get(targetUserId).count;
  assert.equal(targetOrders, 0, "hard-deleting a user should remove the user's orders");

  const remainingTargetBots = getDb()
    .prepare("SELECT COUNT(*) AS count FROM bots WHERE user_id = ?")
    .get(targetUserId).count;
  assert.equal(remainingTargetBots, 0, "hard-deleting a user should remove that user's bots");

  const inactiveTargetBots = getDb()
    .prepare("SELECT COUNT(*) AS count FROM bots WHERE user_id = ? AND is_active = 0")
    .get(targetUserId).count;
  assert.equal(inactiveTargetBots, 0, "hard-deleting a user should not leave inactive bot rows");

  const activeTargetBindings = getDb()
    .prepare(`
      SELECT COUNT(*) AS count
      FROM wechat_accounts wa
      JOIN bots b ON b.id = wa.bot_id
      WHERE b.user_id = ? AND wa.is_connected = 1
    `)
    .get(targetUserId).count;
  assert.equal(activeTargetBindings, 0, "hard-deleting a user must disconnect wechat bindings for that user's bots");
  const anyTargetBindings = getDb()
    .prepare("SELECT COUNT(*) AS count FROM wechat_accounts WHERE bot_id = ?")
    .get(targetBot.botId).count;
  assert.equal(anyTargetBindings, 0, "hard-deleting a user should remove wechat binding rows for that user's bots");
  assert.equal(existsSync(accountFileForToken(targetWechatToken)), false, "hard-deleting a user must remove OpenClaw account files for that user's bots");

  const created = await request("/api/orders", {
    method: "POST",
    headers: { Authorization: `Bearer ${token}` },
    body: JSON.stringify({ plan: "starter" }),
  });
  assert.ok(created.orderId, "order creation should return orderId");
  assert.equal(created.amount, 19, "starter order should have configured price");

  const confirmed = await request(`/api/orders/${created.orderId}/confirm`, {
    method: "POST",
    headers: { Authorization: `Bearer ${token}` },
  });
  assert.equal(confirmed.plan, "starter", "confirming order should upgrade the user plan");

  const mine = await request("/api/orders", {
    headers: { Authorization: `Bearer ${token}` },
  });
  assert.ok(mine.orders.some((order) => order.id === created.orderId), "user orders should include the new order");

  const adminOrders = await request("/api/admin/orders", {
    headers: { Authorization: `Bearer ${token}` },
  });
  assert.ok(adminOrders.orders.some((order) => order.id === created.orderId), "admin orders should include the new order");

  const accountEvents = await request("/api/admin/account-events", {
    headers: { Authorization: `Bearer ${token}` },
  });
  assert.equal(accountEvents.ok, true, "admin account events endpoint should return ok");
  assert.ok(Array.isArray(accountEvents.events), "admin account events should be an array");
  assert.ok(accountEvents.events.some((event) => event.action === "order_create"), "account events should record order creation");
  assert.ok(accountEvents.events.some((event) => event.action === "order_confirm"), "account events should record order confirmation");
  assert.ok(accountEvents.events.some((event) => event.action === "user_blacklist"), "account events should record user blacklist");
  assert.ok(accountEvents.events.some((event) => event.action === "user_restore"), "account events should record user restore");
  assert.ok(accountEvents.events.some((event) => event.action === "user_delete"), "account events should record user delete");

  const analytics = await request("/api/admin/analytics", {
    headers: { Authorization: `Bearer ${token}` },
  });
  assert.equal(analytics.ok, true);
  assert.ok(Array.isArray(analytics.planDistribution), "analytics should include plan distribution");

  console.log("admin orders check passed");
} finally {
  child.kill();
}

async function waitForServer() {
  const started = Date.now();
  while (Date.now() - started < 5000) {
    try {
      await request("/api/health");
      return;
    } catch {
      await new Promise((resolve) => setTimeout(resolve, 100));
    }
  }
  throw new Error(`admin check server did not start. stdout=${stdout} stderr=${stderr}`);
}
