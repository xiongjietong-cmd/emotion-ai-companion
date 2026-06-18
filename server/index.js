import express from "express";
import { createServer } from "http";
import { WebSocketServer } from "ws";
import { fileURLToPath } from "url";
import { dirname, join } from "path";
import fs from "fs";

import {
  initDatabase,
  createUser, getUserByEmail, getUserById, getAllUsers, getUserCount,
  createBot, getBotsByUser, getBotById, updateBot, getTotalBotCount,
  addMessage, getRecentMessages,
  setMemory, getMemories, deleteMemory,
  getRelationship, updateRelationship,
  getCompanionRelationship, updateCompanionRelationship,
  getCompanionMemories, setCompanionMemory, recordReplyJudgement,
  getSetting, setSetting,
  bindWechat, getWechatAccount, getWechatStatus,
  getUserUsage, canCreateBot, canBindWechat, canSendMessage,
  getStats, getMessageStats, getAdminBotRows, recordMessageStat, verifyPassword, getDb,
  createOrder, getOrderById, confirmOrder, getOrdersByUser, getAllOrders, getOrderStats, PLAN_PRICES
} from "./database.js";

import { signToken, authMiddleware, adminMiddleware } from "./auth.js";

// Sync WeChat token to OpenClaw accounts directory
function syncToOpenClaw(token, wxUserId, baseUrl = "https://ilinkai.weixin.qq.com") {
  try {
    const dir = join(
      process.env.OPENCLAW_STATE_DIR || join(__dirname, "..", ".openclaw-state"),
      "openclaw-weixin", "accounts"
    );
    if (!fs.existsSync(dir)) fs.mkdirSync(dir, { recursive: true });
    const accountId = token.split("@")[0] + "@im.bot";
    const data = { token, savedAt: new Date().toISOString(), baseUrl, userId: wxUserId || "" };
    fs.writeFileSync(join(dir, accountId + ".json"), JSON.stringify(data, null, 2), "utf-8");
    const indexFile = join(dir, "..", "accounts.json");
    if (fs.existsSync(indexFile)) {
      let idx = JSON.parse(fs.readFileSync(indexFile, "utf-8"));
      const normId = accountId.replace("@im.bot", "-im-bot");
      if (!idx.includes(normId)) { idx.push(normId); fs.writeFileSync(indexFile, JSON.stringify(idx, null, 2), "utf-8"); }
    }
  } catch(e) {}
}

import { rateLimiter, sanitizeInput, errorHandler, validateBody } from "./security.js";

import { initAI, isReady, chat, chatNonStreaming } from "./ai-adapter.js";
import { createCompanionReply, isCompanionUnavailable } from "./companion-client.js";
import { synthesize } from "./tts.js";
import { DEFAULT_PERSONALITY, buildSystemPrompt, detectUserEmotion } from "./emotional-engine.js";
import { consolidateMemory } from "./memory-consolidator.js";

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
app.use(rateLimiter);
app.use(validateBody(2000));

// Request logger
app.use((req, res, next) => {
  const start = Date.now();
  res.on("finish", () => {
    const ms = Date.now() - start;
    if (req.path.startsWith("/api/")) {
      console.log("[" + new Date().toLocaleTimeString() + "] " + req.method + " " + req.path + " " + res.statusCode + " " + ms + "ms");
    }
  });
  next();
});
app.use(express.static(join(__dirname, "..", "client")));
app.use("/tts-audio", express.static(join(__dirname, "..", "data", "tts")));

// Health check
app.get("/api/health", (req, res) => { res.json({ ok: true, time: new Date().toISOString() }); });

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

app.get("/api/me/usage", authMiddleware, (req, res) => {
  res.json({ ok: true, ...getUserUsage(req.user.id) });
});

// ══════════════════════════════════════════
// 机器人管理
// ══════════════════════════════════════════

app.get("/api/bots", authMiddleware, (req, res) => {
  const bots = getBotsByUser(req.user.id).map((bot) => ({
    ...bot,
    wechatStatus: getWechatStatus(bot.id)
  }));
  res.json({ ok: true, bots });
});

app.post("/api/bots", authMiddleware, (req, res) => {
  const { name, personality } = req.body;
  const quota = canCreateBot(req.user.id);
  if (!quota.ok) {
    return res.status(403).json({
      error: "当前套餐的机器人数量已用完",
      code: "BOT_LIMIT_REACHED",
      quota: quota.state
    });
  }
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


// 聊天历史

// Bot stats
app.get("/api/bots/:id/stats", (req, res) => {
  try {
    const count = getDb().prepare("SELECT COUNT(*) as c FROM conversations WHERE bot_id = ?").get(req.params.id);
    res.json({ ok: true, msgCount: count.c });
  } catch { res.json({ ok: true, msgCount: 0 }); }
});
app.get("/api/bots/:id/history", (req, res) => {
  const bot = getBotById(req.params.id);
  if (!bot) return res.status(404).json({ error: "not found" });
  const messages = getRecentMessages(req.params.id, 50);
  res.json({ ok: true, messages });
});

app.post("/api/chat/:botId", async (req, res) => {
  try {
    const bot = getBotById(req.params.botId);
    if (!bot || !bot.is_active) return res.status(404).json({ error: "机器人不存在或已停用" });
    const quota = canSendMessage(bot.user_id);
    if (!quota.ok) {
      return res.status(403).json({ ok: false, error: "本月消息额度已用完", code: "MESSAGE_LIMIT_REACHED", quota: quota.state });
    }

    const personality = bot.personality ? JSON.parse(bot.personality) : DEFAULT_PERSONALITY;
    const result = await processCompanionMessage({
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
  const quota = canSendMessage(bot.user_id);
  if (!quota.ok) return res.status(403).json({ ok: false, error: "本月消息额度已用完", code: "MESSAGE_LIMIT_REACHED", quota: quota.state });

  const text = req.body.text || req.body.message || "";
  const senderId = req.body.senderId || req.body.from || "";

  try {
    const personality = bot.personality ? JSON.parse(bot.personality) : DEFAULT_PERSONALITY;
    const result = await processCompanionMessage({
      botId: bot.id,
      text,
      personality,
      source: "wechat",
      senderId
    });
    res.json({ ok: true, text: result.reply, texts: result.replyParts || [result.reply], replyParts: result.replyParts || [result.reply], aiEmotion: result.aiEmotion });
  } catch (e) {
    res.status(400).json({ ok: false, error: e.message });
  }
});

// 微信扫码回调（接收微信凭证）
app.post("/api/bots/:id/wechat-bind", authMiddleware, (req, res) => {
  const bot = getBotById(req.params.id);
  if (!bot || bot.user_id !== req.user.id) return res.status(404).json({ error: "机器人不存在" });
  
  const { token, baseUrl, wxUserId } = req.body;
  if (!token || typeof token !== "string" || !token.includes("@")) {
    return res.status(400).json({ error: "invalid wechat token" });
  }
  const finalBaseUrl = baseUrl || "https://ilinkai.weixin.qq.com";
  const quota = canBindWechat(req.user.id, bot.id);
  if (!quota.ok) {
    return res.status(403).json({
      error: "当前套餐的微信绑定数量已用完",
      code: "WECHAT_LIMIT_REACHED",
      quota: quota.state
    });
  }

  // save wechat credentials
  setSetting("wechat_" + bot.id + "_token", token);
  setSetting("wechat_" + bot.id + "_baseUrl", finalBaseUrl);
  setSetting("wechat_" + bot.id + "_userId", wxUserId || "");
  setSetting("wx_bot_" + token.split("@")[0], String(bot.id));
  bindWechat(bot.id, token, finalBaseUrl, wxUserId || "");
  syncToOpenClaw(token, wxUserId || "", finalBaseUrl);
  res.json({ ok: true });
});

app.get("/api/bots/:id/wechat-status", authMiddleware, (req, res) => {
  const bot = getBotById(req.params.id);
  if (!bot || bot.user_id !== req.user.id) return res.status(404).json({ error: "机器人不存在" });
  res.json({ ok: true, status: getWechatStatus(bot.id) });
});

// ══════════════════════════════════════════
// 记忆管理
// ══════════════════════════════════════════

app.get("/api/bots/:id/memories", authMiddleware, (req, res) => {
  const bot = getBotById(req.params.id);
  if (!bot || bot.user_id !== req.user.id) return res.status(404).json({ error: "机器人不存在" });
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

app.delete("/api/bots/:id/memories", authMiddleware, (req, res) => {
  const bot = getBotById(req.params.id);
  if (!bot || bot.user_id !== req.user.id) return res.status(404).json({ error: "机器人不存在" });
  const { key } = req.body;
  if (!key) return res.status(400).json({ error: "缺少记忆关键词" });
  deleteMemory(req.params.id, key);
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

app.post("/api/orders", authMiddleware, (req, res) => {
  const { plan } = req.body;
  if (!PLAN_PRICES[plan]) {
    return res.status(400).json({ error: "invalid plan, allowed: starter, pro" });
  }
  const info = createOrder(req.user.id, plan);
  res.json({ ok: true, orderId: info.lastInsertRowid, amount: PLAN_PRICES[plan] });
});

app.post("/api/orders/:id/confirm", authMiddleware, (req, res) => {
  const order = getOrderById(req.params.id);
  if (!order || order.user_id !== req.user.id) {
    return res.status(404).json({ error: "order not found" });
  }
  const result = confirmOrder(req.params.id);
  if (!result) return res.status(400).json({ error: "order already handled or canceled" });
  res.json({ ok: true, plan: result.plan });
});

app.get("/api/orders", authMiddleware, (req, res) => {
  res.json({ ok: true, orders: getOrdersByUser(req.user.id) });
});

app.get("/api/admin/orders", authMiddleware, adminMiddleware, (req, res) => {
  res.json({ ok: true, orders: getAllOrders(), orderStats: getOrderStats() });
});

// ══════════════════════════════════════════
// 管理员面板
// ══════════════════════════════════════════


// Data export (admin)
app.get("/api/admin/export", authMiddleware, adminMiddleware, (req, res) => {
  const users = getAllUsers();
  const bots = getDb().prepare("SELECT b.*, u.email FROM bots b JOIN users u ON b.user_id = u.id").all();
  let csv = "Type,ID,Name,Email,Created\n";
  users.forEach(u => { csv += "User," + u.id + "," + (u.display_name||"") + "," + u.email + "," + (u.created_at||"") + "\n"; });
  bots.forEach(b => { csv += "Bot," + b.id + "," + b.name + "," + b.email + "," + (b.created_at||"") + "\n"; });
  res.setHeader("Content-Type", "text/csv; charset=utf-8");
  res.setHeader("Content-Disposition", "attachment; filename=emotion-ai-export.csv");
  res.send(csv);
});

app.get("/api/admin/stats", authMiddleware, adminMiddleware, (req, res) => {
  const stats = getStats();
  const msgStats = getMessageStats(7);
  const users = getAllUsers();
  const bots = getAdminBotRows().map((bot) => ({
    ...bot,
    wechatStatus: getWechatStatus(bot.id),
    active: Boolean(bot.is_active),
    hasWechat: Boolean(bot.has_wechat),
    msgIn: bot.msg_in || 0,
    msgOut: bot.msg_out || 0
  }));
  res.json({ ok: true, stats, msgStats, users, bots });
});

// ══════════════════════════════════════════
// 聊天引擎
// ══════════════════════════════════════════

app.get("/api/admin/analytics", authMiddleware, adminMiddleware, (req, res) => {
  const db = getDb();
  const today = new Date().toISOString().slice(0, 10);
  const weekAgo = new Date(Date.now() - 7 * 86400000).toISOString().slice(0, 10);

  const dau = db.prepare(`
    SELECT COUNT(DISTINCT b.user_id) AS count
    FROM conversations c
    JOIN bots b ON b.id = c.bot_id
    WHERE date(c.timestamp) = ?
  `).get(today).count;

  const wau = db.prepare(`
    SELECT COUNT(DISTINCT b.user_id) AS count
    FROM conversations c
    JOIN bots b ON b.id = c.bot_id
    WHERE date(c.timestamp) >= ?
  `).get(weekAgo).count;

  const newUsersByDay = db.prepare(`
    SELECT date(created_at) AS date, COUNT(*) AS count
    FROM users
    WHERE date(created_at) >= ?
    GROUP BY date(created_at)
    ORDER BY date DESC
  `).all(weekAgo);

  const totalBots = db.prepare("SELECT COUNT(*) AS count FROM bots WHERE is_active = 1").get().count;
  const boundBots = db.prepare("SELECT COUNT(*) AS count FROM wechat_accounts WHERE is_connected = 1").get().count;
  const planDistribution = db.prepare("SELECT plan, COUNT(*) AS count FROM users GROUP BY plan").all();

  res.json({ ok: true, dau, wau, newUsersByDay, totalBots, boundBots, planDistribution });
});

function normalizePersonality(p) {
  return { ...DEFAULT_PERSONALITY, ...(p || {}), traits: { ...DEFAULT_PERSONALITY.traits, ...((p && p.traits) || {}) } };
}

function isIdentityQuestion(text) {
  return /你叫(什么|啥|啥名|什么名字)|你是谁|你的名字|怎么称呼/.test(text);
}

async function processMessage({ botId, text, personality, source, senderId }) {
  const cleanText = sanitizeInput(text);
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

  try {
    const msgCount = getDb().prepare("SELECT COUNT(*) AS count FROM conversations WHERE bot_id = ?").get(botId)?.count || 0;
    if (msgCount > 0 && msgCount % 8 === 0) {
      setTimeout(() => {
        consolidateMemory(
          (msgs) => chatNonStreaming(msgs),
          getRecentMessages(botId, 12),
          getMemories(botId)
        ).then((facts) => {
          (facts || []).forEach((fact) => setMemory(botId, fact.key, fact.value, 0.6, "auto"));
        }).catch((e) => {
          console.error("Memory consolidation failed:", e.message);
        });
      }, 1000);
    }
  } catch (e) {
    console.error("Memory consolidation scheduling failed:", e.message);
  }

  return { reply: fullResponse, userEmotion, aiEmotion };
}

// ══════════════════════════════════════════
// 启动
// ══════════════════════════════════════════

async function processCompanionMessage({ botId, text, personality, source, senderId }) {
  const cleanText = sanitizeInput(text);
  if (!cleanText) throw Object.assign(new Error("消息为空"), { code: "EMPTY_MESSAGE" });

  const p = normalizePersonality(personality);
  const userEmotion = detectUserEmotion(cleanText);
  const userKey = senderId || `${source || "unknown"}-user`;
  addMessage(botId, "user", cleanText, userEmotion, userKey);

  try {
    const companion = await createCompanionReply({
      bot_id: String(botId),
      user_key: userKey,
      channel: source || "web",
      text: cleanText,
      recent_messages: getRecentMessages(botId, 50),
      memories: getCompanionMemories(botId, userKey),
      relationship: getCompanionRelationship(botId, userKey),
      provider_config: {
        api_key: getSetting("deepseek_api_key", ""),
        base_url: process.env.DEEPSEEK_BASE_URL || "",
        model: MODEL
      }
    });

    const replyParts = normalizeReplyParts(companion.replyParts, companion.reply);
    const reply = replyParts.join("\n");
    const aiEmotion = detectUserEmotion(reply);
    let assistantMessage = null;
    for (const part of replyParts) {
      assistantMessage = addMessage(botId, "assistant", part, aiEmotion, "");
    }
    updateCompanionRelationship(botId, userKey, companion.relationshipDelta || {});
    for (const memory of companion.memoryCandidates || []) {
      if (memory?.key && memory?.value) setCompanionMemory(botId, userKey, memory);
    }
    recordReplyJudgement(botId, userKey, assistantMessage?.lastInsertRowid || null, companion.judge || {});
    recordMessageStat(botId, 1, replyParts.length);

    return {
      reply,
      replyParts,
      userEmotion,
      aiEmotion,
      companion: {
        directorGoal: companion.directorGoal,
        judge: companion.judge
      }
    };
  } catch (error) {
    if (!isCompanionUnavailable(error)) throw error;
    console.warn("Companion core unavailable, using Node fallback:", error.message);
  }

  if (!isReady()) throw Object.assign(new Error("AI 未配置"), { code: "AI_NOT_READY" });

  if (isIdentityQuestion(cleanText)) {
    const reply = "我是" + (p.name || "小伴") + "。";
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
    ...recent.map((message) => ({ role: message.role, content: message.content }))
  ];

  updateRelationship(botId, { intimacy: 0.01, trust: 0.005, mood: userEmotion });

  let fullResponse = "";
  await chat(messagesForAI, (token) => { fullResponse += token; });

  const aiEmotion = detectUserEmotion(fullResponse);
  const replyParts = normalizeReplyParts([], fullResponse);
  const reply = replyParts.join("\n");
  for (const part of replyParts) {
    addMessage(botId, "assistant", part, aiEmotion, "");
  }
  recordMessageStat(botId, 1, replyParts.length);

  return { reply, replyParts, userEmotion, aiEmotion };
}

function normalizeReplyParts(parts, fallbackReply) {
  const normalized = Array.isArray(parts)
    ? parts.map((part) => String(part || "").trim()).filter(Boolean)
    : [];
  if (normalized.length) return normalized.slice(0, 4);
  const fallback = String(fallbackReply || "").trim();
  if (!fallback) return [];

  const fromLines = fallback
    .split(/\r?\n+/)
    .map((part) => part.replace(/[ \t]+/g, " ").trim())
    .filter(Boolean);
  let splitParts = fromLines.length > 1
    ? fromLines
    : fallback.split(/(?<=[。！？!?])\s*/).map((part) => part.trim()).filter(Boolean);
  if (splitParts.length <= 1 && fallback.length >= 18) {
    splitParts = fallback.split(/[，,；;]/).map((part) => part.trim()).filter(Boolean);
  }
  if (splitParts.length <= 1 && fallback.length >= 28) {
    const midpoint = Math.floor(fallback.length / 2);
    splitParts = [fallback.slice(0, midpoint).trim(), fallback.slice(midpoint).trim()].filter(Boolean);
  }
  return splitParts.slice(0, 4);
}

// ══════════════════════════════════════════
// 语音合成 (TTS)
// ══════════════════════════════════════════

app.post("/api/tts", async (req, res) => {
  try {
    const { text, emotion } = req.body;
    if (!text) return res.status(400).json({ error: "缺少text参数" });
    const { stream, contentType } = await synthesize({ text, emotion: emotion || "平静" });
    res.setHeader("Content-Type", contentType);
    stream.pipe(res);
    stream.on("error", () => { if (!res.headersSent) res.status(500).end(); });
  } catch (e) {
    res.status(500).json({ error: "TTS 合成失败" });
  }
});

app.post("/api/tts-url", async (req, res) => {
  try {
    const { text, emotion, baseUrl } = req.body;
    if (!text) return res.status(400).json({ error: "缺少text参数" });
    const { stream } = await synthesize({ text, emotion: emotion || "平静" });
    const chunks = [];
    stream.on("data", (c) => chunks.push(c));
    stream.on("end", () => {
      const buf = Buffer.concat(chunks);
      const filename = `v_${Date.now()}_${Math.random().toString(36).slice(2,6)}.mp3`;
      const dest = join(__dirname, "..", "data", "tts", filename);
      fs.mkdirSync(join(__dirname, "..", "data", "tts"), { recursive: true });
      fs.writeFileSync(dest, buf);
      const prefix = (baseUrl || "").replace(/\/+$/, "");
      res.json({ ok: true, url: prefix + "/tts-audio/" + filename, duration: Math.round(buf.length / 16 * 10) });
    });
    stream.on("error", () => { if (!res.headersSent) res.status(500).json({ error: "合成失败" }); });
  } catch (e) {
    res.status(500).json({ error: "TTS 合成失败" });
  }
});

app.use(errorHandler);

// 404 handler
app.use((req, res) => { res.status(404).sendFile(join(__dirname, "..", "client", "404.html")); });

server.listen(PORT, () => {
  console.log("\nEmotion AI SaaS is running");
  console.log("Chat:     http://localhost:" + PORT);
  console.log("Admin:    http://localhost:" + PORT + "/admin.html");
  console.log("Dashboard: http://localhost:" + PORT + "/dashboard.html\n");
});
