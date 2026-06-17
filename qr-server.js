// qr-server.js — WeChat QR login with notifyStart

import { createServer } from "http";
import { randomBytes } from "crypto";
import fs from "node:fs";
import path from "node:path";

const PORT = 3002;
const BASE_URL = "https://ilinkai.weixin.qq.com";
const BOT_TYPE = "3";
const STATE_DIR = process.env.OPENCLAW_STATE_DIR || "D:/Documents/New project 2/.openclaw-state";

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

async function notifyStart(token) {
  try {
    await fetch(BASE_URL + "/ilink/bot/msg/notifystart", {
      method: "POST", headers: buildHeaders(token),
      body: JSON.stringify({ base_info: { channel_version: "2.4.3", bot_agent: "OpenClaw" } })
    });
  } catch(e) {}
}

async function saveAccount(token, userId) {
  try {
    const dir = path.join(STATE_DIR, "openclaw-weixin", "accounts");
    if (!fs.existsSync(dir)) fs.mkdirSync(dir, { recursive: true });
    const accountId = token.split("@")[0] + "@im.bot";
    const idxId = accountId.replace("@im.bot", "-im-bot");
    const data = { token, savedAt: new Date().toISOString(), baseUrl: BASE_URL, userId: userId || "" };
    fs.writeFileSync(path.join(dir, accountId + ".json"), JSON.stringify(data, null, 2), "utf-8");
    const indexFile = path.join(dir, "..", "accounts.json");
    let idx = [];
    try { idx = JSON.parse(fs.readFileSync(indexFile, "utf-8")); } catch {}
    if (!idx.includes(idxId)) { idx.push(idxId); fs.writeFileSync(indexFile, JSON.stringify(idx, null, 2), "utf-8"); }
    // Remove old accounts with same userId
    const files = fs.readdirSync(dir).filter(f => f.endsWith(".json") && !f.includes("context") && !f.includes("sync"));
    for (const f of files) {
      if (f === accountId + ".json") continue;
      try {
        const d = JSON.parse(fs.readFileSync(path.join(dir, f), "utf-8"));
        if (d.userId === userId && d.token !== token) {
          fs.unlinkSync(path.join(dir, f));
          try { fs.unlinkSync(path.join(dir, f.replace(".json", ".sync.json"))); } catch {}
          idx = idx.filter(id => id !== f.replace("@im.bot", "-im-bot").replace(".json", ""));
          fs.writeFileSync(indexFile, JSON.stringify(idx, null, 2), "utf-8");
        }
      } catch {}
    }
  } catch(e) { console.error("save failed:", e.message); }
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
      const result = await fetch(BASE_URL + "/ilink/bot/get_bot_qrcode?bot_type=" + BOT_TYPE, {
        method: "POST", headers: buildHeaders(""),
        body: JSON.stringify({ local_token_list: [] })
      });
      const data = await result.json();
      if (!data.qrcode_img_content) {
        res.writeHead(500); res.end(JSON.stringify({error:"QR failed: "+JSON.stringify(data)})); return;
      }
      sessions[sessionId] = { botId, status:"scanning", qrUrl:data.qrcode_img_content, qrcode:data.qrcode, token:null, wxUserId:null };
      // Background poll
      (async function poll() {
        for (let i=0;i<60;i++) {
          await new Promise(r=>setTimeout(r,2000));
          const s = sessions[sessionId]; if(!s||s.status!=="scanning") return;
          try {
            const r = await fetch(BASE_URL+"/ilink/bot/get_qrcode_status?qrcode="+s.qrcode,{method:"GET",headers:buildHeaders("")});
            const d = await r.json();
            if(d.bot_token){s.status="done";s.token=d.bot_token;s.wxUserId=d.user_id||"";await notifyStart(s.token);await saveAccount(s.token,s.wxUserId);return}
          }catch{}
        }
      })();
      res.end(JSON.stringify({ok:true,sessionId}));
    } catch(e) { res.writeHead(500); res.end(JSON.stringify({error:e.message})); }
    return;
  }

  if (req.method === "GET" && url.pathname === "/status") {
    const s = sessions[url.searchParams.get("session")];
    if(!s){res.end(JSON.stringify({status:"not_found"}));return}
    res.end(JSON.stringify({status:s.status,qrText:s.qrUrl||"",token:s.token||"",wxUserId:s.wxUserId||"",botId:s.botId}));
    return;
  }

  res.writeHead(404); res.end(JSON.stringify({}));
});

function readBody(req) {
  return new Promise(r=>{let d="";req.on("data",c=>d+=c);req.on("end",()=>r(d));});
}

server.listen(PORT, () => console.log("QR server on " + PORT));
