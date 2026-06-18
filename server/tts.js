import { spawn } from "child_process";
import { Readable } from "stream";
import fs from "fs";
import path from "path";
import { fileURLToPath } from "url";
import { getTtsStyle } from "./emotional-engine.js";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const VOICE = "zh-CN-XiaoxiaoNeural";

function buildSSML(text, emotion) {
  const style = getTtsStyle(emotion);
  // Escape XML special chars in text
  const safe = String(text)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&apos;");
  return `<speak version="1.0" xmlns="http://www.w3.org/2001/10/synthesis" xmlns:mstts="https://www.w3.org/2001/mstts" xml:lang="zh-CN"><voice name="${VOICE}"><mstts:express-as style="${style}">${safe}</mstts:express-as></voice></speak>`;
}

/**
 * Synthesize speech, return a Readable stream of MP3 audio.
 * @param {{ text: string, emotion?: string }} params
 * @returns {Promise<{stream: Readable, contentType: string}>}
 */
export async function synthesize({ text, emotion = "平静" }) {
  if (!text || !String(text).trim()) {
    throw Object.assign(new Error("Text is required"), { code: "EMPTY_TTS_TEXT" });
  }

  const ssml = buildSSML(String(text).trim(), emotion);

  // Write SSML to temp file (edge-tts reads from file for SSML)
  const tmpDir = path.join(__dirname, "..", "data", "tts");
  fs.mkdirSync(tmpDir, { recursive: true });
  const tmpFile = path.join(tmpDir, `tts_${Date.now()}_${Math.random().toString(36).slice(2, 6)}.mp3`);

  return new Promise((resolve, reject) => {
    const child = spawn("edge-tts", [
      "--voice", VOICE,
      "--text", ssml,
      "--write-media", tmpFile
    ], {
      stdio: ["pipe", "pipe", "pipe"],
      windowsHide: true
    });

    let stderr = "";
    child.stderr.on("data", (d) => { stderr += d.toString(); });

    child.on("close", (code) => {
      if (code !== 0) {
        try { fs.unlinkSync(tmpFile); } catch {}
        const err = new Error(`TTS failed: ${stderr || "exit code " + code}`);
        err.code = "TTS_ERROR";
        reject(err);
        return;
      }

      try {
        const buf = fs.readFileSync(tmpFile);
        const stream = Readable.from(buf);
        // Clean up temp file after streaming
        stream.on("end", () => { try { fs.unlinkSync(tmpFile); } catch {} });
        stream.on("error", () => { try { fs.unlinkSync(tmpFile); } catch {} });
        resolve({ stream, contentType: "audio/mpeg" });
      } catch (e) {
        try { fs.unlinkSync(tmpFile); } catch {}
        reject(e);
      }
    });

    child.on("error", (e) => {
      try { fs.unlinkSync(tmpFile); } catch {}
      const err = new Error(`TTS process failed: ${e.message}`);
      err.code = "TTS_ERROR";
      reject(err);
    });
  });
}

export { VOICE };
