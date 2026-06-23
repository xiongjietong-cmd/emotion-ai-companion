import fs from "node:fs";
import path from "node:path";
import Database from "better-sqlite3";
import { fileURLToPath, pathToFileURL } from "node:url";

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

const STATE_DIR = process.env.WECHAT_STATE_DIR || path.join(__dirname, ".openclaw-state", "openclaw-weixin");
const SAAS_URL = process.env.SAAS_URL || "http://127.0.0.1:3000";
const DB_PATH = path.join(__dirname, "data", "emotion-saas.db");
const SEND_DELAY_MS = Number(process.env.WECHAT_REPLY_PART_DELAY_MS || 800);

let db = null;
try {
  db = new Database(DB_PATH, { readonly: true });
} catch (error) {
  console.error("[bridge] DB open failed:", error.message);
}

const warnedUnmappedAccounts = new Set();

function sleep(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

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

async function callApi(baseUrl, endpoint, body, token) {
  const url = baseUrl.replace(/\/$/, "") + "/" + endpoint;
  const response = await fetch(url, {
    method: "POST",
    headers: buildHeaders(token),
    body: JSON.stringify(body)
  });
  const data = await response.json().catch(() => ({}));
  if (!response.ok) {
    const error = new Error(`WeChat API failed: ${response.status}`);
    error.status = response.status;
    error.data = data;
    throw error;
  }
  return data;
}

function readMappedBotId(accountId) {
  if (!db) return null;
  try {
    const key = "wx_bot_" + accountId.split("@")[0];
    const row = db.prepare("SELECT value FROM settings WHERE key = ?").get(key);
    return row ? row.value : null;
  } catch {
    return null;
  }
}

export function resolveBotId(accountId, accountData = {}, readMapping = readMappedBotId) {
  const mapped = Number(readMapping(accountId));
  if (Number.isInteger(mapped) && mapped > 0) return mapped;
  const saved = Number(accountData.botId);
  if (Number.isInteger(saved) && saved > 0) return saved;
  return null;
}

function discoverAccounts() {
  const dir = path.join(STATE_DIR, "accounts");
  try {
    return fs.readdirSync(dir)
      .filter((file) => file.endsWith(".json") && !file.includes("context") && !file.includes("sync"))
      .map((file) => {
        const id = file.replace(".json", "");
        const data = JSON.parse(fs.readFileSync(path.join(dir, file), "utf-8"));
        const botId = resolveBotId(id, data);
        if (!botId) {
          if (!warnedUnmappedAccounts.has(id)) {
            console.error(`[bridge] account ${id} has no bot mapping; skipping until it is bound`);
            warnedUnmappedAccounts.add(id);
          }
          return null;
        }
        let syncBuf = "";
        try {
          syncBuf = JSON.parse(fs.readFileSync(path.join(dir, id + ".sync.json"), "utf-8")).get_updates_buf || "";
        } catch {}
        return {
          id,
          token: data.token,
          baseUrl: data.baseUrl || "https://ilinkai.weixin.qq.com",
          syncBuf,
          botId
        };
      })
      .filter(Boolean);
  } catch (error) {
    console.error("[bridge] account discovery failed:", error.message);
    return [];
  }
}

function saveSync(account) {
  try {
    const file = path.join(STATE_DIR, "accounts", account.id + ".sync.json");
    fs.writeFileSync(file, JSON.stringify({ get_updates_buf: account.syncBuf }), "utf-8");
  } catch {}
}

export function extractWebhookReplies(data = {}) {
  if (!data || data.ok === false) return [];
  const raw = Array.isArray(data.texts)
    ? data.texts
    : Array.isArray(data.replyParts)
      ? data.replyParts
      : data.text
        ? [data.text]
        : data.reply
          ? [data.reply]
          : [];
  return raw.map((part) => String(part || "").trim()).filter(Boolean);
}

export function extractWebhookReply(data = {}) {
  return extractWebhookReplies(data)[0] || "";
}

export function buildHumanBridgeFallback() {
  return "服务器异常，暂时无法回复。请稍后再试。";
}

export function summarizeWebhookFailure({ status, data } = {}) {
  const code = data?.code || data?.detail?.code || "";
  const error = data?.error || data?.detail?.message || data?.message || "";
  return `webhook failed status=${status || "unknown"} code=${code || "none"} error=${error || "none"}`;
}

async function sendText(account, toUserId, contextToken, text) {
  return callApi(account.baseUrl, "ilink/bot/sendmessage", {
    msg: {
      from_user_id: "",
      to_user_id: toUserId,
      client_id: "mb-" + Date.now() + "-" + Math.random().toString(36).slice(2, 8),
      message_type: 2,
      message_state: 2,
      item_list: [{ type: 1, text_item: { text } }],
      context_token: contextToken || ""
    },
    base_info: { channel_version: "2.4.3", bot_agent: "OpenClaw" }
  }, account.token);
}

async function handleMessage(account, message) {
  const textItem = (message.item_list || []).find((item) => item.type === 1);
  const text = String(textItem?.text_item?.text || "").trim();
  if (!text) return;

  const fromId = message.from_user_id || "";
  const contextToken = message.context_token || "";
  console.log(`[${new Date().toLocaleTimeString()}] ${account.id.slice(0, 12)} -> bot ${account.botId}: ${text.slice(0, 30)}`);

  try {
    const startedAt = Date.now();
    const response = await fetch(`${SAAS_URL}/api/webhook/${account.botId}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ text, senderId: fromId, contextToken })
    });
    const data = await response.json().catch(() => ({}));
    const replies = extractWebhookReplies(data);

    if (!response.ok || !replies.length) {
      console.error("[bridge]", summarizeWebhookFailure({ status: response.status, data }));
      await sendText(account, fromId, contextToken, buildHumanBridgeFallback({ status: response.status, data }));
      return;
    }

    for (let index = 0; index < replies.length; index += 1) {
      if (index > 0) await sleep(SEND_DELAY_MS);
      await sendText(account, fromId, contextToken, replies[index]);
      console.log(`  -> part ${index + 1}/${replies.length} (${Date.now() - startedAt}ms): ${replies[index].slice(0, 30)}`);
    }
  } catch (error) {
    console.error("[bridge] message error:", error.message);
    try {
      await sendText(account, fromId, contextToken, buildHumanBridgeFallback({ error: error.message }));
    } catch (sendError) {
      console.error("[bridge] fallback send failed:", sendError.message);
    }
  }
}

async function pollAccount(account) {
  const data = await callApi(account.baseUrl, "ilink/bot/getupdates", {
    get_updates_buf: account.syncBuf,
    base_info: { channel_version: "2.4.3", bot_agent: "OpenClaw" }
  }, account.token);
  if (data.get_updates_buf) {
    account.syncBuf = data.get_updates_buf;
    saveSync(account);
  }
  if ((data.msgs || []).length > 0) {
    console.log(`[bridge] got ${data.msgs.length} message(s), ret=${data.ret}`);
  }
  for (const message of data.msgs || []) {
    if (message.message_type === 1) await handleMessage(account, message);
  }
}

export async function main() {
  console.log("[bridge] multi-account bridge starting");
  while (true) {
    const accounts = discoverAccounts();
    if (!accounts.length) {
      console.log("[bridge] no accounts, retrying");
      await sleep(10000);
      continue;
    }
    await Promise.allSettled(accounts.map((account) => pollAccount(account)));
    await sleep(Number(process.env.WECHAT_POLL_INTERVAL_MS || 2000));
  }
}

const isDirectRun = process.argv[1] && pathToFileURL(path.resolve(process.argv[1])).href === import.meta.url;
if (isDirectRun) {
  main().catch((error) => {
    console.error("[bridge] fatal:", error);
    process.exitCode = 1;
  });
}
