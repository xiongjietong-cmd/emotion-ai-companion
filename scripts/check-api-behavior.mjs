import assert from "node:assert/strict";
import { existsSync } from "node:fs";
import { join } from "node:path";

import { initDatabase, getDb } from "../server/database.js";

initDatabase();

const baseUrl = process.env.SAAS_URL || "http://127.0.0.1:3000";
const suffix = `${Date.now()}-${Math.random().toString(16).slice(2)}`;
const email = `codex-api-${suffix}@local.test`;
const password = "CodexApi123!";
const deletedWechatToken = `codex-api-deleted-${suffix}@im.bot`;

function accountFileForToken(token) {
  const accountId = token.split("@")[0] + "@im.bot";
  return join(process.cwd(), ".openclaw-state", "openclaw-weixin", "accounts", accountId + ".json");
}

async function request(path, options = {}) {
  const response = await fetch(`${baseUrl}${path}`, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      ...(options.headers || {}),
    },
  });
  const body = await response.json().catch(() => ({}));
  if (!response.ok) {
    throw new Error(`${options.method || "GET"} ${path} failed: ${response.status} ${JSON.stringify(body)}`);
  }
  return body;
}

const registered = await request("/api/auth/register", {
  method: "POST",
  body: JSON.stringify({ email, password }),
});

const token = registered.token;
assert.ok(token, "register must return a token");

const created = await request("/api/bots", {
  method: "POST",
  headers: { Authorization: `Bearer ${token}` },
  body: JSON.stringify({
    name: "Codex API Bot",
    personality: { identity: { aiName: "Api Bot" } },
  }),
});

const deletable = await request("/api/bots", {
  method: "POST",
  headers: { Authorization: `Bearer ${token}` },
  body: JSON.stringify({
    name: "Codex Deleted Bot",
    personality: { identity: { aiName: "Deleted Bot" } },
  }),
});
assert.ok(deletable.botId, "second bot should be created for delete regression");

await request(`/api/bots/${deletable.botId}/wechat-bind`, {
  method: "POST",
  headers: { Authorization: `Bearer ${token}` },
  body: JSON.stringify({
    token: deletedWechatToken,
    baseUrl: "https://ilinkai.weixin.qq.com",
    wxUserId: "codex-api-deleted",
  }),
});

const deletableBinding = getDb()
  .prepare("SELECT * FROM wechat_accounts WHERE bot_id = ? AND is_connected = 1")
  .get(deletable.botId);
assert.ok(deletableBinding, "delete regression bot should start with an active wechat binding");
assert.equal(existsSync(accountFileForToken(deletedWechatToken)), true, "wechat bind should write an OpenClaw account file");

await request(`/api/bots/${deletable.botId}`, {
  method: "DELETE",
  headers: { Authorization: `Bearer ${token}` },
});

const afterDelete = await request("/api/bots", {
  headers: { Authorization: `Bearer ${token}` },
});
assert.ok(!afterDelete.bots.some((bot) => bot.id === deletable.botId), "deleted bots should not appear in user bot list");

const deletedBinding = getDb()
  .prepare("SELECT * FROM wechat_accounts WHERE bot_id = ? AND is_connected = 1")
  .get(deletable.botId);
assert.equal(deletedBinding, undefined, "deleting a bot must disconnect its active wechat binding");
assert.equal(existsSync(accountFileForToken(deletedWechatToken)), false, "deleting a bot must remove its OpenClaw account file");

await request(`/api/bots/${created.botId}/wechat-bind`, {
  method: "POST",
  headers: { Authorization: `Bearer ${token}` },
  body: JSON.stringify({
    token: `codex-api-${suffix}@im.bot`,
    baseUrl: "https://ilinkai.weixin.qq.com",
    wxUserId: "codex-api",
  }),
});

const persistedBinding = getDb()
  .prepare("SELECT * FROM wechat_accounts WHERE bot_id = ? AND is_connected = 1")
  .get(created.botId);
assert.ok(persistedBinding, "wechat-bind API must persist an active wechat account for the created bot");

const status = await request(`/api/bots/${created.botId}/wechat-status`, {
  headers: { Authorization: `Bearer ${token}` },
});
assert.equal(status.ok, true, "wechat status endpoint should return ok");
assert.equal(status.status.isBound, true, "fresh API binding should be reported as bound");
assert.ok(["bound", "online"].includes(status.status.status), "fresh API binding should be bound or already online");

console.log("api behavior check passed");
