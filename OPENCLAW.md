# OpenClaw WeChat Connection

## Architecture

```text
WeChat -> OpenClaw WeChat channel -> emotion-companion skill -> this service
```

OpenClaw owns WeChat login and message delivery. This project owns the
companion personality, relationship state, memory, emotion detection, and
DeepSeek response generation.

## Service Endpoints

- Health: `GET http://127.0.0.1:3000/openclaw/health`
- Message: `POST http://127.0.0.1:3000/openclaw/message`

Example request:

```json
{
  "text": "hello",
  "senderId": "wechat-user-id"
}
```

## OpenClaw Setup

1. Use the channel setup flow provided by your installed OpenClaw version to
   install and log in to the WeChat/Weixin channel.
2. Copy `openclaw-skill` into the active OpenClaw workspace as
   `skills/emotion-companion`.
3. Restart or open a new OpenClaw session so the workspace skill is loaded.
4. Keep this service reachable only from localhost or a trusted private
   network.

Before connecting a real WeChat account, set `OPENCLAW_OWNER_ID` to your sender
ID. Requests from other contacts will receive HTTP `403` and cannot enter the
shared companion memory.
