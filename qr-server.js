import { createServer } from "http";
import { spawn } from "child_process";
import { readFileSync, readdirSync } from "fs";
import { join } from "path";

const PORT = 3002;
const STATE_DIR = process.env.OPENCLAW_STATE_DIR || join(process.env.HOME || ".", ".openclaw-state");
const ACCOUNTS_DIR = join(STATE_DIR, "openclaw-weixin", "accounts");
const OPENCLAW_CMD = process.env.OPENCLAW_CMD || "openclaw";

const sessions = {};

const server = createServer(async (req, res) => {
  res.setHeader("Content-Type", "application/json");
  res.setHeader("Access-Control-Allow-Origin", "*");
  res.setHeader("Access-Control-Allow-Methods", "POST, GET, OPTIONS");
  res.setHeader("Access-Control-Allow-Headers", "Content-Type");
  if (req.method === "OPTIONS") { res.end(JSON.stringify({})); return; }

  const url = new URL(req.url, "http://localhost");

  if (req.method === "POST" && url.pathname === "/start") {
    const body = JSON.parse(await readBody(req));
    const { botId } = body;
    if (!botId) { res.writeHead(400); res.end(JSON.stringify({error:"need botId"})); return; }

    const sessionId = "wx" + Date.now();
    sessions[sessionId] = { botId, status: "waiting", output: "" };

    const env = { ...process.env, OPENCLAW_STATE_DIR: STATE_DIR };
    const child = spawn(OPENCLAW_CMD, ["channels", "login", "--channel", "openclaw-weixin"], { env, stdio: "pipe" });

    child.stdout.on("data", (chunk) => {
      sessions[sessionId].output += chunk.toString();
    });
    child.stderr.on("data", (chunk) => {
      sessions[sessionId].output += chunk.toString();
    });

    child.on("close", (code) => {
      if (code === 0) {
        try {
          const files = readdirSync(ACCOUNTS_DIR).filter(f => f.endsWith(".json") && !f.includes("context") && !f.includes("sync"));
          const latest = files.sort().reverse()[0];
          if (latest) {
            const data = JSON.parse(readFileSync(join(ACCOUNTS_DIR, latest), "utf-8"));
            sessions[sessionId].status = "done";
            sessions[sessionId].token = data.token;
            sessions[sessionId].wxUserId = data.userId;
          } else { sessions[sessionId].status = "error"; }
        } catch(e) { sessions[sessionId].status = "error"; }
      } else {
        sessions[sessionId].status = "error";
      }
    });

    res.end(JSON.stringify({ ok: true, sessionId }));
    return;
  }

  if (req.method === "GET" && url.pathname === "/status") {
    const sessionId = url.searchParams.get("session");
    const s = sessions[sessionId];
    if (!s) { res.end(JSON.stringify({status:"not_found"})); return; }

    let qrText = "";
    // Try to find any URL in the output
    const urls = s.output.match(/https?:\/\/[^\s"']+/g);
    if (urls) qrText = urls[urls.length - 1];

    res.end(JSON.stringify({
      status: s.status,
      qrText: qrText,
      token: s.token || "",
      wxUserId: s.wxUserId || "",
      botId: s.botId
    }));
    return;
  }

  res.writeHead(404); res.end(JSON.stringify({}));
});

function readBody(req) {
  return new Promise((resolve) => {
    let data = "";
    req.on("data", c => data += c);
    req.on("end", () => resolve(data));
  });
}

server.listen(PORT, () => console.log("QR server on " + PORT));
