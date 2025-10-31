# ComfyUI 可视化启动器

一个跨平台（以 Windows 为主）的 ComfyUI 可视化启动工具，替代原有一键启动脚本。提供路径/版本选择、启动与停止、日志面板（实时/过滤/搜索/高亮）、配置导入导出、更新检查等功能，并支持打包为单文件 EXE。

## 项目结构

- `gui_launcher.py`：GUI 主程序（Tkinter/ttk）
- `launch_comfyui.py`：原一键启动 Python 脚本逻辑
- `LaunchGUI.bat`：启动 GUI 的 Windows 批处理脚本
- `LaunchComfyUI.bat`：原一键启动批处理脚本
- `DeployLauncher.bat`、`create_shortcut.vbs`：桌面快捷方式脚本
- `launcher_config.ini`：启动配置文件
- `dist/ComfyUILauncher.exe`：打包后的单文件可执行程序（仅 Windows）

## 快速开始

- 运行 GUI（推荐）：
  - 双击 `LaunchGUI.bat`，或在命令行运行：`python gui_launcher.py`
  - 如果已打包：双击 `dist/ComfyUILauncher.exe`

- 运行旧脚本（保留）：
  - 双击 `LaunchComfyUI.bat`，或在命令行运行：`python launch_comfyui.py`

## 配置说明（launcher_config.ini）

- `COMFYUI_DIR`：ComfyUI 根目录（建议绝对路径）
- `VENV_DIR`：虚拟环境目录名（相对 `COMFYUI_DIR`，如 `venv`、`.venv`、`3.11.venv`；留空表示使用系统 Python）
- `AUTO_ARGS`：启动参数（默认 `--auto-launch`）
- `UPDATE_CHECK`：`1/0`，启用或禁用启动前的 git 更新检查
- `ICON_PATH`：窗口图标（可选，`.ico` 文件路径）

GUI 的“保存配置/导入配置/导出配置”会读写该文件；打包后该文件与 EXE 位于同目录。

## Python 环境配置与自动寻找

### 目录结构要求

- 不需要将整套 Python 安装目录放入项目；推荐使用系统 Python 或项目内的虚拟环境（venv）。
- 项目内仅需虚拟环境目录，例如：
  - Windows：`<COMFYUI_DIR>/venv/Scripts/python.exe`
  - Linux/macOS：`<COMFYUI_DIR>/venv/bin/python`
- 相对路径支持：`VENV_DIR` 使用的是相对 `COMFYUI_DIR` 的目录名；`COMFYUI_DIR` 建议使用绝对路径（相对路径可能受工作目录影响）。

### 自动寻找逻辑（已实现）

1. 使用 GUI 选择或配置的 `VENV_DIR`
2. 在 `COMFYUI_DIR` 下扫描常见 venv 目录名：`venv/.venv/3.11.venv/3.12.venv/venv311/venv312`
3. 回退到系统 Python：
   - Windows：`where python`
   - Linux/macOS（建议增强）：`which python3` 或 `which python`

优先级为：选中 venv > 扫描到的第一个 venv > 系统 Python。

### 多版本识别与选择

- 建议为不同 Python 版本创建不同 venv（如 `3.11.venv`、`3.12.venv`），在 GUI 中“刷新环境”并选择对应目录名。

### 环境验证机制（建议）

在启动前可手动验证：

```powershell
python -V
python -m pip --version
python -c "import torch,fastapi,uvicorn,numpy,PIL"
```

如缺失，请根据需要安装：

```powershell
python -m pip install -r requirements.txt
# 或安装具体库，例如（按你的 CUDA/CPU 情况调整）：
python -m pip install torch torchvision --index-url https://download.pytorch.org/whl/cu121
```

## GUI 功能

- 路径选择：浏览或手动输入 `COMFYUI_DIR`
- 版本选择：扫描并选择虚拟环境目录（或“系统 Python”）
- 启动参数：编辑 `AUTO_ARGS`（默认 `--auto-launch`）
- 更新检查：勾选启用启动前 `git fetch/pull`
- 启动与停止：
  - 启动时使用 `python -u main.py`，实时日志输出到面板
  - 停止流程：`CTRL_BREAK_EVENT` → `terminate` → `taskkill /T /F`（Windows）
- 日志面板：
  - 实时滚动开关、清空日志、搜索高亮
  - 级别过滤：INFO/WARN/ERROR（颜色区分）
- 配置管理：保存/导入/导出 `launcher_config.ini`
- 状态指示：顶部状态点与文案（运行中/已停止）

## 打包为 EXE（仅 Windows）

已内置打包支持，输出位于 `dist/ComfyUILauncher.exe`。

打包命令：

```powershell
python -m PyInstaller -F -w gui_launcher.py --name ComfyUILauncher
```

- `-F` 单文件打包，`-w` 窗口模式（不弹出控制台）
- 已兼容打包后的路径：在 `gui_launcher.py` 中使用 `sys.frozen` 判断，读写配置与 EXE 同目录
- 可选优化：
  - 自定义图标：`--icon path\to\icon.ico`
  - 体积压缩：配合 UPX 使用 `--upx-dir`（需安装 UPX）

## 跨平台注意事项

- Windows：查找 `Scripts\python.exe`，系统 Python 用 `where python`
- Linux/macOS：建议扩展查找 `bin/python`，系统 Python 用 `which python3/python`
- 虚拟环境优先使用项目内 venv；系统 Python 作为兜底（可在未来加入优先级配置项以自定义）

## 故障排查

- 未找到 Python：
  - 确认已创建 venv 或系统 PATH 中有 `python`
  - Windows 可安装并勾选“添加到 PATH”，或在 GUI 选择对应 venv
- 未找到 `main.py`：
  - 检查 `COMFYUI_DIR` 是否指向 ComfyUI 根目录且包含 `main.py`
- 启动失败：
  - 查看日志面板输出，排查依赖缺失或端口占用
  - 关闭所有旧进程后重试（GUI 的“停止”会尝试终止进程树）
- 日志空白：
  - 确认使用 `-u` 无缓冲模式（已启用）
  - 检查过滤开关与搜索关键字是否影响显示

## 许可与贡献

此工具旨在提升 ComfyUI 的使用体验。如需新增跨平台支持、环境验证按钮、命令行参数覆盖配置等增强功能，欢迎提出需求，我可以继续完善实现与文档。