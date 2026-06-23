import assert from "node:assert/strict";
import {
  addMessage,
  createBot,
  createUser,
  deleteUserCompletely,
  getConversationSummary,
  getRecentMessages,
  initDatabase,
  updateConversationSummary,
} from "../server/database.js";

initDatabase();

const suffix = `${Date.now()}-${Math.random().toString(16).slice(2)}`;
let userId;

try {
  createUser(`context-v2-${suffix}@example.test`, "password123");
  const db = (await import("../server/database.js")).getDb();
  userId = db.prepare("SELECT id FROM users WHERE email = ?").get(`context-v2-${suffix}@example.test`).id;
  const botId = createBot(userId, "context-v2-bot", {});

  addMessage(botId, "user", "alice-user-message", "", "alice");
  addMessage(botId, "assistant", "alice-assistant-message", "", "alice");
  addMessage(botId, "user", "bob-user-message", "", "bob");
  addMessage(botId, "assistant", "bob-assistant-message", "", "bob");

  const aliceMessages = getRecentMessages(botId, 20, "alice");
  assert.deepEqual(
    aliceMessages.map((message) => message.content),
    ["alice-user-message", "alice-assistant-message"]
  );

  updateConversationSummary(botId, "alice", {
    rollingSummary: "Alice is testing context isolation.",
    unresolvedTopics: ["context isolation"],
    userPreferences: ["no cross-user leakage"],
    recentFeedback: ["wants continuity"],
  });

  assert.deepEqual(getConversationSummary(botId, "bob").unresolvedTopics, []);
  const aliceSummary = getConversationSummary(botId, "alice");
  assert.equal(aliceSummary.rollingSummary, "Alice is testing context isolation.");
  assert.deepEqual(aliceSummary.unresolvedTopics, ["context isolation"]);
} finally {
  if (userId) deleteUserCompletely(userId);
}

console.log("companion context v2 check passed");
