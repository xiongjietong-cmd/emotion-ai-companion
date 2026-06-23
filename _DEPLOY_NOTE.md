# 部署速查

## 服务器

- **IP**: 134.175.8.123
- **SSH**: `ssh ubuntu@134.175.8.123`（已配密钥 `~/.ssh/id_rsa_deploy`）
- **密码**: 520TXJ...
- **系统**: Ubuntu 5.15, Node v20, Python 3.10

## 项目地址

- **GitHub**: https://github.com/xiongjietong-cmd/emotion-ai-companion
- **服务器路径**: `~/emotion-ai-companion`

## API Key

```
sk-dd131489fc7c4904881765f5e4ea5d6d
```

已写入数据库 `data/emotion-saas.db` → `settings` 表 → `deepseek_api_key`

## 部署步骤

```bash
# 1. SSH 登录
ssh ubuntu@134.175.8.123
cd ~/emotion-ai-companion

# 2. 拉取最新代码
git pull

# 3. 安装依赖
npm install
pip3 install -r companion_core/requirements.txt

# 4. 重启所有服务
pkill -f "node daemon.js"
pkill -f uvicorn
sleep 2
nohup node daemon.js > daemon.log 2>&1 &
bash ~/start-companion.sh > companion-core.log 2>&1 &

# 5. 确认启动
ps aux | grep -E "daemon|uvicorn" | grep -v grep
```

## 服务与端口

| 服务 | 端口 | 启动方式 |
|------|------|----------|
| SaaS 主站 | 3000 | daemon.js 自动 |
| 扫码服务 | 3002 | daemon.js 自动 |
| 微信桥接 | — | daemon.js 自动 |
| AI 引擎 | 3105 | `~/start-companion.sh` |

## 腾讯云安全组（需放行的端口）

| 端口 | 用途 |
|------|------|
| 22 | SSH |
| 3000 | 主站 |
| 3002 | 扫码 |

## 常用命令

```bash
# 查看日志
tail -f ~/emotion-ai-companion/daemon.log

# 重启发消息服务
pkill -f "node daemon.js" && sleep 2 && cd ~/emotion-ai-companion && nohup node daemon.js > daemon.log 2>&1 &

# 重启 AI 引擎
pkill -f uvicorn && sleep 1 && bash ~/start-companion.sh > ~/emotion-ai-companion/companion-core.log 2>&1 &

# 健康检查
curl http://localhost:3000/api/health
curl -s http://localhost:3105/docs | head -c 50

# 删除守护
ps aux | grep node
```
