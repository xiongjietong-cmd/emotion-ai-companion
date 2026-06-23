const DEFAULT_PERSONALITY = {
  name: "小暖",
  traits: { warmth: 0.8, humor: 0.5, directness: 0.3, empathy: 0.9 },
  speakingStyle: "温柔细腻，偶尔带点俏皮",
  background: "你是一个善解人意的朋友，总是耐心倾听，用心回应。"
};

const MOODS = ["开心", "平静", "忧郁", "兴奋", "担心", "俏皮"];

function detectUserEmotion(text) {
  const t = text.toLowerCase();
  if (/开心|高兴|哈哈|太好|棒|开心|快乐|嘻嘻|nice|great|love|happy|amazing/i.test(t)) return "开心";
  if (/难过|伤心|哭|不开心|难受|悲伤|sad|cry|upset|depressed/i.test(t)) return "难过";
  if (/生气|气死|烦|讨厌|annoyed|angry|mad|frustrated/i.test(t)) return "生气";
  if (/担心|害怕|焦虑|紧张|怕|worry|anxious|scared|nervous/i.test(t)) return "担心";
  if (/无聊|没意思|好烦|bored|tired/i.test(t)) return "无聊";
  if (/？|\?|怎么|什么|为什么|如何|where|what|why|how/i.test(t)) return "好奇";
  if (/谢谢|感谢|感恩|thank|thanks|grateful/i.test(t)) return "感激";
  return "平静";
}

function getMoodForPersonality(personality, userEmotion, intimacy) {
  if (personality.traits?.empathy || 0.5 > 0.7) {
    if (userEmotion === "难过") return "担心";
    if (userEmotion === "开心") return "开心";
  }
  if (personality.traits?.humor || 0.5 > 0.6 && userEmotion === "无聊") return "俏皮";
  return "平静";
}

function buildPersonalityPrompt(personality, relationship, userFacts) {
  let factsStr = userFacts.map(f => `- ${f.fact_key}: ${f.fact_value}`).join("\n");
  const intimacyLevel = relationship.intimacy < 0.3 ? "刚认识" : relationship.intimacy < 0.6 ? "熟悉的朋友" : "亲密的朋友";

  return `你是 ${personality.name}，${personality.speakingStyle}的朋友。
身份：你叫${personality.name}，用户问名字时直接回答"我是${personality.name}"。
性格：温暖${Math.round((personality.traits?.warmth||0.5)*100)}% 幽默${Math.round((personality.traits?.humor||0.5)*100)}% 共情${Math.round((personality.traits?.empathy||0.5)*100)}%
关系：${intimacyLevel}
${personality.background ? "背景：" + personality.background + "\n" : ""}${factsStr ? "用户信息：\n" + factsStr + "\n" : ""}
规则：
- 始终用中文回复
- 回复2-3句，自然像真人朋友，不要啰嗦
- 禁止用括号描述动作表情如（笑）（叹气）
- 用户情绪低落时先共情，别急着讲道理
- 可以表达自己的感受和状态`;
}

export function buildSystemPrompt(personality, relationship, userFacts) {
  return buildPersonalityPrompt(personality, relationship, userFacts);
}

export function analyzeConversation(text) {
  return {
    userEmotion: detectUserEmotion(text),
    aiMood: "平静"
  };
}

export function getMoodEmoji(mood) {
  const map = { "开心": "😊", "平静": "😌", "忧郁": "💭", "兴奋": "✨", "担心": "🤔", "俏皮": "😏" };
  return map[mood] || "😌";
}

export { DEFAULT_PERSONALITY, MOODS, detectUserEmotion, getMoodForPersonality };
