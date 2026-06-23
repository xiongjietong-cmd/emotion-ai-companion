import assert from "node:assert/strict";
import { spawn } from "node:child_process";
import fs from "node:fs";
import http from "node:http";
import { join } from "node:path";

const sidecarPort = Number(process.env.COMPANION_MODEL_TEST_PORT || 3126);
const fakeModelPort = Number(process.env.FAKE_DEEPSEEK_TEST_PORT || 3127);
const sidecarUrl = `http://127.0.0.1:${sidecarPort}`;
const venvPython = join(process.cwd(), ".venv", "Scripts", "python.exe");
const python = fs.existsSync(venvPython) ? venvPython : "python";
const modelRequests = [];

const fakeModel = http.createServer((request, response) => {
  if (request.method !== "POST" || request.url !== "/v1/chat/completions") {
    response.writeHead(404, { "Content-Type": "application/json" });
    response.end(JSON.stringify({ error: "not found" }));
    return;
  }

  let raw = "";
  request.on("data", (chunk) => { raw += chunk; });
  request.on("end", () => {
    modelRequests.push(JSON.parse(raw));
    const content = modelRequests.length === 1
      ? "好的"
      : "模型重写：听起来今天确实挺耗人的。你不用急着解释，可以先缓一下，也可以把换工作的事拆开看。";
    const encoded = Buffer.from(JSON.stringify({ choices: [{ message: { content } }] }), "utf8");
    response.writeHead(200, {
      "Content-Type": "application/json",
      "Content-Length": encoded.length,
    });
    response.end(encoded);
  });
});

function listen(server, port) {
  return new Promise((resolve) => server.listen(port, "127.0.0.1", resolve));
}

function close(server) {
  return new Promise((resolve) => server.close(resolve));
}

async function waitForHealth() {
  const deadline = Date.now() + 15000;
  while (Date.now() < deadline) {
    try {
      const response = await fetch(`${sidecarUrl}/health`);
      if (response.ok) return;
    } catch {}
    await new Promise((resolve) => setTimeout(resolve, 250));
  }
  throw new Error("companion core did not become healthy");
}

await listen(fakeModel, fakeModelPort);

const child = spawn(python, [
  "-m",
  "uvicorn",
  "companion_core.app:app",
  "--host",
  "127.0.0.1",
  "--port",
  String(sidecarPort),
], {
  cwd: process.cwd(),
  stdio: "ignore",
  env: {
    ...process.env,
    DEEPSEEK_API_KEY: "test-key",
    DEEPSEEK_BASE_URL: `http://127.0.0.1:${fakeModelPort}/v1`,
    DEEPSEEK_MODEL: "deepseek-v4-flash",
  },
  windowsHide: true,
});

try {
  await waitForHealth();
  const response = await fetch(`${sidecarUrl}/v1/reply`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      bot_id: "1",
      user_key: "model-check",
      channel: "web",
      text: "我最近在想一些事",
      recent_messages: [],
      memories: [],
      relationship: {},
    }),
  });
  const body = await response.json();
  assert.equal(response.status, 200);
  assert.equal(body.reply.includes("模型重写"), true);
  assert.equal(body.judge.passed, true);
  assert.equal(modelRequests.length, 2);
  assert.equal(modelRequests[0].model, "deepseek-v4-flash");
  assert.equal(modelRequests[0].messages[0].role, "system");
  assert.equal(modelRequests[0].messages[0].content.includes("身份自知"), true);
  assert.equal(modelRequests[0].messages[0].content.includes("日常聊天不要主动强调身份"), true);
  assert.equal(modelRequests[0].messages[0].content.includes("不假装真人"), false);
  assert.equal(modelRequests[1].messages[0].content.includes("重写"), true);
  console.log("companion model check passed");
} finally {
  child.kill();
  await close(fakeModel);
}
