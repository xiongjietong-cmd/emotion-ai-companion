const chatMessages = document.getElementById("chatMessages");
const inputField = document.getElementById("inputField");
const sendBtn = document.getElementById("sendBtn");
const emptyState = document.getElementById("emptyState");
const aiNameEl = document.getElementById("aiName");
const aiMoodEl = document.getElementById("aiMood");
const avatarEmoji = document.getElementById("avatarEmoji");
const clearBtn = document.getElementById("clearBtn");

let ws = null;
let isStreaming = false;
let personality = null;

// ─── Connect WebSocket ───
function connectWS() {
  ws = new WebSocket(`ws://${location.host}`);

  ws.onopen = () => console.log("WS connected");

  ws.onmessage = (event) => {
    const data = JSON.parse(event.data);

    switch (data.type) {
      case "token":
        appendStreamToken(data.text);
        break;
      case "start":
        onStreamStart(data.userEmotion);
        break;
      case "done":
        onStreamEnd(data.aiEmotion);
        break;
      case "error":
        onStreamError(data.message);
        break;
      case "reset_done":
        chatMessages.innerHTML = "";
        emptyState.style.display = "flex";
        break;
    }
  };

  ws.onclose = () => {
    console.log("WS disconnected, reconnecting...");
    setTimeout(connectWS, 2000);
  };

  ws.onerror = () => ws.close();
}

// ─── Streaming helpers ───
let currentAiBubble = null;
let currentAiMeta = null;

function onStreamStart(userEmotion) {
  isStreaming = true;
  sendBtn.disabled = true;
  inputField.disabled = true;
  emptyState.style.display = "none";

  // Typing indicator
  const typing = document.createElement("div");
  typing.className = "typing-indicator";
  typing.id = "typingIndicator";
  typing.innerHTML = "<span></span><span></span><span></span>";
  chatMessages.appendChild(typing);
  scrollToBottom();
}

function appendStreamToken(text) {
  let typing = document.getElementById("typingIndicator");
  if (typing) typing.remove();

  if (!currentAiBubble) {
    const msgDiv = document.createElement("div");
    msgDiv.className = "message assistant";
    msgDiv.id = "currentAiMessage";

    const bubble = document.createElement("div");
    bubble.className = "bubble";
    bubble.id = "currentAiBubble";
    msgDiv.appendChild(bubble);
    chatMessages.appendChild(msgDiv);
    currentAiBubble = bubble;
  }

  currentAiBubble.textContent += text;
  scrollToBottom();
}

function onStreamEnd(aiEmotion) {
  isStreaming = false;
  sendBtn.disabled = false;
  inputField.disabled = false;
  inputField.focus();

  // Add meta to current message
  const msgEl = document.getElementById("currentAiMessage");
  if (msgEl) {
    const meta = document.createElement("div");
    meta.className = "meta";
    meta.textContent = `情绪: ${getEmotionLabel(aiEmotion)}`;
    msgEl.appendChild(meta);
  }

  // Update AI mood display
  updateAiMood(aiEmotion);

  currentAiBubble = null;
  currentAiMeta = null;
}

function onStreamError(message) {
  isStreaming = false;
  sendBtn.disabled = false;
  inputField.disabled = false;

  const typing = document.getElementById("typingIndicator");
  if (typing) typing.remove();

  const msgDiv = document.createElement("div");
  msgDiv.className = "message assistant";
  const bubble = document.createElement("div");
  bubble.className = "bubble";
  bubble.style.background = "#ffe8e8";
  bubble.textContent = "⚠️ " + message;
  msgDiv.appendChild(bubble);
  chatMessages.appendChild(msgDiv);
  scrollToBottom();

  currentAiBubble = null;
}

// ─── Send message ───
function sendMessage() {
  const text = inputField.value.trim();
  if (!text || isStreaming) return;

  inputField.value = "";
  inputField.style.height = "auto";
  emptyState.style.display = "none";

  // User message
  const msgDiv = document.createElement("div");
  msgDiv.className = "message user";
  const bubble = document.createElement("div");
  bubble.className = "bubble";
  bubble.textContent = text;
  msgDiv.appendChild(bubble);
  chatMessages.appendChild(msgDiv);
  scrollToBottom();

  // Send via WS
  if (ws && ws.readyState === WebSocket.OPEN) {
    ws.send(JSON.stringify({ type: "chat", text }));
  } else {
    onStreamError("连接断开，请刷新页面重试");
  }
}

// ─── UI updates ───
function updateAiMood(mood) {
  const emojis = { "开心": "😊", "平静": "😌", "难过": "😢", "担心": "🤔", "好奇": "💡", "生气": "😤", "无聊": "😐", "感激": "🥰" };
  const emoji = emojis[mood] || "😌";
  aiMoodEl.innerHTML = `<span>${emoji}</span> <span>${mood || "平静"}</span>`;
}

function updatePersonalityUI() {
  if (personality) {
    aiNameEl.textContent = personality.name || "小暖";
    const letter = (personality.name || "暖")[0];
    avatarEmoji.textContent = letter;
  }
}

function getEmotionLabel(emotion) {
  const labels = { "开心": "😊", "难过": "😢", "生气": "😤", "担心": "😰", "无聊": "😐", "好奇": "🤔", "感激": "🥰", "平静": "😌" };
  return labels[emotion] || "😌";
}

function scrollToBottom() {
  chatMessages.scrollTop = chatMessages.scrollHeight;
}

// ─── Input handling ───
inputField.addEventListener("input", () => {
  inputField.style.height = "auto";
  inputField.style.height = Math.min(inputField.scrollHeight, 150) + "px";
  sendBtn.disabled = !inputField.value.trim() || isStreaming;
});

inputField.addEventListener("keydown", (e) => {
  if (e.key === "Enter" && !e.shiftKey) {
    e.preventDefault();
    sendMessage();
  }
});

sendBtn.addEventListener("click", sendMessage);

// ─── Clear chat ───
clearBtn.addEventListener("click", () => {
  if (!confirm("清空当前对话？")) return;
  if (ws && ws.readyState === WebSocket.OPEN) {
    ws.send(JSON.stringify({ type: "reset" }));
  }
});

// ─── Load settings ───
async function loadAIInfo() {
  try {
    const res = await fetch("/api/settings");
    const data = await res.json();
    personality = data.personality;
    updatePersonalityUI();
  } catch (e) {
    console.error("Failed to load AI info:", e);
  }
}

// ─── Load history ───
async function loadHistory() {
  try {
    const res = await fetch("/api/history");
    const data = await res.json();
    if (data.messages && data.messages.length > 0) {
      emptyState.style.display = "none";
      data.messages.forEach(msg => {
        const div = document.createElement("div");
        div.className = `message ${msg.role}`;
        const bubble = document.createElement("div");
        bubble.className = "bubble";
        bubble.textContent = msg.content;
        div.appendChild(bubble);
        chatMessages.appendChild(div);
      });
      scrollToBottom();
    }
  } catch (e) {
    console.error("Failed to load history:", e);
  }
}

// ─── Init ───
loadAIInfo();
loadHistory();
connectWS();
