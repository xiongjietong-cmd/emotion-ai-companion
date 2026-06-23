import assert from "node:assert/strict";
import { spawn } from "node:child_process";

const port = 3102;
const baseUrl = `http://127.0.0.1:${port}`;

const child = spawn(process.execPath, ["qr-server.js"], {
  cwd: new URL("..", import.meta.url),
  env: {
    ...process.env,
    QR_PORT: String(port),
    QR_TEST_MODE: "1",
    QR_SCAN_TIMEOUT_MS: "700",
    QR_POLL_INTERVAL_MS: "100",
  },
  stdio: ["ignore", "pipe", "pipe"],
});

let stdout = "";
let stderr = "";
child.stdout.on("data", (chunk) => { stdout += chunk.toString(); });
child.stderr.on("data", (chunk) => { stderr += chunk.toString(); });

try {
  await waitForServer();

  const started = await request("/start", {
    method: "POST",
    body: JSON.stringify({ botId: 12345 }),
  });

  assert.equal(started.ok, true, "QR start should return ok");
  assert.ok(started.sessionId, "QR start should return sessionId");
  assert.ok(started.remainingSeconds > 0, "QR start should return remaining seconds");
  assert.ok(started.qrImage?.startsWith("data:image/"), "QR start should return a browser-displayable QR image");
  assert.ok(started.connectLink?.includes("test-qr"), "QR start should return a WeChat-openable connect link");
  assert.equal(Number(started.botId), 12345, "QR start should preserve the target bot id");

  const scanning = await request(`/status?session=${started.sessionId}`);
  assert.equal(scanning.status, "scanning", "new QR session should be scanning");
  assert.ok(scanning.qrText.includes("test-qr"), "test QR session should expose qr text");
  assert.ok(scanning.qrImage?.startsWith("data:image/"), "QR status should keep a browser-displayable QR image");
  assert.ok(scanning.connectLink?.includes("test-qr"), "QR status should keep the WeChat-openable connect link");
  assert.equal(Number(scanning.botId), 12345, "QR status should preserve the target bot id for binding");

  const canceled = await request(`/cancel?session=${started.sessionId}`, { method: "POST" });
  assert.equal(canceled.ok, true, "QR cancel should return ok");

  const canceledStatus = await request(`/status?session=${started.sessionId}`);
  assert.equal(canceledStatus.status, "expired", "canceled QR session should be expired");
  assert.match(canceledStatus.error, /取消|cancel/i);

  const expiring = await request("/start", {
    method: "POST",
    body: JSON.stringify({ botId: 12346 }),
  });

  await sleep(1000);
  const expired = await request(`/status?session=${expiring.sessionId}`);
  assert.equal(expired.status, "expired", "QR session should expire after timeout");
  assert.match(expired.error, /过期/);

  const missing = await request("/status?session=missing");
  assert.equal(missing.status, "not_found", "missing QR session should be explicit");

  console.log("qr behavior check passed");
} finally {
  child.kill();
}

async function request(path, options = {}) {
  const response = await fetch(baseUrl + path, {
    ...options,
    headers: { "Content-Type": "application/json", ...(options.headers || {}) },
  });
  const body = await response.json().catch(() => ({}));
  if (!response.ok) throw new Error(`${path} failed ${response.status}: ${JSON.stringify(body)}`);
  return body;
}

async function waitForServer() {
  const started = Date.now();
  while (Date.now() - started < 5000) {
    try {
      await request("/status?session=probe");
      return;
    } catch {
      await sleep(100);
    }
  }
  throw new Error(`QR test server did not start. stdout=${stdout} stderr=${stderr}`);
}

function sleep(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}
