import assert from "node:assert/strict";

import { getDb, initDatabase, verifyPassword } from "../server/database.js";

initDatabase();

const expectedEmail = process.env.ADMIN_EMAIL || "admin@emotion.local";
const expectedPassword = process.env.ADMIN_PASSWORD || "";

const admins = getDb()
  .prepare("SELECT id, email, role, salt, password_hash FROM users WHERE role = 'admin' ORDER BY id")
  .all();

assert.equal(admins.length, 1, `expected exactly one admin account, found ${admins.length}`);
assert.equal(admins[0].email, expectedEmail, `expected admin email ${expectedEmail}`);

if (expectedPassword) {
  assert.equal(
    verifyPassword(expectedPassword, admins[0].salt, admins[0].password_hash),
    true,
    "expected admin password to verify"
  );
}

console.log("unique admin check passed");
