# Emotion AI Companion Runbook

## Current Workspace

```text
D:\Documents\New project 2\projects\project3_Web_情感AI_20260616
```

The old E-drive workspace is no longer active.

## Start The Service

Default:

```powershell
cd "D:\Documents\New project 2\projects\project3_Web_情感AI_20260616"
node server/index.js
```

With OpenClaw sender protection:

```powershell
.\start-openclaw.ps1 -OwnerId "your-wechat-sender-id"
```

Optional custom port:

```powershell
.\start-openclaw.ps1 -Port 3104 -OwnerId "your-wechat-sender-id"
```

## URLs

- Chat UI: `http://localhost:3000`
- Settings UI: `http://localhost:3000/settings.html`
- OpenClaw health: `http://localhost:3000/openclaw/health`
- OpenClaw message endpoint: `http://localhost:3000/openclaw/message`

Keep `OPENCLAW_OWNER_ID` enabled before connecting a real WeChat account. The
current memory database is still single-user, so this prevents other contacts
from entering your companion memory.
