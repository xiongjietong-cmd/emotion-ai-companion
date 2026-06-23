import assert from "node:assert/strict";
import { spawn } from "node:child_process";
import http from "node:http";

import { getCompanionRelationship, getDb, getSetting, initDatabase, setSetting } from "../server/database.js";

const nodePort = 3117;
const sidecarPort = 3116;
const baseUrl = `http://127.0.0.1:${nodePort}`;

let sidecarRequests = 0;
const sidecarPayloads = [];
const sidecar = http.createServer((request, response) => {
  if (request.method !== "POST" || request.url !== "/v1/reply") {
    response.writeHead(404, { "Content-Type": "application/json" });
    response.end(JSON.stringify({ error: "not found" }));
    return;
  }

  let raw = "";
  request.on("data", (chunk) => { raw += chunk; });
  request.on("end", () => {
    sidecarRequests += 1;
    sidecarPayloads.push(JSON.parse(raw));
    response.writeHead(200, { "Content-Type": "application/json" });
    response.end(JSON.stringify({
      reply: "sidecar integration reply\nsecond integration part",
      reply_parts: ["sidecar integration reply", "second integration part"],
      relationship_delta: { intimacy: 0.03, trust: 0.02, safety: 0.04 },
      memory_candidates: [
        {
          key: "integration_memory",
          value: "用户在集成测试里表达过疲惫",
          type: "episodic",
          emotion: "tired",
          salience: 0.7,
        },
      ],
      director_goal: { primary_goal: "emotion_ack" },
      judge: { score: 0.91, passed: true, details: { topic_momentum: 0.9 } },
    }));
  });
});

function listen(server, port) {
  return new Promise((resolve) => server.listen(port, "127.0.0.1", resolve));
}

function close(server) {
  return new Promise((resolve) => server.close(resolve));
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
    await new Promise((resolve) => setTimeout(resolve, 250));
  }
  throw new Error("node server did not become healthy");
}

await listen(sidecar, sidecarPort);
initDatabase();
const previousApiKey = getSetting("deepseek_api_key", "");

const child = spawn(process.execPath, ["server/index.js"], {
  cwd: process.cwd(),
  env: {
    ...process.env,
    PORT: String(nodePort),
    COMPANION_CORE_URL: `http://127.0.0.1:${sidecarPort}`,
    COMPANION_CONTEXT_UNDERSTANDING_ENABLED: "1",
    COMPANION_CONVERSATION_STATE_ENABLED: "1",
  },
  stdio: "ignore",
  windowsHide: true,
});

try {
  await waitForServer();

  const suffix = `${Date.now()}-${Math.random().toString(16).slice(2)}`;
  const registered = await request("/api/auth/register", {
    method: "POST",
    body: JSON.stringify({ email: `companion-integration-${suffix}@local.test`, password: "Companion123!" }),
  });
  assert.equal(registered.response.status, 200);
  const token = registered.body.token;

  const created = await request("/api/bots", {
    method: "POST",
    headers: { Authorization: `Bearer ${token}` },
    body: JSON.stringify({
      name: "Companion Integration Bot",
      personality: { name: "小伴" },
    }),
  });
  assert.equal(created.response.status, 200);
  const botId = created.body.botId;

  const settings = await request("/api/settings", {
    method: "POST",
    body: JSON.stringify({ apiKey: "node-db-key" }),
  });
  assert.equal(settings.response.status, 200);

  const unauthorized = await request(`/api/chat/${botId}`, {
    method: "POST",
    body: JSON.stringify({ text: "未登录不应能访问", senderId: "web-user" }),
  });
  assert.equal(unauthorized.response.status, 401, "web chat endpoint must require the bot owner's token");

  const first = await request(`/api/chat/${botId}`, {
    method: "POST",
    headers: { Authorization: `Bearer ${token}` },
    body: JSON.stringify({ text: "今天有点累", senderId: "web-user" }),
  });
  assert.equal(first.response.status, 200);
  assert.equal(first.body.reply, "sidecar integration reply\nsecond integration part");
  assert.deepEqual(first.body.replyParts, ["sidecar integration reply", "second integration part"]);
  assert.equal(sidecarRequests, 1);
  assert.equal(sidecarPayloads[0].provider_config.api_key, "node-db-key");
  assert.equal(sidecarPayloads[0].provider_config.model, "deepseek-v4-flash");
  assert.equal(sidecarPayloads[0].personality_config.name, "小伴");
  assert.ok(sidecarPayloads[0].conversation_summary);
  assert.equal(sidecarPayloads[0].personality, undefined, "Node must use companion_core field personality_config, not legacy personality");
  assert.equal(sidecarPayloads[0].summary, undefined, "Node must use companion_core field conversation_summary, not legacy summary");
  assert.equal(sidecarPayloads[0].features.context_understanding, true);
  assert.equal(sidecarPayloads[0].features.conversation_state, true);

  initDatabase();
  const relationship = getCompanionRelationship(botId, "web-user");
  assert.ok(relationship.intimacy >= 0.13);
  const judgement = getDb()
    .prepare("SELECT * FROM reply_judgements WHERE bot_id = ? AND user_key = ? ORDER BY id DESC")
    .get(botId, "web-user");
  assert.equal(judgement.score, 0.91);
  const assistantRows = getDb()
    .prepare("SELECT content FROM conversations WHERE bot_id = ? AND role = 'assistant' ORDER BY id DESC LIMIT 2")
    .all(botId)
    .map((row) => row.content)
    .reverse();
  assert.deepEqual(assistantRows, ["sidecar integration reply", "second integration part"]);

  await close(sidecar);
  const second = await request(`/api/chat/${botId}`, {
    method: "POST",
    headers: { Authorization: `Bearer ${token}` },
    body: JSON.stringify({ text: "再说一句", senderId: "web-user" }),
  });
  assert.equal(second.response.status, 200);
  assert.equal(second.body.reply, "服务器异常，暂时没连上模型。请稍后再试。");
  assert.deepEqual(second.body.replyParts, ["服务器异常，暂时没连上模型。请稍后再试。"]);

  console.log("companion integration check passed");
} finally {
  setSetting("deepseek_api_key", previousApiKey);
  child.kill();
  if (sidecar.listening) await close(sidecar);
}
