import assert from "node:assert/strict";

import {
  initDatabase,
  createUser,
  createBot,
  bindWechat,
  getWechatStatus,
  getDb,
  getStats,
  markWechatStatus,
} from "../server/database.js";

initDatabase();

const suffix = `${Date.now()}-${Math.random().toString(16).slice(2)}`;
const email = `codex-check-${suffix}@local.test`;
const userInfo = createUser(email, "CodexCheck123!");
const userId = userInfo.lastInsertRowid;

const botId = createBot(userId, "Codex Check Bot", {
  identity: { aiName: "Check Bot" },
});

const relationship = getDb()
  .prepare("SELECT bot_id, intimacy, trust FROM relationships WHERE bot_id = ?")
  .get(botId);

assert.equal(relationship?.bot_id, botId, "createBot must initialize relationship state");

const before = getStats().wechatCount;
bindWechat(botId, `codex-check-${suffix}@im.bot`, "https://ilinkai.weixin.qq.com", "codex-check");
const after = getStats().wechatCount;

assert.equal(after, before + 1, "bindWechat must be reflected in admin wechat stats");

const boundStatus = getWechatStatus(botId);
assert.equal(boundStatus.status, "bound", "new binding should start as bound");
assert.equal(boundStatus.isOnline, false, "new binding should not be online before bridge heartbeat");

markWechatStatus(botId, "online");
const onlineStatus = getWechatStatus(botId);
assert.equal(onlineStatus.status, "online", "bridge heartbeat should mark account online");
assert.equal(onlineStatus.isOnline, true, "fresh online heartbeat should be reported as online");

markWechatStatus(botId, "error", "codex simulated bridge error");
const errorStatus = getWechatStatus(botId);
assert.equal(errorStatus.status, "error", "bridge error should mark account error");
assert.match(errorStatus.lastError, /codex simulated bridge error/);

console.log("core behavior check passed");
