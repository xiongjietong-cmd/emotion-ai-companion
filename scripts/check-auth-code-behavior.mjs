import assert from "node:assert/strict";
import { spawn } from "node:child_process";

import { deleteUserCompletely, getDb, getUserByEmail, initDatabase } from "../server/database.js";

initDatabase();

const port = Number(process.env.AUTH_CODE_CHECK_PORT || 3107);
const baseUrl = `http://127.0.0.1:${port}`;
const suffix = `${Date.now()}-${Math.random().toString(16).slice(2)}`;
const adminEmail = `auth-code-admin-${suffix}@local.test`;
const password = "AuthCode123!";
const emailAccount = `auth-code-user-${suffix}@local.test`;
const phoneAccount = `138${String(Date.now()).slice(-8)}`;

const child = spawn(process.execPath, ["server/index.js"], {
  cwd: new URL("..", import.meta.url),
  env: { ...process.env, PORT: String(port), NODE_ENV: "development" },
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

async function sendCode(channel, account) {
  const body = await request("/api/auth/code/send", {
    method: "POST",
    body: JSON.stringify({ channel, account }),
  });
  assert.ok(body.devCode, "development mode should return the verification code for local testing");
  assert.match(body.devCode, /^\d{6}$/, "verification code should be six digits");
  return body.devCode;
}

try {
  await waitForServer();

  await request("/api/auth/register", {
    method: "POST",
    body: JSON.stringify({ email: adminEmail, password }),
  });
  getDb().prepare("UPDATE users SET role = 'admin' WHERE email = ?").run(adminEmail);
  const adminLogin = await request("/api/auth/login", {
    method: "POST",
    body: JSON.stringify({ email: adminEmail, password }),
  });
  assert.equal(adminLogin.user.loginMethod, "email_password", "password login should report email_password");
  assert.equal(adminLogin.user.loginAccount, adminEmail, "password login should report the email account");

  const emailCode = await sendCode("email", emailAccount);
  await request("/api/auth/code/login", {
    method: "POST",
    body: JSON.stringify({ channel: "email", account: emailAccount, code: "000000" }),
  }, 400);
  const emailLogin = await request("/api/auth/code/login", {
    method: "POST",
    body: JSON.stringify({ channel: "email", account: emailAccount, code: emailCode }),
  });
  assert.ok(emailLogin.token, "email code login should return a token");
  assert.equal(emailLogin.user.email, emailAccount, "email code login should create or find the email user");
  assert.equal(emailLogin.user.loginMethod, "email_code");
  assert.equal(emailLogin.user.loginAccount, emailAccount);

  const reused = await request("/api/auth/code/login", {
    method: "POST",
    body: JSON.stringify({ channel: "email", account: emailAccount, code: emailCode }),
  }, 400);
  assert.equal(reused.code, "INVALID_VERIFICATION_CODE", "a used verification code should not be accepted twice");

  const phoneCode = await sendCode("phone", phoneAccount);
  const phoneLogin = await request("/api/auth/code/login", {
    method: "POST",
    body: JSON.stringify({ channel: "phone", account: phoneAccount, code: phoneCode }),
  });
  assert.ok(phoneLogin.token, "phone code login should return a token");
  assert.equal(phoneLogin.user.phone, phoneAccount);
  assert.equal(phoneLogin.user.loginMethod, "phone_code");
  assert.equal(phoneLogin.user.loginAccount, phoneAccount);

  const adminStats = await request("/api/admin/stats", {
    headers: { Authorization: `Bearer ${adminLogin.token}` },
  });
  const emailUser = adminStats.users.find((user) => user.email === emailAccount);
  const phoneUser = adminStats.users.find((user) => user.phone === phoneAccount);
  assert.equal(emailUser.last_login_method, "email_code", "admin users should expose the email login method");
  assert.equal(emailUser.last_login_account, emailAccount, "admin users should expose the email login account");
  assert.equal(phoneUser.last_login_method, "phone_code", "admin users should expose the phone login method");
  assert.equal(phoneUser.last_login_account, phoneAccount, "admin users should expose the phone login account");

  console.log("auth code behavior check passed");
} finally {
  child.kill();
  for (const email of [adminEmail, emailAccount, `phone-${phoneAccount}@phone.local`]) {
    const user = getUserByEmail(email);
    if (user) deleteUserCompletely(user.id);
  }
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
  throw new Error(`auth code check server did not start. stdout=${stdout} stderr=${stderr}`);
}
