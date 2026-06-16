import Database from "better-sqlite3";
import { fileURLToPath } from "url";
import { dirname, join } from "path";
import crypto from "crypto";

const __dirname = dirname(fileURLToPath(import.meta.url));
const DB_PATH = join(__dirname, "..", "data", "emotion-saas.db");

let db;

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
  return db.prepare("INSERT INTO users (email, password_hash, salt) VALUES (?, ?, ?)").run(email, hash, salt);
}

export function getUserByEmail(email) {
  return db.prepare("SELECT * FROM users WHERE email = ?").get(email);
}

export function getUserById(id) {
  return db.prepare("SELECT id, email, role, display_name, created_at, last_login FROM users WHERE id = ?").get(id);
}

export function getAllUsers() {
  return db.prepare("SELECT id, email, role, display_name, created_at, last_login FROM users ORDER BY created_at DESC").all();
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
  return db.prepare("SELECT * FROM bots WHERE user_id = ? ORDER BY created_at DESC").all(userId);
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
    "INSERT OR REPLACE INTO wechat_accounts (bot_id, token, base_url, wx_user_id, is_connected) VALUES (?, ?, ?, ?, 1)"
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

export function recordMessageStat(botId) {
  const today = new Date().toISOString().slice(0, 10);
  db.prepare(
    "INSERT INTO message_stats (bot_id, date, msg_in, msg_out) VALUES (?, ?, 1, 1) ON CONFLICT(bot_id, date) DO UPDATE SET msg_in = msg_in + 1, msg_out = msg_out + 1"
  ).run(botId, today);
}
