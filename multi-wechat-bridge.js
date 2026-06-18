// multi-wechat-bridge.js — 多账号微信桥接 (生产版)
// 从 OpenClaw state 自动发现所有账号，映射到 SaaS bot，并行轮询

import fs from "node:fs";
import path from "node:path";
import Database from "better-sqlite3";
import { fileURLToPath, pathToFileURL } from "url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const STATE_DIR = process.env.WECHAT_STATE_DIR || path.join(__dirname, ".openclaw-state", "openclaw-weixin");
const SAAS_URL = process.env.SAAS_URL || "http://127.0.0.1:3000";
const DB_PATH = path.join(__dirname, "data", "emotion-saas.db");

let db = null;
try { db = new Database(DB_PATH); } catch(e) { console.error("DB open failed:", e.message); }

function sleep(ms) { return new Promise(r => setTimeout(r, ms)); }

export function extractWebhookReply(data = {}) {
  const replies = extractWebhookReplies(data);
  return replies.join("\n");
}

export function extractWebhookReplies(data = {}) {
  if (!data || data.ok === false) return [];
  const candidates = Array.isArray(data.texts)
    ? data.texts
    : Array.isArray(data.replyParts)
      ? data.replyParts
      : Array.isArray(data.reply_parts)
        ? data.reply_parts
        : [data.text ?? data.reply ?? ((!data.error && !data.code) ? data.message : "")];
  return candidates.map((candidate) => typeof candidate === "string" ? candidate.trim() : "").filter(Boolean);
}

export function summarizeWebhookFailure({ status = 0, data = {}, error = "" } = {}) {
  const parts = [];
  if (status) parts.push("status=" + status);
  if (data?.code) parts.push("code=" + data.code);
  if (data?.error) parts.push("error=" + data.error);
  if (error) parts.push("error=" + error);
  return parts.join(" ") || "empty webhook reply";
}

export function buildHumanBridgeFallback({ status = 0, code = "", error = "" } = {}) {
  if (code === "MESSAGE_LIMIT_REACHED" || status === 403) {
    return "我这边消息额度好像暂时用完了，先别急，我恢复后再认真回你。";
  }
  if (code === "AI_NOT_READY" || status === 409) {
    return "我这边的 AI 服务还没完全连上，稍后恢复后我再好好陪你聊。";
  }
  if (error && /fetch|ECONNREFUSED|connect|network|terminated/i.test(error)) {
    return "我这边暂时连接不上服务，先别担心，恢复后我会继续陪你。";
  }
  return "我这边服务有点不稳定，稍后恢复后我再认真回复你。";
}

function markBridgeStatus(botId, status, error = "") {
  if (!db || !botId) return;
  try {
    if (status === "online") {
      db.prepare(`
        UPDATE wechat_accounts
        SET status = 'online', last_seen_at = CURRENT_TIMESTAMP, last_error = NULL, last_error_at = NULL
        WHERE bot_id = ? AND is_connected = 1
      `).run(botId);
      return;
    }
    db.prepare(`
      UPDATE wechat_accounts
      SET status = 'error', last_error = ?, last_error_at = CURRENT_TIMESTAMP
      WHERE bot_id = ? AND is_connected = 1
    `).run(String(error || "bridge error").slice(0, 500), botId);
  } catch (e) {
    console.error("[bridge] status write failed:", e.message);
  }
}

// ─── 微信 API ───
function buildHeaders(token) {
  const uin = String(Math.floor(Math.random() * 4294967295));
  return {
    "Content-Type": "application/json", "AuthorizationType": "ilink_bot_token",
    "Authorization": "Bearer " + (token || "").trim(),
    "X-WECHAT-UIN": Buffer.from(uin).toString("base64"),
    "iLink-App-Id": "bot", "iLink-App-ClientVersion": "131328"
  };
}

async function callApi(baseUrl, endpoint, body, token) {
  const url = baseUrl.replace(/\/$/, "") + "/" + endpoint;
  const res = await fetch(url, { method: "POST", headers: buildHeaders(token), body: JSON.stringify(body) });
  return res.json();
}

async function sendWechatReply(acct, toUserId, contextToken, reply) {
  const result = await callApi(acct.baseUrl, "ilink/bot/sendmessage", {
    msg: {
      from_user_id: "", to_user_id: toUserId,
      client_id: "mb-" + Date.now() + "-" + Math.random().toString(36).slice(2, 8),
      message_type: 2, message_state: 2,
      item_list: [{ type: 1, text_item: { text: reply } }],
      context_token: contextToken || ""
    },
    base_info: { channel_version: "2.4.3", bot_agent: "OpenClaw" }
  }, acct.token);
  if (result && result.ret != null && Number(result.ret) !== 0) {
    throw new Error("sendmessage ret=" + result.ret);
  }
  return result;
}

// ─── 语音消息 ───
const TTS_URL = (process.env.TTS_URL || "http://127.0.0.1:3001").replace(/\/+$/, "");
const TUNNEL_URL = (process.env.TUNNEL_URL || "").replace(/\/+$/, "");

async function fetchTtsAudio(text, emotion) {
  // Always generate locally (fast), use tunnel for WeChat download
  const res = await fetch(TTS_URL + "/api/tts-url", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ text, emotion: emotion || "平静", baseUrl: TUNNEL_URL || TTS_URL })
  });
  if (!res.ok) throw new Error("TTS URL gen failed: " + res.status);
  const data = await res.json();
  if (!data.url) throw new Error("TTS returned no URL");
  return { url: data.url, durationMs: data.duration || 3000 };
}

async function sendWechatVoice(acct, toUserId, contextToken, voiceObj, durationMs) {
  const result = await callApi(acct.baseUrl, "ilink/bot/sendmessage", {
    msg: {
      from_user_id: "", to_user_id: toUserId,
      client_id: "mv-" + Date.now() + "-" + Math.random().toString(36).slice(2, 8),
      message_type: 2, message_state: 2,
      item_list: [{
        type: 3,
        voice_item: {
          voice_url: voiceObj.url,
          duration_ms: durationMs || 3000
        }
      }],
      context_token: contextToken || ""
    },
    base_info: { channel_version: "2.4.3", bot_agent: "OpenClaw" }
  }, acct.token);
  console.log("  [voice api] ret=" + result.ret + " errcode=" + result.errcode + " errmsg=" + (result.errmsg || "") + " url=" + (voiceObj.url||"").slice(0,80));
  if (result && result.ret != null && Number(result.ret) !== 0) {
    throw new Error("voice sendmessage ret=" + result.ret + " errmsg=" + (result.errmsg || ""));
  }
  return result;
}

// ─── 账号发现 ───
function discoverAccounts() {
  const dir = path.join(STATE_DIR, "accounts");
  try {
    const files = fs.readdirSync(dir).filter(f => f.endsWith(".json") && !f.includes("context") && !f.includes("sync"));
    return files.map(f => {
      const id = f.replace(".json", "");
      const data = JSON.parse(fs.readFileSync(path.join(dir, f), "utf-8"));
      // Read sync buf
      let syncBuf = "";
      try { syncBuf = JSON.parse(fs.readFileSync(path.join(dir, id + ".sync.json"), "utf-8")).get_updates_buf || ""; } catch {}
      // Map to bot
      let botId = 1;
      if (db) {
        try {
          const key = "wx_bot_" + id.split("@")[0];
          const row = db.prepare("SELECT value FROM settings WHERE key = ?").get(key);
          if (row) botId = parseInt(row.value);
        } catch {}
      }
      return { id, token: data.token, baseUrl: data.baseUrl || "https://ilinkai.weixin.qq.com", syncBuf, botId };
    });
  } catch(e) { console.error("Account discovery failed:", e.message); return []; }
}

function saveSync(acct) {
  try {
    const file = path.join(STATE_DIR, "accounts", acct.id + ".sync.json");
    fs.writeFileSync(file, JSON.stringify({ get_updates_buf: acct.syncBuf }), "utf-8");
  } catch {}
}

// ─── 消息处理 ───
async function handleMessage(acct, msg) {
  const ti = (msg.item_list || []).find(i => i.type === 1);
  if (!ti || !ti.text_item) return;
  const text = ti.text_item.text.trim();
  if (!text) return;
  const fromId = msg.from_user_id || "";
  const ctxToken = msg.context_token || "";
  console.log("[" + new Date().toLocaleTimeString() + "] " + acct.id.slice(0, 12) + " -> bot " + acct.botId + ": " + text.slice(0, 30));
  try {
    const t0 = Date.now();
    const res = await fetch(SAAS_URL + "/api/webhook/" + acct.botId, {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ text, senderId: fromId, contextToken: ctxToken })
    });
    const data = await res.json().catch(() => ({}));
    let replies = extractWebhookReplies(data);
    if (!replies.length) {
      const summary = summarizeWebhookFailure({ status: res.status, data });
      console.error("  webhook no reply:", summary);
      markBridgeStatus(acct.botId, "error", summary);
      replies = [buildHumanBridgeFallback({ status: res.status, code: data.code, error: data.error })];
    }
    // ─── 语音模式：先发文字保证送达，再追语音 ───
    const voiceMode = process.env.VOICE_MODE !== "0" && process.env.VOICE_MODE !== "false";
    // Always send first reply as text (reliable)
    const firstReply = replies[0] || "";
    await sendWechatReply(acct, fromId, ctxToken, firstReply);
    console.log("  -> text (" + (Date.now() - t0) + "ms): " + firstReply.slice(0, 30));
    
    // Then attempt voice
    if (voiceMode && replies.length > 0) {
      const fullReply = replies.join(" ");
      const emotion = data.aiEmotion || "平静";
      try {
        const voice = await fetchTtsAudio(fullReply, emotion);
        await sendWechatVoice(acct, fromId, ctxToken, voice, voice.durationMs);
        console.log("  -> voice (" + (Date.now() - t0) + "ms): " + fullReply.slice(0, 30));
      } catch (voiceErr) {
        console.error("  voice skipped:", voiceErr.message);
      }
    }
    // Send remaining text parts if any
    for (let i = 1; i < replies.length; i += 1) {
      await sleep(Number(process.env.WECHAT_REPLY_PART_DELAY_MS || 900) + Math.floor(Math.random() * 500));
      await sendWechatReply(acct, fromId, ctxToken, replies[i]);
      console.log("  -> part " + (i + 1) + "/" + replies.length + " (" + (Date.now() - t0) + "ms): " + replies[i].slice(0, 30));
    }
  } catch(e) {
    const summary = summarizeWebhookFailure({ error: e.message });
    console.error("  err:", summary);
    markBridgeStatus(acct.botId, "error", summary);
    try {
      const fallback = buildHumanBridgeFallback({ error: e.message });
      await sendWechatReply(acct, fromId, ctxToken, fallback);
      console.log("  -> fallback: " + fallback.slice(0, 30));
    } catch (sendError) {
      console.error("  fallback send failed:", sendError.message);
      markBridgeStatus(acct.botId, "error", "fallback send failed: " + sendError.message);
    }
  }
}

async function pollAccount(acct) {
  try {
    const data = await callApi(acct.baseUrl, "ilink/bot/getupdates", {
      get_updates_buf: acct.syncBuf,
      base_info: { channel_version: "2.4.3", bot_agent: "OpenClaw" }
    }, acct.token);
    if (data && data.ret != null && Number(data.ret) !== 0) {
      markBridgeStatus(acct.botId, "error", "getupdates ret=" + data.ret);
      return;
    }
    markBridgeStatus(acct.botId, "online");
    if (data.get_updates_buf) { acct.syncBuf = data.get_updates_buf; saveSync(acct); }
    if ((data.msgs||[]).length > 0) console.log("[bridge] Got " + data.msgs.length + " msgs, ret=" + data.ret);
    for (const msg of (data.msgs || [])) {
      if (msg.message_type === 1) await handleMessage(acct, msg);
    }
  } catch (e) {
    // If auth failed, try refreshing token from SaaS
    if (e.message && (e.message.includes("401") || e.message.includes("403"))) {
      console.log("[bridge] Auth error for " + acct.id + ", trying DB refresh...");
      if (db) {
        try {
          const row = db.prepare("SELECT value FROM settings WHERE key = ?").get("wechat_" + (db.prepare("SELECT value FROM settings WHERE key = ?").get("wx_bot_" + acct.id.split("@")[0])?.value || "1") + "_token");
          if (row) {
            acct.token = row.value;
            console.log("[bridge] Token refreshed from DB");
          }
        } catch {}
      }
    }
    markBridgeStatus(acct.botId, "error", e.message);
  }
}

// ─── 主循环 ───
async function main() {
  console.log("Multi-account bridge starting...");
  while (true) {
    const accounts = discoverAccounts();
    if (accounts.length === 0) { console.log("No accounts, retrying..."); await sleep(10000); continue; }
    console.log("Polling " + accounts.length + " account(s)");
    await Promise.all(accounts.map(a => pollAccount(a)));
    await sleep(5000);
  }
}
if (process.argv[1] && import.meta.url === pathToFileURL(process.argv[1]).href) {
  main().catch(e => console.error("Fatal:", e));
}
