# 新人上手指南

## 5 分钟跑起来

```bash
git clone https://github.com/xiongjietong-cmd/emotion-ai-companion.git
cd emotion-ai-companion
npm install
echo DEEPSEEK_API_KEY=sk-your-key > .env
node daemon.js
```

打开 http://localhost:3000

## 项目结构

```
server/            # 后端
  index.js         # 主入口 + 全部 API 路由
  database.js      # SQLite 数据层 (7 表)
  auth.js          # JWT 认证
  security.js      # 安全中间件
  ai-adapter.js    # DeepSeek API 适配
  companion-service.js  # 对话逻辑 (已弃用)
  emotional-engine.js   # 系统 prompt + 情绪检测
  memory-consolidator.js # 记忆整合
client/            # 前端
  index.html       # 登录/注册页
  dashboard.html   # 用户后台
  admin.html       # 管理面板
  404.html         # 404 页面
daemon.js          # 进程守护
qr-server.js       # 微信扫码服务
multi-wechat-bridge.js  # 多账号微信桥接
```

## 核心概念

### 用户 → 机器人 → 对话

每个用户创建多个机器人，每个机器人有独立的：
- 对话历史
- 长期记忆
- 微信绑定

### 微信接入

1. 用户创建机器人
2. 点"扫码绑定"
3. qr-server 调用微信 API 生成二维码
4. 用户手机扫码
5. 凭证保存到 OpenClaw state 目录
6. multi-wechat-bridge 自动发现新账号
7. 消息通过桥接 → SaaS webhook → AI 回复

### 安全

- 密码: PBKDF2-SHA512 哈希
- 认证: JWT (7天过期)
- 速率限制: 60次/分钟
- 输入: 2000字上限 + XSS过滤
- 数据库: 参数化查询防注入

## 常用命令

```bash
node daemon.js              # 启动全部服务
git push origin master      # 推送代码
sqlite3 data/emotion-saas.db ".tables"  # 查看数据库
```
