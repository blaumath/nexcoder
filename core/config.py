"""
Gerenciamento de configurações persistentes
"""
import configparser
import json
from pathlib import Path

class ConfigManager:
    def __init__(self):
        self.config_dir = Path.home() / ".nexcoder"
        self.config_file = self.config_dir / "config.ini"
        self.history_file = self.config_dir / "history.json"
        self.calibration_file = self.config_dir / "calibration.json"
        self.watch_file = self.config_dir / "watch_folders.json"
        
        # Valores padrão
        self.defaults = {
            'audio_bitrate': '192k',
            'limite_telegram': '1945',
            'pasta_saida_base': 'Downloads',
            'pasta_saida_nome': 'nexcoder',
            'workers_paralelos': '2',
            'telegram_bot_token': '',
            'telegram_chat_filmes': '',
            'telegram_chat_animes': '',
            'telegram_upload_mode': 'perguntar',
            'modo_auto_anime': 'legendado',
            'modo_auto_serie': 'dublado',
            'modo_auto_filme': 'perguntar',
            'watch_enabled': 'nao',
            'watch_interval': '300',
            'watch_move_original': 'sim',
            'watch_backup_folder': 'originais_backup',
        }
        
        self.config = self._carregar_config()
        self.historico = self._carregar_json(self.history_file, [])
        self.calibracao = self._carregar_json(self.calibration_file, {})
        self.watch_config = self._carregar_json(self.watch_file, {})
        
        # Estado runtime
        self.use_cpu = True
        self.gpu_vendor = "CPU"
        self.encoder_gpu = "libx265"
    
    def _carregar_config(self):
        config = configparser.ConfigParser()
        config['DEFAULT'] = self.defaults
        
        if self.config_file.exists():
            config.read(self.config_file)
        else:
            self.config_dir.mkdir(exist_ok=True)
            with open(self.config_file, 'w', encoding='utf-8') as f:
                config.write(f)
        
        return config
    
    def _carregar_json(self, arquivo, default=None):
        if arquivo.exists():
            try:
                with open(arquivo, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except:
                pass
        return default if default is not None else []
    
    def salvar_config(self):
        with open(self.config_file, 'w', encoding='utf-8') as f:
            self.config.write(f)
    
    def salvar_json(self, arquivo, dados):
        with open(arquivo, 'w', encoding='utf-8') as f:
            json.dump(dados, f, indent=2, ensure_ascii=False)
    
    def get(self, chave, fallback=''):
        return self.config.get('DEFAULT', chave, fallback=fallback)
    
    def set(self, chave, valor):
        self.config['DEFAULT'][chave] = str(valor)
        self.salvar_config()
    
    def get_int(self, chave, fallback=0):
        return int(self.config.get('DEFAULT', chave, fallback=str(fallback)))
    
    def get_bool(self, chave, fallback=False):
        valor = self.config.get('DEFAULT', chave, fallback='sim' if fallback else 'nao')
        return valor.lower() == 'sim'
    
    def add_historico(self, entrada):
        self.historico.append(entrada)
        if len(self.historico) > 100:
            self.historico = self.historico[-100:]
        self.salvar_json(self.history_file, self.historico)
    
    def get_historico(self, limite=15):
        return self.historico[-limite:]
    
    def add_calibracao(self, cq, duracao, tamanho_bytes):
        cq_str = str(cq)
        if cq_str not in self.calibracao:
            self.calibracao[cq_str] = {'count': 0, 'total_bitrate': 0, 'avg_bitrate_kbps': 0}
        
        dados = self.calibracao[cq_str]
        audio_bytes = int(192 * 1000 / 8 * duracao)
        video_bytes = max(0, tamanho_bytes - audio_bytes)
        video_bitrate = int(video_bytes * 8 / duracao / 1000) if duracao > 0 else 0
        
        dados['count'] += 1
        dados['total_bitrate'] += video_bitrate
        dados['avg_bitrate_kbps'] = int(dados['total_bitrate'] / dados['count'])
        
        if dados['count'] > 50:
            dados['count'] = 50
            dados['total_bitrate'] = dados['avg_bitrate_kbps'] * 50
        
        self.salvar_json(self.calibration_file, self.calibracao)
    
    def get_calibracao(self, cq):
        return self.calibracao.get(str(cq))