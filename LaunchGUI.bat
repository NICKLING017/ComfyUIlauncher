@echo off
setlocal EnableExtensions

set "SCRIPT_DIR=%~dp0"
set "GUI=%SCRIPT_DIR%gui_launcher.py"

if not exist "%GUI%" (
  echo [ERROR] 未找到 GUI 启动器: "%GUI%"
  pause
  exit /b 1
)

where python >nul 2>&1
if errorlevel 1 (
  echo [ERROR] 未找到 Python，请先安装 Python 并配置到 PATH。
  pause
  exit /b 1
)

python "%GUI%"
exit /b %ERRORLEVEL%