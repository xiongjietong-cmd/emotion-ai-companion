# Emotion AI SaaS

多租户情感 AI 聊天平台 — 用户创建个性化机器人，接入微信。

## 功能

- 🤖 多租户架构：每个用户独立机器人、独立记忆
- 📱 微信接入：扫码绑定，直连微信 API
- 🎭 自定义人格：温暖度、幽默感、共情能力可调
- 💕 情绪感知：自动识别用户情绪调整回复
- 📊 管理后台：用户统计、机器人列表、消息统计

## 快速开始

```bash
npm install
npm start
```

打开 http://localhost:3000

## 服务

| 服务 | 端口 | 说明 |
|------|------|------|
| SaaS | 3000 | 主服务 |
| QR | 3002 | 扫码登录 |
| Bridge | - | 微信收发 |

## 环境变量

- `DEEPSEEK_API_KEY` - DeepSeek API 密钥
- `PORT` - 主服务端口（默认 3000）

## 技术栈

- Node.js + Express
- SQLite (better-sqlite3)
- DeepSeek API
- WeChat Bot API
