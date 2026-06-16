import Database from "better-sqlite3";
import { fileURLToPath } from "url";
import { dirname, join } from "path";

const __dirname = dirname(fileURLToPath(import.meta.url));
const DB_PATH = join(__dirname, "..", "data", "emotion-ai.db");

let db;

export function initDatabase() {
  db = new Database(DB_PATH);
  db.pragma("journal_mode = WAL");
  db.pragma("foreign_keys = ON");

  db.exec(`
    CREATE TABLE IF NOT EXISTS settings (
      key   TEXT PRIMARY KEY,
      value TEXT NOT NULL
    );

    CREATE TABLE IF NOT EXISTS conversations (
      id        INTEGER PRIMARY KEY AUTOINCREMENT,
      role      TEXT NOT NULL,
      content   TEXT NOT NULL,
      emotion   TEXT DEFAULT '',
      timestamp TEXT DEFAULT CURRENT_TIMESTAMP
    );

    CREATE TABLE IF NOT EXISTS user_facts (
      id          INTEGER PRIMARY KEY AUTOINCREMENT,
      fact_key    TEXT NOT NULL,
      fact_value  TEXT NOT NULL,
      confidence  REAL DEFAULT 1.0,
      source      TEXT DEFAULT 'auto',
      created_at  TEXT DEFAULT CURRENT_TIMESTAMP,
      updated_at  TEXT DEFAULT CURRENT_TIMESTAMP
    );

    CREATE TABLE IF NOT EXISTS relationship (
      id        INTEGER PRIMARY KEY CHECK (id = 1),
      intimacy  REAL DEFAULT 0.3,
      trust     REAL DEFAULT 0.5,
      mood      TEXT DEFAULT '平静',
      updated_at TEXT DEFAULT CURRENT_TIMESTAMP
    );
  `);

  const row = db.prepare("SELECT id FROM relationship WHERE id = 1").get();
  if (!row) {
    db.prepare("INSERT INTO relationship (id, intimacy, trust, mood) VALUES (1, 0.3, 0.5, '平静')").run();
  }

  return db;
}

export function getDb() { return db; }

export function getSetting(key, defaultValue = null) {
  const row = db.prepare("SELECT value FROM settings WHERE key = ?").get(key);
  return row ? row.value : defaultValue;
}

export function setSetting(key, value) {
  db.prepare("INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)").run(key, value);
}

export function addMessage(role, content, emotion = "") {
  const info = db.prepare("INSERT INTO conversations (role, content, emotion) VALUES (?, ?, ?)").run(role, content, emotion);
  return info.lastInsertRowid;
}

export function getRecentMessages(limit = 50) {
  return db.prepare("SELECT role, content, emotion FROM conversations ORDER BY id DESC LIMIT ?").all(limit).reverse();
}

export function getSummaryContext(limit = 10) {
  return db.prepare("SELECT role, content FROM conversations ORDER BY id DESC LIMIT ?").all(limit).reverse();
}

export function setUserFact(key, value, confidence = 0.8, source = "auto") {
  const existing = db.prepare("SELECT id FROM user_facts WHERE fact_key = ?").get(key);
  if (existing) {
    db.prepare("UPDATE user_facts SET fact_value = ?, confidence = ?, source = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?")
      .run(value, confidence, source, existing.id);
  } else {
    db.prepare("INSERT INTO user_facts (fact_key, fact_value, confidence, source) VALUES (?, ?, ?, ?)")
      .run(key, value, confidence, source);
  }
}

export function getAllUserFacts() {
  return db.prepare("SELECT fact_key, fact_value, confidence, source, updated_at FROM user_facts ORDER BY updated_at DESC").all();
}

export function getRelationship() {
  const row = db.prepare("SELECT intimacy, trust, mood, updated_at FROM relationship WHERE id = 1").get();
  return row || { intimacy: 0.3, trust: 0.5, mood: "平静" };
}

export function updateRelationship(delta) {
  const cur = getRelationship();
  const intimacy = Math.max(0, Math.min(1, cur.intimacy + (delta.intimacy || 0)));
  const trust = Math.max(0, Math.min(1, cur.trust + (delta.trust || 0)));
  db.prepare("UPDATE relationship SET intimacy = ?, trust = ?, mood = ?, updated_at = CURRENT_TIMESTAMP WHERE id = 1")
    .run(intimacy, trust, delta.mood || cur.mood);
  return getRelationship();
}
