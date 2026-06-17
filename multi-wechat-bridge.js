// multi-wechat-bridge.js — 多账号微信桥接 (生产版)
// 从 OpenClaw state 自动发现所有账号，映射到 SaaS bot，并行轮询

import fs from "node:fs";
import path from "node:path";
import Database from "better-sqlite3";
import { fileURLToPath } from "url";

const STATE_DIR = process.env.WECHAT_STATE_DIR || "D:/Documents/New project 2/.openclaw-state/openclaw-weixin";
const SAAS_URL = process.env.SAAS_URL || "http://127.0.0.1:3000";
const DB_PATH = path.join(path.dirname(fileURLToPath(import.meta.url)), "data", "emotion-saas.db");

let db = null;
try { db = new Database(DB_PATH, { readonly: true }); } catch(e) { console.error("DB open failed:", e.message); }

function sleep(ms) { return new Promise(r => setTimeout(r, ms)); }

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
    const reply = data.text || data.reply || "";
    if (reply) {
      await callApi(acct.baseUrl, "ilink/bot/sendmessage", {
        msg: {
          from_user_id: "", to_user_id: fromId,
          client_id: "mb-" + Date.now() + "-" + Math.random().toString(36).slice(2, 8),
          message_type: 2, message_state: 2,
          item_list: [{ type: 1, text_item: { text: reply } }],
          context_token: ctxToken || ""
        },
        base_info: { channel_version: "2.4.3", bot_agent: "OpenClaw" }
      }, acct.token);
      console.log("  -> (" + (Date.now() - t0) + "ms): " + reply.slice(0, 30));
    }
  } catch(e) { console.error("  err:", e.message); }
}

async function pollAccount(acct) {
  try {
    const data = await callApi(acct.baseUrl, "ilink/bot/getupdates", {
      get_updates_buf: acct.syncBuf,
      base_info: { channel_version: "2.4.3", bot_agent: "OpenClaw" }
    }, acct.token);
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
  }
}
main().catch(e => console.error("Fatal:", e));
