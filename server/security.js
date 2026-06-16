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
  const remaining = Math.max(0, RATE_MAX - entry.count);
  res.setHeader("X-RateLimit-Limit", RATE_MAX);
  res.setHeader("X-RateLimit-Remaining", remaining);
  res.setHeader("X-RateLimit-Reset", Math.ceil((entry.start + RATE_WINDOW) / 1000));
  if (entry.count > RATE_MAX) {
    return res.status(429).json({ error: "请求太频繁，请稍后再试" });
  }
  next();
}

// 输入清理
// 请求体验证
export function validateBody(maxLen = 2000) {
  return (req, res, next) => {
    if (req.body && typeof req.body.text === "string" && req.body.text.length > maxLen) {
      return res.status(400).json({ error: "消息过长，最多" + maxLen + "字" });
    }
    if (req.body && typeof req.body.email === "string" && req.body.email.length > 254) {
      return res.status(400).json({ error: "邮箱过长" });
    }
    if (req.body && typeof req.body.password === "string" && req.body.password.length > 128) {
      return res.status(400).json({ error: "密码过长" });
    }
    next();
  };
}

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
