# 生产部署指南

## 本地运行

```bash
npm install
node daemon.js
```

打开 http://localhost:3000

## 三个服务

| 服务 | 端口 | 文件 |
|------|------|------|
| SaaS 主服务 | 3000 | server/index.js |
| 扫码服务 | 3002 | qr-server.js |
| 微信桥接 | - | wechat-bridge.js |

守护进程 (daemon.js) 会自动启动全部三个，崩溃自动重启，每 30 秒健康检查。

## 云端部署

### Render (推荐 — 支持语音消息)

1. 打开 [Render Dashboard](https://dashboard.render.com) → New → Web Service
2. 连接仓库 `xiongjietong-cmd/emotion-ai-companion`
3. 配置:
   - **Runtime**: Node
   - **Build Command**: `npm install`
   - **Start Command**: `npm start`
4. 环境变量 (Environment):
   - `DEEPSEEK_API_KEY` = `sk-xxx` (必填)
   - `PORT` = `3000`
5. 点击 Create Web Service
6. 部署完成后获得公网 URL，例如 `https://emotion-ai-companion.onrender.com`

部署后本地 bridge 设置:
```powershell
$env:TUNNEL_URL="https://你的服务名.onrender.com"
node multi-wechat-bridge.js
```

语音消息会通过 Render 公网 URL 投递到微信。

### 腾讯云轻量服务器

```bash
# 1. SSH 登录
ssh ubuntu@你的IP

# 2. 安装 Node.js
curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -
sudo apt install -y nodejs git

# 3. 克隆代码
git clone https://github.com/xiongjietong-cmd/emotion-ai-companion.git
cd emotion-ai-companion

# 4. 安装依赖
npm install

# 5. 设置环境变量
echo 'DEEPSEEK_API_KEY=你的key' > .env

# 6. 启动守护进程
node daemon.js &

# 7. 防火墙
sudo ufw allow 3000
sudo ufw allow 3002
```

### 微信桥接配置

云端桥接需要微信凭证。先在服务器上扫码一次：

```bash
# 用 OpenClaw 扫码获取凭证
openclaw channels login --channel openclaw-weixin
```

然后启动桥接，会自动读取凭证。

## 管理员设置

注册后，手动在数据库设置管理员：

```bash
sqlite3 data/emotion-saas.db "UPDATE users SET role='admin' WHERE email='你的邮箱'"
```

## 环境变量

| 变量 | 必填 | 说明 |
|------|------|------|
| DEEPSEEK_API_KEY | 是 | DeepSeek API 密钥 |
| PORT | 否 | 主服务端口 (默认 3000) |
| JWT_SECRET | 否 | JWT 签名密钥 (生产环境必改) |
