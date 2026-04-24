"""
Detecção inteligente de tipo de conteúdo (Filme/Série/Anime)
"""
import re
from pathlib import Path

SERIE_RE = re.compile(r'[Ss](\d{1,2})[Ee](\d{1,2})|(\d{1,2})x(\d{1,2})', re.IGNORECASE)
TEMPORADA_RE = re.compile(r'(?:Season|Temporada|S)\s*(\d{1,2})', re.IGNORECASE)

ANIME_PATTERNS = [
    r'\[\w+\].*?\d+',
    r'\[HorribleSubs\]|\[Erai-raws\]|\[SubsPlease\]|\[Asenshi\]',
    r'(?:anime|Anime)',
]

def detectar_tipo_conteudo(arq_path):
    nome = Path(arq_path).stem
    pasta = Path(arq_path).parent.name
    
    for pattern in ANIME_PATTERNS:
        if re.search(pattern, nome, re.IGNORECASE):
            return 'anime', extrair_info_anime(nome)
    
    match = SERIE_RE.search(nome)
    if match:
        if match.group(1) and match.group(2):
            temporada, episodio = int(match.group(1)), int(match.group(2))
        elif match.group(3) and match.group(4):
            temporada, episodio = int(match.group(3)), int(match.group(4))
        else:
            temporada, episodio = 1, 1
        
        nome_serie = extrair_nome_serie(nome)
        
        if eh_anime_pelo_conteudo(nome, pasta):
            return 'anime', extrair_info_anime(nome)
        
        return 'serie', (nome_serie, temporada, episodio)
    
    temp_match = TEMPORADA_RE.search(nome)
    if temp_match:
        temporada = int(temp_match.group(1))
        nome_serie = extrair_nome_serie(nome)
        return 'serie', (nome_serie, temporada, 1)
    
    return 'filme', nome

def extrair_nome_serie(nome):
    nome = re.sub(r'[Ss]\d{1,2}[Ee]\d{1,2}', '', nome, flags=re.IGNORECASE)
    nome = re.sub(r'\d{1,2}x\d{1,2}', '', nome, flags=re.IGNORECASE)
    nome = re.sub(r'(?:19|20)\d{2}', '', nome)
    nome = re.sub(r'(?:1080p|720p|2160p|4K|WEB-DL|WEBRip|BluRay|BRRip|HDRip|DVDRip|HDTV)', '', nome, flags=re.IGNORECASE)
    nome = re.sub(r'(?:x264|x265|HEVC|H264|AAC|AC3|DDP|DTS)', '', nome, flags=re.IGNORECASE)
    nome = re.sub(r'(?:DUAL|DUBLADO|LEGENDADO|DUB|LEG|SUB)', '', nome, flags=re.IGNORECASE)
    nome = re.sub(r'\[.*?\]', '', nome)
    nome = re.sub(r'[._\-]+', ' ', nome)
    return nome.strip() or "Serie_Desconhecida"

def extrair_info_anime(nome):
    grupo = ''
    grupo_match = re.match(r'\[(.*?)\]', nome)
    if grupo_match:
        grupo = grupo_match.group(1)
        nome = nome[grupo_match.end():].strip()
    
    temporada = 1
    temp_match = re.search(r'(?:S|Season)\s*(\d+)', nome, re.IGNORECASE)
    if temp_match:
        temporada = int(temp_match.group(1))
    
    ep_match = re.search(r'(?:E|EP|Episódio|Ep)\s*(\d{2,3})', nome, re.IGNORECASE)
    if ep_match:
        episodio = int(ep_match.group(1))
    else:
        ep_match = re.search(r'\b(\d{2,3})\b', nome)
        episodio = int(ep_match.group(1)) if ep_match else 1
    
    nome_anime = re.sub(r'(?:E|EP|Episódio|Ep)\s*\d{2,3}', '', nome, re.IGNORECASE)
    nome_anime = re.sub(r'\b\d{2,3}\b', '', nome_anime).strip()
    
    return (nome_anime or "Anime_Desconhecido", temporada, episodio, grupo)

def eh_anime_pelo_conteudo(nome, pasta):
    pastas_anime = {'anime', 'animes', 'fansub'}
    if pasta.lower() in pastas_anime:
        return True
    
    anime_indicators = [r'\[\w+\]', r'S\d{2}E\d{2,3}', r'\d{2,3}v\d']
    for pattern in anime_indicators:
        if re.search(pattern, nome):
            return True
    
    return False

def sugerir_modo_audio(tipo_conteudo, config_mgr):
    if tipo_conteudo == 'anime':
        return config_mgr.get('modo_auto_anime', 'legendado')
    elif tipo_conteudo == 'serie':
        return config_mgr.get('modo_auto_serie', 'dublado')
    else:
        return config_mgr.get('modo_auto_filme', 'perguntar')

def eh_serie(path):
    return bool(SERIE_RE.search(Path(path).name))