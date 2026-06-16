@echo off
cd /d "%~dp0"
if not exist "_logs" mkdir "_logs"
echo [%date% %time%] starting server >> "_logs\server-runtime.log"
node server\index.js >> "_logs\server-runtime.log" 2>&1
echo [%date% %time%] server exited with code %ERRORLEVEL% >> "_logs\server-runtime.log"
