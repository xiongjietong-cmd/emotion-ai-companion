// wechat-bridge.js — 直连微信 API，绕过 OpenClaw agent
// 启动: node wechat-bridge.js
// 依赖: node-fetch (Node 18+ 内置 fetch)

import fs from "node:fs";
import path from "node:path";

// ─── 配置 ───
const ACCOUNT_ID = "6ae71321691f-im-bot";
const STATE_DIR = process.env.WECHAT_STATE_DIR || "D:/Documents/New project 2/.openclaw-state/openclaw-weixin";
const EMOTION_URL = process.env.EMOTION_URL || "http://134.175.8.123:3000/openclaw/message";

// 加载账户凭证
// 优先从环境变量读取，否则从文件
let TOKEN, BASE_URL;
if (process.env.WECHAT_TOKEN && process.env.WECHAT_BASE_URL) {
  TOKEN = process.env.WECHAT_TOKEN;
  BASE_URL = process.env.WECHAT_BASE_URL;
  console.log("Using env vars for WeChat credentials");
} else {
  const account = JSON.parse(
    fs.readFileSync(path.join(STATE_DIR, "accounts", ACCOUNT_ID + ".json"), "utf-8")
  );
  TOKEN = account.token;
  BASE_URL = account.baseUrl;
}
const SYNC_FILE = path.join(STATE_DIR, "accounts", ACCOUNT_ID + ".sync.json");

// 上次同步游标
let syncBuf = "";
try {
  syncBuf = JSON.parse(fs.readFileSync(SYNC_FILE, "utf-8")).get_updates_buf || "";
} catch { syncBuf = ""; }

// API call with proper WeChat headers
function buildHeaders(token) {
  const uint32 = Buffer.from(String(Math.floor(Math.random() * 4294967295)), "utf-8").toString("base64");
  return {
    "Content-Type": "application/json",
    "AuthorizationType": "ilink_bot_token",
    "Authorization": "Bearer " + (token || "").trim(),
    "X-WECHAT-UIN": uint32,
    "iLink-App-Id": "bot",
    "iLink-App-ClientVersion": String(132099)
  };
}

function buildBaseInfo() {
  return { channel_version: "2.4.3", bot_agent: "OpenClaw" };
}

async function callApi(endpoint, body, token) {
  const base = "https://ilinkai.weixin.qq.com".replace(/\/$/, "") + "/";
  const url = new URL(endpoint, base).toString();
  const res = await fetch(url, {
    method: "POST",
    headers: buildHeaders(token),
    body: JSON.stringify(body)
  });
  const text = await res.text();
  try { return JSON.parse(text); } catch { return { _raw: text }; }
}

async function getUpdates() {
  const data = await callApi("ilink/bot/getupdates", { get_updates_buf: syncBuf, base_info: buildBaseInfo() }, TOKEN);
  if (data.get_updates_buf) {
    syncBuf = data.get_updates_buf;
    fs.writeFileSync(SYNC_FILE, JSON.stringify({ get_updates_buf: syncBuf }), "utf-8");
  }
  if (data.ret !== 0 && data.errcode) console.error("getUpdates err:", data.errcode, data.errmsg);
  return data.msgs || [];
}

async function sendMessage(toUserId, contextToken, text) {
  const clientId = "wb-" + Date.now() + "-" + Math.random().toString(36).slice(2,8);
  console.log("  send to=" + toUserId.slice(0,12) + "... ctx=" + (contextToken||"").slice(0,10) + "... text=" + text.slice(0,20));
  const sendRes = await callApi("ilink/bot/sendmessage", {
    msg: {
      from_user_id: "",
      to_user_id: toUserId,
      client_id: clientId,
      message_type: 2,
      message_state: 2,
      item_list: [{ type: 1, text_item: { text } }],
      context_token: contextToken || ""
    },
    base_info: buildBaseInfo()
  }, TOKEN);
  console.log("  send resp: ret=" + sendRes.ret + " err=" + (sendRes.errcode||"none"));
  // sendMessage returns {} on success — ret is undefined, that is OK
}
// ─── 消息处理 ───
async function handleMessage(msg) {
  const textItem = (msg.item_list || []).find(i => i.type === 1);
  if (!textItem || !textItem.text_item) return;

  const text = textItem.text_item.text.trim();
  if (!text) return;

  const fromId = msg.from_user_id || "";
  const ctxToken = msg.context_token || "";

  console.log(`[${new Date().toLocaleTimeString()}] 收到: ${text.slice(0, 30)}`);

  try {
    const t0 = Date.now();
    const res = await fetch(EMOTION_URL, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ text, senderId: fromId })
    });
    const data = await res.json();
    const reply = data.reply || data.text || data.message || "";
    const elapsed = Date.now() - t0;

    if (reply) {
      await sendMessage(fromId, ctxToken, reply);
      console.log(`  -> 回复 (${elapsed}ms): ${reply.slice(0, 30)}`);
    }
  } catch (e) {
    console.error("  -> 处理失败:", e.message);
  }
}

// ─── 主循环 ───
console.log("微信桥接已启动 (绕过 OpenClaw agent)");
console.log("账户:", ACCOUNT_ID);
console.log("");

async function poll() {
  while (true) {
    try {
      const msgs = await getUpdates();
      for (const msg of msgs) {
        // 只处理文本消息，跳过机器人自己的消息
        if (msg.message_type === 1) { // 1 = USER
          await handleMessage(msg);
        }
      }
    } catch (e) {
      console.error("轮询错误:", e.message);
      await sleep(5000);
    }
  }
}

function sleep(ms) { return new Promise(r => setTimeout(r, ms)); }

poll();
