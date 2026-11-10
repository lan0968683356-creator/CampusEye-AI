@echo off
chcp 65001 >nul
cd /d "%~dp0"
py download_ai_model.py
if errorlevel 1 (
 echo.
 echo Download failed. See the message above.
) else (
 echo.
 echo Model installed successfully. Restart CampusEye AI to enable YOLOv8n.
)
pause
