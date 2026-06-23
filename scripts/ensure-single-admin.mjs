import crypto from "node:crypto";

import { createUser, getDb, getUserByEmail, hashPassword, initDatabase } from "../server/database.js";

initDatabase();

const email = process.env.ADMIN_EMAIL || "admin@emotion.local";
const password = process.env.ADMIN_PASSWORD || generatePassword();
const db = getDb();

let user = getUserByEmail(email);
if (!user) {
  createUser(email, password);
  user = getUserByEmail(email);
} else {
  const { salt, hash } = hashPassword(password);
  db.prepare("UPDATE users SET password_hash = ?, salt = ? WHERE id = ?").run(hash, salt, user.id);
}

db.prepare("UPDATE users SET role = 'user' WHERE role = 'admin' AND email <> ?").run(email);
db.prepare("UPDATE users SET role = 'admin', display_name = ? WHERE email = ?").run("管理员", email);

const admins = db.prepare("SELECT id, email, role FROM users WHERE role = 'admin' ORDER BY id").all();

console.log(JSON.stringify({
  ok: admins.length === 1 && admins[0]?.email === email,
  email,
  password,
  admin: admins[0] || null,
  adminCount: admins.length
}, null, 2));

function generatePassword() {
  return "Admin-" + crypto.randomBytes(12).toString("base64url");
}
