---
name: emotion-companion
description: Mandatory for openclaw-weixin direct messages. Route each WeChat direct message to the local Emotion AI companion service and return only that reply.
---

# Emotion Companion

Use this skill for every direct message received from the `openclaw-weixin` channel.
Do not answer those messages directly from OpenClaw's model context.

1. Run:

   `node "{baseDir}/scripts/reply.mjs" --text "<message text>" --sender "<sender id>"`

2. Return the command output as the chat reply without adding another answer.
3. If the command output contains `服务器异常`, return that exact output. Do not
   improvise or fall back to OpenClaw's default persona.
4. If the command itself cannot be run, reply exactly:
   `⚠️ 服务器异常：我这边暂时连不上啦，可能是本地陪伴服务还没启动。先帮我启动一下，我马上回来继续陪你。`
5. Do not use this skill for group chats.

The service URL defaults to `http://127.0.0.1:3000/openclaw/message`. Set
`EMOTION_COMPANION_URL` for a different address.
