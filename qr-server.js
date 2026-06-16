// qr-server.js — 正确调用 WeChat get_bot_qrcode API

import { createServer } from "http";
import { randomBytes } from "crypto";

const PORT = 3002;
const BASE_URL = "https://ilinkai.weixin.qq.com";
const BOT_TYPE = "3";

function buildHeaders(token) {
  const uin = randomBytes(4).readUInt32BE(0).toString();
  return {
    "Content-Type": "application/json",
    "AuthorizationType": "ilink_bot_token",
    "Authorization": "Bearer " + (token || "").trim(),
    "X-WECHAT-UIN": Buffer.from(uin).toString("base64"),
    "iLink-App-Id": "bot",
    "iLink-App-ClientVersion": "131328"
  };
}

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

    try {
      // Call WeChat get_bot_qrcode API (same as OpenClaw plugin uses)
      const result = await fetch(BASE_URL + "/ilink/bot/get_bot_qrcode?bot_type=" + BOT_TYPE, {
        method: "POST",
        headers: buildHeaders(""),
        body: JSON.stringify({ local_token_list: [] })
      });
      const data = await result.json();
      console.log("[qr-debug] get_bot_qrcode:", JSON.stringify(data).slice(0, 300));

      const qrcode = data.qrcode || "";
      const qrUrl = data.qrcode_img_content || data.qr_url || "";

      if (!qrcode && !data.qr_url) {
        res.writeHead(500);
        res.end(JSON.stringify({error:"No QR: " + JSON.stringify(data)}));
        return;
      }

      sessions[sessionId] = {
        botId, status: "scanning", qrUrl: qrUrl,
        qrcode: qrcode, token: null, wxUserId: null
      };

      // Background polling for scan completion
      (async function poll() {
        for (let i = 0; i < 60; i++) {
          await new Promise(r => setTimeout(r, 2000));
          const s = sessions[sessionId];
          if (!s || s.status !== "scanning") return;
          try {
            const r = await fetch(BASE_URL + "/ilink/bot/get_qrcode_status?qrcode=" + s.qrcode, { method: "GET", headers: buildHeaders("") });
            const d = await r.json();
            console.log("[qr-poll] status:", JSON.stringify(d).slice(0,100));
            if (d.status === "confirmed" || d.bot_token) {
              s.status = "done";
              s.token = d.bot_token || "";
              s.wxUserId = d.user_id || "";
              console.log("[qr] login success for " + sessionId);
              return;
            }
          } catch {}
        }
        sessions[sessionId].status = "timeout";
      })();

      res.end(JSON.stringify({ ok: true, sessionId }));
    } catch(e) {
      res.writeHead(500);
      res.end(JSON.stringify({error:e.message}));
    }
    return;
  }

  if (req.method === "GET" && url.pathname === "/status") {
    const sessionId = url.searchParams.get("session");
    const s = sessions[sessionId];
    if (!s) { res.end(JSON.stringify({status:"not_found"})); return; }

    // Status polling happens in background, started after QR is obtained

    res.end(JSON.stringify({
      status: s.status, qrText: s.qrUrl || "",
      token: s.token || "", wxUserId: s.wxUserId || "", botId: s.botId
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
