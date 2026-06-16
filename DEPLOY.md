# 部署指南

## Render 免费部署

### 1. 准备
- GitHub 账号（已关联此仓库）
- Render 账号：https://render.com（用 GitHub 登录）

### 2. 创建服务
1. Render Dashboard → New → Web Service
2. 连接 GitHub 仓库 `xiongjietong-cmd/emotion-ai-companion`
3. 配置：
   - **Name**: emotion-ai-companion
   - **Runtime**: Node
   - **Build Command**: `npm install`
   - **Start Command**: `npm start`
4. 点 Create Web Service

### 3. 配置环境变量
在 Render Dashboard → Environment 添加：

| 变量 | 值 | 说明 |
|------|-----|------|
| `DEEPSEEK_API_KEY` | sk-xxx | DeepSeek API 密钥 |
| `PORT` | 3000 | 端口 |

### 4. 微信桥接（可选）
微信桥接需要微信凭证。两种方式：
- **本地运行**：PC 开机时跑 `node wechat-bridge.js`，设置 `EMOTION_URL` 指向 Render 服务
- **云端运行**：需要先在 Render 服务器上完成微信登录（目前不支持，可通过 OpenClaw 插件实现）

### 5. 访问
部署完成后访问 `https://你的服务名.onrender.com`
