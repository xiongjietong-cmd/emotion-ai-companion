import OpenAI from "openai";

let client = null;
let currentModel = "deepseek-v4-flash";

export function initAI(apiKey, model = "deepseek-chat") {
  client = new OpenAI({
    apiKey: apiKey,
    baseURL: "https://api.deepseek.com"
  });
  currentModel = model;
}

export function isReady() {
  return client !== null;
}

export async function chat(messages, onToken) {
  if (!client) throw new Error("AI δ���ã���������������д DeepSeek API Key");

  const stream = await client.chat.completions.create({
    model: currentModel,
    messages: messages,
    stream: true,
    temperature: 0.8,
    max_tokens: 512
  });

  let fullContent = "";
  for await (const chunk of stream) {
    const content = chunk.choices[0]?.delta?.content || "";
    fullContent += content;
    if (onToken) onToken(content);
  }
  return fullContent;
}

export async function chatNonStreaming(messages) {
  if (!client) throw new Error("AI not configured");
  const response = await client.chat.completions.create({
    model: currentModel,
    messages: messages,
    stream: false,
    temperature: 0.3,
    max_tokens: 256
  });
  return response.choices[0].message.content;
}