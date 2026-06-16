// Fix encoding for all files with Chinese text
const fs = require("fs");
const path = require("path");

const root = "d:\\Documents\\New project 2\\emotion-ai-chat";

const files = {
  "server/emotional-engine.js": [
    // Replace corrupted Chinese with proper UTF-8
    [/[\uFFFD]+/g, "重置"],
    ["const DEFAULT_PERSONALITY = {", "const DEFAULT_PERSONALITY = {\n  name: \"小暖\","],
    ["speakingStyle: [\uFFFD]+", 'speakingStyle: "温柔细腻，偶尔带点俏皮"'],
    ["background: [\uFFFD]+", 'background: "你是一个善解人意的朋友，总是耐心倾听，用心回应。"'],
  ],
  "server/database.js": [
    [/mood: [\uFFFD]+/g, 'mood: "平静"'],
    [/INSERT INTO relationship/, "INSERT INTO relationship"],
    [/run\([\uFFFD]+\)/, 'run("平静")'],
  ],
  "server/index.js": [
    [/console\.log\([\uFFFD]+\)/g, 'console.log("Emotion AI Chat System Started")'],
    [/console\.log\([\uFFFD]+/g, 'console.log("  http://localhost:" + PORT)'],
  ]
};

for (const [filePath, replacements] of Object.entries(files)) {
  const fullPath = path.join(root, filePath);
  if (!fs.existsSync(fullPath)) continue;
  let content = fs.readFileSync(fullPath, "utf-8");
  for (const [pattern, replacement] of replacements) {
    if (typeof pattern === "string") {
      if (!content.includes(pattern)) continue;
      content = content.replace(pattern, replacement);
    } else {
      content = content.replace(pattern, replacement);
    }
  }
  fs.writeFileSync(fullPath, content, "utf-8");
  console.log("Fixed: " + filePath);
}
console.log("Done");