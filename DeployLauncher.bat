@echo off
setlocal EnableExtensions EnableDelayedExpansion

set "SCRIPT_DIR=%~dp0"
set "CFG_FILE=%SCRIPT_DIR%launcher_config.ini"

set "COMFYUI_DIR=C:\ComFyUI\ComfyUI"
set "ICON_PATH="

if exist "%CFG_FILE%" (
  for /f "usebackq eol=# tokens=1,* delims==" %%A in ("%CFG_FILE%") do (
    if /i "%%~A"=="COMFYUI_DIR" set "COMFYUI_DIR=%%~B"
    if /i "%%~A"=="ICON_PATH" set "ICON_PATH=%%~B"
  )
)

set "DESKTOP=%USERPROFILE%\Desktop"
if exist "%USERPROFILE%\OneDrive\Desktop" set "DESKTOP=%USERPROFILE%\OneDrive\Desktop"
set "SHORTCUT=%DESKTOP%\ComfyUI Launcher.lnk"
set "TARGET=%SCRIPT_DIR%LaunchComfyUI.bat"

if not exist "%TARGET%" (
  echo [ERROR] 未找到启动脚本: "%TARGET%"
  pause
  exit /b 1
)

if not defined ICON_PATH (
  if exist "%COMFYUI_DIR%\comfyui.ico" set "ICON_PATH=%COMFYUI_DIR%\comfyui.ico"
)
if not defined ICON_PATH set "ICON_PATH=%SystemRoot%\System32\shell32.dll, 44"

cscript //nologo "%SCRIPT_DIR%create_shortcut.vbs" "%SHORTCUT%" "%TARGET%" "%SCRIPT_DIR%" "%ICON_PATH%"

if exist "%SHORTCUT%" (
  echo [INFO] 桌面快捷方式已创建: "%SHORTCUT%"
  echo [INFO] 图标: "%ICON_PATH%"
) else (
  echo [ERROR] 快捷方式创建失败。
)

pause
exit /b 0