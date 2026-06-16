@echo off
echo ========================================
echo   Emotion AI — 一键启动
echo ========================================
echo.
cd /d "%~dp0"

echo [1/3] 检查依赖...
if not exist "node_modules" (
    echo 正在安装依赖...
    call npm install
)

echo [2/3] 检查环境变量...
if not exist ".env" (
    echo 创建 .env 文件...
    echo DEEPSEEK_API_KEY=your-key-here > .env
    echo 请编辑 .env 填入你的 DeepSeek API Key
)

echo [3/3] 启动服务...
start "EmotionAI-SaaS" cmd /c "title SaaS ^& node server/index.js"
start "EmotionAI-QR" cmd /c "title QR ^& node qr-server.js"  
start "EmotionAI-Bridge" cmd /c "title Bridge ^& node multi-wechat-bridge.js"

echo.
echo 服务已启动！
echo   主页面: http://localhost:3000
echo   管理面板: http://localhost:3000/admin.html
echo.
echo 关闭此窗口不会停止服务。
echo 要停止所有服务，请关闭三个服务窗口。
pause
