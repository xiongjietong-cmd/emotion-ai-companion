// reply.mjs — OpenClaw skill -> SaaS webhook
// 用法: node reply.mjs --text "消息" --sender "发送者" --bot 机器人ID
// 环境变量: SAAS_URL (默认 http://127.0.0.1:3000)

const args = process.argv.slice(2);
function getArg(name) { const i = args.indexOf(name); return i >= 0 ? (args[i+1] || "") : ""; }

const text = getArg("--text").trim();
const sender = getArg("--sender").trim();
const botId = getArg("--bot").trim() || process.env.BOT_ID || "";
const saasUrl = process.env.SAAS_URL || "http://127.0.0.1:3000";

if (!text) { console.error("需要 --text"); process.exit(2); }

try {
  const body = JSON.stringify({ text, senderId: sender });
  const url = botId ? saasUrl + "/api/webhook/" + botId : saasUrl + "/api/chat/1";
  const res = await fetch(url, { method: "POST", headers: { "Content-Type": "application/json" }, body });
  const data = await res.json().catch(() => ({}));
  process.stdout.write(data.reply || data.text || data.message || "服务器异常");
} catch {
  process.stdout.write("服务器异常：服务未启动");
}
