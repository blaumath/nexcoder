"""
Integração com Telegram - Envio inteligente por tipo de conteúdo
"""
import requests
from pathlib import Path

class TelegramBot:
    def __init__(self, config_mgr):
        self.config_mgr = config_mgr
        self.token = config_mgr.get('telegram_bot_token', '')
        self.chat_filmes = config_mgr.get('telegram_chat_filmes', '')
        self.chat_animes = config_mgr.get('telegram_chat_animes', '')
        self.upload_mode = config_mgr.get('telegram_upload_mode', 'perguntar')
        self.base_url = f"https://api.telegram.org/bot{self.token}" if self.token else ""
        
        self.chats = {
            'filme': [c.strip() for c in self.chat_filmes.split(',') if c.strip()],
            'anime': [c.strip() for c in self.chat_animes.split(',') if c.strip()],
            'serie': [c.strip() for c in self.chat_filmes.split(',') if c.strip()],
        }
        
        self.enabled = bool(self.token and any(self.chats.values()))
    
    def get_chats_para_tipo(self, tipo):
        if tipo in self.chats:
            chats = self.chats[tipo]
            if not chats and tipo != 'filme':
                chats = self.chats.get('filme', [])
            return chats
        return self.chats.get('filme', [])
    
    def get_nome_grupo(self, tipo):
        nomes = {'filme': '🎬 Filmes', 'anime': '🌸 Animes', 'serie': '📺 Séries'}
        return nomes.get(tipo, '📁 Geral')
    
    def get_emoji(self, tipo):
        emojis = {'filme': '🎬', 'anime': '🌸', 'serie': '📺'}
        return emojis.get(tipo, '📁')
    
    def enviar_mensagem(self, texto, chat_ids=None):
        if not self.enabled:
            return False
        
        if chat_ids is None:
            todos_chats = set()
            for chats in self.chats.values():
                todos_chats.update(chats)
            chat_ids = list(todos_chats)
        
        for chat_id in chat_ids:
            try:
                url = f"{self.base_url}/sendMessage"
                data = {
                    'chat_id': chat_id,
                    'text': texto,
                    'parse_mode': 'HTML',
                    'disable_web_page_preview': True
                }
                requests.post(url, json=data, timeout=15)
            except:
                pass
        
        return True
    
    def enviar_arquivo(self, arquivo, legenda='', chat_ids=None):
        if not self.enabled:
            return False
        
        arquivo_path = Path(arquivo)
        
        if arquivo_path.stat().st_size > 2000 * 1024 * 1024:
            legenda += "\n⚠️ Arquivo > 2GB"
            return self.enviar_mensagem(legenda, chat_ids)
        
        if chat_ids is None:
            todos_chats = set()
            for chats in self.chats.values():
                todos_chats.update(chats)
            chat_ids = list(todos_chats)
        
        for chat_id in chat_ids:
            try:
                url = f"{self.base_url}/sendDocument"
                with open(arquivo_path, 'rb') as f:
                    files = {'document': (arquivo_path.name, f)}
                    data = {
                        'chat_id': chat_id,
                        'caption': legenda[:1024],
                        'parse_mode': 'HTML'
                    }
                    requests.post(url, files=files, data=data, timeout=300)
            except:
                pass
        
        return True
    
    def notificar_conclusao(self, arquivo_original, arquivo_final, stats):
        if not self.enabled:
            return
        
        from .utils import bytes_to_human
        
        tipo = stats.get('tipo', 'filme')
        chats_destino = self.get_chats_para_tipo(tipo)
        
        if not chats_destino:
            return
        
        nome_final = Path(arquivo_final).name
        tamanho_antes = bytes_to_human(stats.get('tamanho_original', 0))
        tamanho_depois = bytes_to_human(stats.get('tamanho_final', 0))
        reducao = stats.get('reducao_percent', 0)
        tempo = stats.get('tempo_processamento', 0)
        
        emoji = self.get_emoji(tipo)
        
        mensagem = (
            f"{emoji} <b>NexCoder - Novo {tipo.title()}!</b>\n\n"
            f"📦 <b>Final:</b> {nome_final}\n"
            f"📊 <b>Antes:</b> {tamanho_antes}\n"
            f"📉 <b>Depois:</b> {tamanho_depois}\n"
            f"✨ <b>Redução:</b> {reducao}%\n"
            f"⏱️ <b>Tempo:</b> {tempo//60}min {tempo%60}s"
        )
        
        self.enviar_mensagem(mensagem, chats_destino)
        
        if Path(arquivo_final).exists():
            legenda = f"{emoji} {Path(arquivo_final).name}\n📦 {tamanho_depois} | ✨ -{reducao}%"
            self.enviar_arquivo(arquivo_final, legenda, chats_destino)
    
    def deve_enviar(self, tipo_conteudo):
        if self.upload_mode == 'sempre':
            return True
        elif self.upload_mode == 'nunca':
            return False
        else:
            return None
    
    def atualizar_config(self):
        self.token = self.config_mgr.get('telegram_bot_token', '')
        self.chat_filmes = self.config_mgr.get('telegram_chat_filmes', '')
        self.chat_animes = self.config_mgr.get('telegram_chat_animes', '')
        self.upload_mode = self.config_mgr.get('telegram_upload_mode', 'perguntar')
        self.base_url = f"https://api.telegram.org/bot{self.token}" if self.token else ""
        
        self.chats = {
            'filme': [c.strip() for c in self.chat_filmes.split(',') if c.strip()],
            'anime': [c.strip() for c in self.chat_animes.split(',') if c.strip()],
            'serie': [c.strip() for c in self.chat_filmes.split(',') if c.strip()],
        }
        
        self.enabled = bool(self.token and any(self.chats.values()))