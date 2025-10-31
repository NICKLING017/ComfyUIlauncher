import os
import sys
import subprocess
import threading
import signal
import tkinter as tk
from tkinter import ttk, filedialog, messagebox


DEFAULT_CFG = {
    "COMFYUI_DIR": r"C:\ComFyUI\ComfyUI",
    "VENV_DIR": "",
    "AUTO_ARGS": "--auto-launch",
    "UPDATE_CHECK": "1",
    "ICON_PATH": "",
}


def read_config(cfg_path: str):
    cfg = DEFAULT_CFG.copy()
    if os.path.isfile(cfg_path):
        try:
            with open(cfg_path, "r", encoding="utf-8", errors="ignore") as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith("#"):
                        continue
                    if "=" in line:
                        k, v = line.split("=", 1)
                        cfg[k.strip()] = v.strip()
        except Exception:
            pass
    return cfg


def write_config(cfg_path: str, cfg: dict):
    lines = ["# ComfyUI Launcher Config"]
    for k in ["COMFYUI_DIR", "VENV_DIR", "AUTO_ARGS", "UPDATE_CHECK", "ICON_PATH"]:
        lines.append(f"{k}={cfg.get(k, DEFAULT_CFG.get(k, ''))}")
    with open(cfg_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")


def find_python(comfy_dir: str, venv_dir: str = ""):
    candidates = []
    if venv_dir:
        candidates.append(os.path.join(comfy_dir, venv_dir, "Scripts", "python.exe"))
    candidates.extend([
        os.path.join(comfy_dir, "venv", "Scripts", "python.exe"),
        os.path.join(comfy_dir, ".venv", "Scripts", "python.exe"),
        os.path.join(comfy_dir, "3.11.venv", "Scripts", "python.exe"),
        os.path.join(comfy_dir, "3.12.venv", "Scripts", "python.exe"),
        os.path.join(comfy_dir, "venv311", "Scripts", "python.exe"),
        os.path.join(comfy_dir, "venv312", "Scripts", "python.exe"),
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


def git_update_if_needed(comfy_dir: str, log=lambda s: None):
    try:
        subprocess.run(["git", "rev-parse", "--is-inside-work-tree"], cwd=comfy_dir,
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
    except Exception:
        return
    try:
        log("[INFO] 检查更新…")
        subprocess.run(["git", "fetch"], cwd=comfy_dir, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        local = subprocess.check_output(["git", "rev-parse", "@"], cwd=comfy_dir).decode().strip()
        try:
            remote = subprocess.check_output(["git", "rev-parse", "@{u}"], cwd=comfy_dir).decode().strip()
        except Exception:
            remote = local
        if local != remote:
            log("[INFO] 发现更新，执行拉取…")
            subprocess.run(["git", "--no-pager", "pull"], cwd=comfy_dir)
        else:
            log("[INFO] 已是最新。")
    except Exception as e:
        log(f"[WARN] 更新检查失败: {e}")


def scan_venvs(comfy_dir: str):
    venv_names = ["venv", ".venv", "3.11.venv", "3.12.venv", "venv311", "venv312"]
    found = []
    for name in venv_names:
        py = os.path.join(comfy_dir, name, "Scripts", "python.exe")
        if os.path.isfile(py):
            found.append(name)
    return found


class LauncherApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("ComfyUI 可视化启动器")
        self.geometry("980x600")
        self.minsize(860, 520)
        self.attributes("-alpha", 0.0)  # 用于淡入动画

        # 兼容打包后的可执行文件路径
        if getattr(sys, "frozen", False):
            self.script_dir = os.path.abspath(os.path.dirname(sys.executable))
        else:
            self.script_dir = os.path.abspath(os.path.dirname(__file__))
        self.cfg_path = os.path.join(self.script_dir, "launcher_config.ini")
        self.cfg = read_config(self.cfg_path)
        self.proc = None
        self.stdout_thread = None
        self.stderr_thread = None
        self.running = False
        self.log_buffer = []  # (level, text)
        self.auto_scroll = tk.BooleanVar(value=True)
        self.filter_info = tk.BooleanVar(value=True)
        self.filter_warn = tk.BooleanVar(value=True)
        self.filter_error = tk.BooleanVar(value=True)

        # 图标
        icon_path = self.cfg.get("ICON_PATH", "").strip()
        if not icon_path:
            candidate = os.path.join(self.cfg.get("COMFYUI_DIR", DEFAULT_CFG["COMFYUI_DIR"]), "comfyui.ico")
            if os.path.isfile(candidate):
                icon_path = candidate
        try:
            if icon_path and os.path.isfile(icon_path):
                self.iconbitmap(icon_path)
        except Exception:
            pass

        # 主题样式
        self.style = ttk.Style()
        try:
            self.style.theme_use("clam")
        except Exception:
            pass
        base_font = ("Microsoft YaHei UI", 10)
        mono_font = ("Consolas", 10)
        self.style.configure("TLabel", font=base_font)
        self.style.configure("TButton", font=base_font)
        self.style.configure("TEntry", font=mono_font)
        self.style.configure("TCombobox", font=base_font)
        # 悬停效果
        try:
            self.style.map("TButton", background=[("active", "#e6f0ff")])
        except Exception:
            pass

        self._build_ui()
        self._load_initial_values()
        self._fade_in()

    def _build_ui(self):
        self.columnconfigure(0, weight=1)
        self.rowconfigure(1, weight=1)

        # 顶部操作栏
        topbar = ttk.Frame(self, padding=(16, 12))
        topbar.grid(row=0, column=0, sticky="ew")
        for i in range(6):
            topbar.columnconfigure(i, weight=1)

        self.btn_start = ttk.Button(topbar, text="启动 ComfyUI", command=self.on_launch)
        self.btn_start.grid(row=0, column=0, sticky="w")
        self.btn_stop = ttk.Button(topbar, text="停止", command=self.on_stop, state="disabled")
        self.btn_stop.grid(row=0, column=1, sticky="w")

        # 状态指示器
        self.var_status = tk.StringVar(value="已停止")
        status_wrap = ttk.Frame(topbar)
        status_wrap.grid(row=0, column=2, sticky="w")
        self.status_dot = tk.Canvas(status_wrap, width=12, height=12, highlightthickness=0)
        self.status_dot.grid(row=0, column=0, padx=(0, 6))
        self.lbl_status = ttk.Label(status_wrap, textvariable=self.var_status)
        self.lbl_status.grid(row=0, column=1, sticky="w")
        self._update_status_indicator(False)

        # 右侧进度条
        self.progress = ttk.Progressbar(topbar, mode="indeterminate")
        self.progress.grid(row=0, column=5, sticky="e")

        # 主体区域：左右分栏
        body = ttk.Panedwindow(self, orient="horizontal")
        body.grid(row=1, column=0, sticky="nsew")

        # 左侧配置区
        left = ttk.Frame(body, padding=16)
        for i in range(4):
            left.columnconfigure(i, weight=1)
        body.add(left, weight=1)

        ttk.Label(left, text="ComfyUI 目录").grid(row=0, column=0, sticky="w")
        self.var_dir = tk.StringVar()
        self.entry_dir = ttk.Entry(left, textvariable=self.var_dir)
        self.entry_dir.grid(row=1, column=0, columnspan=3, sticky="ew", pady=(4, 8))
        ttk.Button(left, text="浏览…", command=self.on_browse_dir).grid(row=1, column=3, sticky="e")

        ttk.Label(left, text="Python 环境/版本").grid(row=2, column=0, sticky="w")
        self.var_venv = tk.StringVar()
        self.combo_venv = ttk.Combobox(left, textvariable=self.var_venv, state="readonly")
        self.combo_venv.grid(row=3, column=0, columnspan=2, sticky="ew", pady=(4, 8))
        ttk.Button(left, text="刷新环境", command=self.on_refresh_venv).grid(row=3, column=2, sticky="ew")
        ttk.Button(left, text="打开目录", command=self.on_open_dir).grid(row=3, column=3, sticky="e")

        ttk.Label(left, text="启动参数 (AUTO_ARGS)").grid(row=4, column=0, sticky="w")
        self.var_args = tk.StringVar()
        self.entry_args = ttk.Entry(left, textvariable=self.var_args)
        self.entry_args.grid(row=5, column=0, columnspan=3, sticky="ew", pady=(4, 8))
        self.var_update = tk.BooleanVar(value=True)
        ttk.Checkbutton(left, text="启动前检查并拉取更新", variable=self.var_update).grid(row=5, column=3, sticky="e")

        btn_frame = ttk.Frame(left)
        btn_frame.grid(row=6, column=0, columnspan=4, sticky="ew", pady=(12, 0))
        for i in range(4):
            btn_frame.columnconfigure(i, weight=1)
        ttk.Button(btn_frame, text="保存配置", command=self.on_save).grid(row=0, column=0, sticky="ew")
        ttk.Button(btn_frame, text="导入配置", command=self.on_import).grid(row=0, column=1, sticky="ew")
        ttk.Button(btn_frame, text="导出配置", command=self.on_export).grid(row=0, column=2, sticky="ew")
        ttk.Button(btn_frame, text="清空日志", command=self.on_log_clear).grid(row=0, column=3, sticky="ew")

        # 右侧日志区
        right = ttk.Frame(body, padding=(8, 16))
        right.columnconfigure(0, weight=1)
        right.rowconfigure(2, weight=1)
        body.add(right, weight=2)

        # 日志过滤与搜索
        filt = ttk.Frame(right)
        filt.grid(row=0, column=0, sticky="ew")
        filt.columnconfigure(5, weight=1)
        ttk.Checkbutton(filt, text="INFO", variable=self.filter_info, command=self.on_filter_changed).grid(row=0, column=0, sticky="w")
        ttk.Checkbutton(filt, text="WARN", variable=self.filter_warn, command=self.on_filter_changed).grid(row=0, column=1, sticky="w")
        ttk.Checkbutton(filt, text="ERROR", variable=self.filter_error, command=self.on_filter_changed).grid(row=0, column=2, sticky="w")
        ttk.Checkbutton(filt, text="自动滚动", variable=self.auto_scroll).grid(row=0, column=3, sticky="w")
        self.var_search = tk.StringVar()
        ttk.Entry(filt, textvariable=self.var_search).grid(row=0, column=4, sticky="ew", padx=(6, 6))
        ttk.Button(filt, text="搜索", command=self.on_search).grid(row=0, column=5, sticky="e")

        # 日志文本
        log_wrap = ttk.Frame(right)
        log_wrap.grid(row=2, column=0, sticky="nsew")
        log_wrap.columnconfigure(0, weight=1)
        log_wrap.rowconfigure(0, weight=1)
        self.log_text = tk.Text(log_wrap, wrap="none", undo=False, height=20)
        self.log_text.grid(row=0, column=0, sticky="nsew")
        yscroll = ttk.Scrollbar(log_wrap, orient="vertical", command=self.log_text.yview)
        yscroll.grid(row=0, column=1, sticky="ns")
        self.log_text.configure(yscrollcommand=yscroll.set, font=("Consolas", 10))
        # 颜色标签
        self.log_text.tag_configure("INFO", foreground="#007a1f")
        self.log_text.tag_configure("WARN", foreground="#b36b00")
        self.log_text.tag_configure("ERROR", foreground="#b30000")
        self.log_text.tag_configure("HILIGHT", background="#fff59d")

    def _load_initial_values(self):
        self.var_dir.set(self.cfg.get("COMFYUI_DIR", DEFAULT_CFG["COMFYUI_DIR"]))
        self.var_args.set(self.cfg.get("AUTO_ARGS", DEFAULT_CFG["AUTO_ARGS"]))
        self.var_update.set(str(self.cfg.get("UPDATE_CHECK", "1")).strip() == "1")
        # 填充 venv 列表
        self._populate_venvs()
        venv_dir = self.cfg.get("VENV_DIR", "").strip()
        if venv_dir:
            self.var_venv.set(venv_dir)
        else:
            self.var_venv.set("系统 Python")

    def _populate_venvs(self):
        comfy_dir = self.var_dir.get().strip()
        venvs = scan_venvs(comfy_dir)
        values = ["系统 Python"] + venvs
        self.combo_venv["values"] = values
        # 如果当前选择不在列表中，重置为系统 Python
        if self.var_venv.get() not in values:
            self.var_venv.set("系统 Python")

    def _fade_in(self):
        def anim():
            alpha = 0.0
            while alpha < 1.0:
                alpha = min(1.0, alpha + 0.05)
                try:
                    self.attributes("-alpha", alpha)
                except Exception:
                    break
                self.update_idletasks()
                self.after(15)
        self.after(50, anim)

    def _update_status_indicator(self, running: bool):
        self.status_dot.delete("all")
        color = "#12b76a" if running else "#667085"
        self.status_dot.create_oval(2, 2, 10, 10, fill=color, outline=color)
        self.var_status.set("运行中" if running else "已停止")
        self.btn_stop.configure(state="normal" if running else "disabled")
        self.btn_start.configure(state="disabled" if running else "normal")

    # 事件处理
    def on_browse_dir(self):
        path = filedialog.askdirectory(initialdir=self.var_dir.get() or os.getcwd(), title="选择 ComfyUI 目录")
        if path:
            self.var_dir.set(path)
            self._populate_venvs()

    def on_refresh_venv(self):
        self._populate_venvs()

    def on_open_dir(self):
        d = self.var_dir.get().strip()
        if os.path.isdir(d):
            try:
                os.startfile(d)
            except Exception:
                messagebox.showinfo("提示", f"请手动打开目录: {d}")
        else:
            messagebox.showwarning("目录不存在", d or "未设置目录")

    def on_save(self):
        cfg = {
            "COMFYUI_DIR": self.var_dir.get().strip() or DEFAULT_CFG["COMFYUI_DIR"],
            "VENV_DIR": (self.var_venv.get().strip() if self.var_venv.get() != "系统 Python" else ""),
            "AUTO_ARGS": self.var_args.get().strip() or DEFAULT_CFG["AUTO_ARGS"],
            "UPDATE_CHECK": "1" if self.var_update.get() else "0",
            "ICON_PATH": self.cfg.get("ICON_PATH", ""),
        }
        write_config(self.cfg_path, cfg)
        self.cfg = cfg.copy()
        self.var_status.set("[INFO] 配置已保存")

    def on_import(self):
        file = filedialog.askopenfilename(initialdir=self.script_dir, title="导入配置",
                                          filetypes=[("INI 文件", "*.ini"), ("所有文件", "*.*")])
        if not file:
            return
        cfg = read_config(file)
        self.cfg = cfg.copy()
        self.var_dir.set(cfg.get("COMFYUI_DIR", DEFAULT_CFG["COMFYUI_DIR"]))
        self.var_args.set(cfg.get("AUTO_ARGS", DEFAULT_CFG["AUTO_ARGS"]))
        self.var_update.set(str(cfg.get("UPDATE_CHECK", "1")).strip() == "1")
        self._populate_venvs()
        venv_dir = cfg.get("VENV_DIR", "").strip()
        self.var_venv.set(venv_dir if venv_dir else "系统 Python")
        self.var_status.set("[INFO] 配置已导入")

    def on_export(self):
        file = filedialog.asksaveasfilename(initialdir=self.script_dir, title="导出配置",
                                            defaultextension=".ini",
                                            filetypes=[("INI 文件", "*.ini"), ("所有文件", "*.*")])
        if not file:
            return
        cfg = {
            "COMFYUI_DIR": self.var_dir.get().strip() or DEFAULT_CFG["COMFYUI_DIR"],
            "VENV_DIR": (self.var_venv.get().strip() if self.var_venv.get() != "系统 Python" else ""),
            "AUTO_ARGS": self.var_args.get().strip() or DEFAULT_CFG["AUTO_ARGS"],
            "UPDATE_CHECK": "1" if self.var_update.get() else "0",
            "ICON_PATH": self.cfg.get("ICON_PATH", ""),
        }
        write_config(file, cfg)
        self.var_status.set("[INFO] 配置已导出")

    # 日志操作
    def on_log_clear(self):
        self.log_buffer.clear()
        self.log_text.delete("1.0", tk.END)

    def on_filter_changed(self):
        self._rebuild_log_view()

    def on_search(self):
        pattern = self.var_search.get().strip()
        self.log_text.tag_remove("HILIGHT", "1.0", tk.END)
        if not pattern:
            return
        start = "1.0"
        while True:
            idx = self.log_text.search(pattern, start, stopindex=tk.END, nocase=True)
            if not idx:
                break
            end = f"{idx}+{len(pattern)}c"
            self.log_text.tag_add("HILIGHT", idx, end)
            start = end

    def _append_log(self, level: str, text: str):
        self.log_buffer.append((level, text))
        # 仅在过滤允许时插入
        allow = ((level == "INFO" and self.filter_info.get()) or
                 (level == "WARN" and self.filter_warn.get()) or
                 (level == "ERROR" and self.filter_error.get()))
        if allow:
            self.log_text.insert(tk.END, text + "\n", (level,))
            if self.auto_scroll.get():
                self.log_text.see(tk.END)

    def _rebuild_log_view(self):
        self.log_text.delete("1.0", tk.END)
        for level, text in self.log_buffer:
            allow = ((level == "INFO" and self.filter_info.get()) or
                     (level == "WARN" and self.filter_warn.get()) or
                     (level == "ERROR" and self.filter_error.get()))
            if allow:
                self.log_text.insert(tk.END, text + "\n", (level,))
        if self.auto_scroll.get():
            self.log_text.see(tk.END)

    def _set_busy(self, busy: bool):
        for w in (self.entry_dir, self.combo_venv, self.entry_args):
            w.configure(state="disabled" if busy else "normal")
        self.progress.configure(mode="indeterminate" if busy else "determinate")
        if busy:
            self.progress.start(12)
        else:
            self.progress.stop()

    def on_launch(self):
        comfy_dir = self.var_dir.get().strip()
        venv_sel = self.var_venv.get().strip()
        venv_dir = "" if venv_sel == "系统 Python" else venv_sel
        auto_args = self.var_args.get().strip() or "--auto-launch"
        update_check = self.var_update.get()

        if not os.path.isdir(comfy_dir):
            messagebox.showerror("错误", f"ComfyUI 目录不存在: {comfy_dir}")
            return
        main_py = os.path.join(comfy_dir, "main.py")
        if not os.path.isfile(main_py):
            messagebox.showerror("错误", f"未找到 main.py: {main_py}")
            return

        py = find_python(comfy_dir, venv_dir)
        if not py:
            messagebox.showerror("错误", "未找到 Python 解释器。请安装或创建 venv。")
            return

        if self.running:
            messagebox.showinfo("提示", "已在运行中，请先停止后再启动。")
            return

        self.var_status.set("[INFO] 正在启动…")
        self._set_busy(True)

        def log(msg):
            self._append_log("INFO", msg)
            self.var_status.set(msg)
            self.update_idletasks()

        def worker():
            try:
                if update_check:
                    git_update_if_needed(comfy_dir, log)
                # 使用 -u 强制禁用缓冲，便于日志实时显示
                cmd = [py, "-u", main_py] + auto_args.split()
                env = os.environ.copy()
                env["PYTHONUNBUFFERED"] = "1"
                self.proc = subprocess.Popen(
                    cmd,
                    cwd=comfy_dir,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    bufsize=1,
                    creationflags=(subprocess.CREATE_NEW_PROCESS_GROUP if hasattr(subprocess, "CREATE_NEW_PROCESS_GROUP") else 0),
                    env=env,
                )
                self.running = True
                self._update_status_indicator(True)
                log(f"[INFO] 已启动: {os.path.basename(py)} {os.path.basename(main_py)}")
                # 启动日志读取线程
                self.stdout_thread = threading.Thread(target=self._read_stream, args=(self.proc.stdout, "INFO"), daemon=True)
                self.stderr_thread = threading.Thread(target=self._read_stream, args=(self.proc.stderr, "ERROR"), daemon=True)
                self.stdout_thread.start()
                self.stderr_thread.start()
            except Exception as e:
                messagebox.showerror("启动异常", str(e))
            finally:
                self._set_busy(False)

        threading.Thread(target=worker, daemon=True).start()

    def _read_stream(self, stream, default_level: str):
        try:
            for line in iter(stream.readline, ""):
                txt = line.rstrip("\n")
                lvl = default_level
                if txt.startswith("[INFO]"):
                    lvl = "INFO"
                elif txt.startswith("[WARN]") or txt.startswith("[WARNING]"):
                    lvl = "WARN"
                elif txt.startswith("[ERROR]"):
                    lvl = "ERROR"
                self._append_log(lvl, txt)
            stream.close()
        except Exception:
            pass

    def on_stop(self):
        if not self.running or not self.proc:
            messagebox.showinfo("提示", "当前未在运行。")
            return
        if not messagebox.askyesno("确认停止", "确定要停止 ComfyUI 并结束进程吗？"):
            return

        self.var_status.set("[INFO] 正在停止…")
        self._set_busy(True)

        def stopper():
            try:
                # 优先尝试发送 CTRL_BREAK 进行相对温和的中断
                try:
                    if hasattr(signal, "CTRL_BREAK_EVENT") and hasattr(subprocess, "CREATE_NEW_PROCESS_GROUP"):
                        self.proc.send_signal(signal.CTRL_BREAK_EVENT)
                except Exception:
                    pass

                # 等待一小段时间看是否退出
                try:
                    self.proc.wait(timeout=5)
                except Exception:
                    pass

                if self.proc.poll() is None:
                    # 尝试 terminate
                    try:
                        self.proc.terminate()
                    except Exception:
                        pass
                try:
                    self.proc.wait(timeout=3)
                except Exception:
                    pass

                if self.proc.poll() is None:
                    # 强制杀死整个进程树（Windows）
                    if os.name == "nt":
                        try:
                            subprocess.run(["taskkill", "/PID", str(self.proc.pid), "/T", "/F"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                        except Exception:
                            pass
                    else:
                        try:
                            self.proc.kill()
                        except Exception:
                            pass

                self._append_log("INFO", "[INFO] 进程已停止。")
            finally:
                self.running = False
                self._update_status_indicator(False)
                self._set_busy(False)
                self.proc = None

        threading.Thread(target=stopper, daemon=True).start()


def main():
    app = LauncherApp()
    app.mainloop()


if __name__ == "__main__":
    main()