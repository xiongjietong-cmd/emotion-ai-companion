import Database from "better-sqlite3";
import { fileURLToPath } from "url";
import { dirname, join } from "path";
import crypto from "crypto";

const __dirname = dirname(fileURLToPath(import.meta.url));
const DB_PATH = join(__dirname, "..", "data", "emotion-saas.db");

let db;

export const PLAN_PRICES = {
  starter: 19,
  pro: 59
};

const PLAN_LIMITS = {
  free: { code: "free", name: "免费版", botLimit: 2, wechatLimit: 1, baseMonthlyMessageLimit: 200 },
  starter: { code: "starter", name: "入门版", botLimit: 5, wechatLimit: 3, baseMonthlyMessageLimit: 1000 },
  pro: { code: "pro", name: "专业版", botLimit: 20, wechatLimit: 10, baseMonthlyMessageLimit: 10000 }
};

function hasColumn(table, column) {
  return db.prepare(`PRAGMA table_info(${table})`).all().some((row) => row.name === column);
}

function ensureColumn(table, column, definition) {
  if (!hasColumn(table, column)) {
    db.prepare(`ALTER TABLE ${table} ADD COLUMN ${column} ${definition}`).run();
  }
}

function ensureSchemaUpgrades() {
  ensureColumn("users", "plan", "TEXT DEFAULT 'free'");
  ensureColumn("users", "status", "TEXT DEFAULT 'active'");
  ensureColumn("users", "status_reason", "TEXT DEFAULT ''");
  ensureColumn("users", "status_updated_at", "TEXT");
  ensureColumn("users", "invite_code", "TEXT");
  ensureColumn("users", "referred_by_user_id", "INTEGER");
  ensureColumn("users", "bonus_message_quota", "INTEGER DEFAULT 0");
  ensureColumn("users", "phone", "TEXT");
  ensureColumn("users", "last_login_method", "TEXT");
  ensureColumn("users", "last_login_account", "TEXT");

  ensureColumn("wechat_accounts", "status", "TEXT DEFAULT 'bound'");
  ensureColumn("wechat_accounts", "last_seen_at", "TEXT");
  ensureColumn("wechat_accounts", "last_error", "TEXT");
  ensureColumn("wechat_accounts", "last_error_at", "TEXT");

  db.exec(`
    CREATE TABLE IF NOT EXISTS orders (
      id         INTEGER PRIMARY KEY AUTOINCREMENT,
      user_id    INTEGER NOT NULL REFERENCES users(id),
      plan       TEXT NOT NULL,
      amount     INTEGER NOT NULL,
      status     TEXT DEFAULT 'pending',
      created_at TEXT DEFAULT CURRENT_TIMESTAMP,
      paid_at    TEXT
    );

    CREATE TABLE IF NOT EXISTS account_events (
      id         INTEGER PRIMARY KEY AUTOINCREMENT,
      user_id    INTEGER,
      bot_id     INTEGER,
      action     TEXT NOT NULL,
      channel    TEXT DEFAULT '',
      detail     TEXT DEFAULT '',
      created_at TEXT DEFAULT CURRENT_TIMESTAMP
    );

    CREATE TABLE IF NOT EXISTS companion_relationships (
      id              INTEGER PRIMARY KEY AUTOINCREMENT,
      bot_id          INTEGER NOT NULL,
      user_key        TEXT NOT NULL,
      intimacy        REAL DEFAULT 0.1,
      trust           REAL DEFAULT 0.1,
      attachment      REAL DEFAULT 0.1,
      humor           REAL DEFAULT 0.4,
      activity        REAL DEFAULT 0.5,
      rationality     REAL DEFAULT 0.5,
      emotionality    REAL DEFAULT 0.5,
      safety          REAL DEFAULT 0.3,
      loneliness      REAL DEFAULT 0.35,
      expressiveness  REAL DEFAULT 0.45,
      updated_at      TEXT DEFAULT CURRENT_TIMESTAMP,
      UNIQUE(bot_id, user_key)
    );

    CREATE TABLE IF NOT EXISTS companion_memories (
      id            INTEGER PRIMARY KEY AUTOINCREMENT,
      bot_id        INTEGER NOT NULL,
      user_key      TEXT NOT NULL,
      memory_key    TEXT NOT NULL,
      memory_value  TEXT NOT NULL,
      memory_type   TEXT DEFAULT 'episodic',
      emotion       TEXT DEFAULT '',
      salience      REAL DEFAULT 0.5,
      source        TEXT DEFAULT 'auto',
      last_used_at  TEXT,
      created_at    TEXT DEFAULT CURRENT_TIMESTAMP,
      updated_at    TEXT DEFAULT CURRENT_TIMESTAMP,
      UNIQUE(bot_id, user_key, memory_key)
    );

    CREATE TABLE IF NOT EXISTS conversation_summaries (
      id                INTEGER PRIMARY KEY AUTOINCREMENT,
      bot_id            INTEGER NOT NULL,
      user_key          TEXT NOT NULL,
      rolling_summary   TEXT DEFAULT '',
      active_topic      TEXT DEFAULT '',
      emotional_thread  TEXT DEFAULT '',
      user_boundary     TEXT DEFAULT '',
      last_ai_mistake   TEXT DEFAULT '',
      unresolved_need   TEXT DEFAULT '',
      user_patience     TEXT DEFAULT 'normal',
      next_reply_task   TEXT DEFAULT '',
      evidence          TEXT DEFAULT '[]',
      updated_at        TEXT DEFAULT CURRENT_TIMESTAMP,
      UNIQUE(bot_id, user_key)
    );

    CREATE TABLE IF NOT EXISTS reply_judgements (
      id          INTEGER PRIMARY KEY AUTOINCREMENT,
      bot_id      INTEGER NOT NULL,
      user_key    TEXT NOT NULL,
      message_id  INTEGER,
      score       REAL DEFAULT 0,
      passed      INTEGER DEFAULT 0,
      details     TEXT DEFAULT '{}',
      created_at  TEXT DEFAULT CURRENT_TIMESTAMP
    );
  `);

  ensureColumn("companion_relationships", "attachment", "REAL DEFAULT 0.1");
  ensureColumn("companion_relationships", "humor", "REAL DEFAULT 0.4");
  ensureColumn("companion_relationships", "activity", "REAL DEFAULT 0.5");
  ensureColumn("companion_relationships", "rationality", "REAL DEFAULT 0.5");
  ensureColumn("companion_relationships", "emotionality", "REAL DEFAULT 0.5");
  ensureColumn("companion_relationships", "safety", "REAL DEFAULT 0.3");
  ensureColumn("companion_relationships", "loneliness", "REAL DEFAULT 0.35");
  ensureColumn("companion_relationships", "expressiveness", "REAL DEFAULT 0.45");
  ensureColumn("companion_relationships", "updated_at", "TEXT");

  ensureColumn("companion_memories", "memory_type", "TEXT DEFAULT 'episodic'");
  ensureColumn("companion_memories", "emotion", "TEXT DEFAULT ''");
  ensureColumn("companion_memories", "salience", "REAL DEFAULT 0.5");
  ensureColumn("companion_memories", "source", "TEXT DEFAULT 'auto'");
  ensureColumn("companion_memories", "last_used_at", "TEXT");
  ensureColumn("companion_memories", "created_at", "TEXT");
  ensureColumn("companion_memories", "updated_at", "TEXT");

  ensureColumn("conversation_summaries", "active_topic", "TEXT DEFAULT ''");
  ensureColumn("conversation_summaries", "emotional_thread", "TEXT DEFAULT ''");
  ensureColumn("conversation_summaries", "user_boundary", "TEXT DEFAULT ''");
  ensureColumn("conversation_summaries", "last_ai_mistake", "TEXT DEFAULT ''");
  ensureColumn("conversation_summaries", "unresolved_need", "TEXT DEFAULT ''");
  ensureColumn("conversation_summaries", "user_patience", "TEXT DEFAULT 'normal'");
  ensureColumn("conversation_summaries", "next_reply_task", "TEXT DEFAULT ''");
  ensureColumn("conversation_summaries", "evidence", "TEXT DEFAULT '[]'");
  ensureColumn("conversation_summaries", "updated_at", "TEXT");

  db.prepare("UPDATE users SET plan = 'free' WHERE plan IS NULL OR plan = ''").run();
  db.prepare("UPDATE users SET status = 'active' WHERE status IS NULL OR status = ''").run();
  db.prepare("UPDATE users SET bonus_message_quota = 0 WHERE bonus_message_quota IS NULL").run();
  db.prepare("UPDATE users SET invite_code = ? || id WHERE invite_code IS NULL OR invite_code = ''").run("U");
}

export function initDatabase() {
  db = new Database(DB_PATH);
  db.pragma("journal_mode = WAL");
  db.pragma("foreign_keys = ON");

  db.exec(`
    -- 用户表
    CREATE TABLE IF NOT EXISTS users (
      id            INTEGER PRIMARY KEY AUTOINCREMENT,
      email         TEXT NOT NULL UNIQUE,
      password_hash TEXT NOT NULL,
      salt          TEXT NOT NULL,
      role          TEXT DEFAULT 'user',
      display_name  TEXT DEFAULT '',
      created_at    TEXT DEFAULT CURRENT_TIMESTAMP,
      last_login    TEXT
    );

    -- 机器人表
    CREATE TABLE IF NOT EXISTS bots (
      id            INTEGER PRIMARY KEY AUTOINCREMENT,
      user_id       INTEGER NOT NULL REFERENCES users(id),
      name          TEXT NOT NULL DEFAULT '小暖',
      personality   TEXT DEFAULT '{}',
      webhook_secret TEXT UNIQUE,
      is_active     INTEGER DEFAULT 1,
      created_at    TEXT DEFAULT CURRENT_TIMESTAMP
    );

    -- 对话记录
    CREATE TABLE IF NOT EXISTS conversations (
      id            INTEGER PRIMARY KEY AUTOINCREMENT,
      bot_id        INTEGER NOT NULL REFERENCES bots(id),
      sender_id     TEXT DEFAULT '',
      role          TEXT NOT NULL,
      content       TEXT NOT NULL,
      emotion       TEXT DEFAULT '',
      timestamp     TEXT DEFAULT CURRENT_TIMESTAMP
    );

    -- 长期记忆
    CREATE TABLE IF NOT EXISTS memories (
      id            INTEGER PRIMARY KEY AUTOINCREMENT,
      bot_id        INTEGER NOT NULL REFERENCES bots(id),
      fact_key      TEXT NOT NULL,
      fact_value    TEXT NOT NULL,
      confidence    REAL DEFAULT 1.0,
      source        TEXT DEFAULT 'auto',
      created_at    TEXT DEFAULT CURRENT_TIMESTAMP,
      updated_at    TEXT DEFAULT CURRENT_TIMESTAMP,
      UNIQUE(bot_id, fact_key)
    );

    -- 关系状态（每个机器人独立）
    CREATE TABLE IF NOT EXISTS relationships (
      id            INTEGER PRIMARY KEY AUTOINCREMENT,
      bot_id        INTEGER NOT NULL REFERENCES bots(id) UNIQUE,
      intimacy      REAL DEFAULT 0.3,
      trust         REAL DEFAULT 0.5,
      mood          TEXT DEFAULT '平静',
      updated_at    TEXT DEFAULT CURRENT_TIMESTAMP
    );

    -- 微信账号绑定
    CREATE TABLE IF NOT EXISTS wechat_accounts (
      id            INTEGER PRIMARY KEY AUTOINCREMENT,
      bot_id        INTEGER NOT NULL REFERENCES bots(id) UNIQUE,
      token         TEXT NOT NULL,
      base_url      TEXT NOT NULL DEFAULT 'https://ilinkai.weixin.qq.com',
      wx_user_id    TEXT DEFAULT '',
      sync_buf      TEXT DEFAULT '',
      is_connected  INTEGER DEFAULT 0,
      created_at    TEXT DEFAULT CURRENT_TIMESTAMP
    );

    -- 平台设置
    CREATE TABLE IF NOT EXISTS settings (
      key           TEXT PRIMARY KEY,
      value         TEXT NOT NULL
    );

    -- 消息统计（按天汇总）
    CREATE TABLE IF NOT EXISTS message_stats (
      id            INTEGER PRIMARY KEY AUTOINCREMENT,
      bot_id        INTEGER NOT NULL REFERENCES bots(id),
      date          TEXT NOT NULL,
      msg_in        INTEGER DEFAULT 0,
      msg_out       INTEGER DEFAULT 0,
      UNIQUE(bot_id, date)
    );
  `);

  ensureSchemaUpgrades();

  return db;
}

export function getDb() { return db; }

// ─── 密码工具 ───
export function hashPassword(password) {
  const salt = crypto.randomBytes(16).toString("hex");
  const hash = crypto.pbkdf2Sync(password, salt, 10000, 64, "sha512").toString("hex");
  return { salt, hash };
}

export function verifyPassword(password, salt, hash) {
  const testHash = crypto.pbkdf2Sync(password, salt, 10000, 64, "sha512").toString("hex");
  return testHash === hash;
}

// ─── 用户操作 ───
export function createUser(email, password) {
  const { salt, hash } = hashPassword(password);
  const inviteCode = makeInviteCode();
  return db.prepare(
    "INSERT INTO users (email, password_hash, salt, invite_code, plan, status, bonus_message_quota, last_login_method, last_login_account) VALUES (?, ?, ?, ?, 'free', 'active', 0, 'email_password', ?)"
  ).run(email, hash, salt, inviteCode, email);
}

export function getUserByEmail(email) {
  return db.prepare("SELECT * FROM users WHERE email = ?").get(email);
}

export function getUserById(id) {
  return db.prepare(`
    SELECT id, email, role, display_name, created_at, last_login, plan, status,
           status_reason, invite_code, referred_by_user_id, bonus_message_quota,
           phone, last_login_method, last_login_account
    FROM users WHERE id = ?
  `).get(id);
}

export function getAllUsers() {
  return db.prepare(`
    SELECT id, email, role, display_name, created_at, last_login, plan, status,
           status_reason, invite_code, referred_by_user_id, bonus_message_quota,
           phone, last_login_method, last_login_account
    FROM users ORDER BY created_at DESC
  `).all();
}

export function getUserCount() {
  return db.prepare("SELECT COUNT(*) as count FROM users").get().count;
}

// ─── 机器人操作 ───
export function createBot(userId, name, personality) {
  const webhookSecret = crypto.randomBytes(16).toString("hex");
  const info = db.prepare(
    "INSERT INTO bots (user_id, name, personality, webhook_secret) VALUES (?, ?, ?, ?)"
  ).run(userId, name, JSON.stringify(personality || {}), webhookSecret);
  
  // 初始化关系
  db.prepare("INSERT INTO relationships (bot_id) VALUES (?)").run(info.lastInsertRowid);
  return info.lastInsertRowid;
}

export function getBotsByUser(userId) {
  return db.prepare(`
    SELECT b.*,
           COALESCE(ms.msg_in, 0) AS msg_in,
           COALESCE(ms.msg_out, 0) AS msg_out,
           COALESCE(mm.memory_count, 0) AS memory_count,
           lm.last_message_at
    FROM bots b
    LEFT JOIN (
      SELECT bot_id, SUM(msg_in) AS msg_in, SUM(msg_out) AS msg_out
      FROM message_stats GROUP BY bot_id
    ) ms ON ms.bot_id = b.id
    LEFT JOIN (
      SELECT bot_id, COUNT(*) AS memory_count FROM memories GROUP BY bot_id
    ) mm ON mm.bot_id = b.id
    LEFT JOIN (
      SELECT bot_id, MAX(timestamp) AS last_message_at FROM conversations GROUP BY bot_id
    ) lm ON lm.bot_id = b.id
    WHERE b.user_id = ? AND b.is_active = 1
    ORDER BY b.created_at DESC
  `).all(userId);
}

export function getBotById(botId) {
  return db.prepare("SELECT * FROM bots WHERE id = ?").get(botId);
}

export function updateBot(botId, updates) {
  const fields = [];
  const values = [];
  for (const [k, v] of Object.entries(updates)) {
    if (k === 'personality') {
      fields.push("personality = ?");
      values.push(JSON.stringify(v));
    } else {
      fields.push(k + " = ?");
      values.push(v);
    }
  }
  values.push(botId);
  return db.prepare("UPDATE bots SET " + fields.join(", ") + " WHERE id = ?").run(...values);
}

export function getTotalBotCount() {
  return db.prepare("SELECT COUNT(*) as count FROM bots").get().count;
}

export function deleteBotCompletely(botId) {
  const bot = db.prepare("SELECT * FROM bots WHERE id = ?").get(botId);
  if (!bot) return { changes: 0, tokens: [] };
  const tokens = db.prepare("SELECT token FROM wechat_accounts WHERE bot_id = ?").all(botId).map((row) => row.token).filter(Boolean);
  const tx = db.transaction(() => {
    db.prepare("DELETE FROM wechat_accounts WHERE bot_id = ?").run(botId);
    db.prepare("DELETE FROM memories WHERE bot_id = ?").run(botId);
    db.prepare("DELETE FROM relationships WHERE bot_id = ?").run(botId);
    db.prepare("DELETE FROM message_stats WHERE bot_id = ?").run(botId);
    db.prepare("DELETE FROM conversations WHERE bot_id = ?").run(botId);
    db.prepare("DELETE FROM companion_relationships WHERE bot_id = ?").run(botId);
    db.prepare("DELETE FROM companion_memories WHERE bot_id = ?").run(botId);
    db.prepare("DELETE FROM conversation_summaries WHERE bot_id = ?").run(botId);
    db.prepare("DELETE FROM reply_judgements WHERE bot_id = ?").run(botId);
    db.prepare("DELETE FROM bots WHERE id = ?").run(botId);
  });
  tx();
  return { changes: 1, tokens };
}

// ─── 对话操作 ───
export function addMessage(botId, role, content, emotion = "", senderId = "") {
  return db.prepare(
    "INSERT INTO conversations (bot_id, sender_id, role, content, emotion) VALUES (?, ?, ?, ?, ?)"
  ).run(botId, senderId, role, content, emotion);
}

export function getRecentMessages(botId, limit = 30) {
  return db.prepare(
    "SELECT role, content, emotion, sender_id FROM conversations WHERE bot_id = ? ORDER BY id DESC LIMIT ?"
  ).all(botId, limit).reverse();
}

// ─── 记忆操作 ───
export function setMemory(botId, key, value, confidence = 0.8, source = "auto") {
  return db.prepare(
    "INSERT OR REPLACE INTO memories (bot_id, fact_key, fact_value, confidence, source, updated_at) VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP)"
  ).run(botId, key, value, confidence, source);
}

export function getMemories(botId) {
  return db.prepare(
    "SELECT fact_key, fact_value, confidence, source FROM memories WHERE bot_id = ? ORDER BY updated_at DESC"
  ).all(botId);
}

export function deleteMemory(botId, key) {
  return db.prepare("DELETE FROM memories WHERE bot_id = ? AND fact_key = ?").run(botId, key);
}

// ─── 关系操作 ───
export function getRelationship(botId) {
  const row = db.prepare("SELECT * FROM relationships WHERE bot_id = ?").get(botId);
  return row || { intimacy: 0.3, trust: 0.5, mood: "平静" };
}

export function updateRelationship(botId, delta) {
  const cur = getRelationship(botId);
  const intimacy = Math.max(0, Math.min(1, cur.intimacy + (delta.intimacy || 0)));
  const trust = Math.max(0, Math.min(1, cur.trust + (delta.trust || 0)));
  db.prepare("UPDATE relationships SET intimacy = ?, trust = ?, mood = ?, updated_at = CURRENT_TIMESTAMP WHERE bot_id = ?")
    .run(intimacy, trust, delta.mood || cur.mood, botId);
  return getRelationship(botId);
}

function clamp01(value) {
  const number = Number(value);
  if (!Number.isFinite(number)) return 0;
  return Math.max(0, Math.min(1, number));
}

function parseJson(value, fallback) {
  try {
    return value ? JSON.parse(value) : fallback;
  } catch {
    return fallback;
  }
}

export function getCompanionRelationship(botId, userKey) {
  const key = String(userKey || "default");
  let row = db.prepare("SELECT * FROM companion_relationships WHERE bot_id = ? AND user_key = ?").get(botId, key);
  if (!row) {
    db.prepare("INSERT INTO companion_relationships (bot_id, user_key) VALUES (?, ?)").run(botId, key);
    row = db.prepare("SELECT * FROM companion_relationships WHERE bot_id = ? AND user_key = ?").get(botId, key);
  }
  return row;
}

export function updateCompanionRelationship(botId, userKey, delta = {}) {
  const current = getCompanionRelationship(botId, userKey);
  const fields = [
    "intimacy",
    "trust",
    "attachment",
    "humor",
    "activity",
    "rationality",
    "emotionality",
    "safety",
    "loneliness",
    "expressiveness"
  ];
  const next = {};
  for (const field of fields) {
    next[field] = clamp01(Number(current[field] || 0) + Number(delta[field] || 0));
  }
  db.prepare(`
    UPDATE companion_relationships
    SET intimacy = ?, trust = ?, attachment = ?, humor = ?, activity = ?,
        rationality = ?, emotionality = ?, safety = ?, loneliness = ?,
        expressiveness = ?, updated_at = CURRENT_TIMESTAMP
    WHERE bot_id = ? AND user_key = ?
  `).run(
    next.intimacy,
    next.trust,
    next.attachment,
    next.humor,
    next.activity,
    next.rationality,
    next.emotionality,
    next.safety,
    next.loneliness,
    next.expressiveness,
    botId,
    String(userKey || "default")
  );
  return getCompanionRelationship(botId, userKey);
}

export function setCompanionMemory(botId, userKey, memory = {}) {
  const key = String(memory.key || memory.memory_key || "").trim();
  const value = String(memory.value || memory.memory_value || "").trim();
  if (!key || !value) return { changes: 0 };
  return db.prepare(`
    INSERT INTO companion_memories
      (bot_id, user_key, memory_key, memory_value, memory_type, emotion, salience, source, updated_at)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
    ON CONFLICT(bot_id, user_key, memory_key)
    DO UPDATE SET
      memory_value = excluded.memory_value,
      memory_type = excluded.memory_type,
      emotion = excluded.emotion,
      salience = excluded.salience,
      source = excluded.source,
      updated_at = CURRENT_TIMESTAMP
  `).run(
    botId,
    String(userKey || "default"),
    key,
    value,
    memory.type || memory.memory_type || "episodic",
    memory.emotion || "",
    Number(memory.salience ?? 0.5),
    memory.source || "auto"
  );
}

export function getCompanionMemories(botId, userKey, limit = 20) {
  return db.prepare(`
    SELECT memory_key AS key,
           memory_value AS value,
           memory_type AS type,
           emotion,
           salience,
           source,
           created_at,
           updated_at,
           last_used_at
    FROM companion_memories
    WHERE bot_id = ? AND user_key = ?
    ORDER BY salience DESC, updated_at DESC
    LIMIT ?
  `).all(botId, String(userKey || "default"), limit);
}

export function getConversationSummary(botId, userKey) {
  const key = String(userKey || "default");
  let row = db.prepare("SELECT * FROM conversation_summaries WHERE bot_id = ? AND user_key = ?").get(botId, key);
  if (!row) {
    db.prepare("INSERT INTO conversation_summaries (bot_id, user_key) VALUES (?, ?)").run(botId, key);
    row = db.prepare("SELECT * FROM conversation_summaries WHERE bot_id = ? AND user_key = ?").get(botId, key);
  }
  const evidence = parseJson(row.evidence, []);
  return {
    ...row,
    evidence,
    rollingSummary: row.rolling_summary || "",
    activeTopic: row.active_topic || "",
    emotionalThread: row.emotional_thread || "",
    userBoundary: row.user_boundary || "",
    lastAiMistake: row.last_ai_mistake || "",
    unresolvedNeed: row.unresolved_need || "",
    userPatience: row.user_patience || "normal",
    nextReplyTask: row.next_reply_task || ""
  };
}

export function updateConversationSummary(botId, userKey, patch = {}) {
  const current = getConversationSummary(botId, userKey);
  const next = {
    rolling_summary: patch.rollingSummary ?? patch.rolling_summary ?? current.rolling_summary ?? "",
    active_topic: patch.activeTopic ?? patch.active_topic ?? current.active_topic ?? "",
    emotional_thread: patch.emotionalThread ?? patch.emotional_thread ?? current.emotional_thread ?? "",
    user_boundary: patch.userBoundary ?? patch.user_boundary ?? current.user_boundary ?? "",
    last_ai_mistake: patch.lastAiMistake ?? patch.last_ai_mistake ?? current.last_ai_mistake ?? "",
    unresolved_need: patch.unresolvedNeed ?? patch.unresolved_need ?? current.unresolved_need ?? "",
    user_patience: patch.userPatience ?? patch.user_patience ?? current.user_patience ?? "normal",
    next_reply_task: patch.nextReplyTask ?? patch.next_reply_task ?? current.next_reply_task ?? "",
    evidence: JSON.stringify(patch.evidence ?? current.evidence ?? [])
  };
  db.prepare(`
    INSERT INTO conversation_summaries
      (bot_id, user_key, rolling_summary, active_topic, emotional_thread, user_boundary,
       last_ai_mistake, unresolved_need, user_patience, next_reply_task, evidence, updated_at)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
    ON CONFLICT(bot_id, user_key)
    DO UPDATE SET
      rolling_summary = excluded.rolling_summary,
      active_topic = excluded.active_topic,
      emotional_thread = excluded.emotional_thread,
      user_boundary = excluded.user_boundary,
      last_ai_mistake = excluded.last_ai_mistake,
      unresolved_need = excluded.unresolved_need,
      user_patience = excluded.user_patience,
      next_reply_task = excluded.next_reply_task,
      evidence = excluded.evidence,
      updated_at = CURRENT_TIMESTAMP
  `).run(
    botId,
    String(userKey || "default"),
    next.rolling_summary,
    next.active_topic,
    next.emotional_thread,
    next.user_boundary,
    next.last_ai_mistake,
    next.unresolved_need,
    next.user_patience,
    next.next_reply_task,
    next.evidence
  );
  return getConversationSummary(botId, userKey);
}

export function recordReplyJudgement(botId, userKey, messageId, judgement = {}) {
  return db.prepare(`
    INSERT INTO reply_judgements (bot_id, user_key, message_id, score, passed, details)
    VALUES (?, ?, ?, ?, ?, ?)
  `).run(
    botId,
    String(userKey || "default"),
    messageId || null,
    Number(judgement.score || 0),
    judgement.passed ? 1 : 0,
    JSON.stringify(judgement.details || judgement || {})
  );
}

// ─── 设置操作 ───
export function getSetting(key, defaultValue = null) {
  const row = db.prepare("SELECT value FROM settings WHERE key = ?").get(key);
  return row ? row.value : defaultValue;
}

export function setSetting(key, value) {
  db.prepare("INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)").run(key, value);
}

// ─── 微信账号 ───
export function bindWechat(botId, token, baseUrl, wxUserId) {
  return db.prepare(
    "INSERT OR REPLACE INTO wechat_accounts (bot_id, token, base_url, wx_user_id, is_connected, status, last_seen_at, last_error, last_error_at) VALUES (?, ?, ?, ?, 1, 'bound', CURRENT_TIMESTAMP, '', NULL)"
  ).run(botId, token, baseUrl, wxUserId);
}

export function getWechatAccount(botId) {
  return db.prepare("SELECT * FROM wechat_accounts WHERE bot_id = ? AND is_connected = 1").get(botId);
}

export function getAllActiveWechatAccounts() {
  return db.prepare("SELECT * FROM wechat_accounts WHERE is_connected = 1").all();
}

export function updateWechatSyncBuf(botId, syncBuf) {
  return db.prepare("UPDATE wechat_accounts SET sync_buf = ? WHERE bot_id = ?").run(syncBuf, botId);
}

export function disconnectWechat(botId) {
  const row = db.prepare("SELECT * FROM wechat_accounts WHERE bot_id = ?").get(botId);
  db.prepare("DELETE FROM wechat_accounts WHERE bot_id = ?").run(botId);
  return row;
}

export function markWechatStatus(botId, status = "online", error = "") {
  const allowed = new Set(["bound", "online", "offline", "error"]);
  const nextStatus = allowed.has(status) ? status : "bound";
  return db.prepare(`
    UPDATE wechat_accounts
    SET status = ?,
        last_seen_at = CASE WHEN ? = 'online' THEN CURRENT_TIMESTAMP ELSE last_seen_at END,
        last_error = CASE WHEN ? = 'error' THEN ? ELSE '' END,
        last_error_at = CASE WHEN ? = 'error' THEN CURRENT_TIMESTAMP ELSE last_error_at END
    WHERE bot_id = ?
  `).run(nextStatus, nextStatus, nextStatus, error || "", nextStatus, botId);
}

export function getWechatStatus(botId) {
  const row = db.prepare("SELECT * FROM wechat_accounts WHERE bot_id = ?").get(botId);
  if (!row || !row.is_connected) {
    return { isBound: false, status: "unbound", label: "未绑定", lastSeenAt: null, lastError: "" };
  }
  const status = row.status || "bound";
  const labels = {
    bound: "已绑定",
    online: "在线",
    offline: "离线",
    error: "异常"
  };
  return {
    isBound: true,
    isOnline: status === "online",
    status,
    label: labels[status] || "已绑定",
    baseUrl: row.base_url,
    wxUserId: row.wx_user_id,
    lastSeenAt: row.last_seen_at || row.created_at,
    lastError: row.last_error || ""
  };
}

// ─── 统计 ───
export function getStats() {
  const userCount = getUserCount();
  const botCount = getTotalBotCount();
  const msgCount = db.prepare("SELECT COUNT(*) as count FROM conversations").get().count;
  const wechatCount = db.prepare("SELECT COUNT(*) as count FROM wechat_accounts WHERE is_connected = 1").get().count;
  const today = new Date().toISOString().slice(0, 10);
  const todayMsgs = db.prepare(
    "SELECT COUNT(*) as count FROM conversations WHERE date(timestamp) = ?"
  ).get(today).count;
  
  return { userCount, botCount, msgCount, wechatCount, todayMsgs };
}

export function getMessageStats(days = 7) {
  return db.prepare(
    "SELECT date, SUM(msg_in) as msg_in, SUM(msg_out) as msg_out FROM message_stats GROUP BY date ORDER BY date DESC LIMIT ?"
  ).all(days).reverse();
}

export function recordMessageStat(botId, msgIn = 1, msgOut = 1) {
  const today = new Date().toISOString().slice(0, 10);
  db.prepare(
    "INSERT INTO message_stats (bot_id, date, msg_in, msg_out) VALUES (?, ?, ?, ?) ON CONFLICT(bot_id, date) DO UPDATE SET msg_in = msg_in + excluded.msg_in, msg_out = msg_out + excluded.msg_out"
  ).run(botId, today, msgIn, msgOut);
}

export function getAdminBotRows() {
  return db.prepare(`
    SELECT b.*,
           u.email AS owner,
           CASE WHEN wa.id IS NULL THEN 0 ELSE 1 END AS has_wechat,
           COALESCE(ms.msg_in, 0) AS msg_in,
           COALESCE(ms.msg_out, 0) AS msg_out,
           COALESCE(mm.memory_count, 0) AS memory_count,
           lm.last_message_at
    FROM bots b
    JOIN users u ON u.id = b.user_id
    LEFT JOIN wechat_accounts wa ON wa.bot_id = b.id AND wa.is_connected = 1
    LEFT JOIN (
      SELECT bot_id, SUM(msg_in) AS msg_in, SUM(msg_out) AS msg_out
      FROM message_stats GROUP BY bot_id
    ) ms ON ms.bot_id = b.id
    LEFT JOIN (
      SELECT bot_id, COUNT(*) AS memory_count FROM memories GROUP BY bot_id
    ) mm ON mm.bot_id = b.id
    LEFT JOIN (
      SELECT bot_id, MAX(timestamp) AS last_message_at FROM conversations GROUP BY bot_id
    ) lm ON lm.bot_id = b.id
    ORDER BY b.created_at DESC
  `).all();
}

function makeInviteCode() {
  return crypto.randomBytes(4).toString("hex").toUpperCase();
}

function getPlanLimitsForUser(user) {
  const planCode = user?.plan && PLAN_LIMITS[user.plan] ? user.plan : "free";
  const plan = PLAN_LIMITS[planCode];
  const bonusMessageQuota = Number(user?.bonus_message_quota || 0);
  return {
    ...plan,
    bonusMessageQuota,
    monthlyMessageLimit: plan.baseMonthlyMessageLimit + bonusMessageQuota
  };
}

export function getUserUsage(userId) {
  const user = getUserById(userId);
  if (!user) return null;
  const limits = getPlanLimitsForUser(user);
  const botCount = db.prepare("SELECT COUNT(*) AS count FROM bots WHERE user_id = ? AND is_active = 1").get(userId).count;
  const wechatCount = db.prepare(`
    SELECT COUNT(*) AS count
    FROM wechat_accounts wa
    JOIN bots b ON b.id = wa.bot_id
    WHERE b.user_id = ? AND b.is_active = 1 AND wa.is_connected = 1
  `).get(userId).count;
  const monthStart = new Date();
  monthStart.setDate(1);
  monthStart.setHours(0, 0, 0, 0);
  const messageCount = db.prepare(`
    SELECT COUNT(*) AS count
    FROM conversations c
    JOIN bots b ON b.id = c.bot_id
    WHERE b.user_id = ? AND c.role = 'user' AND datetime(c.timestamp) >= datetime(?)
  `).get(userId, monthStart.toISOString()).count;
  return {
    plan: { code: user.plan || "free", name: PLAN_LIMITS[user.plan]?.name || PLAN_LIMITS.free.name },
    usage: { botCount, wechatCount, messageCount },
    limits,
    remaining: {
      bots: Math.max(0, limits.botLimit - botCount),
      wechat: Math.max(0, limits.wechatLimit - wechatCount),
      messages: Math.max(0, limits.monthlyMessageLimit - messageCount)
    },
    invite: {
      code: user.invite_code,
      referredByUserId: user.referred_by_user_id || null
    }
  };
}

export function canCreateBot(userId) {
  const state = getUserUsage(userId);
  return { ok: Boolean(state && state.remaining.bots > 0), state };
}

export function canBindWechat(userId, botId) {
  const ownBinding = db.prepare("SELECT id FROM wechat_accounts WHERE bot_id = ? AND is_connected = 1").get(botId);
  if (ownBinding) return { ok: true, state: getUserUsage(userId) };
  const state = getUserUsage(userId);
  return { ok: Boolean(state && state.remaining.wechat > 0), state };
}

export function canSendMessage(userId) {
  const state = getUserUsage(userId);
  return { ok: Boolean(state && state.remaining.messages > 0), state };
}

export function createOrder(userId, plan) {
  const amount = PLAN_PRICES[plan];
  if (!amount) throw new Error("invalid plan");
  const info = db.prepare("INSERT INTO orders (user_id, plan, amount, status) VALUES (?, ?, ?, 'pending')").run(userId, plan, amount);
  recordAccountEvent(userId, null, "order_create", "web", JSON.stringify({ orderId: info.lastInsertRowid, plan, amount }));
  return info;
}

export function getOrderById(orderId) {
  return db.prepare("SELECT * FROM orders WHERE id = ?").get(orderId);
}

export function confirmOrder(orderId) {
  const order = getOrderById(orderId);
  if (!order || order.status !== "pending") return null;
  db.prepare("UPDATE orders SET status = 'paid', paid_at = CURRENT_TIMESTAMP WHERE id = ?").run(orderId);
  db.prepare("UPDATE users SET plan = ? WHERE id = ?").run(order.plan, order.user_id);
  recordAccountEvent(order.user_id, null, "order_confirm", "web", JSON.stringify({ orderId, plan: order.plan }));
  return getOrderById(orderId);
}

export function getOrdersByUser(userId) {
  return db.prepare("SELECT * FROM orders WHERE user_id = ? ORDER BY created_at DESC").all(userId);
}

export function getAllOrders() {
  return db.prepare(`
    SELECT o.*, u.email AS user_email
    FROM orders o
    LEFT JOIN users u ON u.id = o.user_id
    ORDER BY o.created_at DESC
  `).all();
}

export function getOrderStats() {
  const row = db.prepare(`
    SELECT COUNT(*) AS orderCount,
           COALESCE(SUM(CASE WHEN status = 'paid' THEN amount ELSE 0 END), 0) AS paidAmount,
           SUM(CASE WHEN status = 'pending' THEN 1 ELSE 0 END) AS pendingCount,
           SUM(CASE WHEN status = 'paid' THEN 1 ELSE 0 END) AS paidCount
    FROM orders
  `).get();
  return row || { orderCount: 0, paidAmount: 0, pendingCount: 0, paidCount: 0 };
}

export function recordAccountEvent(userId, botId, action, channel = "", detail = "") {
  return db.prepare("INSERT INTO account_events (user_id, bot_id, action, channel, detail) VALUES (?, ?, ?, ?, ?)")
    .run(userId || null, botId || null, action, channel, detail || "");
}

export function getAccountEvents(limit = 200) {
  return db.prepare(`
    SELECT e.*, u.email AS user_email, b.name AS bot_name
    FROM account_events e
    LEFT JOIN users u ON u.id = e.user_id
    LEFT JOIN bots b ON b.id = e.bot_id
    ORDER BY e.created_at DESC, e.id DESC
    LIMIT ?
  `).all(limit);
}

export function applyInviteReward(newUserId, inviteCode) {
  const code = String(inviteCode || "").trim();
  if (!code) return { applied: false };
  const inviter = db.prepare("SELECT id FROM users WHERE invite_code = ? AND id != ?").get(code, newUserId);
  if (!inviter) {
    const error = new Error("邀请码无效");
    error.code = "INVALID_INVITE_CODE";
    throw error;
  }
  db.prepare("UPDATE users SET referred_by_user_id = ?, bonus_message_quota = COALESCE(bonus_message_quota, 0) + 50 WHERE id = ?")
    .run(inviter.id, newUserId);
  db.prepare("UPDATE users SET bonus_message_quota = COALESCE(bonus_message_quota, 0) + 50 WHERE id = ?")
    .run(inviter.id);
  recordAccountEvent(inviter.id, null, "invite_reward", "system", JSON.stringify({ invitedUserId: newUserId }));
  recordAccountEvent(newUserId, null, "invite_reward", "system", JSON.stringify({ inviterUserId: inviter.id }));
  return { applied: true, inviterUserId: inviter.id };
}

export function markUserLogin(userId, method, account) {
  return db.prepare(`
    UPDATE users
    SET last_login = CURRENT_TIMESTAMP,
        last_login_method = ?,
        last_login_account = ?
    WHERE id = ?
  `).run(method, account, userId);
}

export function blacklistUser(userId, reason = "") {
  const info = db.prepare(`
    UPDATE users
    SET status = 'blacklisted',
        status_reason = ?,
        status_updated_at = CURRENT_TIMESTAMP
    WHERE id = ? AND role != 'admin'
  `).run(reason, userId);
  if (info.changes) recordAccountEvent(userId, null, "user_blacklist", "admin", reason);
  return info;
}

export function restoreUser(userId) {
  const info = db.prepare(`
    UPDATE users
    SET status = 'active',
        status_reason = '',
        status_updated_at = CURRENT_TIMESTAMP
    WHERE id = ?
  `).run(userId);
  if (info.changes) recordAccountEvent(userId, null, "user_restore", "admin", "");
  return info;
}

export function deleteUserCompletely(userId) {
  const user = db.prepare("SELECT * FROM users WHERE id = ?").get(userId);
  if (!user || user.role === "admin") return { changes: 0, tokens: [] };
  const bots = db.prepare("SELECT id FROM bots WHERE user_id = ?").all(userId);
  const tokens = db.prepare(`
    SELECT wa.token
    FROM wechat_accounts wa
    JOIN bots b ON b.id = wa.bot_id
    WHERE b.user_id = ?
  `).all(userId).map((row) => row.token).filter(Boolean);

  const tx = db.transaction(() => {
    for (const bot of bots) {
      db.prepare("DELETE FROM wechat_accounts WHERE bot_id = ?").run(bot.id);
      db.prepare("DELETE FROM memories WHERE bot_id = ?").run(bot.id);
      db.prepare("DELETE FROM relationships WHERE bot_id = ?").run(bot.id);
      db.prepare("DELETE FROM message_stats WHERE bot_id = ?").run(bot.id);
      db.prepare("DELETE FROM conversations WHERE bot_id = ?").run(bot.id);
      db.prepare("DELETE FROM companion_relationships WHERE bot_id = ?").run(bot.id);
      db.prepare("DELETE FROM companion_memories WHERE bot_id = ?").run(bot.id);
      db.prepare("DELETE FROM conversation_summaries WHERE bot_id = ?").run(bot.id);
      db.prepare("DELETE FROM reply_judgements WHERE bot_id = ?").run(bot.id);
      db.prepare("DELETE FROM bots WHERE id = ?").run(bot.id);
    }
    db.prepare("DELETE FROM orders WHERE user_id = ?").run(userId);
    db.prepare("INSERT INTO account_events (user_id, action, channel, detail) VALUES (?, 'user_delete', 'admin', ?)")
      .run(userId, JSON.stringify({ email: user.email }));
    db.prepare("DELETE FROM users WHERE id = ?").run(userId);
  });
  tx();
  return { changes: 1, tokens };
}
