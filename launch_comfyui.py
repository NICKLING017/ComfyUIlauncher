import os
import subprocess
import sys

def read_config(cfg_path):
    cfg = {
        "COMFYUI_DIR": r"C:\ComFyUI\ComfyUI",
        "VENV_DIR": "",
        "AUTO_ARGS": "--auto-launch",
        "UPDATE_CHECK": "1",
        "ICON_PATH": "",
    }
    if os.path.isfile(cfg_path):
        with open(cfg_path, "r", encoding="utf-8", errors="ignore") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                if "=" in line:
                    k, v = line.split("=", 1)
                    cfg[k.strip()] = v.strip()
    return cfg

def find_python(comfy_dir, venv_dir=""):
    candidates = []
    if venv_dir:
        candidates.append(os.path.join(comfy_dir, venv_dir, "Scripts", "python.exe"))
    candidates.extend([
        os.path.join(comfy_dir, "venv", "Scripts", "python.exe"),
        os.path.join(comfy_dir, ".venv", "Scripts", "python.exe"),
        os.path.join(comfy_dir, "3.11.venv", "Scripts", "python.exe"),
        os.path.join(comfy_dir, "3.12.venv", "Scripts", "python.exe"),
        os.path.join(comfy_dir, "3.13.venv", "Scripts", "python.exe"),
        os.path.join(comfy_dir, "venv311", "Scripts", "python.exe"),
        os.path.join(comfy_dir, "venv312", "Scripts", "python.exe"),
        os.path.join(comfy_dir, "venv313", "Scripts", "python.exe"),
        os.path.join(comfy_dir, "python.exe"),
    ])
    for c in candidates:
        if os.path.isfile(c):
            return c
    try:
        out = subprocess.check_output(["where", "python"], shell=False)
        first = out.decode(errors="ignore").splitlines()[0].strip()
        if first:
            return first
    except Exception:
        pass
    return None

def git_update_if_needed(comfy_dir):
    try:
        subprocess.run(["git", "rev-parse", "--is-inside-work-tree"], cwd=comfy_dir, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
    except Exception:
        return
    try:
        subprocess.run(["git", "fetch"], cwd=comfy_dir, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        local = subprocess.check_output(["git", "rev-parse", "@"], cwd=comfy_dir).decode().strip()
        try:
            remote = subprocess.check_output(["git", "rev-parse", "@{u}"], cwd=comfy_dir).decode().strip()
        except Exception:
            remote = local
        if local != remote:
            print("[INFO] 发现更新，执行拉取...")
            subprocess.run(["git", "--no-pager", "pull"], cwd=comfy_dir)
        else:
            print("[INFO] 已是最新。")
    except Exception as e:
        print(f"[WARN] 更新检查失败: {e}")

def main():
    script_dir = os.path.abspath(os.path.dirname(__file__))
    cfg = read_config(os.path.join(script_dir, "launcher_config.ini"))
    comfy_dir = cfg.get("COMFYUI_DIR", r"C:\ComFyUI\ComfyUI")
    venv_dir = cfg.get("VENV_DIR", "")
    auto_args = cfg.get("AUTO_ARGS", "--auto-launch")
    update_check = cfg.get("UPDATE_CHECK", "1")

    if not os.path.isdir(comfy_dir):
        print(f"[ERROR] ComfyUI 目录不存在: {comfy_dir}")
        print(f"[HINT] 请在 {os.path.join(script_dir, 'launcher_config.ini')} 中修改 COMFYUI_DIR 或安装到默认位置。")
        sys.exit(1)

    py = find_python(comfy_dir, venv_dir)
    if not py:
        print("[ERROR] 未找到 Python 解释器。请确保已安装 Python 或已创建 venv。")
        sys.exit(1)

    main_py = os.path.join(comfy_dir, "main.py")
    if not os.path.isfile(main_py):
        print(f"[ERROR] 未找到 main.py: {main_py}")
        sys.exit(1)

    if not auto_args:
        auto_args = "--auto-launch"

    print(f"[INFO] 目标目录: {comfy_dir}")
    print(f"[INFO] 使用 Python: {py}")
    if os.path.abspath(comfy_dir) not in os.path.abspath(py):
        print("[WARN] 当前使用的是系统 Python，建议改为 venv（可在 launcher_config.ini 设置 VENV_DIR）。")
    print(f"[INFO] 启动参数: {auto_args}")

    if str(update_check).strip() == "1":
        print("[INFO] 检查更新...")
        git_update_if_needed(comfy_dir)

    cmd = [py, main_py] + auto_args.split()
    try:
        proc = subprocess.Popen(cmd, cwd=comfy_dir)
        proc.wait()
        code = proc.returncode or 0
        if code != 0:
            print(f"[ERROR] 启动失败，退出码: {code}")
            sys.exit(code)
    except Exception as e:
        print(f"[ERROR] 启动异常: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()