import os, runpy
reserve_bytes = int(os.getenv('COMFYUI_VRAM_RESERVE_BYTES','0'))
device = int(os.getenv('COMFYUI_DEVICE','0') or '0')
try:
    import torch
    if torch.cuda.is_available():
        total = torch.cuda.get_device_properties(device).total_memory
        target = max(0, total - reserve_bytes)
        fraction = 1.0 if total == 0 else max(0.0, min(1.0, target/float(total)))
        try:
            torch.cuda.set_per_process_memory_fraction(fraction, device=device)
            print(f'[INFO] VRAM fraction set to {fraction:.3f}, reserve {reserve_bytes/(1024**3):.2f} GB')
        except Exception as e:
            print('[WARN] set_per_process_memory_fraction not supported:', e)
except Exception as e:
    print('[WARN] VRAM reserve setup failed:', e)
path = os.getenv('COMFYUI_MAIN_PATH')
if not path:
    raise RuntimeError('Missing COMFYUI_MAIN_PATH')
# 确保 ComfyUI 目录在 sys.path，并切换到该目录
import sys
dirpath = os.path.dirname(path)
try:
    os.chdir(dirpath)
except Exception:
    pass
if dirpath not in sys.path:
    sys.path.insert(0, dirpath)
runpy.run_path(path, run_name='__main__')
