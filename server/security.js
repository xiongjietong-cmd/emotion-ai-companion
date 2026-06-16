// security.js — 安全中间件

// 简易速率限制 (内存)
const rateStore = new Map();
const RATE_WINDOW = 60000; // 1 分钟
const RATE_MAX = 60;       // 最多 60 次

export function rateLimiter(req, res, next) {
  const key = req.ip || req.socket?.remoteAddress || "unknown";
  const now = Date.now();
  let entry = rateStore.get(key);
  if (!entry || now - entry.start > RATE_WINDOW) {
    entry = { start: now, count: 1 };
    rateStore.set(key, entry);
    return next();
  }
  entry.count++;
  if (entry.count > RATE_MAX) {
    return res.status(429).json({ error: "请求太频繁，请稍后再试" });
  }
  next();
}

// 输入清理
export function sanitizeInput(text) {
  if (typeof text !== "string") return "";
  return text
    .replace(/<script[\s\S]*?<\/script>/gi, "")
    .replace(/<[^>]*>/g, "")
    .replace(/&lt;/g, "<")
    .replace(/&gt;/g, ">")
    .slice(0, 2000); // 限制长度 2000 字
}

// 通用错误处理
export function errorHandler(err, req, res, next) {
  console.error(`[${new Date().toISOString()}] Error:`, err.message);
  const status = err.status || 500;
  res.status(status).json({
    error: status === 500 ? "服务器内部错误" : err.message
  });
}
