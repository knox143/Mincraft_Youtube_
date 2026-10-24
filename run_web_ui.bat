@echo off
title Minecraft YouTube Shorts AI Studio
cd /d "%~dp0"

echo =======================================================
echo    MINECRAFT YOUTUBE SHORTS AI PIPELINE & STUDIO
echo =======================================================
echo.
echo Starting Web Dashboard on http://127.0.0.1:5000 ...
echo Press Ctrl+C in this window to stop the server.
echo.

start "" "http://127.0.0.1:5000"
python web_app.py
pause
