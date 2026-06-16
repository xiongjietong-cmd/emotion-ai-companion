# Changelog

## 2026-06-17

### Added
- 多租户 SaaS 架构 (users, bots, conversations, memories 独立)
- JWT 认证系统 (注册/登录 + 管理员角色)
- 微信扫码登录 (qr-server.js, 直连微信 API)
- 微信桥接 (wechat-bridge.js, 3-4s 延迟)
- 进程守护 (daemon.js, 崩溃自动重启)
- 安全中间件 (rate limiter, input sanitizer, error handler)
- 管理面板 (用户统计, 机器人列表, 消息图表)
- 聊天历史加载
- Bot 删除功能
- 404 页面
- API 文档 (API.md)
- 部署指南 (DEPLOY.md)

### Changed
- 登录/注册页面全面翻新
- 仪表盘 UI 重新设计
- 管理面板 UI 重新设计
- System prompt 精简 (110行→8行)
- max_tokens 降低 (2048→512)

### Fixed
- 扫码重复账号自动去重
- 桥接 DB 路径修正
- 桥接 ACCOUNT_ID 调用顺序修复
- 桥接 Bot 映射生效

### Removed
- WebSocket 依赖 (ws)
- OpenClaw Agent 消息路由 (改用直连桥接)
- 死代码清理 (multi-wechat-bridge.js, fix-encoding.js, sync-wechat.js)
