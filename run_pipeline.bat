@echo off
title Minecraft YouTube Shorts Pipeline CLI
cd /d "%~dp0"

echo =======================================================
echo    MINECRAFT SHORTS PIPELINE - BATCH RUNNER
echo =======================================================
echo.
python pipeline.py %*
pause
