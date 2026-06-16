// multi-wechat-bridge.js — 直连微信 API，从 SaaS 数据库读取所有账号

import Database from "better-sqlite3";
import { fileURLToPath } from "url";
import { dirname, join } from "path";

const __dirname = dirname(fileURLToPath(import.meta.url));
const DB_PATH = join(__dirname, "..", "data", "emotion-saas.db");
const SAAS_URL = process.env.SAAS_URL || "http://127.0.0.1:3000";

const STATE_DIR = process.env.OPENCLAW_STATE_DIR || "D:/Documents/New project 2/.openclaw-state";
const ACCOUNTS_DIR = join(STATE_DIR, "openclaw-weixin", "accounts");
const INDEX_FILE = join(STATE_DIR, "openclaw-weixin", "accounts.json");

function sleep(ms) { return new Promise(r => setTimeout(r, ms)); }

function buildHeaders(token) {
  const uin = String(Math.floor(Math.random() * 4294967295));
  return {
    "Content-Type": "application/json",
    "AuthorizationType": "ilink_bot_token",
    "Authorization": "Bearer " + (token || "").trim(),
    "X-WECHAT-UIN": Buffer.from(uin).toString("base64"),
    "iLink-App-Id": "bot",
    "iLink-App-ClientVersion": "131328"
  };
}

function loadAccounts() {
  try {
    const { readFileSync, readdirSync, existsSync } = require("fs");
    if (!existsSync(INDEX_FILE)) return [];
    const ids = JSON.parse(readFileSync(INDEX_FILE, "utf-8"));
    return ids.map(id => {
      try {
        const data = JSON.parse(readFileSync(join(ACCOUNTS_DIR, id + ".json"), "utf-8"));
        const syncFile = join(ACCOUNTS_DIR, id + ".sync.json");
        let syncBuf = "";
        try { syncBuf = JSON.parse(readFileSync(syncFile, "utf-8")).get_updates_buf || ""; } catch {}
        // Also read bot mapping from SaaS DB
        const db = new Database(DB_PATH, { readonly: true });
        const row = db.prepare("SELECT value FROM settings WHERE key = 'wx_user_' || ?").get(id.split("@")[0]);
        db.close();
        return { accountId: id, token: data.token, baseUrl: data.baseUrl, syncBuf, botId: row ? parseInt(row.value) : 1 };
      } catch { return null; }
    }).filter(Boolean);
  } catch { return []; }
}

async function callApi(baseUrl, endpoint, body, token) {
  const url = baseUrl.replace(/\/$/, "") + "/" + endpoint;
  const res = await fetch(url, { method: "POST", headers: buildHeaders(token), body: JSON.stringify(body) });
  const text = await res.text();
  try { return JSON.parse(text); } catch { return {}; }
}

function saveSync(accountId, syncBuf) {
  try {
    const { writeFileSync } = require("fs");
    const syncFile = join(ACCOUNTS_DIR, accountId + ".sync.json");
    writeFileSync(syncFile, JSON.stringify({ get_updates_buf: syncBuf }), "utf-8");
  } catch {}
}

async function handleMessage(acct, msg) {
  const ti = (msg.item_list || []).find(i => i.type === 1);
  if (!ti || !ti.text_item) return;
  const text = ti.text_item.text.trim();
  if (!text) return;

  const fromId = msg.from_user_id || "";
  const ctxToken = msg.context_token || "";
  console.log("[" + new Date().toLocaleTimeString() + "] " + acct.accountId.slice(0,10) + " <- " + text.slice(0,30));

  try {
    const t0 = Date.now();
    const res = await fetch(SAAS_URL + "/api/webhook/" + (acct.botId || 1), {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ text, senderId: fromId, contextToken: ctxToken })
    });
    const data = await res.json().catch(() => ({}));
    const reply = data.text || data.reply || "";
    const elapsed = Date.now() - t0;

    if (reply) {
      await callApi(acct.baseUrl, "ilink/bot/sendmessage", {
        msg: {
          from_user_id: "", to_user_id: fromId,
          client_id: "wb-" + Date.now() + "-" + Math.random().toString(36).slice(2, 8),
          message_type: 2, message_state: 2,
          item_list: [{ type: 1, text_item: { text: reply } }],
          context_token: ctxToken || ""
        },
        base_info: { channel_version: "2.4.3", bot_agent: "OpenClaw" }
      }, acct.token);
      console.log("  -> (" + elapsed + "ms): " + reply.slice(0, 30));
    }
  } catch(e) { console.error("  err:", e.message); }
}

async function pollAccount(acct) {
  try {
    const data = await callApi(acct.baseUrl, "ilink/bot/getupdates", {
      get_updates_buf: acct.syncBuf,
      base_info: { channel_version: "2.4.3", bot_agent: "OpenClaw" }
    }, acct.token);
    if (data.get_updates_buf) { acct.syncBuf = data.get_updates_buf; saveSync(acct.accountId, acct.syncBuf); }
    for (const msg of (data.msgs || [])) {
      if (msg.message_type === 1) await handleMessage(acct, msg);
    }
  } catch {}
}

async function main() {
  console.log("Multi-account bridge starting (direct API, no agent)");
  while (true) {
    const accounts = loadAccounts();
    if (accounts.length === 0) { await sleep(10000); continue; }
    await Promise.all(accounts.map(a => pollAccount(a)));
  }
}
main().catch(e => console.error("Fatal:", e));
