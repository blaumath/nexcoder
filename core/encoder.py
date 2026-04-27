"""
Motor de encode de vídeo
"""
import os
import re
import time
import tempfile
import subprocess
from pathlib import Path
from datetime import datetime
from .utils import (bytes_to_human, get_duracao, get_recursos, 
                   limpar_nome_pasta, sep, ask, G, Y, C, R, DM, BO, NC)

def estimar_tamanho(dur, cq, config_mgr, vbitrate_k=0):
    calib = config_mgr.get_calibracao(cq)
    if calib and calib['count'] >= 3:
        avg_bitrate = calib['avg_bitrate_kbps']
        audio_k = 192
        total_k = avg_bitrate + audio_k
        return int(total_k * 1000 / 8 * dur)
    
    if vbitrate_k > 0:
        vbr = vbitrate_k
    else:
        tabela = {
            18: 6500, 19: 5200, 20: 4000, 21: 3200, 22: 2500,
            23: 2000, 24: 1600, 25: 1300, 26: 1050, 27: 850,
            28: 680, 29: 550, 30: 440, 31: 370, 32: 300,
        }
        vbr = tabela.get(cq, 800)
    
    audio_k = 192
    total_k = vbr + audio_k
    return int(total_k * 1000 / 8 * dur)

def cq_automatico(arq, tipo_conteudo, limite_tg):
    GB = 1024 ** 3
    sz = Path(arq).stat().st_size
    vbr_k = 0
    altura = 1080
    
    try:
        r = subprocess.run(
            ['ffprobe', '-v', 'quiet', '-select_streams', 'v:0',
             '-show_entries', 'stream=bit_rate,height',
             '-of', 'csv=p=0', str(arq)],
            capture_output=True, text=True, timeout=15
        )
        linha = r.stdout.strip().split('\n')[0].strip()
        partes = [p.strip() for p in linha.split(',') if p.strip() and p.strip() != 'N/A']
        for p in partes:
            try:
                v = int(p)
                if 200 <= v <= 5000:
                    altura = v
                elif v > 100000:
                    vbr_k = v // 1000
            except:
                pass
    except:
        pass

    if vbr_k == 0:
        dur = get_duracao(arq)
        if dur > 0:
            vbr_k = max(int(sz * 8 / dur / 1000) - 192, 100)

    eh_4k = altura >= 2000
    is_serie = tipo_conteudo in ('serie', 'anime')

    if sz < 1 * GB:
        return 20, f"arquivo pequeno ({bytes_to_human(sz)}) → qualidade máxima"

    if eh_4k:
        if vbr_k >= 20000:
            cq, desc = 22, f"4K premium ({vbr_k}kbps)"
        elif vbr_k >= 12000:
            cq, desc = 24, f"4K alta ({vbr_k}kbps)"
        elif vbr_k >= 6000:
            cq, desc = 26, f"4K média ({vbr_k}kbps)"
        else:
            cq, desc = 28, f"4K comprimido ({vbr_k}kbps)"
    else:
        if vbr_k >= 8000:
            cq, desc = 20, f"fonte premium ({vbr_k}kbps)"
        elif vbr_k >= 5000:
            cq, desc = 22, f"fonte alta ({vbr_k}kbps)"
        elif vbr_k >= 3000:
            cq, desc = 24, f"fonte média-alta ({vbr_k}kbps)"
        elif vbr_k >= 1500:
            cq, desc = 26, f"fonte média ({vbr_k}kbps)"
        else:
            cq, desc = 28, f"fonte comprimida ({vbr_k}kbps)"

    if is_serie:
        if cq > 22:
            cq -= 1
            desc += " [+1 série]"
        if sz >= limite_tg * 0.8:
            cq = min(cq + 2, 30)
            desc += " [modo Telegram]"

    res_str = f"4K ({altura}p)" if eh_4k else f"{altura}p"
    return cq, f"[{res_str}] {desc}"

def pasta_saida(arq, config_mgr, tipo_conteudo='filme', info_conteudo=None):
    raiz = Path(os.environ.get("USERPROFILE", str(Path.home())))
    pasta_base_name = config_mgr.get('pasta_saida_base', 'Downloads')
    pasta_saida_nome = config_mgr.get('pasta_saida_nome', 'nexcoder')
    
    pasta_base = raiz / pasta_base_name / pasta_saida_nome
    
    if tipo_conteudo == 'serie' and info_conteudo:
        nome_serie, temporada, _ = info_conteudo
        out = pasta_base / limpar_nome_pasta(nome_serie) / f"Season {temporada:02d}"
    elif tipo_conteudo == 'anime' and info_conteudo:
        nome_anime, temporada, _, _ = info_conteudo
        out = pasta_base / f"🌸 {limpar_nome_pasta(nome_anime)}"
        if temporada > 1:
            out = out / f"Season {temporada:02d}"
    else:
        out = pasta_base / limpar_nome_pasta(Path(arq).stem)
    
    out.mkdir(parents=True, exist_ok=True)
    return out

def nome_arquivo_saida(arq, tipo_conteudo, info_conteudo, sufixo_modo):
    if tipo_conteudo == 'serie' and info_conteudo:
        nome_serie, temporada, episodio = info_conteudo
        return f"{limpar_nome_pasta(nome_serie)} - S{temporada:02d}E{episodio:02d}{sufixo_modo}.mp4"
    elif tipo_conteudo == 'anime' and info_conteudo:
        nome_anime, _, episodio, _ = info_conteudo
        return f"{limpar_nome_pasta(nome_anime)} - E{episodio:02d}{sufixo_modo}.mp4"
    else:
        return f"{Path(arq).stem}{sufixo_modo}.mp4"

def encode(input_file, output_file, vbitrate, log_file, config_mgr,
           sub_action="none", sub_file="", idx_sub="0",
           audio_pt_idx="", audio_total=1, cq=22,
           audio_override_idx="", idx_sub_rel="0"):
    
    dur = get_duracao(input_file)
    rate_flags = []
    if vbitrate:
        bufsize = f"{int(vbitrate.rstrip('k')) * 2}k"
        rate_flags = ["-maxrate", vbitrate, "-bufsize", bufsize]

    if audio_override_idx:
        audio_map = ["-map", f"0:{audio_override_idx}"]
    elif audio_pt_idx and int(audio_total or 1) > 1:
        audio_map = ["-map", f"0:{audio_pt_idx}"]
    else:
        audio_map = ["-map", "0:a:0"]

    map_flags = ["-map", "0:v:0"] + audio_map
    vf_flags = []
    
    def esc(p):
        return str(p).replace('\\', '/').replace(':', '\\:').replace("'", "\\'")

    if sub_action == "burn_internal":
        tmp_sub = _extrair_sub_temp(input_file, idx_sub or "0")
        if tmp_sub:
            vf_flags = ["-vf",
                f"subtitles='{esc(tmp_sub)}':"
                "force_style='FontSize=22,PrimaryColour=&H00FFFFFF,Outline=2,Shadow=1'"
            ]
        else:
            si = idx_sub_rel or "0"
            vf_flags = ["-vf",
                f"subtitles='{esc(input_file)}':si={si}:"
                "force_style='FontSize=22,PrimaryColour=&H00FFFFFF,Outline=2,Shadow=1'"
            ]
    elif sub_action == "burn_external":
        if Path(sub_file).exists():
            vf_flags = ["-vf",
                f"subtitles='{esc(sub_file)}':"
                "force_style='FontSize=22,PrimaryColour=&H00FFFFFF,Outline=2,Shadow=1'"
            ]

    use_cpu = config_mgr.use_cpu
    encoder_gpu = config_mgr.encoder_gpu
    audio_br = config_mgr.get('audio_bitrate', '192k')
    
    if not use_cpu and encoder_gpu == "hevc_nvenc":
        vid = ["-c:v", "hevc_nvenc", "-preset", "p5", "-rc", "vbr",
               "-cq", str(cq), "-b:v", "0"] + rate_flags + \
              ["-map_metadata", "0", "-movflags", "+faststart"]
    else:
        vid = ["-c:v", "libx265", "-crf", str(cq), "-preset", "slow",
               "-b:v", "0"] + rate_flags + \
              ["-map_metadata", "0", "-movflags", "+faststart"]
    
    prog = tempfile.mktemp(suffix='.txt')
    cmd = (
        ["ffmpeg", "-y", "-i", str(input_file)] +
        vid + vf_flags +
        ["-c:a", "aac", "-b:a", audio_br, "-ac", "2", "-af", "aresample=async=1000"] +
        map_flags +
        ["-progress", prog, "-stats_period", "2", str(output_file)]
    )

    with open(log_file, 'a', encoding='utf-8', errors='ignore') as lf:
        lf.write(f"CMD: {' '.join(cmd)}\n")
        proc = subprocess.Popen(cmd, stderr=lf, stdout=subprocess.DEVNULL)

    t0 = time.time()
    BAR = 30
    speeds = []

    while proc.poll() is None:
        time.sleep(1.0)
        info = {}
        try:
            for line in Path(prog).read_text(errors='ignore').splitlines():
                if '=' in line:
                    k, _, v = line.partition('=')
                    info[k.strip()] = v.strip()
        except:
            pass

        us = int(info.get('out_time_us', '0').replace('N/A', '0').strip() or '0')
        spd = info.get('speed', '-')
        fps = info.get('fps', '-')
        pct = eta_m = eta_s = 0

        if spd and spd != 'N/A' and 'x' in spd:
            try:
                speeds.append(float(spd.replace('x', '')))
                if len(speeds) > 10:
                    speeds.pop(0)
            except:
                pass

        if us > 0 and dur > 0:
            el = time.time() - t0
            pct = min(int(us // 1_000_000 * 100 / dur), 100)
            if pct > 0:
                eta = max(int(el * 100 / pct - el), 0)
                eta_m = eta // 60
                eta_s = eta % 60

        bar = '█' * int(pct * BAR / 100) + '░' * (BAR - int(pct * BAR / 100))
        sz_now = ""
        try:
            sz_now = bytes_to_human(Path(str(output_file)).stat().st_size)
        except:
            pass
        
        recursos = get_recursos()
        recursos_str = f"  [{recursos}]" if recursos else ""
        avg_speed = sum(speeds) / len(speeds) if speeds else 0
        speed_str = f"{avg_speed:.1f}x" if avg_speed > 0 else spd
        
        print(f"\r  \033[32m[{bar}]\033[0m \033[1m{pct:3d}%\033[0m  "
              f"ETA: {eta_m}min{eta_s:02d}s  {speed_str}  fps: {fps:<5}  "
              f"{sz_now}{recursos_str}",
              end='', flush=True)

    proc.wait()
    print(f"\r  \033[32m[{'█'*BAR}]\033[0m \033[1m100%\033[0m  Concluído!{' '*20}")

    try:
        os.unlink(prog)
    except:
        pass

    return proc.returncode

def _extrair_sub_temp(input_file, idx_sub_global):
    try:
        tmp = tempfile.mktemp(suffix='.srt')
        r = subprocess.run(
            ["ffmpeg", "-y", "-i", str(input_file),
             "-map", f"0:{idx_sub_global}",
             "-c:s", "srt", tmp],
            capture_output=True, timeout=30
        )
        if r.returncode == 0 and Path(tmp).exists() and Path(tmp).stat().st_size > 0:
            return tmp
    except:
        pass
    return ""

def verificar_integridade(arq):
    try:
        r = subprocess.run(
            ["ffprobe", "-v", "error", "-select_streams", "v:0",
             "-show_entries", "stream=codec_name",
             "-of", "default=noprint_wrappers=1", str(arq)],
            capture_output=True, text=True, timeout=30
        )
        return r.returncode == 0 and "codec_name" in r.stdout
    except:
        return False

def processar_arquivo(arq, saida_dir, log, config_mgr, telegram,
                      tipo_conteudo='filme', info_conteudo=None,
                      batch_total=1, batch_n=1, modo_audio_fixo=None,
                      preview=False):
    from .analyzer import decidir_modo_audio
    from .detector import sugerir_modo_audio
    
    arq = Path(arq)
    sz0 = arq.stat().st_size
    sep()
    
    print(f"  {Y}{arq.name}{NC}")
    tipo_str = {'anime': '🌸 Anime', 'serie': '📺 Série', 'filme': '🎬 Filme'}.get(tipo_conteudo, '🎬 Filme')
    print(f"  Tipo     : {C}{tipo_str}{NC}")
    print(f"  Original : {R}{bytes_to_human(sz0)}{NC}")
    
    dur = get_duracao(arq)
    print(f"  Duração  : {C}{dur//60}min{NC}")

    # Modo áudio
    if modo_audio_fixo is not None:
        leg = modo_audio_fixo
        sufixo = "_leg" if leg.get('audio_override_idx') else "_dub"
    else:
        # Para séries: modo automático = dublado (não pergunta)
        # Para animes: modo automático = legendado
        # Para filmes: pergunta (ou configurado)
        preferencia = sugerir_modo_audio(tipo_conteudo, config_mgr)
        
        if preferencia == 'perguntar' and tipo_conteudo in ('serie', 'anime'):
            # Força o padrão para séries/animes
            if tipo_conteudo == 'serie':
                preferencia = 'dublado'
            elif tipo_conteudo == 'anime':
                preferencia = 'legendado'
        
        leg = decidir_modo_audio(str(arq), tipo_conteudo, config_mgr)
        sufixo = "_leg" if leg.get('audio_override_idx') else "_dub"

    nome_saida = nome_arquivo_saida(arq, tipo_conteudo, info_conteudo, sufixo)
    out = saida_dir / nome_saida

    # Verifica se arquivo já existe
    if out.exists():
        if batch_total > 1:
            sz2 = out.stat().st_size
            print(f"  {G}[✓] Já convertido — pulando{NC}")
            return sz0, sz2, True, tipo_conteudo
        else:
            print(f"  {Y}[!] Já existe: {out.name}{NC}")
            if not ask("Sobrescrever?", default="n"):
                print(f"  {Y}  → Cancelado. Voltando ao menu...{NC}")
                time.sleep(1)
                return sz0, out.stat().st_size, True, tipo_conteudo  # Retorna True para não dar erro

    # CQ automático
    limite_tg = config_mgr.get_int('limite_telegram', 1945) * 1024 * 1024
    CQ, cq_motivo = cq_automatico(arq, tipo_conteudo, limite_tg)
    print(f"  {C}CQ automático: {BO}{CQ}{NC}  {DM}{cq_motivo}{NC}")

    # Bitrate limitado
    vbitrate = ""
    if sz0 >= limite_tg * 0.8:
        vkbps = max(int((limite_tg - 24000*(dur or 7200)) / (dur or 7200) / 1000), 1000)
        vbitrate = f"{vkbps}k"
        print(f"  {C}Bitrate limitado: {vkbps}kbps (modo Telegram){NC}")

    # Mostra encoder
    enc = f"{config_mgr.gpu_vendor} {config_mgr.encoder_gpu} 🚀" if not config_mgr.use_cpu else "CPU x265"
    print(f"  {DM}{config_mgr.get('audio_bitrate', '192k')} stereo | {enc}{NC}")

    # Pergunta sobre envio Telegram
    enviar_telegram = False
    if telegram.enabled:
        upload_mode = config_mgr.get('telegram_upload_mode', 'perguntar')
        
        if upload_mode == 'sempre':
            enviar_telegram = True
            nome_grupo = telegram.get_nome_grupo(tipo_conteudo)
            print(f"  {C}[📤] Upload automático para: {nome_grupo}{NC}")
        elif upload_mode == 'perguntar':
            nome_grupo = telegram.get_nome_grupo(tipo_conteudo)
            print(f"  {C}[📤] Destino: {nome_grupo}{NC}")
            enviar_telegram = ask("Enviar para o Telegram?", default="s")
        else:
            print(f"  {DM}[📤] Upload desativado (modo: nunca){NC}")
    print()

    # Inicia encode
    t0 = time.time()
    st = encode(str(arq), str(out), vbitrate, log, config_mgr,
                leg['sub_action'], leg['sub_file'],
                leg['idx_sub_pt'], leg['audio_pt_idx'], leg.get('audio_total', 1),
                cq=CQ, audio_override_idx=leg.get('audio_override_idx', ''),
                idx_sub_rel=leg.get('idx_sub_pt_rel', '0'))
    dt = int(time.time() - t0)

    if st == 0 and out.exists():
        sz2 = out.stat().st_size
        r = int((sz0 - sz2) * 100 / sz0)
        
        # Salva calibração e histórico
        config_mgr.add_calibracao(CQ, dur, sz2)
        config_mgr.add_historico({
            'data': datetime.now().isoformat(),
            'arquivo': arq.name,
            'tipo': tipo_conteudo,
            'tamanho_original': sz0,
            'tamanho_final': sz2,
            'reducao_percent': r,
            'cq_usado': CQ,
            'duracao': dur,
            'tempo_processamento': dt,
            'upload_telegram': enviar_telegram
        })
        
        print(f"  Final    : {G}{bytes_to_human(sz2)}{NC}  ({G}-{r}%{NC})")
        print(f"  Tempo    : {dt//60}min {dt%60}s")
        
        # Verifica integridade
        if verificar_integridade(out):
            print(f"  {G}✓ Arquivo íntegro{NC}")
            
            # Upload Telegram
            if enviar_telegram and telegram.enabled:
                nome_grupo = telegram.get_nome_grupo(tipo_conteudo)
                print(f"  {C}[📤] Enviando para {nome_grupo}...{NC}")
                
                stats = {
                    'tamanho_original': sz0,
                    'tamanho_final': sz2,
                    'reducao_percent': r,
                    'tempo_processamento': dt,
                    'tipo': tipo_conteudo
                }
                telegram.notificar_conclusao(str(arq), str(out), stats)
        else:
            print(f"  {R}✗ AVISO: arquivo pode estar corrompido!{NC}")
        
        print(f"  {G}✓ {out.name}{NC}")
        return sz0, sz2, True, tipo_conteudo
    else:
        print(f"  {R}✗ ERRO — verifique o log{NC}")
        return sz0, 0, False, tipo_conteudo