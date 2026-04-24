"""
Utilitários e funções auxiliares
"""
import os
import sys
import subprocess
from pathlib import Path

VERSION = "6.0"

# Cores ANSI
try:
    import ctypes
    ctypes.windll.kernel32.SetConsoleMode(ctypes.windll.kernel32.GetStdHandle(-11), 7)
except:
    pass

R = '\033[0;31m'
G = '\033[0;32m'
Y = '\033[1;33m'
C = '\033[0;36m'
M = '\033[0;35m'
B = '\033[0;34m'
BO = '\033[1m'
DM = '\033[2m'
NC = '\033[0m'

VIDEO_EXTS = {".mkv", ".mp4", ".avi", ".mov", ".wmv", ".m4v", ".webm"}
PASTAS_BUSCA = ["Videos", "Vídeos", "Downloads", "Desktop", "Área de Trabalho"]

def header():
    os.system("cls" if os.name == "nt" else "clear")
    print(f"""
  {C}{BO}
  ███╗   ██╗███████╗██╗  ██╗ ██████╗ ██████╗ ██████╗ ███████╗██████╗
  ████╗  ██║██╔════╝╚██╗██╔╝██╔════╝██╔═══██╗██╔══██╗██╔════╝██╔══██╗
  ██╔██╗ ██║█████╗   ╚███╔╝ ██║     ██║   ██║██║  ██║█████╗  ██████╔╝
  ██║╚██╗██║██╔══╝   ██╔██╗ ██║     ██║   ██║██║  ██║██╔══╝  ██╔══██╗
  ██║ ╚████║███████╗██╔╝ ██╗╚██████╗╚██████╔╝██████╔╝███████╗██║  ██║
  ╚═╝  ╚═══╝╚══════╝╚═╝  ╚═══╝ ╚═════╝ ╚═════╝ ╚═════╝ ╚══════╝╚═╝  ╚═╝{NC}
  {DM}v{VERSION} · HEVC · CQ Auto · 4K · Detecção IA · Telegram · Modular{NC}
""")

def detectar_gpu(config_mgr):
    """Detecta GPU e configura encoder"""
    config_mgr.use_cpu = True
    config_mgr.gpu_vendor = "CPU"
    config_mgr.encoder_gpu = "libx265"
    
    try:
        r = subprocess.run(["ffmpeg", "-hide_banner", "-encoders"],
                         capture_output=True, text=True, timeout=10)
        if 'hevc_nvenc' in r.stdout:
            try:
                r2 = subprocess.run(["nvidia-smi", "--query-gpu=name", "--format=csv,noheader"],
                                  capture_output=True, text=True, timeout=5)
                if r2.returncode == 0 and r2.stdout.strip():
                    nome = r2.stdout.strip().split('\n')[0].strip()
                    config_mgr.use_cpu = False
                    config_mgr.encoder_gpu = "hevc_nvenc"
                    config_mgr.gpu_vendor = "NVIDIA"
                    print(f"  {DM}Encoder:{NC} {G}{nome} (NVENC 🚀){NC}")
                    return
            except:
                pass
    except:
        pass
    
    print(f"  {DM}Encoder:{NC} {Y}CPU (x265){NC}")
    
    try:
        subprocess.run(["ffmpeg", "-version"], capture_output=True, timeout=5)
    except FileNotFoundError:
        print(f"\n  {R}[✗] ffmpeg não encontrado!{NC}")
        sys.exit(1)

def sep():
    print(f"  {C}{'━'*55}{NC}")

def ask(msg, default="s"):
    op = "[S/n]" if default == "s" else "[s/N]"
    r = input(f"  {BO}{msg} {op}:{NC} ").strip().lower()
    return (r in ("s", "sim", "y", "yes")) if r else (default == "s")

def bytes_to_human(b):
    for u, d in [("GiB", 1<<30), ("MiB", 1<<20), ("KiB", 1<<10)]:
        if b >= d:
            return f"{b/d:.2f} {u}"
    return f"{b} B"

def limpar_nome_pasta(nome):
    invalidos = '<>:"/\\|?*'
    for c in invalidos:
        nome = nome.replace(c, '_')
    return nome[:100]

def get_duracao(arq):
    try:
        r = subprocess.run(
            ["ffprobe", "-v", "quiet", "-show_entries", "format=duration",
             "-of", "csv=p=0", str(arq)],
            capture_output=True, text=True, timeout=30
        )
        if r.returncode == 0:
            lines = r.stdout.strip().split('\n')
            if lines and lines[0].strip():
                return int(float(lines[0]))
    except:
        pass
    return 0

def get_recursos():
    info = []
    try:
        import psutil
        cpu = psutil.cpu_percent(interval=0.1)
        ram = psutil.virtual_memory().percent
        info.append(f"CPU:{cpu:5.1f}% RAM:{ram:5.1f}%")
    except:
        pass
    
    try:
        r = subprocess.run(
            ["nvidia-smi", "--query-gpu=utilization.gpu,memory.used",
             "--format=csv,noheader,nounits"],
            capture_output=True, text=True, timeout=3
        )
        if r.returncode == 0:
            parts = r.stdout.strip().split(',')
            if len(parts) >= 2:
                info.append(f"GPU:{parts[0].strip()}% VRAM:{parts[1].strip()}MB")
    except:
        pass
    
    return ' | '.join(info) if info else ""

def encontrar_videos():
    raiz = Path(os.environ.get("USERPROFILE", str(Path.home())))
    videos = []
    vistos = set()
    
    for nome_pasta in PASTAS_BUSCA:
        pasta = raiz / nome_pasta
        if not pasta.is_dir():
            continue
        for f in _scan_pasta(pasta):
            if f not in vistos:
                vistos.add(f)
                videos.append(f)
    
    return videos

def _scan_pasta(pasta, max_depth=3):
    resultados = []
    try:
        for entry in sorted(pasta.iterdir()):
            if entry.is_file() and entry.suffix.lower() in VIDEO_EXTS:
                resultados.append(entry)
            elif entry.is_dir() and max_depth > 1:
                resultados.extend(_scan_pasta(entry, max_depth - 1))
    except PermissionError:
        pass
    return resultados

def notificar_windows(titulo, mensagem):
    try:
        script = (
            f"[Windows.UI.Notifications.ToastNotificationManager, Windows.UI.Notifications, "
            f"ContentType = WindowsRuntime] | Out-Null; "
            f"$template = [Windows.UI.Notifications.ToastNotificationManager]::"
            f"GetTemplateContent([Windows.UI.Notifications.ToastTemplateType]::ToastText02); "
            f"$template.SelectSingleNode('//text[@id=1]').InnerText = '{titulo}'; "
            f"$template.SelectSingleNode('//text[@id=2]').InnerText = '{mensagem}'; "
            f"$notif = [Windows.UI.Notifications.ToastNotification]::new($template); "
            f"[Windows.UI.Notifications.ToastNotificationManager]::"
            f"CreateToastNotifier('NexCoder').Show($notif)"
        )
        subprocess.Popen(
            ["powershell", "-NoProfile", "-WindowStyle", "Hidden", "-Command", script],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
        )
    except:
        pass