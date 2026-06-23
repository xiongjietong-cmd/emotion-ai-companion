import assert from "node:assert/strict";

import { deleteUserCompletely, getDb, getUserByEmail, initDatabase } from "../server/database.js";

initDatabase();

const baseUrl = process.env.SAAS_URL || "http://127.0.0.1:3000";
const suffix = `${Date.now()}-${Math.random().toString(16).slice(2)}`;
const inviterEmail = `invite-owner-${suffix}@local.test`;
const invitedEmail = `invite-friend-${suffix}@local.test`;
const password = "InviteTest123!";

async function request(path, options = {}, expectedStatus = 200) {
  const response = await fetch(`${baseUrl}${path}`, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      ...(options.headers || {}),
    },
  });
  const body = await response.json().catch(() => ({}));
  assert.equal(response.status, expectedStatus, `${path} expected ${expectedStatus}, got ${response.status}: ${JSON.stringify(body)}`);
  return body;
}

async function register(email, inviteCode = "", expectedStatus = 200) {
  return request("/api/auth/register", {
    method: "POST",
    body: JSON.stringify({ email, password, inviteCode }),
  }, expectedStatus);
}

try {
  const owner = await register(inviterEmail);
  assert.ok(owner.user.inviteCode, "registered user should receive an invite code");

  const ownerUsageBefore = await request("/api/me/usage", {
    headers: { Authorization: `Bearer ${owner.token}` },
  });
  assert.equal(ownerUsageBefore.limits.baseMonthlyMessageLimit, 200, "free base monthly quota should be 200");
  assert.equal(ownerUsageBefore.limits.monthlyMessageLimit, 200, "user without invite bonus should start at 200");
  assert.equal(ownerUsageBefore.invite.code, owner.user.inviteCode, "usage endpoint should expose invite code");

  await register(`invite-invalid-${suffix}@local.test`, "BAD-CODE", 400);

  const friend = await register(invitedEmail, owner.user.inviteCode);
  const friendUsage = await request("/api/me/usage", {
    headers: { Authorization: `Bearer ${friend.token}` },
  });
  assert.equal(friendUsage.limits.baseMonthlyMessageLimit, 200);
  assert.equal(friendUsage.limits.bonusMessageQuota, 50, "invited user should receive 50 bonus messages");
  assert.equal(friendUsage.limits.monthlyMessageLimit, 250, "invited user total quota should be 250");

  const ownerUsageAfter = await request("/api/me/usage", {
    headers: { Authorization: `Bearer ${owner.token}` },
  });
  assert.equal(ownerUsageAfter.limits.bonusMessageQuota, 50, "inviter should receive 50 bonus messages");
  assert.equal(ownerUsageAfter.limits.monthlyMessageLimit, 250, "inviter total quota should be 250");

  const db = getDb();
  const ownerRow = getUserByEmail(inviterEmail);
  const friendRow = getUserByEmail(invitedEmail);
  assert.equal(friendRow.referred_by_user_id, ownerRow.id, "invited user should store inviter id");
  assert.equal(db.prepare("SELECT COUNT(*) AS count FROM account_events WHERE action = 'invite_reward' AND user_id = ?").get(ownerRow.id).count, 1);

  console.log("invite behavior check passed");
} finally {
  for (const email of [inviterEmail, invitedEmail, `invite-invalid-${suffix}@local.test`]) {
    const user = getUserByEmail(email);
    if (user) deleteUserCompletely(user.id);
  }
}
