import {
  addMessage,
  getRecentMessages,
  getAllUserFacts,
  getRelationship,
  updateRelationship,
  getSetting,
  setSetting
} from "./database.js";
import { isReady, chat } from "./ai-adapter.js";
import { DEFAULT_PERSONALITY, buildSystemPrompt, detectUserEmotion } from "./emotional-engine.js";

function normalizePersonality(personality) {
  return {
    ...DEFAULT_PERSONALITY,
    ...(personality || {}),
    traits: {
      ...DEFAULT_PERSONALITY.traits,
      ...((personality && personality.traits) || {})
    }
  };
}

export function getSavedPersonality() {
  const saved = getSetting("personality");
  if (!saved) return DEFAULT_PERSONALITY;
  try {
    return normalizePersonality(JSON.parse(saved));
  } catch {
    return DEFAULT_PERSONALITY;
  }
}

function buildSourceHint(source, senderId) {
  if (source === "openclaw" || source === "wechat") {
    return "\n\n## Channel\nWeChat. Reply in Chinese concisely.";
  }
  return "\n\n## Channel\nWeb chat. Reply in Chinese.";
}

function conflictsWithCurrentIdentity(message, personality) {
  if (!message || message.role !== "assistant") return false;
  const currentName = String(personality?.name || "").trim();
  if (!currentName) return false;
  const content = String(message.content || "");
  if (!/(我叫|我是|我的名字|名字|你是谁|叫什么)/.test(content)) return false;
  return !content.includes(currentName);
}

function isIdentityQuestion(text) {
  return /你(叫(什么|啥|啥名|什么名字)?|是谁|什么名字|名字是什么)|怎么称呼你|你的名字/.test(text);
}

function buildTimeHint() {
  const now = Date.now();
  const lastActive = parseInt(getSetting("last_active_time", "0")) || 0;
  setSetting("last_active_time", String(now));
  const gapMin = lastActive ? Math.round((now - lastActive) / 60000) : 0;

  if (gapMin > 120) {
    return `\n用户离开了${Math.round(gapMin / 60)}小时刚回来，自然打个招呼。`;
  } else if (gapMin > 30) {
    return `\n用户${gapMin}分钟没说话了，可以关心一下。`;
  }
  return "";
}

export async function createCompanionReply({
  text,
  source = "web",
  senderId = "",
  onStart,
  onToken
} = {}) {
  const cleanText = String(text || "").trim();
  if (!cleanText) {
    const error = new Error("Message text is required");
    error.code = "EMPTY_MESSAGE";
    throw error;
  }

  if (!isReady()) {
    const error = new Error("AI is not configured. Add a DeepSeek API key in settings.");
    error.code = "AI_NOT_READY";
    throw error;
  }

  const personality = getSavedPersonality();
  const userEmotion = detectUserEmotion(cleanText);
  addMessage("user", cleanText, userEmotion);

  if (isIdentityQuestion(cleanText)) {
    const reply = `我是${personality.name}。`;
    const aiEmotion = detectUserEmotion(reply);
    addMessage("assistant", reply, aiEmotion);
    return { reply, userEmotion, aiEmotion };
  }

  const relationship = getRelationship();
  const userFacts = getAllUserFacts();
  const timeHint = buildTimeHint();

  const systemPrompt = buildSystemPrompt(personality, relationship, userFacts)
    + buildSourceHint(source, senderId)
    + timeHint;

  const recent = getRecentMessages(10)
    .filter((m) => !conflictsWithCurrentIdentity(m, personality));

  const messagesForAI = [
    { role: "system", content: systemPrompt },
    ...recent.map((m) => ({ role: m.role, content: m.content }))
  ];

  const intimacyDelta = userEmotion === "平静" ? 0.01 : 0.005;
  updateRelationship({ intimacy: intimacyDelta, trust: 0.005, mood: userEmotion });

  if (onStart) onStart({ userEmotion });

  let fullResponse = "";
  await chat(messagesForAI, (token) => {
    fullResponse += token;
    if (onToken) onToken(token);
  });

  const aiEmotion = detectUserEmotion(fullResponse);
  addMessage("assistant", fullResponse, aiEmotion);

  return { reply: fullResponse, userEmotion, aiEmotion };
}
