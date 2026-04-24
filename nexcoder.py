#!/usr/bin/env python3
"""
NexCoder v6.0 - Compressor de Vídeo Inteligente
GitHub: https://github.com/nexum/nexcoder
"""

import os
import sys
from pathlib import Path

# Adiciona diretório core ao path
sys.path.insert(0, str(Path(__file__).parent))

from core.config import ConfigManager
from core.utils import header, detectar_gpu, G, Y, C, R, BO, DM, NC
from core.telegram_bot import TelegramBot
from core.watch_folder import WatchFolder

VERSION = "6.0"

def main():
    """Função principal do NexCoder"""
    config_mgr = ConfigManager()
    
    header()
    detectar_gpu(config_mgr)
    
    # Inicializa Telegram
    telegram = TelegramBot(config_mgr)
    
    # Inicializa Watch Folder
    watch_folder = WatchFolder(config_mgr)
    
    # Mostra status
    raiz = Path(os.environ.get("USERPROFILE", str(Path.home())))
    pasta_base = raiz / config_mgr.get('pasta_saida_base', 'Downloads') / config_mgr.get('pasta_saida_nome', 'nexcoder')
    print(f"  {DM}Pasta saída: {pasta_base}{NC}")
    
    if telegram.enabled:
        print(f"  {C}[📤] Telegram configurado:{NC}")
        if telegram.chats.get('filme'):
            print(f"  {C}      🎬 Filmes: {G}OK{NC}")
        if telegram.chats.get('anime'):
            print(f"  {C}      🌸 Animes: {G}OK{NC}")
        print(f"  {C}      Modo upload: {BO}{telegram.upload_mode}{NC}")
    
    print()
    
    # Menu principal
    while True:
        print(f"  {BO}O que deseja fazer?{NC}\n")
        print(f"  {C}[1]{NC} 🎬  {BO}Comprimir para Telegram{NC}")
        print(f"  {C}[2]{NC} ℹ️   {BO}Info do vídeo{NC}")
        print(f"  {C}[3]{NC} ⚙️   {BO}Configurações{NC}")
        print(f"  {C}[4]{NC} 📊 {BO}Histórico{NC}")
        print(f"  {C}[0]{NC} Sair\n")
        
        op = input(f"  {BO}Opção: {NC}").strip().lower()
        
        if op == "1":
            from core.modes import modo_telegram
            modo_telegram(config_mgr, telegram, watch_folder)
        elif op == "2":
            from core.modes import modo_info
            modo_info()
        elif op == "3":
            from core.modes import modo_config
            modo_config(config_mgr, telegram, watch_folder)
        elif op == "4":
            from core.modes import modo_historico
            modo_historico()
        elif op == "0":
            if watch_folder.running:
                watch_folder.parar()
            print(f"\n  {G}Até mais! 👋{NC}\n")
            sys.exit(0)
        else:
            print(f"  {R}Opção inválida.{NC}")
        
        print(f"\n  {DM}{'━'*55}{NC}\n")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print(f"\n\n  {Y}Interrompido pelo usuário.{NC}")
        sys.exit(0)