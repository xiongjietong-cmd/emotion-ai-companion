import { setUserFact } from "./database.js";

// Main consolidation function - analyzes recent conversation and extracts knowledge
export async function consolidateMemory(chatFn, recentMessages, userFacts) {
  if (recentMessages.length < 6) return; // Need at least 6 messages to analyze
  
  const analysisPrompt = `你是一个记忆分析助手。分析以下对话，提取关于用户的关键信息。

从这些维度提取（如果没有相关信息就跳过）：
1. 名字/称呼 - 用户怎么称呼自己
2. 偏好/喜好 - 用户喜欢什么、不喜欢什么
3. 性格特点 - 用户的性格特征
4. 生活状态 - 工作、学习、生活近况
5. 兴趣爱好 - 用户平时喜欢做什么
6. 情绪状态 - 用户近期的情绪倾向
7. 重要经历 - 用户提到的重要事件

输出格式（每行一条）：
LABEL: 具体信息
例如：
名字: 小王
喜好: 喜欢喝咖啡，特别是拿铁
性格: 比较乐观，但容易焦虑
兴趣: 打游戏、看动漫
情绪: 最近工作压力有点大

只输出事实信息，不要输出分析过程。`;

  const messages = [
    { role: "system", content: analysisPrompt },
    ...recentMessages.slice(-10), // Last 10 messages
    { role: "user", content: "请分析以上对话，提取关于我的关键信息。" }
  ];

  try {
    const analysis = await chatFn(messages);
    const facts = parseFacts(analysis);
    
    // Save each fact to database
    for (const fact of facts) {
      setUserFact(fact.key, fact.value, 0.6, "auto_consolidate");
    }
    
    return facts;
  } catch (e) {
    console.error('Memory consolidation failed:', e.message);
    const fs = await import('fs');
    fs.appendFileSync('d:\\Documents\\New project 2\\consolidate-debug.log', new Date().toISOString() + ' ERROR: ' + e.message + '\\n', 'utf-8');
    return [];
  }
}

function parseFacts(text) {
  const facts = [];
  const lines = text.split("\n").filter(l => l.includes(":"));
  
  for (const line of lines) {
    const colonIdx = line.indexOf(":");
    if (colonIdx < 1) continue;
    const key = line.substring(0, colonIdx).trim();
    const value = line.substring(colonIdx + 1).trim();
    if (key && value) {
      facts.push({ key, value });
    }
  }
  return facts;
}

// Generate a brief conversation summary
export async function summarizeConversation(chatFn, recentMessages) {
  if (recentMessages.length < 4) return "";
  
  const summaryPrompt = "用一句话总结这段对话的核心内容（20字以内）：";
  const messages = [
    { role: "system", content: "你是一个简洁的对话总结助手。" },
    ...recentMessages.slice(-4),
    { role: "user", content: summaryPrompt }
  ];
  
  try {
    return await chatFn(messages);
  } catch (e) {
    return "";
  }
}