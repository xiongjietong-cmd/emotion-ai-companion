const args = process.argv.slice(2);

function getArg(name) {
  const index = args.indexOf(name);
  return index >= 0 ? args[index + 1] || "" : "";
}

const text = getArg("--text").trim();
const senderId = getArg("--sender").trim();
const endpoint = process.env.EMOTION_COMPANION_URL || "http://127.0.0.1:3000/openclaw/message";
const serverErrorReply = "⚠️ 服务器异常：我这边暂时连不上啦，可能是本地陪伴服务还没启动。先帮我启动一下，我马上回来继续陪你。";

if (!text) {
  console.error("Message text is required");
  process.exit(2);
}

try {
  const response = await fetch(endpoint, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ text, senderId })
  });

  const body = await response.json().catch(() => ({}));
  if (!response.ok) {
    process.stdout.write(serverErrorReply);
    process.exit(0);
  }

  process.stdout.write(body.reply || body.text || body.message || serverErrorReply);
} catch {
  process.stdout.write(serverErrorReply);
  process.exit(0);
}
