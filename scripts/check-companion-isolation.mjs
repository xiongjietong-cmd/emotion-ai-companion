import assert from "node:assert/strict";
import { spawn } from "node:child_process";

import {
  addMessage,
  bindWechat,
  getCompanionMemories,
  getConversationSummary,
  getDb,
  initDatabase,
  recordReplyJudgement,
  setCompanionMemory,
  updateCompanionRelationship,
  updateConversationSummary,
} from "../server/database.js";

const nodePort = 3127;
const baseUrl = `http://127.0.0.1:${nodePort}`;

function sleep(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
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
  return { response, body };
}

async function waitForServer() {
  const deadline = Date.now() + 15000;
  while (Date.now() < deadline) {
    try {
      const { response } = await request("/api/health");
      if (response.ok) return;
    } catch {}
    await sleep(250);
  }
  throw new Error("node server did not become healthy");
}

async function register(email, password) {
  const result = await request("/api/auth/register", {
    method: "POST",
    body: JSON.stringify({ email, password }),
  });
  assert.equal(result.response.status, 200, `register ${email} should succeed`);
  assert.ok(result.body.token, "register should return token");
  return result.body.token;
}

const child = spawn(process.execPath, ["server/index.js"], {
  cwd: process.cwd(),
  env: {
    ...process.env,
    PORT: String(nodePort),
  },
  stdio: "ignore",
  windowsHide: true,
});

try {
  initDatabase();
  await waitForServer();

  const suffix = `${Date.now()}-${Math.random().toString(16).slice(2)}`;
  const ownerToken = await register(`isolation-owner-${suffix}@local.test`, "Companion123!");
  const otherToken = await register(`isolation-other-${suffix}@local.test`, "Companion123!");

  const created = await request("/api/bots", {
    method: "POST",
    headers: { Authorization: `Bearer ${ownerToken}` },
    body: JSON.stringify({ name: "Isolation Bot", personality: {} }),
  });
  assert.equal(created.response.status, 200, "owner should create bot");
  const botId = created.body.botId;
  assert.ok(botId, "created bot should have id");

  const secondCreated = await request("/api/bots", {
    method: "POST",
    headers: { Authorization: `Bearer ${ownerToken}` },
    body: JSON.stringify({ name: "Second Isolation Bot", personality: {} }),
  });
  assert.equal(secondCreated.response.status, 200, "owner should create a second bot");
  const secondBotId = secondCreated.body.botId;
  assert.ok(secondBotId, "second created bot should have id");

  addMessage(botId, "user", "alice-private-message", "", "alice");
  addMessage(botId, "assistant", "alice-private-reply", "", "alice");
  addMessage(botId, "user", "bob-private-message", "", "bob");
  addMessage(botId, "assistant", "bob-private-reply", "", "bob");
  setCompanionMemory(botId, "alice", { key: "shared-key", value: "alice memory in bot one" });
  setCompanionMemory(secondBotId, "alice", { key: "shared-key", value: "alice memory in bot two" });
  updateConversationSummary(botId, "alice", { rollingSummary: "bot one summary" });
  updateConversationSummary(secondBotId, "alice", { rollingSummary: "bot two summary" });
  updateCompanionRelationship(botId, "alice", { trust: 0.2 });
  updateCompanionRelationship(secondBotId, "alice", { trust: 0.4 });
  recordReplyJudgement(botId, "alice", null, { score: 0.8, passed: true, details: { bot: "one" } });
  bindWechat(botId, `isolation-delete-${suffix}@im.bot`, "https://ilinkai.weixin.qq.com", "isolation-delete");

  assert.deepEqual(
    getCompanionMemories(botId, "alice").map((memory) => memory.value),
    ["alice memory in bot one"],
    "first bot should keep its own memory value"
  );
  assert.deepEqual(
    getCompanionMemories(secondBotId, "alice").map((memory) => memory.value),
    ["alice memory in bot two"],
    "second bot should keep the same memory key isolated"
  );
  assert.equal(getConversationSummary(botId, "alice").rollingSummary, "bot one summary");
  assert.equal(getConversationSummary(secondBotId, "alice").rollingSummary, "bot two summary");

  const unauth = await request(`/api/bots/${botId}/history?senderId=alice`);
  assert.equal(unauth.response.status, 401, "history endpoint must require authentication");

  const unauthCount = await request(`/api/bots/${botId}/stats`);
  assert.equal(unauthCount.response.status, 401, "message count endpoint must require authentication");

  const crossAccount = await request(`/api/bots/${botId}/history?senderId=alice`, {
    headers: { Authorization: `Bearer ${otherToken}` },
  });
  assert.equal(crossAccount.response.status, 404, "history endpoint must reject non-owner accounts");

  const crossAccountCount = await request(`/api/bots/${botId}/stats`, {
    headers: { Authorization: `Bearer ${otherToken}` },
  });
  assert.equal(crossAccountCount.response.status, 404, "message count endpoint must reject non-owner accounts");

  const ownerAlice = await request(`/api/bots/${botId}/history?senderId=alice`, {
    headers: { Authorization: `Bearer ${ownerToken}` },
  });
  assert.equal(ownerAlice.response.status, 200, "owner should read scoped history");
  const contents = ownerAlice.body.messages.map((message) => message.content);
  assert.deepEqual(contents, ["alice-private-message", "alice-private-reply"]);
  assert.ok(!contents.includes("bob-private-message"), "scoped history must not include another sender");

  const unscoped = await request(`/api/bots/${botId}/history`, {
    headers: { Authorization: `Bearer ${ownerToken}` },
  });
  assert.equal(unscoped.response.status, 400, "history endpoint must require senderId scope");

  const ownerRow = getDb().prepare("SELECT id FROM users WHERE email = ?").get(`isolation-owner-${suffix}@local.test`);
  const otherRow = getDb().prepare("SELECT id FROM users WHERE email = ?").get(`isolation-other-${suffix}@local.test`);
  assert.ok(ownerRow?.id);
  assert.ok(otherRow?.id);

  const crossDelete = await request(`/api/bots/${botId}`, {
    method: "DELETE",
    headers: { Authorization: `Bearer ${otherToken}` },
  });
  assert.equal(crossDelete.response.status, 404, "non-owner accounts must not delete another user's bot");

  const deleted = await request(`/api/bots/${botId}`, {
    method: "DELETE",
    headers: { Authorization: `Bearer ${ownerToken}` },
  });
  assert.equal(deleted.response.status, 200, "owner should delete bot");

  const deletedHistory = await request(`/api/bots/${botId}/history?senderId=alice`, {
    headers: { Authorization: `Bearer ${ownerToken}` },
  });
  assert.equal(deletedHistory.response.status, 404, "deleted bot history should not remain accessible");

  const deletedStats = await request(`/api/bots/${botId}/stats`, {
    headers: { Authorization: `Bearer ${ownerToken}` },
  });
  assert.equal(deletedStats.response.status, 404, "deleted bot stats should not remain accessible");

  for (const [table, where] of [
    ["conversations", "bot_id = ?"],
    ["companion_memories", "bot_id = ?"],
    ["conversation_summaries", "bot_id = ?"],
    ["companion_relationships", "bot_id = ?"],
    ["reply_judgements", "bot_id = ?"],
    ["wechat_accounts", "bot_id = ?"],
  ]) {
    const count = getDb().prepare(`SELECT COUNT(*) AS count FROM ${table} WHERE ${where}`).get(botId).count;
    assert.equal(count, 0, `deleting a bot should remove rows from ${table}`);
  }

  assert.deepEqual(
    getCompanionMemories(secondBotId, "alice").map((memory) => memory.value),
    ["alice memory in bot two"],
    "deleting one bot must not delete another bot's memory"
  );
  assert.equal(getConversationSummary(secondBotId, "alice").rollingSummary, "bot two summary");

  console.log("companion isolation check passed");
} finally {
  child.kill();
}
