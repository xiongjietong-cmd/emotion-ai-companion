import { createServer } from "http";
import { randomBytes } from "crypto";
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import QRCode from "qrcode";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const PORT = Number(process.env.QR_PORT || 3002);
const BASE_URL = "https://ilinkai.weixin.qq.com";
const BOT_TYPE = "3";
const STATE_DIR = process.env.OPENCLAW_STATE_DIR || path.join(__dirname, ".openclaw-state");
const TEST_MODE = process.env.QR_TEST_MODE === "1";
const SCAN_TIMEOUT_MS = Number(process.env.QR_SCAN_TIMEOUT_MS || 120000);
const POLL_INTERVAL_MS = Number(process.env.QR_POLL_INTERVAL_MS || 2000);

const sessions = new Map();

function buildHeaders(token) {
  const uin = String(Math.floor(Math.random() * 4294967295));
  return {
    "Content-Type": "application/json",
    AuthorizationType: "ilink_bot_token",
    Authorization: "Bearer " + String(token || "").trim(),
    "X-WECHAT-UIN": Buffer.from(uin).toString("base64"),
    "iLink-App-Id": "bot",
    "iLink-App-ClientVersion": "131328"
  };
}

async function notifyStart(token) {
  try {
    await fetch(BASE_URL + "/ilink/bot/msg/notifystart", {
      method: "POST",
      headers: buildHeaders(token),
      body: JSON.stringify({ base_info: { channel_version: "2.4.3", bot_agent: "OpenClaw" } })
    });
  } catch {}
}

async function saveAccount(token, userId, botId) {
  try {
    const dir = path.join(STATE_DIR, "openclaw-weixin", "accounts");
    if (!fs.existsSync(dir)) fs.mkdirSync(dir, { recursive: true });
    const accountId = token.split("@")[0] + "@im.bot";
    const idxId = accountId.replace("@im.bot", "-im-bot");
    const data = { token, savedAt: new Date().toISOString(), baseUrl: BASE_URL, userId: userId || "", botId: botId || "" };
    fs.writeFileSync(path.join(dir, accountId + ".json"), JSON.stringify(data, null, 2), "utf-8");
    const indexFile = path.join(dir, "..", "accounts.json");
    let index = [];
    try { index = JSON.parse(fs.readFileSync(indexFile, "utf-8")); } catch {}
    if (!index.includes(idxId)) {
      index.push(idxId);
      fs.writeFileSync(indexFile, JSON.stringify(index, null, 2), "utf-8");
    }
  } catch (error) {
    console.error("[qr] save account failed:", error.message);
  }
}

function json(res, status, body) {
  res.writeHead(status, {
    "Content-Type": "application/json",
    "Access-Control-Allow-Origin": "*",
    "Access-Control-Allow-Methods": "POST, GET, OPTIONS",
    "Access-Control-Allow-Headers": "Content-Type"
  });
  res.end(JSON.stringify(body));
}

function readBody(req) {
  return new Promise((resolve) => {
    let data = "";
    req.on("data", (chunk) => { data += chunk; });
    req.on("end", () => resolve(data));
  });
}

function remainingSeconds(session) {
  return Math.max(0, Math.ceil((session.expiresAt - Date.now()) / 1000));
}

async function buildQrImage(text) {
  return QRCode.toDataURL(text, {
    errorCorrectionLevel: "M",
    margin: 2,
    width: 320,
    color: { dark: "#111827", light: "#ffffff" }
  });
}

function normalizeSession(session) {
  if (!session) return { status: "not_found" };
  if (session.status === "scanning" && Date.now() >= session.expiresAt) {
    session.status = "expired";
    session.error = "二维码已过期";
  }
  return {
    status: session.status,
    error: session.error || "",
    qrText: session.qrText || session.qrUrl || "",
    qrUrl: session.qrUrl || session.qrText || "",
    qrImage: session.qrImage || "",
    connectLink: session.connectLink || session.qrText || session.qrUrl || "",
    token: session.token || "",
    wxUserId: session.wxUserId || "",
    botId: session.botId,
    remainingSeconds: remainingSeconds(session)
  };
}

async function createTestSession(botId) {
  const sessionId = "test-" + Date.now() + "-" + randomBytes(4).toString("hex");
  const qrText = "test-qr-" + sessionId;
  const qrImage = await buildQrImage(qrText);
  sessions.set(sessionId, {
    botId,
    status: "scanning",
    qrText,
    qrUrl: qrText,
    qrImage,
    connectLink: qrText,
    token: "",
    wxUserId: "",
    expiresAt: Date.now() + SCAN_TIMEOUT_MS
  });
  return { ok: true, sessionId, session: sessionId, qrText, qr: qrImage, qrUrl: qrText, qrImage, connectLink: qrText, botId, remainingSeconds: remainingSeconds(sessions.get(sessionId)) };
}

async function createWechatSession(botId) {
  const sessionId = "wx-" + Date.now() + "-" + randomBytes(4).toString("hex");
  const result = await fetch(BASE_URL + "/ilink/bot/get_bot_qrcode?bot_type=" + BOT_TYPE, {
    method: "POST",
    headers: buildHeaders(""),
    body: JSON.stringify({ local_token_list: [] })
  });
  const data = await result.json();
  if (!data.qrcode_img_content) {
    throw new Error("QR failed: " + JSON.stringify(data));
  }
  const connectLink = data.qrcode_img_content;
  const qrImage = await buildQrImage(connectLink);
  const session = {
    botId,
    status: "scanning",
    qrText: connectLink,
    qrUrl: connectLink,
    qrImage,
    connectLink,
    qrcode: data.qrcode,
    token: "",
    wxUserId: "",
    expiresAt: Date.now() + SCAN_TIMEOUT_MS
  };
  sessions.set(sessionId, session);
  pollWechatSession(sessionId).catch((error) => console.error("[qr] poll failed:", error.message));
  return { ok: true, sessionId, session: sessionId, qrText: session.qrText, qr: session.qrImage, qrUrl: session.qrUrl, qrImage: session.qrImage, connectLink: session.connectLink, botId: session.botId, remainingSeconds: remainingSeconds(session) };
}

async function pollWechatSession(sessionId) {
  while (true) {
    await new Promise((resolve) => setTimeout(resolve, POLL_INTERVAL_MS));
    const session = sessions.get(sessionId);
    if (!session || session.status !== "scanning") return;
    if (Date.now() >= session.expiresAt) {
      session.status = "expired";
      session.error = "二维码已过期";
      return;
    }
    const response = await fetch(BASE_URL + "/ilink/bot/get_qrcode_status?qrcode=" + session.qrcode, {
      method: "GET",
      headers: buildHeaders("")
    });
    const data = await response.json();
    if (data.bot_token) {
      session.status = "done";
      session.token = data.bot_token;
      session.wxUserId = data.user_id || "";
      await notifyStart(session.token);
      await saveAccount(session.token, session.wxUserId, session.botId);
      return;
    }
  }
}

const server = createServer(async (req, res) => {
  if (req.method === "OPTIONS") return json(res, 200, {});
  const url = new URL(req.url, "http://localhost");

  if ((req.method === "POST" || req.method === "GET") && url.pathname === "/start") {
    try {
      let body = {};
      if (req.method === "POST") {
        const raw = await readBody(req);
        body = raw ? JSON.parse(raw) : {};
      }
      const botId = body.botId || url.searchParams.get("botId");
      if (!botId) return json(res, 400, { error: "need botId" });
      const payload = TEST_MODE ? await createTestSession(botId) : await createWechatSession(botId);
      return json(res, 200, payload);
    } catch (error) {
      return json(res, 500, { error: error.message });
    }
  }

  if (req.method === "GET" && url.pathname === "/status") {
    const session = sessions.get(url.searchParams.get("session"));
    return json(res, 200, normalizeSession(session));
  }

  if ((req.method === "POST" || req.method === "GET") && url.pathname === "/cancel") {
    const session = sessions.get(url.searchParams.get("session"));
    if (!session) return json(res, 200, { ok: false, status: "not_found" });
    session.status = "expired";
    session.error = "扫码已取消";
    return json(res, 200, { ok: true, status: "expired" });
  }

  return json(res, 404, {});
});

server.listen(PORT, () => console.log("QR server on " + PORT));
