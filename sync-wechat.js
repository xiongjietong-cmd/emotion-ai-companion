// sync-wechat.js — 从 OpenClaw 同步微信凭证到 SaaS 数据库
// 用法: node sync-wechat.js <botId>

import Database from "better-sqlite3";
import { fileURLToPath } from "url";
import { dirname, join } from "path";

const __dirname = dirname(fileURLToPath(import.meta.url));
const DB_PATH = join(__dirname, "..", "data", "emotion-saas.db");
const STATE_DIR = process.env.OPENCLAW_STATE_DIR
  || join(process.env.HOME || process.env.USERPROFILE || ".", ".openclaw-state", "openclaw-weixin");

const botId = parseInt(process.argv[2]);
if (!botId) {
  console.log("用法: node sync-wechat.js <botId>");
  console.log("先运行 openclaw channels login --channel openclaw-weixin 扫码登录");
  process.exit(1);
}

// 读取最新的微信账户凭证
const accountsDir = join(STATE_DIR, "accounts");
const files = fs.readdirSync(accountsDir).filter(f => f.endsWith(".json") && !f.includes("context") && !f.includes("sync"));

if (files.length === 0) {
  console.log("未找到微信凭证，请先运行:");
  console.log("  openclaw channels login --channel openclaw-weixin");
  process.exit(1);
}

// 取最新的账户
let latest = null;
for (const f of files) {
  const data = JSON.parse(fs.readFileSync(join(accountsDir, f), "utf-8"));
  if (!latest || new Date(data.savedAt) > new Date(latest.savedAt)) {
    latest = { accountId: f.replace(".json", ""), ...data };
  }
}

console.log("找到微信账户:", latest.accountId);
console.log("用户ID:", latest.userId);

// 写入 SaaS 数据库
const db = new Database(DB_PATH);
db.pragma("journal_mode = WAL");

const existing = db.prepare("SELECT id FROM wechat_accounts WHERE bot_id = ?").get(botId);
if (existing) {
  db.prepare("UPDATE wechat_accounts SET token=?, base_url=?, wx_user_id=?, is_connected=1 WHERE bot_id=?")
    .run(latest.token, latest.baseUrl, latest.userId, botId);
  console.log("已更新绑定");
} else {
  db.prepare("INSERT INTO wechat_accounts (bot_id, token, base_url, wx_user_id, is_connected) VALUES (?,?,?,?,1)")
    .run(botId, latest.token, latest.baseUrl, latest.userId);
  console.log("已创建绑定");
}

db.close();
console.log("\n机器人 " + botId + " 已绑定微信 " + latest.userId);
console.log("桥接将自动接管该机器人的微信消息");
