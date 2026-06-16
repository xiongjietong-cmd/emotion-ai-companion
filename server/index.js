import express from "express";
import { createServer } from "http";
import { WebSocketServer } from "ws";
import { fileURLToPath } from "url";
import { dirname, join } from "path";

import { initDatabase, getSetting, setSetting, getRecentMessages, getAllUserFacts, setUserFact, getRelationship, getDb } from "./database.js";
import { initAI, isReady } from "./ai-adapter.js";
import { createCompanionReply, getSavedPersonality } from "./companion-service.js";

const __dirname = dirname(fileURLToPath(import.meta.url));
const PORT = Number(process.env.PORT) || 3000;
const MODEL = "deepseek-v4-flash";
const OPENCLAW_OWNER_ID = String(process.env.OPENCLAW_OWNER_ID || "").trim();

//  Init
initDatabase();
const savedApiKey = getSetting("deepseek_api_key", "");
if (savedApiKey) initAI(savedApiKey, MODEL);

const app = express();
const server = createServer(app);
const wss = new WebSocketServer({ server });

app.use(express.json());
app.use(express.static(join(__dirname, "..", "client")));

//  REST API 

// Settings
app.get("/api/settings", (req, res) => {
  const personality = getSavedPersonality();
  const apiKey = getSetting("deepseek_api_key", "");
  res.json({ personality, apiKey: apiKey ? "已设置" : "", model: MODEL, isAiReady: isReady() });
});

app.post("/api/settings", (req, res) => {
  const { apiKey, personality } = req.body;

  if (apiKey) {
    setSetting("deepseek_api_key", apiKey);
    initAI(apiKey, MODEL);
  }

  setSetting("model", MODEL);
  if (personality) setSetting("personality", JSON.stringify(personality));
  res.json({ ok: true });
});

// Memory / facts
app.get("/api/memory", (req, res) => {
  const facts = getAllUserFacts();
  const relationship = getRelationship();
  res.json({ facts, relationship });
});

app.post("/api/memory/fact", (req, res) => {
  const { key, value } = req.body;
  if (key && value !== undefined) setUserFact(key, value, 1.0, "manual");
  res.json({ ok: true });
});

app.delete("/api/memory/fact", async (req, res) => {
  const db = getDb();
  db.prepare("DELETE FROM user_facts WHERE fact_key = ?").run(req.body.key);
  res.json({ ok: true });
});

// History (for chat page to load)
app.get("/api/history", (req, res) => {
  const messages = getRecentMessages(50);
  res.json({ messages });
});

app.post("/api/chat", async (req, res) => {
  try {
    const result = await createCompanionReply({
      text: req.body.text,
      source: req.body.source || "api",
      senderId: req.body.senderId || ""
    });
    res.json({ ok: true, ...result });
  } catch (e) {
    const status = e.code === "AI_NOT_READY" ? 409 : 400;
    res.status(status).json({ ok: false, code: e.code || "CHAT_ERROR", error: e.message });
  }
});

app.get("/openclaw/health", (req, res) => {
  res.json({
    ok: true,
    service: "emotion-ai-companion",
    model: MODEL,
    isAiReady: isReady(),
    ownerRestricted: Boolean(OPENCLAW_OWNER_ID)
  });
});

app.post("/openclaw/message", async (req, res) => {
  const text = req.body.text || req.body.message || req.body.content || req.body.query || req.body?.data?.text;
  const senderId = req.body.senderId || req.body.fromUserName || req.body.from || req.body.userId || req.body?.data?.senderId || "";

  if (OPENCLAW_OWNER_ID && senderId !== OPENCLAW_OWNER_ID) {
    res.status(403).json({ ok: false, code: "SENDER_NOT_ALLOWED", error: "Sender is not allowed" });
    return;
  }

  try {
    const result = await createCompanionReply({ text, source: "openclaw", senderId });
    res.json({
      ok: true,
      text: result.reply,
      reply: result.reply,
      message: result.reply,
      data: {
        type: "text",
        content: result.reply,
        userEmotion: result.userEmotion,
        aiEmotion: result.aiEmotion,
        senderId
      }
    });
  } catch (e) {
    const status = e.code === "AI_NOT_READY" ? 409 : 400;
    res.status(status).json({ ok: false, code: e.code || "OPENCLAW_MESSAGE_ERROR", error: e.message });
  }
});

//  WebSocket 
wss.on("connection", (ws) => {
  console.log("WebSocket connected");

  ws.on("message", async (raw) => {
    try {
      const { type, text } = JSON.parse(raw);

      if (type === "chat" && text) {
        const result = await createCompanionReply({
          text,
          source: "web",
          onStart: ({ userEmotion }) => ws.send(JSON.stringify({ type: "start", userEmotion })),
          onToken: (token) => ws.send(JSON.stringify({ type: "token", text: token }))
        });

        ws.send(JSON.stringify({ type: "done", aiEmotion: result.aiEmotion }));
      }

      if (type === "reset") {
        getDb().prepare("DELETE FROM conversations").run();
        ws.send(JSON.stringify({ type: "reset_done" }));
      }

    } catch (e) {
      console.error("WS error:", e);
      ws.send(JSON.stringify({ type: "error", message: e.message }));
    }
  });
});

//  Start 
server.listen(PORT, () => {
  console.log("\nEmotion AI companion is running");
  console.log(`Chat:     http://localhost:${PORT}`);
  console.log(`Settings: http://localhost:${PORT}/settings.html`);
  console.log(`OpenClaw: POST http://localhost:${PORT}/openclaw/message\n`);
});
