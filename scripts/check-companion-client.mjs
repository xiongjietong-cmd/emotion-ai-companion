import assert from "node:assert/strict";
import http from "node:http";

const server = http.createServer((request, response) => {
  if (request.method !== "POST" || request.url !== "/v1/reply") {
    response.writeHead(404, { "Content-Type": "application/json" });
    response.end(JSON.stringify({ error: "not found" }));
    return;
  }

  request.resume();
  response.writeHead(200, { "Content-Type": "application/json" });
  response.end(JSON.stringify({
    reply: "sidecar reply",
    reply_parts: ["sidecar reply", "second part"],
    relationship_delta: { intimacy: 0.01 },
    memory_candidates: [],
    director_goal: { primary_goal: "emotion_ack" },
    judge: { score: 0.9, passed: true },
  }));
});

await new Promise((resolve) => server.listen(3115, "127.0.0.1", resolve));
process.env.COMPANION_CORE_URL = "http://127.0.0.1:3115";

try {
  const { DEFAULT_COMPANION_CORE_TIMEOUT_MS, createCompanionReply } = await import("../server/companion-client.js");
  assert.equal(DEFAULT_COMPANION_CORE_TIMEOUT_MS, 30000);
  const result = await createCompanionReply({
    bot_id: "1",
    user_key: "client-test",
    channel: "web",
    text: "今天有点累",
    recent_messages: [],
    memories: [],
    relationship: {},
  });

  assert.deepEqual(result, {
    ok: true,
    reply: "sidecar reply",
    replyParts: ["sidecar reply", "second part"],
    relationshipDelta: { intimacy: 0.01 },
    memoryCandidates: [],
    directorGoal: { primary_goal: "emotion_ack" },
    judge: { score: 0.9, passed: true },
  });

  console.log("companion client check passed");
} finally {
  await new Promise((resolve) => server.close(resolve));
}
