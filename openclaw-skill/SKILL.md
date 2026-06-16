---
name: emotion-companion
description: Route WeChat messages to Emotion AI SaaS. Pass --bot <id> to target a specific bot.
---

# Emotion Companion

For every WeChat direct message, run:

```
node "{baseDir}/scripts/reply.mjs" --text "<message>" --sender "<sender>" --bot <botId>
```

If command fails, reply: "服务器异常"

The service URL defaults to http://127.0.0.1:3000. Set SAAS_URL env var for remote servers.
