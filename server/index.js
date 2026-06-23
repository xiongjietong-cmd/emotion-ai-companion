import express from "express";
import { createServer } from "http";
import { WebSocketServer } from "ws";
import { fileURLToPath } from "url";
import { dirname, join } from "path";
import fs from "fs";

import {
  initDatabase,
  createUser, getUserByEmail, getUserById, getAllUsers, getUserCount,
  createBot, getBotsByUser, getBotById, updateBot, getTotalBotCount, deleteBotCompletely,
  addMessage, getRecentMessages,
  setMemory, getMemories, deleteMemory,
  getRelationship, updateRelationship,
  getCompanionRelationship, updateCompanionRelationship,
  getCompanionMemories, setCompanionMemory,
  getConversationSummary, updateConversationSummary, recordReplyJudgement,
  getSetting, setSetting,
  bindWechat, disconnectWechat, getWechatAccount, getWechatStatus,
  getUserUsage, canCreateBot, canBindWechat, canSendMessage,
  getStats, getMessageStats, getAdminBotRows, recordMessageStat, verifyPassword, getDb,
  createOrder, getOrderById, confirmOrder, getOrdersByUser, getAllOrders, getOrderStats, PLAN_PRICES,
  getAccountEvents, applyInviteReward, markUserLogin, blacklistUser, restoreUser, deleteUserCompletely
} from "./database.js";

import { signToken, authMiddleware, adminMiddleware } from "./auth.js";

// Sync WeChat token to OpenClaw accounts directory
function openClawAccountPath(token) {
  const accountId = token.split("@")[0] + "@im.bot";
  return join(__dirname, "..", ".openclaw-state", "openclaw-weixin", "accounts", accountId + ".json");
}

function syncToOpenClaw(token, wxUserId, baseUrl = "https://ilinkai.weixin.qq.com", botId = "") {
  try {
    const dir = join(__dirname, "..", ".openclaw-state", "openclaw-weixin", "accounts");
    if (!fs.existsSync(dir)) fs.mkdirSync(dir, { recursive: true });
    const accountId = token.split("@")[0] + "@im.bot";
    const data = { token, savedAt: new Date().toISOString(), baseUrl, userId: wxUserId || "", botId: botId || "" };
    fs.writeFileSync(join(dir, accountId + ".json"), JSON.stringify(data, null, 2), "utf-8");
    const indexFile = join(dir, "..", "accounts.json");
    if (fs.existsSync(indexFile)) {
      let idx = JSON.parse(fs.readFileSync(indexFile, "utf-8"));
      const normId = accountId.replace("@im.bot", "-im-bot");
      if (!idx.includes(normId)) { idx.push(normId); fs.writeFileSync(indexFile, JSON.stringify(idx, null, 2), "utf-8"); }
    }
  } catch(e) {}
}

function removeOpenClawAccount(token) {
  if (!token) return;
  try {
    const file = openClawAccountPath(token);
    if (fs.existsSync(file)) fs.unlinkSync(file);
  } catch {}
}

import { rateLimiter, sanitizeInput, errorHandler, validateBody } from "./security.js";

import { initAI, isReady } from "./ai-adapter.js";
import { DEFAULT_PERSONALITY, detectUserEmotion } from "./emotional-engine.js";
import { createCompanionReply, isCompanionUnavailable } from "./companion-client.js";

const __dirname = dirname(fileURLToPath(import.meta.url));
const PORT = process.env.PORT || 3000;
const MODEL = "deepseek-v4-flash";
const COMPANION_FAILURE_REPLY = "服务器异常，暂时没连上模型。请稍后再试。";

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

// Health check
app.get("/api/health", (req, res) => { res.json({ ok: true, time: new Date().toISOString() }); });

app.get("/api/persona-presets", (req, res) => {
  try {
    const file = join(__dirname, "..", "data", "persona_presets.json");
    const presets = fs.existsSync(file) ? JSON.parse(fs.readFileSync(file, "utf-8")) : [];
    res.json({ ok: true, presets });
  } catch (error) {
    res.status(500).json({ ok: false, error: "persona presets unavailable" });
  }
});

// Current auth contract. Kept before the legacy routes below so the UI gets the
// account-state and invite fields it expects.
app.post("/api/auth/register", (req, res) => {
  const { email, password, inviteCode } = req.body;
  if (!email || !password || password.length < 6) {
    return res.status(400).json({ error: "邮箱不能为空，密码至少6位" });
  }
  try {
    createUser(email, password);
    const user = getUserByEmail(email);
    if (inviteCode) applyInviteReward(user.id, inviteCode);
    markUserLogin(user.id, "email_password", email);
    const freshUser = getUserByEmail(email);
    const token = signToken(freshUser);
    return res.json({
      ok: true,
      token,
      user: {
        id: freshUser.id,
        email: freshUser.email,
        role: freshUser.role,
        inviteCode: freshUser.invite_code,
        loginMethod: "email_password",
        loginAccount: email
      }
    });
  } catch (e) {
    if (e.message && e.message.includes("UNIQUE")) {
      return res.status(409).json({ error: "该邮箱已注册" });
    }
    if (e.code === "INVALID_INVITE_CODE") {
      return res.status(400).json({ error: "邀请码无效", code: e.code });
    }
    return res.status(500).json({ error: "注册失败" });
  }
});

app.post("/api/auth/login", (req, res) => {
  const { email, password } = req.body;
  const user = getUserByEmail(email);
  if (!user || !verifyPassword(password, user.salt, user.password_hash)) {
    return res.status(401).json({ error: "邮箱或密码错误" });
  }
  if (user.status === "blacklisted") {
    return res.status(403).json({ ok: false, error: "账号已被拉黑", code: "ACCOUNT_BLACKLISTED" });
  }
  if (user.status === "deleted") {
    return res.status(401).json({ ok: false, error: "账号不存在", code: "ACCOUNT_DELETED" });
  }
  markUserLogin(user.id, "email_password", email);
  const token = signToken(user);
  return res.json({
    ok: true,
    token,
    user: {
      id: user.id,
      email: user.email,
      role: user.role,
      displayName: user.display_name,
      inviteCode: user.invite_code,
      loginMethod: "email_password",
      loginAccount: email
    }
  });
});

app.get("/api/me/usage", authMiddleware, (req, res) => {
  const usage = getUserUsage(req.user.id);
  if (!usage) return res.status(404).json({ error: "用户不存在", code: "ACCOUNT_DELETED" });
  res.json({ ok: true, ...usage });
});

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
  const result = deleteBotCompletely(req.params.id);
  for (const token of result.tokens || []) removeOpenClawAccount(token);
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
app.get("/api/bots/:id/stats", authMiddleware, (req, res) => {
  const bot = getBotById(req.params.id);
  if (!bot || !bot.is_active || bot.user_id !== req.user.id) return res.status(404).json({ error: "not found" });
  try {
    const count = getDb().prepare("SELECT COUNT(*) as c FROM conversations WHERE bot_id = ?").get(req.params.id);
    res.json({ ok: true, msgCount: count.c });
  } catch { res.json({ ok: true, msgCount: 0 }); }
});
app.get("/api/bots/:id/history", authMiddleware, (req, res) => {
  const bot = getBotById(req.params.id);
  if (!bot || !bot.is_active || bot.user_id !== req.user.id) return res.status(404).json({ error: "not found" });
  const senderId = String(req.query.senderId || "").trim();
  if (!senderId) return res.status(400).json({ error: "senderId required" });
  const messages = getDb()
    .prepare("SELECT role, content, emotion, sender_id FROM conversations WHERE bot_id = ? AND sender_id = ? ORDER BY id ASC LIMIT 50")
    .all(req.params.id, senderId);
  res.json({ ok: true, messages });
});

app.post("/api/chat/:botId", authMiddleware, async (req, res) => {
  try {
    const bot = getBotById(req.params.botId);
    if (!bot || !bot.is_active) return res.status(404).json({ error: "机器人不存在或已停用" });

    if (bot.user_id !== req.user.id) return res.status(404).json({ error: "机器人不存在" });
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
    res.json({ ok: true, text: result.reply, texts: result.replyParts, reply: result.reply, replyParts: result.replyParts, aiEmotion: result.aiEmotion });
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
  syncToOpenClaw(token, wxUserId || "", finalBaseUrl, bot.id);
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

app.get("/api/admin/account-events", authMiddleware, adminMiddleware, (req, res) => {
  res.json({ ok: true, events: getAccountEvents(200) });
});

app.post("/api/admin/users/:id/blacklist", authMiddleware, adminMiddleware, (req, res) => {
  const info = blacklistUser(req.params.id, req.body?.reason || "");
  if (!info.changes) return res.status(404).json({ error: "用户不存在或不能拉黑管理员" });
  res.json({ ok: true, userId: Number(req.params.id) });
});

app.post("/api/admin/users/:id/restore", authMiddleware, adminMiddleware, (req, res) => {
  const info = restoreUser(req.params.id);
  if (!info.changes) return res.status(404).json({ error: "用户不存在" });
  res.json({ ok: true, userId: Number(req.params.id) });
});

app.delete("/api/admin/users/:id", authMiddleware, adminMiddleware, (req, res) => {
  const result = deleteUserCompletely(Number(req.params.id));
  if (!result.changes) return res.status(404).json({ error: "用户不存在或不能删除管理员" });
  for (const token of result.tokens || []) removeOpenClawAccount(token);
  res.json({ ok: true, deletedUserId: Number(req.params.id) });
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

// ══════════════════════════════════════════
// 聊天引擎
// ══════════════════════════════════════════

function normalizePersonality(p) {
  return { ...DEFAULT_PERSONALITY, ...(p || {}), traits: { ...DEFAULT_PERSONALITY.traits, ...((p && p.traits) || {}) } };
}

function isIdentityQuestion(text) {
  return /你叫(什么|啥|啥名|什么名字)|你是谁|你的名字|怎么称呼/.test(text);
}

async function legacyNodeProcessDisabled({ botId, text, personality, source, senderId }) {
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
  const systemPrompt = legacyPromptBuilder(p, relationship, memories);
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

function normalizeReplyParts(parts, fallback = "") {
  const sourceParts = Array.isArray(parts) ? parts : [];
  const normalized = sourceParts.map((part) => String(part || "").trim()).filter(Boolean);
  if (normalized.length) return normalized;
  const fallbackText = String(fallback || "").trim();
  return fallbackText ? [fallbackText] : [COMPANION_FAILURE_REPLY];
}

function getProviderConfig() {
  return {
    api_key: getSetting("deepseek_api_key", ""),
    base_url: process.env.DEEPSEEK_BASE_URL || "",
    model: MODEL
  };
}

async function processCompanionMessage({ botId, text, personality, source, senderId }) {
  const cleanText = sanitizeInput(text);
  if (!cleanText) throw Object.assign(new Error("消息为空"), { code: "EMPTY_MESSAGE" });
  const userKey = String(senderId || `${source || "unknown"}-user`);
  const p = normalizePersonality(personality);
  const userEmotion = detectUserEmotion(cleanText);
  addMessage(botId, "user", cleanText, userEmotion, userKey);

  try {
    const companion = await createCompanionReply({
      bot_id: String(botId),
      user_key: userKey,
      channel: source || "web",
      text: cleanText,
      personality_config: p,
      recent_messages: getRecentMessages(botId, 40),
      relationship: getCompanionRelationship(botId, userKey),
      memories: getCompanionMemories(botId, userKey),
      conversation_summary: getConversationSummary(botId, userKey),
      provider_config: getProviderConfig(),
      features: {
        context_understanding: process.env.COMPANION_CONTEXT_UNDERSTANDING_ENABLED === "1",
        conversation_state: process.env.COMPANION_CONVERSATION_STATE_ENABLED === "1",
        reply_rhythm: true
      }
    });

    const replyParts = normalizeReplyParts(companion.replyParts, companion.reply);
    const reply = replyParts.join("\n");
    const aiEmotion = detectUserEmotion(reply);
    const assistantMessageIds = replyParts.map((part) => addMessage(botId, "assistant", part, aiEmotion, userKey).lastInsertRowid);

    updateCompanionRelationship(botId, userKey, companion.relationshipDelta || { intimacy: 0.01, trust: 0.005 });
    for (const memory of companion.memoryCandidates || []) {
      setCompanionMemory(botId, userKey, memory);
    }
    updateConversationSummary(botId, userKey, {
      nextReplyTask: companion.directorGoal?.primary_goal || companion.directorGoal?.goal || "",
      evidence: [
        { type: "last_user_message", text: cleanText.slice(0, 120) },
        { type: "last_reply_parts", count: replyParts.length }
      ]
    });
    recordReplyJudgement(botId, userKey, assistantMessageIds.at(-1) || null, companion.judge || {});
    recordMessageStat(botId, 1, replyParts.length);

    return {
      reply,
      replyParts,
      userEmotion,
      aiEmotion,
      companion: {
        directorGoal: companion.directorGoal || {},
        judge: companion.judge || {},
        memoryCount: (companion.memoryCandidates || []).length
      }
    };
  } catch (error) {
    if (!isCompanionUnavailable(error)) throw error;
    console.warn("[companion] unavailable:", error.message);
    addMessage(botId, "assistant", COMPANION_FAILURE_REPLY, "平静", userKey);
    recordMessageStat(botId, 1, 1);
    return {
      reply: COMPANION_FAILURE_REPLY,
      replyParts: [COMPANION_FAILURE_REPLY],
      userEmotion,
      aiEmotion: "平静"
    };
  }
}

// ══════════════════════════════════════════
// 启动
// ══════════════════════════════════════════

app.use(errorHandler);

// 404 handler
app.use((req, res) => { res.status(404).sendFile(join(__dirname, "..", "client", "404.html")); });

server.listen(PORT, () => {
  console.log("\nEmotion AI SaaS is running");
  console.log("Chat:     http://localhost:" + PORT);
  console.log("Admin:    http://localhost:" + PORT + "/admin.html");
  console.log("Dashboard: http://localhost:" + PORT + "/dashboard.html\n");
});
