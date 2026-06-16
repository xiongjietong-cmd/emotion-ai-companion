// qr-server.js — 扫码服务器
// SaaS 端运行，接收扫码请求，调用 OpenClaw 登录，流式返回二维码给前端

import { createServer } from "http";
import { spawn } from "child_process";
import { readFileSync, readdirSync, existsSync } from "fs";
import { join } from "path";

const PORT = 3002;
const STATE_DIR = process.env.OPENCLAW_STATE_DIR || join(process.env.HOME || ".", ".openclaw-state");
const ACCOUNTS_DIR = join(STATE_DIR, "openclaw-weixin", "accounts");

// 活跃的扫码会话
const sessions = {};

const server = createServer(async (req, res) => {
  res.setHeader("Content-Type", "application/json");
  res.setHeader("Access-Control-Allow-Origin", "*");
  res.setHeader("Access-Control-Allow-Methods", "POST, GET, OPTIONS");
  res.setHeader("Access-Control-Allow-Headers", "Content-Type");

  if (req.method === "OPTIONS") { res.end("{}"); return; }

  const url = new URL(req.url, "http://localhost");

  // POST /start — 启动扫码
  if (req.method === "POST" && url.pathname === "/start") {
    const body = await readBody(req);
    const { botId } = JSON.parse(body);
    if (!botId) { res.writeHead(400); res.end(JSON.stringify({error:"need botId"})); return; }

    const sessionId = "wx-" + Date.now();
    sessions[sessionId] = { botId, status: "starting", qrText: "" };

    // 调用 OpenClaw 登录
    const env = { ...process.env, OPENCLAW_STATE_DIR: STATE_DIR };
    const child = spawn("openclaw", ["channels", "login", "--channel", "openclaw-weixin"], { env, stdio: "pipe" });

    let output = "";
    child.stdout.on("data", (chunk) => {
      output += chunk.toString();
      // 从输出提取二维码文本
      const qrMatch = output.match(/https://[^s]+/g);
      if (qrMatch) sessions[sessionId].qrText = qrMatch[qrMatch.length - 1];
    });

    child.on("close", (code) => {
      if (code === 0) {
        // 查找新创建的账户文件
        try {
          const files = readdirSync(ACCOUNTS_DIR).filter(f => f.endsWith(".json") && !f.includes("context") && !f.includes("sync"));
          const latest = files.sort().reverse()[0];
          if (latest) {
            const data = JSON.parse(readFileSync(join(ACCOUNTS_DIR, latest), "utf-8"));
            sessions[sessionId].status = "done";
            sessions[sessionId].token = data.token;
            sessions[sessionId].wxUserId = data.userId;
          }
        } catch(e) { sessions[sessionId].status = "error"; }
      } else {
        sessions[sessionId].status = "error";
      }
    });

    res.end(JSON.stringify({ ok: true, sessionId }));
    return;
  }

  // GET /status?session=xxx — 查询状态
  if (req.method === "GET" && url.pathname === "/status") {
    const sessionId = url.searchParams.get("session");
    const s = sessions[sessionId];
    if (!s) { res.end(JSON.stringify({status:"not_found"})); return; }
    res.end(JSON.stringify({
      status: s.status,
      qrText: s.qrText || "",
      token: s.token || "",
      wxUserId: s.wxUserId || "",
      botId: s.botId
    }));
    return;
  }

  res.writeHead(404); res.end("{}");
});

function readBody(req) {
  return new Promise((resolve) => {
    let data = "";
    req.on("data", c => data += c);
    req.on("end", () => resolve(data));
  });
}

server.listen(PORT, () => console.log("QR server on port " + PORT));
