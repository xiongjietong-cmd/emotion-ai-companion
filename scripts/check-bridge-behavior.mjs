import assert from "node:assert/strict";

import {
  buildHumanBridgeFallback,
  extractWebhookReply,
  extractWebhookReplies,
  resolveBotId,
  summarizeWebhookFailure,
} from "../multi-wechat-bridge.js";

assert.equal(
  extractWebhookReply({ ok: true, text: "hello from text" }),
  "hello from text",
  "bridge should prefer webhook text replies"
);

assert.equal(
  extractWebhookReply({ ok: true, reply: "hello from reply" }),
  "hello from reply",
  "bridge should accept webhook reply replies"
);

assert.deepEqual(
  extractWebhookReplies({ ok: true, texts: ["first", " second ", "", null] }),
  ["first", "second"],
  "bridge should accept multi-part webhook replies"
);

assert.equal(
  extractWebhookReply({ ok: false, error: "AI not ready" }),
  "",
  "bridge should not treat error payloads as successful replies"
);

const fallback = buildHumanBridgeFallback({
  status: 409,
  code: "AI_NOT_READY",
  error: "AI is not configured",
});
assert.equal(
  fallback,
  "服务器异常，暂时无法回复。请稍后再试。",
  "bridge fallback should be a plain service error"
);
assert.doesNotMatch(
  fallback,
  /陪|想你|等你|恢复后|认真回复|继续/,
  "bridge fallback must not pretend to be companion content"
);
assert.ok(fallback.length <= 120, "fallback should be short enough for WeChat");

const summary = summarizeWebhookFailure({
  status: 403,
  data: { code: "MESSAGE_LIMIT_REACHED", error: "limit reached" },
});
assert.match(summary, /403/);
assert.match(summary, /MESSAGE_LIMIT_REACHED/);

assert.equal(
  resolveBotId("abc123@im.bot", { botId: 167 }, () => null),
  167,
  "bridge should use botId saved in the account file when DB mapping is missing"
);

assert.equal(
  resolveBotId("abc123@im.bot", { botId: 167 }, () => "282"),
  282,
  "bridge should prefer the database mapping when it exists"
);

assert.equal(
  resolveBotId("abc123@im.bot", {}, () => null),
  null,
  "bridge should not silently fall back to bot 1 for unmapped accounts"
);

console.log("bridge behavior check passed");
