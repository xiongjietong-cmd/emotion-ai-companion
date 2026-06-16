import Database from "better-sqlite3";
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "url";

const STATE_DIR = process.env.WECHAT_STATE_DIR || "D:/Documents/New project 2/.openclaw-state/openclaw-weixin";
// Look up bot ID from SaaS database by WeChat account
const DB_PATH = path.join(path.dirname(fileURLToPath(import.meta.url)), "..", "data", "emotion-saas.db");
const DB = (() => { try { return new Database(DB_PATH, {readonly: true}); } catch { return null; } })();


// Auto-detect WeChat account
function findAccount() {
  try {
    const dir = path.join(STATE_DIR, "accounts");
    const files = fs.readdirSync(dir).filter(f => f.endsWith(".json") && !f.includes("context") && !f.includes("sync"));
    if (files.length === 0) throw new Error("No account found");
    const id = files[0].replace(".json", "");
    console.log("Using account:", id);
    return id;
  } catch(e) {
    console.error("No WeChat account found. Run QR scan first.");
    process.exit(1);
  }
}

const ACCOUNT_ID = findAccount();

// Look up which bot this account belongs to
function getBotIdForAccount(){
  if(!DB) return 1;
  const key = "wx_bot_" + ACCOUNT_ID.split("@")[0];
  try {
    const row = DB.prepare("SELECT value FROM settings WHERE key = ?").get(key);
    return row ? parseInt(row.value) : 1;
  } catch { return 1; }
}
const BOT_ID = getBotIdForAccount();
console.log("Mapped to bot:", BOT_ID);
const EMOTION_URL = "http://127.0.0.1:3000/api/webhook/" + BOT_ID;
const account = JSON.parse(fs.readFileSync(path.join(STATE_DIR, "accounts", ACCOUNT_ID + ".json"), "utf-8"));
const TOKEN = account.token;
const BASE_URL = account.baseUrl;

const SYNC_FILE = process.env.WECHAT_SYNC_FILE || path.join(process.cwd(), ACCOUNT_ID + ".sync.json");
let syncBuf = "";
try { syncBuf = JSON.parse(fs.readFileSync(SYNC_FILE, "utf-8")).get_updates_buf || ""; } catch {}

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

function buildBaseInfo() {
  return { channel_version: "2.4.3", bot_agent: "OpenClaw" };
}

async function callApi(endpoint, body) {
  const url = BASE_URL.replace(/\/$/, "") + "/" + endpoint;
  const res = await fetch(url, { method: "POST", headers: buildHeaders(TOKEN), body: JSON.stringify(body) });
  return res.json();
}

async function getUpdates() {
  const data = await callApi("ilink/bot/getupdates", { get_updates_buf: syncBuf, base_info: buildBaseInfo() });
  if (data.get_updates_buf) { syncBuf = data.get_updates_buf; fs.writeFileSync(SYNC_FILE, JSON.stringify({ get_updates_buf: syncBuf }), "utf-8"); }
  return data.msgs || [];
}

async function sendMessage(toUserId, contextToken, text) {
  await callApi("ilink/bot/sendmessage", {
    msg: {
      from_user_id: "", to_user_id: toUserId,
      client_id: "wb-" + Date.now() + "-" + Math.random().toString(36).slice(2, 8),
      message_type: 2, message_state: 2,
      item_list: [{ type: 1, text_item: { text } }],
      context_token: contextToken || ""
    },
    base_info: buildBaseInfo()
  });
}

async function handleMessage(msg) {
  const ti = (msg.item_list || []).find(i => i.type === 1);
  if (!ti || !ti.text_item) return;
  const text = ti.text_item.text.trim();
  if (!text) return;
  const fromId = msg.from_user_id || "";
  const ctxToken = msg.context_token || "";
  console.log("[" + new Date().toLocaleTimeString() + "] <- " + text.slice(0, 30));
  try {
    const t0 = Date.now();
    const res = await fetch(EMOTION_URL, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ text, senderId: fromId }) });
    const data = await res.json();
    const reply = data.reply || data.text || "";
    if (reply) {
      await sendMessage(fromId, ctxToken, reply);
      console.log("  -> (" + (Date.now() - t0) + "ms): " + reply.slice(0, 30));
    }
  } catch(e) { console.error("err:", e.message); }
}

console.log("WeChat bridge started (account: " + ACCOUNT_ID + ")");

while (true) {
  try {
    const msgs = await getUpdates();
    for (const msg of msgs) {
      if (msg.message_type === 1) await handleMessage(msg);
    }
  } catch(e) { await new Promise(r => setTimeout(r, 5000)); }
}
