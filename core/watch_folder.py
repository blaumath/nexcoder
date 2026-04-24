"""
Watch Folder - Monitoramento automático de pastas
"""
import time
import shutil
import threading
from pathlib import Path
from datetime import datetime

class WatchFolder:
    def __init__(self, config_mgr):
        self.config_mgr = config_mgr
        self.pastas_monitoradas = self.config_mgr.watch_config.get('pastas', [])
        self.intervalo = self.config_mgr.get_int('watch_interval', 300)
        self.arquivos_processados = set(self.config_mgr.watch_config.get('processados', []))
        self.running = False
        self.thread = None
        self.move_original = self.config_mgr.get_bool('watch_move_original', True)
        self.backup_folder = self.config_mgr.get('watch_backup_folder', 'originais_backup')
    
    def adicionar_pasta(self, pasta):
        if pasta not in self.pastas_monitoradas:
            self.pastas_monitoradas.append(pasta)
            self._salvar()
    
    def remover_pasta(self, pasta):
        if pasta in self.pastas_monitoradas:
            self.pastas_monitoradas.remove(pasta)
            self._salvar()
    
    def limpar_processados(self):
        self.arquivos_processados.clear()
        self._salvar()
    
    def _salvar(self):
        self.config_mgr.watch_config['pastas'] = self.pastas_monitoradas
        self.config_mgr.watch_config['processados'] = list(self.arquivos_processados)[-500:]
        self.config_mgr.salvar_json(self.config_mgr.watch_file, self.config_mgr.watch_config)
    
    def iniciar(self):
        if self.running:
            return
        self.running = True
        self.thread = threading.Thread(target=self._loop, daemon=True)
        self.thread.start()
    
    def parar(self):
        self.running = False
        if self.thread:
            self.thread.join(timeout=5)
    
    def _loop(self):
        while self.running:
            try:
                # Aqui seria chamado o processamento automático
                pass
            except:
                pass
            
            for _ in range(self.intervalo // 10):
                if not self.running:
                    break
                time.sleep(10)