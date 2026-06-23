import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const root = path.join(__dirname, "..");
const index = fs.readFileSync(path.join(root, "client", "index.html"), "utf-8");

assert.match(index, /id="regInviteCode"/, "register page should include an invite code field");
assert.match(index, /invitePayload/, "register page should normalize invite codes before submit");
assert.match(index, /inviteCode/, "register request should submit inviteCode");
assert.match(index, /双方各加 50 条额度/, "register page should explain invitation bonus");
assert.match(index, /id="codeLoginForm"/, "login page should include a verification-code login form");
assert.match(index, /id="codeChannel"/, "verification-code login should let users choose email or phone");
assert.match(index, /id="codeAccount"/, "verification-code login should collect email or phone account");
assert.match(index, /id="codeValue"/, "verification-code login should collect the verification code");
assert.match(index, /function\s+sendLoginCode/, "login page should send login verification codes");
assert.match(index, /\/api\/auth\/code\/send/, "login page should call the send-code API");
assert.match(index, /function\s+loginWithCode/, "login page should submit verification-code login");
assert.match(index, /\/api\/auth\/code\/login/, "login page should call the code-login API");

console.log("auth UI check passed");
