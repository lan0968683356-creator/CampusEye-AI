@echo off
setlocal
chcp 65001 >nul
cd /d "%~dp0"
title CampusEye AI - Build Windows EXE (YOLO)
echo =============================================
echo    CampusEye AI v1.1 - Windows EXE Builder
echo =============================================
echo.

if not exist "launcher.py" (
  echo ERROR: launcher.py is missing. Run this file inside the MAIN project folder.
  goto :fail
)
if not exist "app.py" (
  echo ERROR: app.py is missing.
  goto :fail
)
if not exist "CampusEye-AI.ico" (
  echo ERROR: CampusEye-AI.ico is missing.
  goto :fail
)
if not exist "models\yolov8n.onnx" (
  echo ERROR: models\yolov8n.onnx is missing.
  echo Run Download_AI_Model.bat in the main project folder first.
  goto :fail
)

echo [1/3] Checking YOLO model integrity...
py -c "import hashlib, pathlib, sys; p=pathlib.Path('models/yolov8n.onnx'); actual=hashlib.file_digest(p.open('rb'), 'sha256').hexdigest(); expected='e97df4e336ab724b22b4513ff39040a08770428e54628abd31b642e7babf75e5'; print('SHA-256:',actual); sys.exit(0 if actual==expected else 1)"
if errorlevel 1 (
  echo ERROR: Model integrity check failed. Re-download the verified model.
  goto :fail
)

echo.
echo [2/3] Building EXE with web resources and YOLO model...
echo Close all running CampusEye AI instances before continuing.
py -m PyInstaller ^
  --noconfirm ^
  --clean ^
  --onedir ^
  --windowed ^
  --name "CampusEye-AI" ^
  --icon "CampusEye-AI.ico" ^
  --add-data "templates;templates" ^
  --add-data "static;static" ^
  --add-data "models\yolov8n.onnx;models" ^
  launcher.py
if errorlevel 1 goto :fail

if not exist "dist\CampusEye-AI\CampusEye-AI.exe" (
  echo ERROR: Missing packaged EXE.
  goto :fail
)
if not exist "dist\CampusEye-AI\_internal\models\yolov8n.onnx" (
  echo ERROR: The packaged YOLO model is missing!
  goto :fail
)

echo.
echo [3/3] Success: EXE and ONNX model are included.
echo File: dist\CampusEye-AI\CampusEye-AI.exe
echo Model: dist\CampusEye-AI\_internal\models\yolov8n.onnx
echo Next: open CampusEyeAI-Setup.iss in Inno Setup and click Build ^> Compile.
echo.
pause
exit /b 0

:fail
echo.
echo BUILD FAILED. No installer should be compiled until this is fixed.
pause
exit /b 1
