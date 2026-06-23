import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

import { createUser, getDb, getUserByEmail, initDatabase } from "../server/database.js";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const root = path.resolve(__dirname, "..");
const preferredAdminEmail = process.env.ADMIN_EMAIL || "admin@emotion.local";
const fallbackPassword = process.env.ADMIN_PASSWORD || "Admin-ChangeMe-2026";

initDatabase();
const db = getDb();

let admin = getUserByEmail(preferredAdminEmail);
if (!admin) {
  createUser(preferredAdminEmail, fallbackPassword);
  admin = getUserByEmail(preferredAdminEmail);
}

const before = collectCounts();

const cleanup = db.transaction(() => {
  db.prepare("DELETE FROM reply_judgements").run();
  db.prepare("DELETE FROM companion_memories").run();
  db.prepare("DELETE FROM companion_relationships").run();
  db.prepare("DELETE FROM memories").run();
  db.prepare("DELETE FROM relationships").run();
  db.prepare("DELETE FROM message_stats").run();
  db.prepare("DELETE FROM conversations").run();
  db.prepare("DELETE FROM wechat_accounts").run();
  db.prepare("DELETE FROM orders").run();
  db.prepare("DELETE FROM account_events").run();
  db.prepare("DELETE FROM bots").run();
  db.prepare("DELETE FROM settings WHERE key LIKE 'wechat_%' OR key LIKE 'wx_bot_%'").run();
  db.prepare("DELETE FROM users WHERE id <> ?").run(admin.id);
  db.prepare(`
    UPDATE users
    SET role = 'admin',
        status = 'active',
        status_reason = '',
        status_updated_at = CURRENT_TIMESTAMP,
        display_name = COALESCE(NULLIF(display_name, ''), '管理员')
    WHERE id = ?
  `).run(admin.id);
});

cleanup();
const removedOpenClawFiles = removeOpenClawAccountFiles();
const after = collectCounts();
const remainingAdmins = db.prepare("SELECT id, email, role, status FROM users ORDER BY id").all();

console.log(JSON.stringify({
  ok: remainingAdmins.length === 1 && remainingAdmins[0].role === "admin" && remainingAdmins[0].status === "active",
  keptAdmin: remainingAdmins[0] || null,
  before,
  after,
  removedOpenClawFiles
}, null, 2));

function collectCounts() {
  const tables = db.prepare("SELECT name FROM sqlite_master WHERE type = 'table' AND name NOT LIKE 'sqlite_%' ORDER BY name").all();
  return Object.fromEntries(tables.map(({ name }) => [
    name,
    db.prepare(`SELECT COUNT(*) AS count FROM ${name}`).get().count
  ]));
}

function removeOpenClawAccountFiles() {
  const accountsDir = path.resolve(root, ".openclaw-state", "openclaw-weixin", "accounts");
  if (!fs.existsSync(accountsDir)) return 0;
  const files = fs.readdirSync(accountsDir, { withFileTypes: true })
    .filter((entry) => entry.isFile() && entry.name.endsWith(".json"))
    .map((entry) => path.resolve(accountsDir, entry.name));

  let removed = 0;
  for (const file of files) {
    if (!file.startsWith(accountsDir + path.sep)) {
      throw new Error(`refusing to remove file outside OpenClaw accounts dir: ${file}`);
    }
    fs.rmSync(file);
    removed += 1;
  }
  return removed;
}
