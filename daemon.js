// daemon.js — 进程守护，自动重启
// 用法: node daemon.js

import { spawn } from "child_process";
import { fileURLToPath } from "url";
import { dirname, join } from "path";

const __dirname = dirname(fileURLToPath(import.meta.url));

const services = [
  { name: "SaaS", file: "server/index.js", restartDelay: 3000 },
  { name: "QR", file: "qr-server.js", restartDelay: 2000 },
  { name: "Bridge", file: "multi-wechat-bridge.js", restartDelay: 5000 }
];

function start(service) {
  const child = spawn("node", [join(__dirname, service.file)], {
    cwd: __dirname,
    stdio: "pipe",
    env: { ...process.env }
  });

  child.stdout.on("data", (d) => process.stdout.write(`[${service.name}] ${d}`));
  child.stderr.on("data", (d) => process.stderr.write(`[${service.name}] ${d}`));

  child.on("exit", (code) => {
    const ts = new Date().toLocaleTimeString();
    console.log(`[${ts}] ${service.name} 退出 (code:${code})，${service.restartDelay/1000}s 后重启`);
    setTimeout(() => start(service), service.restartDelay);
  });

  console.log(`[${new Date().toLocaleTimeString()}] ${service.name} 已启动`);
  return child;
}

console.log("=== Emotion AI 进程守护启动 ===\n");
services.forEach(s => start(s));

// 保持进程存活

// Health monitoring
setInterval(async () => {
  try {
    const r = await fetch("http://127.0.0.1:3000/api/health");
    const d = await r.json();
    if (!d.ok) console.log("[Health] SaaS unhealthy, will restart...");
  } catch {
    console.log("[Health] SaaS unreachable");
  }
}, 30000);

process.on("SIGINT", () => {
  console.log("\n正在关闭所有服务...");
  process.exit(0);
});
