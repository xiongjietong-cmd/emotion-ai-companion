// multi-wechat-bridge.js — 多账号微信桥接
// 从数据库读取所有已绑定的微信账号，统一轮询，分发到各机器人 webhook

import Database from "better-sqlite3";
import { fileURLToPath } from "url";
import { dirname, join } from "path";
import crypto from "crypto";

const __dirname = dirname(fileURLToPath(import.meta.url));
const DB_PATH = join(__dirname, "..", "data", "emotion-saas.db");
const SAAS_URL = process.env.SAAS_URL || "http://127.0.0.1:3000";

// ── 工具 ──
function sleep(ms) { return new Promise(r => setTimeout(r, ms)); }

// ── 微信 API ──
function buildHeaders(token) {
  const uin = Buffer.from(String(Math.floor(Math.random() * 4294967295)), "utf-8").toString("base64");
  return {
    "Content-Type": "application/json",
    "AuthorizationType": "ilink_bot_token",
    "Authorization": "Bearer " + (token || "").trim(),
    "X-WECHAT-UIN": uin,
    "iLink-App-Id": "",
    "iLink-App-ClientVersion": "131328"
  };
}

async function callApi(baseUrl, endpoint, body, token) {
  const url = baseUrl.replace(//$/, "") + "/" + endpoint;
  const res = await fetch(url, { method: "POST", headers: buildHeaders(token), body: JSON.stringify(body) });
  const text = await res.text();
  try { return JSON.parse(text); } catch { return { _raw: text }; }
}

// ── 账号管理 ──
let accounts = []; // [{botId, token, baseUrl, syncBuf, wxUserId}]
let db;

function loadAccounts() {
  db = new Database(DB_PATH, { readonly: true });
  const rows = db.prepare(
    "SELECT bot_id, token, base_url, sync_buf, wx_user_id FROM wechat_accounts WHERE is_connected = 1"
  ).all();
  db.close();

  accounts = rows.map(r => ({
    botId: r.bot_id,
    token: r.token,
    baseUrl: r.base_url || "https://ilinkai.weixin.qq.com",
    syncBuf: r.sync_buf || "",
    wxUserId: r.wx_user_id || ""
  }));
  console.log("已加载 " + accounts.length + " 个微信账号");
}

function saveSyncBuf(botId, syncBuf) {
  const wdb = new Database(DB_PATH);
  wdb.prepare("UPDATE wechat_accounts SET sync_buf = ? WHERE bot_id = ?").run(syncBuf, botId);
  wdb.close();
}

// ── 消息处理 ──
async function handleMessage(acct, msg) {
  const textItem = (msg.item_list || []).find(i => i.type === 1);
  if (!textItem || !textItem.text_item) return;

  const text = textItem.text_item.text.trim();
  if (!text) return;

  const fromId = msg.from_user_id || "";
  const ctxToken = msg.context_token || "";

  console.log("[" + new Date().toLocaleTimeString() + "] bot=" + acct.botId + " 收到: " + text.slice(0, 30));

  try {
    const t0 = Date.now();
    const res = await fetch(SAAS_URL + "/api/webhook/" + acct.botId, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ text, senderId: fromId, contextToken: ctxToken })
    });
    const data = await res.json().catch(() => ({}));
    const reply = data.text || data.reply || "";
    const elapsed = Date.now() - t0;

    if (reply) {
      // 发回微信
      await callApi(acct.baseUrl, "ilink/bot/sendmessage", {
        msg: {
          from_user_id: "",
          to_user_id: fromId,
          client_id: "wb-" + Date.now() + "-" + Math.random().toString(36).slice(2, 8),
          message_type: 2,
          message_state: 2,
          item_list: [{ type: 1, text_item: { text: reply } }],
          context_token: ctxToken || ""
        },
        base_info: { channel_version: "2.4.3", bot_agent: "OpenClaw" }
      }, acct.token);
      console.log("  -> 回复 (" + elapsed + "ms): " + reply.slice(0, 30));
    }
  } catch (e) {
    console.error("  -> 处理失败:", e.message);
  }
}

// ── 轮询 ──
async function pollAccount(acct) {
  try {
    const data = await callApi(acct.baseUrl, "ilink/bot/getupdates", {
      get_updates_buf: acct.syncBuf,
      base_info: { channel_version: "2.4.3", bot_agent: "OpenClaw" }
    }, acct.token);

    if (data.get_updates_buf) {
      acct.syncBuf = data.get_updates_buf;
      saveSyncBuf(acct.botId, acct.syncBuf);
    }

    const msgs = data.msgs || [];
    for (const msg of msgs) {
      if (msg.message_type === 1) await handleMessage(acct, msg);
    }
  } catch (e) {
    // 长轮询超时正常
  }
}

// ── 主循环 ──
async function main() {
  console.log("多账号微信桥接启动");
  console.log("SaaS 地址: " + SAAS_URL);

  while (true) {
    loadAccounts();
    if (accounts.length === 0) {
      console.log("暂无微信账号，60秒后重试...");
      await sleep(60000);
      continue;
    }
    // 并行轮询所有账号
    await Promise.all(accounts.map(a => pollAccount(a)));
  }
}

main().catch(e => console.error("Fatal:", e));
