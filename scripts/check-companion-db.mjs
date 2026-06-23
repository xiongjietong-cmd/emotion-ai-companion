import assert from "node:assert/strict";
import {
  getCompanionMemories,
  getCompanionRelationship,
  getDb,
  initDatabase,
  recordReplyJudgement,
  setCompanionMemory,
  updateCompanionRelationship,
} from "../server/database.js";

initDatabase();

const botId = 1;
const userKey = `companion-db-test-${Date.now()}-${Math.random().toString(16).slice(2)}`;

const initial = getCompanionRelationship(botId, userKey);
assert.equal(initial.bot_id, botId);
assert.equal(initial.user_key, userKey);

updateCompanionRelationship(botId, userKey, { intimacy: 0.2, trust: 0.1 });
const updated = getCompanionRelationship(botId, userKey);
assert.ok(updated.intimacy > initial.intimacy);
assert.ok(updated.trust > initial.trust);

setCompanionMemory(botId, userKey, {
  key: "job_change",
  value: "用户最近在考虑换工作",
  type: "episodic",
  emotion: "stress",
  salience: 0.8,
});
const memories = getCompanionMemories(botId, userKey);
assert.ok(memories.some((memory) => memory.key === "job_change"));

recordReplyJudgement(botId, userKey, null, {
  score: 0.82,
  passed: true,
  details: { topic_momentum: 0.8 },
});
const judgement = getDb()
  .prepare("SELECT * FROM reply_judgements WHERE user_key = ? ORDER BY id DESC")
  .get(userKey);
assert.equal(judgement.score, 0.82);

console.log("companion db check passed");
