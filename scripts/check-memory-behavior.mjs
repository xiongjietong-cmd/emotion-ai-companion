import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const root = path.join(__dirname, "..");
const index = fs.readFileSync(path.join(root, "server", "index.js"), "utf-8");
const database = fs.readFileSync(path.join(root, "server", "database.js"), "utf-8");

assert.match(index, /createCompanionReply/, "server should call companion core for replies");
assert.match(index, /companion\.memoryCandidates/, "server should read memory candidates from companion core");
assert.match(index, /setCompanionMemory/, "server should persist companion memory candidates");
assert.match(index, /getCompanionMemories/, "server should load per-user companion memories");

assert.doesNotMatch(index, /async function processMessage/, "legacy Node chat process should not remain in main server");
assert.doesNotMatch(index, /chatNonStreaming/, "main server should not use old non-streaming memory extraction path");
assert.doesNotMatch(index, /consolidateMemory/, "main server should not use old memory consolidator path");
assert.doesNotMatch(index, /buildSystemPrompt/, "main server should not build legacy Node prompts");

assert.match(database, /UNIQUE\(bot_id, user_key, memory_key\)/, "companion memories must be isolated by bot and user");
assert.match(database, /getCompanionMemories\(botId, userKey/, "database should expose per-user companion memory lookup");

console.log("memory behavior check passed");
