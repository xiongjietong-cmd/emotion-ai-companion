# API 文档

Base URL: http://localhost:3000

## 认证

所有需要认证的接口在 Header 中携带：
```
Authorization: Bearer <token>
```

## 公开接口

### 注册
```
POST /api/auth/register
Body: { "email": "user@example.com", "password": "123456" }
Response: { "ok": true, "token": "...", "user": { "id": 1, "email": "...", "role": "user" } }
```

### 登录
```
POST /api/auth/login
Body: { "email": "user@example.com", "password": "123456" }
Response: { "ok": true, "token": "...", "user": {...} }
```

### 机器人公开信息
```
GET /api/bots/:id/public
Response: { "ok": true, "name": "...", "personality": {...} }
```

### 聊天
```
POST /api/chat/:botId
Body: { "text": "你好" }
Response: { "ok": true, "reply": "...", "userEmotion": "...", "aiEmotion": "..." }
```

### 微信 Webhook
```
POST /api/webhook/:botId
Body: { "text": "消息", "senderId": "wx-user-id" }
Response: { "ok": true, "text": "回复内容" }
```

### 健康检查
```
GET /api/health
Response: { "ok": true, "time": "2026-06-17T..." }
```

## 需认证接口

### 当前用户
```
GET /api/auth/me
Header: Authorization: Bearer <token>
Response: { "ok": true, "user": {...} }
```

### 我的机器人列表
```
GET /api/bots
Response: { "ok": true, "bots": [...] }
```

### 创建机器人
```
POST /api/bots
Body: { "name": "小暖", "personality": {...} }
Response: { "ok": true, "botId": 1 }
```

### 修改机器人
```
PUT /api/bots/:id
Body: { "name": "新名字", "personality": {...} }
Response: { "ok": true }
```

### 删除机器人
```
DELETE /api/bots/:id
Response: { "ok": true }
```

### 聊天历史
```
GET /api/bots/:id/history
Response: { "ok": true, "messages": [...] }
```

### 绑定微信
```
POST /api/bots/:id/wechat-bind
Body: { "token": "微信token", "baseUrl": "...", "wxUserId": "..." }
Response: { "ok": true }
```

### 系统设置
```
GET /api/settings
POST /api/settings
Body: { "apiKey": "sk-..." }
```

## 管理员接口

### 统计面板
```
GET /api/admin/stats
Header: Authorization: Bearer <admin-token>
Response: { "ok": true, "stats": {...}, "users": [...], "bots": [...] }
```

## 错误码

| 状态码 | 含义 |
|--------|------|
| 400 | 请求参数错误 |
| 401 | 未登录或 token 过期 |
| 403 | 权限不足 |
| 404 | 资源不存在 |
| 409 | 冲突 (如邮箱已注册) |
| 429 | 请求太频繁 |
| 500 | 服务器错误 |
