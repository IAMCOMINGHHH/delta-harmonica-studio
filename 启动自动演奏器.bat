@echo off
chcp 65001 >nul
cd /d "%~dp0"
python desktop_player.py
if errorlevel 1 pause
