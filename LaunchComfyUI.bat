@echo off
setlocal EnableExtensions EnableDelayedExpansion

set "SCRIPT_DIR=%~dp0"
set "CFG_FILE=%SCRIPT_DIR%launcher_config.ini"

set "COMFYUI_DIR=C:\ComFyUI\ComfyUI"
set "VENV_DIR="
set "AUTO_ARGS=--auto-launch"
set "UPDATE_CHECK=1"
set "ICON_PATH="

if exist "%CFG_FILE%" (
  for /f "usebackq eol=# tokens=1,* delims==" %%A in ("%CFG_FILE%") do (
    set "key=%%~A"
    set "val=%%~B"
    if /i "!key!"=="COMFYUI_DIR" set "COMFYUI_DIR=!val!"
    if /i "!key!"=="VENV_DIR" set "VENV_DIR=!val!"
    if /i "!key!"=="AUTO_ARGS" set "AUTO_ARGS=!val!"
    if /i "!key!"=="UPDATE_CHECK" set "UPDATE_CHECK=!val!"
    if /i "!key!"=="ICON_PATH" set "ICON_PATH=!val!"
  )
)

if not exist "%COMFYUI_DIR%" (
  echo [ERROR] ComfyUI 目录不存在: "%COMFYUI_DIR%"
  echo [HINT] 请在 "%CFG_FILE%" 中修改 COMFYUI_DIR 或安装到默认位置。
  pause
  exit /b 1
)

rem 优先使用配置的 VENV_DIR，其次尝试常见的 venv 目录名
set "PYTHON_EXE="
if defined VENV_DIR (
  if exist "%COMFYUI_DIR%\%VENV_DIR%\Scripts\python.exe" set "PYTHON_EXE=%COMFYUI_DIR%\%VENV_DIR%\Scripts\python.exe"
)
if not defined PYTHON_EXE (
  for %%V in (venv .venv 3.11.venv 3.12.venv venv311 venv312) do (
    if exist "%COMFYUI_DIR%\%%V\Scripts\python.exe" (
      set "PYTHON_EXE=%COMFYUI_DIR%\%%V\Scripts\python.exe"
      goto :foundvenv
    )
  )
)
:foundvenv
if not defined PYTHON_EXE (
  if exist "%COMFYUI_DIR%\python.exe" set "PYTHON_EXE=%COMFYUI_DIR%\python.exe"
)
if not defined PYTHON_EXE (
  for /f "delims=" %%P in ('where python 2^>nul') do (
    set "PYTHON_EXE=%%~fP"
    goto :gotpy
  )
)
:gotpy
if not exist "%PYTHON_EXE%" (
  echo [ERROR] 未找到 Python 解释器。请确保已安装 Python 或已创建 venv。
  pause
  exit /b 1
)

if not exist "%COMFYUI_DIR%\main.py" (
  echo [ERROR] 未找到 main.py: "%COMFYUI_DIR%\main.py"
  pause
  exit /b 1
)

if "%AUTO_ARGS%"=="" set "AUTO_ARGS=--auto-launch"

echo [INFO] 目标目录: "%COMFYUI_DIR%"
echo [INFO] 使用 Python: "%PYTHON_EXE%"
echo %PYTHON_EXE% | findstr /i /c:"%COMFYUI_DIR%" >nul
if errorlevel 1 (
  echo [WARN] 当前使用的是系统 Python，建议改为 venv（可在 launcher_config.ini 设置 VENV_DIR）。
)
echo [INFO] 启动参数: %AUTO_ARGS%

if /i "%UPDATE_CHECK%"=="1" (
  pushd "%COMFYUI_DIR%"
  git rev-parse --is-inside-work-tree >nul 2>&1
  if not errorlevel 1 (
    echo [INFO] 检查更新...
    git fetch >nul 2>&1
    for /f "delims=" %%L in ('git rev-parse @') do set "LOCAL=%%L"
    for /f "delims=" %%R in ('git rev-parse @{u} 2^>nul') do set "REMOTE=%%R"
    if defined LOCAL if defined REMOTE (
      if not "!LOCAL!"=="!REMOTE!" (
        echo [INFO] 发现更新，执行拉取...
        git --no-pager pull
      ) else (
        echo [INFO] 已是最新。
      )
    )
  )
  popd
)

pushd "%COMFYUI_DIR%"
"%PYTHON_EXE%" "main.py" %AUTO_ARGS%
set "EXITCODE=%ERRORLEVEL%"
popd

if not "%EXITCODE%"=="0" (
  echo [ERROR] 启动失败，退出码: %EXITCODE%
  pause
)
exit /b %EXITCODE%