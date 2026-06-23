import assert from "node:assert/strict";
import { spawn } from "node:child_process";
import fs from "node:fs";
import { join } from "node:path";

const port = Number(process.env.COMPANION_CORE_TEST_PORT || 3125);
const baseUrl = `http://127.0.0.1:${port}`;
const venvPython = join(process.cwd(), ".venv", "Scripts", "python.exe");
const python = fs.existsSync(venvPython) ? venvPython : "python";

const child = spawn(python, [
  "-m",
  "uvicorn",
  "companion_core.app:app",
  "--host",
  "127.0.0.1",
  "--port",
  String(port),
], {
  cwd: process.cwd(),
  stdio: "ignore",
  env: {
    ...process.env,
    DEEPSEEK_API_KEY: "",
  },
  windowsHide: true,
});

async function waitForHealth() {
  const deadline = Date.now() + 15000;
  while (Date.now() < deadline) {
    try {
      const response = await fetch(`${baseUrl}/health`);
      if (response.ok) return await response.json();
    } catch {}
    await new Promise((resolve) => setTimeout(resolve, 250));
  }
  throw new Error("companion core did not become healthy");
}

try {
  const health = await waitForHealth();
  assert.equal(health.ok, true);

  const response = await fetch(`${baseUrl}/v1/reply`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      bot_id: "1",
      user_key: "runtime-test",
      channel: "web",
      text: "在干嘛呢",
      recent_messages: [],
      memories: [],
      relationship: {},
      provider_config: { api_key: "" },
    }),
  });
  const body = await response.json();
  assert.equal(response.status, 503, "companion core must not fabricate fallback chat when the model is unavailable");
  assert.equal(body.code, "MODEL_UNAVAILABLE");
  assert.equal(body.reply, undefined, "model-unavailable errors should not include a chat reply");

  console.log("companion core check passed");
} finally {
  child.kill();
}
