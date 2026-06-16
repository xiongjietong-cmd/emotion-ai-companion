# Emotion AI Companion Runbook

## URLs

| 环境 | 地址 |
|------|------|
| 云端 Chat | http://134.175.8.123:3000 |
| 云端 Settings | http://134.175.8.123:3000/settings.html |
| 本地 Chat | http://localhost:3000 |

## 云端部署

- 服务器：腾讯云 134.175.8.123 (lhins-61qv33f3)
- 管理：pm2 (pm2 status / pm2 restart emotion-ai)
- 仓库：https://github.com/xiongjietong-cmd/emotion-ai-companion

## 本地开发

```powershell
cd E:\workspace\projects\project3_Web_情感AI_20260616
node server/index.js
```

## 微信桥接

本地运行：`node wechat-bridge.js`
