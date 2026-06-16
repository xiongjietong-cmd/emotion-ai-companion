import express from "express";
import { createServer } from "http";
import { WebSocketServer } from "ws";
import { fileURLToPath } from "url";
import { dirname, join } from "path";

import {
  initDatabase,
  createUser, getUserByEmail, getUserById, getAllUsers, getUserCount,
  createBot, getBotsByUser, getBotById, updateBot, getTotalBotCount,
  addMessage, getRecentMessages,
  setMemory, getMemories,
  getRelationship, updateRelationship,
  getSetting, setSetting,
  getWechatAccount,
  getStats, getMessageStats, recordMessageStat, verifyPassword
} from "./database.js";

import { signToken, authMiddleware, adminMiddleware } from "./auth.js";
import { initAI, isReady, chat } from "./ai-adapter.js";
import { DEFAULT_PERSONALITY, buildSystemPrompt, detectUserEmotion } from "./emotional-engine.js";

const __dirname = dirname(fileURLToPath(import.meta.url));
const PORT = process.env.PORT || 3000;
const MODEL = "deepseek-v4-flash";

// Init
initDatabase();
const savedApiKey = getSetting("deepseek_api_key", "");
if (savedApiKey) initAI(savedApiKey, MODEL);

const app = express();
const server = createServer(app);
const wss = new WebSocketServer({ server });

app.use(express.json());
app.use(express.static(join(__dirname, "..", "client")));

// ══════════════════════════════════════════
// 认证路由
// ══════════════════════════════════════════

app.post("/api/auth/register", (req, res) => {
  const { email, password } = req.body;
  if (!email || !password || password.length < 6) {
    return res.status(400).json({ error: "邮箱不能为空，密码至少6位" });
  }
  try {
    createUser(email, password);
    const user = getUserByEmail(email);
    const token = signToken(user);
    res.json({ ok: true, token, user: { id: user.id, email: user.email, role: user.role } });
  } catch (e) {
    if (e.message && e.message.includes("UNIQUE")) {
      return res.status(409).json({ error: "该邮箱已注册" });
    }
    res.status(500).json({ error: "注册失败" });
  }
});

app.post("/api/auth/login", (req, res) => {
  const { email, password } = req.body;
  const user = getUserByEmail(email);
  if (!user || !verifyPassword(password, user.salt, user.password_hash)) {
    return res.status(401).json({ error: "邮箱或密码错误" });
  }
  const token = signToken(user);
  res.json({ ok: true, token, user: { id: user.id, email: user.email, role: user.role, displayName: user.display_name } });
});

app.get("/api/auth/me", authMiddleware, (req, res) => {
  const user = getUserById(req.user.id);
  if (!user) return res.status(404).json({ error: "用户不存在" });
  res.json({ ok: true, user });
});

// ══════════════════════════════════════════
// 机器人管理
// ══════════════════════════════════════════

app.get("/api/bots", authMiddleware, (req, res) => {
  const bots = getBotsByUser(req.user.id);
  res.json({ ok: true, bots });
});

app.post("/api/bots", authMiddleware, (req, res) => {
  const { name, personality } = req.body;
  const botId = createBot(req.user.id, name || "小暖", personality || DEFAULT_PERSONALITY);
  res.json({ ok: true, botId });
});

app.put("/api/bots/:id", authMiddleware, (req, res) => {
  const bot = getBotById(req.params.id);
  if (!bot || bot.user_id !== req.user.id) return res.status(404).json({ error: "机器人不存在" });
  updateBot(req.params.id, req.body);
  res.json({ ok: true });
});

app.delete("/api/bots/:id", authMiddleware, (req, res) => {
  const bot = getBotById(req.params.id);
  if (!bot || bot.user_id !== req.user.id) return res.status(404).json({ error: "机器人不存在" });
  updateBot(req.params.id, { is_active: 0 });
  res.json({ ok: true });
});

// 机器人公开信息（聊天页面用）
app.get("/api/bots/:id/public", (req, res) => {
  const bot = getBotById(req.params.id);
  if (!bot || !bot.is_active) return res.status(404).json({ error: "机器人不存在" });
  res.json({
    ok: true,
    name: bot.name,
    personality: bot.personality ? JSON.parse(bot.personality) : DEFAULT_PERSONALITY
  });
});

// ══════════════════════════════════════════
// 聊天（Web）
// ══════════════════════════════════════════

app.post("/api/chat/:botId", async (req, res) => {
  try {
    const bot = getBotById(req.params.botId);
    if (!bot || !bot.is_active) return res.status(404).json({ error: "机器人不存在或已停用" });

    const personality = bot.personality ? JSON.parse(bot.personality) : DEFAULT_PERSONALITY;
    const result = await processMessage({
      botId: bot.id,
      text: req.body.text,
      personality,
      source: "web",
      senderId: req.body.senderId || "web-user"
    });
    res.json({ ok: true, ...result });
  } catch (e) {
    const status = e.code === "AI_NOT_READY" ? 409 : 400;
    res.status(status).json({ ok: false, error: e.message });
  }
});

// ══════════════════════════════════════════
// 微信消息入口（每个机器人独立 webhook）
// ══════════════════════════════════════════

app.post("/api/webhook/:botId", async (req, res) => {
  const bot = getBotById(req.params.botId);
  if (!bot || !bot.is_active) return res.status(404).json({ error: "机器人不存在" });

  const text = req.body.text || req.body.message || "";
  const senderId = req.body.senderId || req.body.from || "";

  try {
    const personality = bot.personality ? JSON.parse(bot.personality) : DEFAULT_PERSONALITY;
    const result = await processMessage({
      botId: bot.id,
      text,
      personality,
      source: "wechat",
      senderId
    });
    res.json({ ok: true, text: result.reply });
  } catch (e) {
    res.status(400).json({ ok: false, error: e.message });
  }
});

// 微信扫码回调（接收微信凭证）
app.post("/api/bots/:id/wechat-bind", authMiddleware, (req, res) => {
  const bot = getBotById(req.params.id);
  if (!bot || bot.user_id !== req.user.id) return res.status(404).json({ error: "机器人不存在" });
  
  const { token, baseUrl, wxUserId } = req.body;
  const { bindWechat } = require("./database.js")?.bindWechat || (() => {});
  // save wechat credentials
  setSetting("wechat_" + bot.id + "_token", token);
  setSetting("wechat_" + bot.id + "_baseUrl", baseUrl || "https://ilinkai.weixin.qq.com");
  setSetting("wechat_" + bot.id + "_userId", wxUserId || "");
  res.json({ ok: true });
});

// ══════════════════════════════════════════
// 记忆管理
// ══════════════════════════════════════════

app.get("/api/bots/:id/memories", (req, res) => {
  const memories = getMemories(req.params.id);
  res.json({ ok: true, memories });
});

app.post("/api/bots/:id/memories", authMiddleware, (req, res) => {
  const bot = getBotById(req.params.id);
  if (!bot || bot.user_id !== req.user.id) return res.status(404).json({ error: "机器人不存在" });
  const { key, value } = req.body;
  setMemory(req.params.id, key, value, 1.0, "manual");
  res.json({ ok: true });
});

// ══════════════════════════════════════════
// 设置
// ══════════════════════════════════════════

app.get("/api/settings", (req, res) => {
  const apiKey = getSetting("deepseek_api_key", "");
  res.json({ model: MODEL, isAiReady: isReady(), apiKey: apiKey ? "已设置" : "" });
});

app.post("/api/settings", (req, res) => {
  if (req.body.apiKey) {
    setSetting("deepseek_api_key", req.body.apiKey);
    initAI(req.body.apiKey, MODEL);
  }
  res.json({ ok: true });
});

// ══════════════════════════════════════════
// 管理员面板
// ══════════════════════════════════════════

app.get("/api/admin/stats", authMiddleware, adminMiddleware, (req, res) => {
  const stats = getStats();
  const msgStats = getMessageStats(7);
  const users = getAllUsers();
  res.json({ ok: true, stats, msgStats, users });
});

// ══════════════════════════════════════════
// 聊天引擎
// ══════════════════════════════════════════

function normalizePersonality(p) {
  return { ...DEFAULT_PERSONALITY, ...(p || {}), traits: { ...DEFAULT_PERSONALITY.traits, ...((p && p.traits) || {}) } };
}

function isIdentityQuestion(text) {
  return /你(叫(什么|啥|啥名)?|是谁|什么名字|名字是什么)|怎么称呼你|你的名字/.test(text);
}

async function processMessage({ botId, text, personality, source, senderId }) {
  const cleanText = String(text || "").trim();
  if (!cleanText) throw Object.assign(new Error("消息为空"), { code: "EMPTY_MESSAGE" });
  if (!isReady()) throw Object.assign(new Error("AI 未配置"), { code: "AI_NOT_READY" });

  const p = normalizePersonality(personality);
  const userEmotion = detectUserEmotion(cleanText);
  addMessage(botId, "user", cleanText, userEmotion, senderId);

  if (isIdentityQuestion(cleanText)) {
    const reply = "我是" + p.name + "。";
    addMessage(botId, "assistant", reply, "平静", "");
    recordMessageStat(botId);
    return { reply, userEmotion, aiEmotion: "平静" };
  }

  const relationship = getRelationship(botId);
  const memories = getMemories(botId);
  const systemPrompt = buildSystemPrompt(p, relationship, memories);
  const recent = getRecentMessages(botId, 10);

  const messagesForAI = [
    { role: "system", content: systemPrompt },
    ...recent.map(m => ({ role: m.role, content: m.content }))
  ];

  updateRelationship(botId, { intimacy: 0.01, trust: 0.005, mood: userEmotion });

  let fullResponse = "";
  await chat(messagesForAI, (token) => { fullResponse += token; });

  const aiEmotion = detectUserEmotion(fullResponse);
  addMessage(botId, "assistant", fullResponse, aiEmotion, "");
  recordMessageStat(botId);

  return { reply: fullResponse, userEmotion, aiEmotion };
}

// ══════════════════════════════════════════
// 启动
// ══════════════════════════════════════════

server.listen(PORT, () => {
  console.log("\nEmotion AI SaaS is running");
  console.log("Chat:     http://localhost:" + PORT);
  console.log("Admin:    http://localhost:" + PORT + "/admin.html");
  console.log("Dashboard: http://localhost:" + PORT + "/dashboard.html\n");
});
