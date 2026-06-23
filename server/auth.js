import jwt from "jsonwebtoken";
import { getUserByEmail, getUserById } from "./database.js";

const JWT_SECRET = process.env.JWT_SECRET || "emotion-saas-dev-secret-change-in-production";
const TOKEN_EXPIRY = "7d";

// 签发 token
export function signToken(user) {
  return jwt.sign({ id: user.id, role: user.role, email: user.email }, JWT_SECRET, { expiresIn: TOKEN_EXPIRY });
}

// 验证 token 中间件
export function authMiddleware(req, res, next) {
  const header = req.headers.authorization || "";
  const token = header.startsWith("Bearer ") ? header.slice(7) : header;

  if (!token) {
    return res.status(401).json({ error: "请先登录" });
  }

  try {
    const payload = jwt.verify(token, JWT_SECRET);
    const user = getUserById(payload.id);
    if (!user) {
      return res.status(401).json({ ok: false, error: "账号不存在", code: "ACCOUNT_DELETED" });
    }
    if (user.status === "blacklisted") {
      return res.status(403).json({ ok: false, error: "账号已被拉黑", code: "ACCOUNT_BLACKLISTED" });
    }
    req.user = payload;
    next();
  } catch {
    return res.status(401).json({ error: "登录已过期，请重新登录" });
  }
}

// 管理员中间件
export function adminMiddleware(req, res, next) {
  if (!req.user || req.user.role !== "admin") {
    return res.status(403).json({ error: "需要管理员权限" });
  }
  next();
}
