"""
Modos de operação do NexCoder
"""
import json
import subprocess
import time
from pathlib import Path
from .utils import (G, Y, C, R, BO, DM, NC, sep, ask, 
                   bytes_to_human, encontrar_videos, notificar_windows, VIDEO_EXTS)
from .detector import detectar_tipo_conteudo
from .analyzer import analisar_video
from .encoder import processar_arquivo, pasta_saida

def modo_telegram(config_mgr, telegram, watch_folder):
    """Modo principal: comprimir para Telegram"""
    print(f"\n{C}{BO}  ━━━━ 🎬 Comprimir para Telegram ━━━━{NC}")
    
    videos = encontrar_videos()
    arq = listar_e_escolher(videos)
    if arq is None:
        return
    
    arq = Path(arq)
    if not arq.is_file():
        print(f"  {R}Arquivo não encontrado.{NC}")
        return

    tipo_conteudo, info_conteudo = detectar_tipo_conteudo(arq)
    tipo_str = {'anime': '🌸 Anime', 'serie': '📺 Série', 'filme': '🎬 Filme'}.get(tipo_conteudo, '🎬 Filme')
    print(f"  {C}[🤖] Detectado: {tipo_str}{NC}")
    
    saida = pasta_saida(arq, config_mgr, tipo_conteudo, info_conteudo)
    log = str(saida / "nexcoder.log")

    try:
        sz0, sz2, sucesso, _ = processar_arquivo(
            arq, saida, log, config_mgr, telegram,
            tipo_conteudo, info_conteudo, preview=True
        )
        
        if sucesso and sz2 > 0:
            print(f"\n  {G}✓ Salvo em: {Y}{saida}{NC}\n")
            notificar_windows("NexCoder ✓ Concluído", f"{Path(arq).name} · {bytes_to_human(sz2)}")
        else:
            print(f"\n  {Y}Operação cancelada ou arquivo já existe.{NC}\n")
    except Exception as e:
        print(f"\n  {R}[✗] Erro inesperado: {e}{NC}\n")
        print(f"  {DM}Voltando ao menu principal...{NC}")
        time.sleep(2)

def modo_info():
    """Mostra informações detalhadas do vídeo"""
    print(f"\n{C}{BO}  ━━━━ ℹ️  Info do Vídeo ━━━━{NC}\n")
    videos = encontrar_videos()
    arq = listar_e_escolher(videos)
    if arq is None:
        return
    arq = Path(arq)
    if not arq.is_file():
        print(f"  {R}Arquivo não encontrado.{NC}")
        return
    
    tipo, info = detectar_tipo_conteudo(arq)
    tipo_str = {'anime': '🌸 Anime', 'serie': '📺 Série', 'filme': '🎬 Filme'}.get(tipo, '?')
    print(f"  {C}[🤖] Detectado: {tipo_str}{NC}")

    try:
        r = subprocess.run(
            ['ffprobe', '-v', 'quiet', '-print_format', 'json',
             '-show_format', '-show_streams', str(arq)],
            capture_output=True, text=True, timeout=30
        )
        data = json.loads(r.stdout)
        fmt = data.get('format', {})
    except:
        print(f"  {R}Erro ao analisar.{NC}")
        return

    dur = int(float(fmt.get('duration', 0)))
    sz = int(fmt.get('size', arq.stat().st_size))
    brate = int(int(fmt.get('bit_rate', 0)) / 1000)

    sep()
    print(f"  {BO}{arq.name}{NC}")
    print(f"  Tamanho : {bytes_to_human(sz)}")
    print(f"  Duração : {dur//3600:02d}:{(dur%3600)//60:02d}:{dur%60:02d}")
    print(f"  Bitrate : {brate} kbps")
    sep()
    print()

def modo_config(config_mgr, telegram, watch_folder):
    """Menu de configurações"""
    while True:
        print(f"\n{C}{BO}  ━━━━ ⚙️  Configurações ━━━━{NC}\n")
        print(f"  {C}[1]{NC} Bitrate áudio: {BO}{config_mgr.get('audio_bitrate', '192k')}{NC}")
        print(f"  {C}[2]{NC} Limite Telegram: {BO}{config_mgr.get('limite_telegram', '1945')} MB{NC}")
        print(f"  {C}[3]{NC} Upload: {BO}{config_mgr.get('telegram_upload_mode', 'perguntar')}{NC}")
        print(f"  {C}[4]{NC} Configurar Telegram")
        print(f"  {C}[5]{NC} Modo Anime: {BO}{config_mgr.get('modo_auto_anime', 'legendado')}{NC}")
        print(f"  {C}[6]{NC} Modo Série: {BO}{config_mgr.get('modo_auto_serie', 'dublado')}{NC}")
        print(f"  {C}[7]{NC} Modo Filme: {BO}{config_mgr.get('modo_auto_filme', 'perguntar')}{NC}")
        print(f"  {C}[0]{NC} Voltar\n")
        
        op = input(f"  {BO}Opção: {NC}").strip()
        
        if op == "1":
            novo = input("  Bitrate (ex: 192k): ").strip()
            if novo and 'k' in novo:
                config_mgr.set('audio_bitrate', novo)
                print(f"  {G}[✓] Alterado{NC}")
        
        elif op == "2":
            novo = input("  Limite MB: ").strip()
            if novo and novo.isdigit():
                config_mgr.set('limite_telegram', novo)
                print(f"  {G}[✓] Alterado{NC}")
        
        elif op == "3":
            print(f"\n  {C}Modo Upload:{NC}")
            print(f"  [1] Perguntar [2] Sempre [3] Nunca")
            m = input("  Opção: ").strip()
            modos = {'1': 'perguntar', '2': 'sempre', '3': 'nunca'}
            if m in modos:
                config_mgr.set('telegram_upload_mode', modos[m])
                telegram.atualizar_config()
                print(f"  {G}[✓] Modo: {modos[m]}{NC}")
        
        elif op == "4":
            print(f"\n  {C}Configurar Telegram:{NC}")
            token = input("  Bot Token: ").strip()
            if token:
                config_mgr.set('telegram_bot_token', token)
            chat_f = input("  Chat Filmes: ").strip()
            if chat_f:
                config_mgr.set('telegram_chat_filmes', chat_f)
            chat_a = input("  Chat Animes: ").strip()
            if chat_a:
                config_mgr.set('telegram_chat_animes', chat_a)
            telegram.atualizar_config()
            if telegram.enabled:
                telegram.enviar_mensagem("✅ NexCoder conectado!")
                print(f"  {G}[✓] Configurado!{NC}")
        
        elif op in ("5", "6", "7"):
            chaves = {'5': 'modo_auto_anime', '6': 'modo_auto_serie', '7': 'modo_auto_filme'}
            tipos = {'5': 'anime', '6': 'série', '7': 'filme'}
            print(f"  [1] Legendado [2] Dublado [3] Perguntar")
            m = input(f"  Modo {tipos[op]}: ").strip()
            modos = {'1': 'legendado', '2': 'dublado', '3': 'perguntar'}
            if m in modos:
                config_mgr.set(chaves[op], modos[m])
                print(f"  {G}[✓] Alterado{NC}")
        
        elif op == "0":
            break

def modo_historico():
    """Mostra histórico de processamentos"""
    from .config import ConfigManager
    config_mgr = ConfigManager()
    hist = config_mgr.get_historico(15)
    
    if hist:
        print(f"\n  {C}{BO}  ━━━━ 📊 Histórico ━━━━{NC}\n")
        for h in reversed(hist):
            data = h.get('data', '?')[:10]
            arq = h.get('arquivo', '?')
            red = h.get('reducao_percent', 0)
            cq = h.get('cq_usado', '?')
            tempo = h.get('tempo_processamento', 0)
            tipo = h.get('tipo', 'filme')
            emoji = {'anime': '🌸', 'serie': '📺', 'filme': '🎬'}.get(tipo, '🎬')
            upload = '📤' if h.get('upload_telegram') else ''
            print(f"  {DM}{data}{NC} | {emoji} {upload} {arq[:35]} | {G}-{red}%{NC} | CQ:{cq} | {tempo//60}min")
        print()
    else:
        print(f"\n  {Y}Nenhum histórico.{NC}\n")

def listar_e_escolher(videos):
    """Lista vídeos e permite escolher um"""
    from .utils import M, B  # Importa cores adicionais
    
    if not videos:
        print(f"  {Y}Nenhum vídeo encontrado.{NC}")
        return None

    pasta_atual = None
    mapa = {}
    idx = 0
    for f in videos:
        p = f.parent
        if p != pasta_atual:
            pasta_atual = p
            try:
                rel = p.relative_to(Path.home())
            except ValueError:
                rel = p
            print(f"\n  {DM}📁 {rel}{NC}")
        idx += 1
        sz = f.stat().st_size
        tipo, _ = detectar_tipo_conteudo(f)
        if tipo == 'anime':
            icone = f"{M}🌸{NC}"
        elif tipo == 'serie':
            icone = f"{C}📺{NC}"
        else:
            icone = f"{B}🎬{NC}"
        print(f"    {C}[{idx}]{NC} {icone} {f.name}  {DM}({R}{bytes_to_human(sz)}{DM}){NC}")
        mapa[idx] = f

    print(f"\n    {C}[0]{NC} Caminho manual\n")
    esc = input(f"  {BO}Escolha: {NC}").strip()
    
    if not esc or esc == "0":
        caminho = input("  Caminho: ").strip().strip('"')
        p = Path(caminho)
        if p.is_file():
            return p
        if p.is_dir():
            vids = [v for v in p.iterdir() if v.suffix.lower() in VIDEO_EXTS]
            if vids:
                return vids[0]
        return None

    try:
        return mapa[int(esc)]
    except:
        return None