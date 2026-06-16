// wechat-login.js — 微信扫码登录，输出 token 供仪表盘绑定
// 用法: node wechat-login.js
// 屏幕会显示二维码，手机微信扫码确认后自动保存 token

const ILOGIN_URL = "https://ilinkai.weixin.qq.com/ilink/bot/ilogin";

// 生成随机 nonce
function randHex(len) {
  return Array.from({ length: len }, () => Math.floor(Math.random() * 16).toString(16)).join("");
}

async function requestQR() {
  const nonce = randHex(16);
  const body = {
    ilink_appid: "",
    nonce: nonce,
    timestamp_ms: Date.now()
  };

  const res = await fetch(ILOGIN_URL, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body)
  });

  const data = await res.json();
  if (data.ret !== 0) throw new Error("QR request failed: " + JSON.stringify(data));
  return { qrUrl: data.qr_url || data.qrcode_url, token: data.token, nonce };
}

function showQR(qrUrl) {
  // 在终端显示二维码链接
  console.log("\n==================================");
  console.log("请用微信扫描以下链接（复制到浏览器打开）：");
  console.log(qrUrl);
  console.log("==================================");
  console.log("\n或者在浏览器中打开该链接，用微信扫码\n");
}

async function pollLogin(token, nonce) {
  const checkUrl = "https://ilinkai.weixin.qq.com/ilink/bot/ichecklogin";
  const maxRetries = 60; // 最多等 2 分钟
  for (let i = 0; i < maxRetries; i++) {
    await new Promise(r => setTimeout(r, 2000));
    const res = await fetch(checkUrl, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ token, nonce })
    });
    const data = await res.json();
    if (data.ret === 0 && data.bot_token) {
      console.log("\n登录成功！");
      console.log("Token: " + data.bot_token);
      console.log("User ID: " + (data.user_id || ""));
      console.log("\n将此信息填入仪表盘即可绑定");
      return data;
    }
    if (data.ret !== 0 && data.ret !== -1) {
      console.log("登录状态: " + JSON.stringify(data));
    }
    process.stdout.write(".");
  }
  throw new Error("登录超时");
}

async function main() {
  console.log("正在请求微信登录二维码...");
  const { qrUrl, token, nonce } = await requestQR();
  
  // 生成终端二维码
  try {
    const qr = await import("qrcode");
    console.log(await qr.toString(qrUrl, { type: "terminal", small: true }));
  } catch {
    // 如果没有 qrcode 包，直接输出链接
    showQR(qrUrl);
  }
  
  const result = await pollLogin(token, nonce);
  
  // 保存到当前目录
  const output = {
    token: result.bot_token,
    baseUrl: "https://ilinkai.weixin.qq.com",
    userId: result.user_id || "",
    savedAt: new Date().toISOString()
  };
  fs.writeFileSync("wechat-credentials.json", JSON.stringify(output, null, 2));
  console.log("\n凭证已保存到 wechat-credentials.json");
  console.log("\n在仪表盘中填入以下信息：");
  console.log("Token: " + result.bot_token);
}

main().catch(e => { console.error("失败:", e.message); process.exit(1); });
