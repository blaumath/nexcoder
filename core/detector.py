"""
Detecção inteligente de tipo de conteúdo (Filme/Série/Anime)
Ordem de verificação: SÉRIE primeiro, depois anime, depois filme
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
    """
    Detecta automaticamente se é Filme, Série ou Anime.
    Ordem de verificação: SÉRIE primeiro, depois anime, depois filme.
    """
    nome = Path(arq_path).stem
    pasta = Path(arq_path).parent.name
    
    # 1. PRIMEIRO verifica se é SÉRIE (padrões S01E01, 1x01, Season)
    match = SERIE_RE.search(nome)
    if match:
        if match.group(1) and match.group(2):
            temporada = int(match.group(1))
            episodio = int(match.group(2))
        elif match.group(3) and match.group(4):
            temporada = int(match.group(3))
            episodio = int(match.group(4))
        else:
            temporada, episodio = 1, 1
        
        nome_serie = extrair_nome_serie(nome)
        
        # Verifica se é anime pelo conteúdo (grupos de fansub, etc)
        # Mas só se NÃO for uma série clara
        if eh_anime_pelo_conteudo(nome, pasta) and not eh_serie_clara(nome):
            return 'anime', extrair_info_anime(nome)
        
        return 'serie', (nome_serie, temporada, episodio)
    
    # 2. Verifica indicativos de temporada (Season 1, Temporada 1, etc)
    temp_match = TEMPORADA_RE.search(nome)
    if temp_match:
        temporada = int(temp_match.group(1))
        nome_serie = extrair_nome_serie(nome)
        
        # Verifica se NÃO é anime
        if not eh_anime_pelo_conteudo(nome, pasta) or eh_serie_clara(nome):
            return 'serie', (nome_serie, temporada, 1)
    
    # 3. Verifica padrões de ANIME (apenas se não for série clara)
    if not eh_serie_clara(nome):
        for pattern in ANIME_PATTERNS:
            if re.search(pattern, nome, re.IGNORECASE):
                return 'anime', extrair_info_anime(nome)
    
    # 4. Se não é série nem anime, é FILME
    return 'filme', nome


def eh_serie_clara(nome):
    """
    Verifica se o nome tem características CLARAS de série (não anime).
    Ex: "Euphoria S03", "Breaking Bad S01E01", "The Office 1x01"
    """
    # Tem S## ou S##E## (formato de série)
    if re.search(r'[Ss]\d{1,2}(?:[Ee]\d{1,2})?', nome):
        return True
    # Tem formato 1x01
    if re.search(r'\d{1,2}x\d{1,2}', nome):
        return True
    # Tem "Season" ou "Temporada" escrito
    if re.search(r'(?:Season|Temporada)\s*\d', nome, re.IGNORECASE):
        return True
    return False


def eh_anime_pelo_conteudo(nome, pasta):
    """
    Verifica se conteúdo tem características de anime.
    Só retorna True se tiver indicadores FORTES de anime.
    """
    # Pastas com nomes óbvios de anime
    pastas_anime = {'anime', 'animes', 'fansub'}
    if pasta.lower() in pastas_anime:
        return True
    
    # Indicadores FORTES de anime (grupos de fansub, etc)
    anime_indicators = [
        r'\[\w+\]',                    # [SubsPlease], [Erai-raws], [HorribleSubs]
        r'\[HorribleSubs\]',           # Grupo específico
        r'\[Erai-raws\]',              # Grupo específico
        r'\[SubsPlease\]',             # Grupo específico
        r'\[Asenshi\]',                # Grupo específico
        r'E\d{2,3}(?!\d)',            # E01, E001 (episódios com 2-3 dígitos)
        r'\d{2,3}v\d',                # v2, v3 (versões de anime)
        r'(?:OP|ED)\d',               # OP1, ED1 (openings/endings)
        r'NC(?:OP|ED)',               # Creditless OP/ED
    ]
    
    for pattern in anime_indicators:
        if re.search(pattern, nome, re.IGNORECASE):
            return True
    
    return False


def extrair_nome_serie(nome):
    """Extrai o nome base da série removendo informações de episódio"""
    nome = re.sub(r'[Ss]\d{1,2}[Ee]\d{1,2}', '', nome, flags=re.IGNORECASE)
    nome = re.sub(r'\d{1,2}x\d{1,2}', '', nome, flags=re.IGNORECASE)
    nome = re.sub(r'(?:19|20)\d{2}', '', nome)
    nome = re.sub(r'(?:1080p|720p|2160p|4K|WEB-DL|WEBRip|BluRay|BRRip|HDRip|DVDRip|HDTV|AMZN|NF|WEB|HMAX|DSNP)', '', nome, flags=re.IGNORECASE)
    nome = re.sub(r'(?:x264|x265|HEVC|H264|AAC|AC3|DDP|DTS|TRUEHD|FLAC)', '', nome, flags=re.IGNORECASE)
    nome = re.sub(r'(?:DUAL|DUBLADO|LEGENDADO|DUB|LEG|SUB)', '', nome, flags=re.IGNORECASE)
    nome = re.sub(r'\[.*?\]', '', nome)
    nome = re.sub(r'[._\-]+', ' ', nome)
    return nome.strip() or "Serie_Desconhecida"


def extrair_info_anime(nome):
    """Extrai informações específicas de anime"""
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


def sugerir_modo_audio(tipo_conteudo, config_mgr):
    """
    Sugere modo de áudio baseado no tipo de conteúdo.
    Séries: Dublado por padrão
    Animes: Legendado por padrão
    Filmes: Perguntar por padrão
    """
    if tipo_conteudo == 'anime':
        return config_mgr.get('modo_auto_anime', 'legendado')
    elif tipo_conteudo == 'serie':
        return config_mgr.get('modo_auto_serie', 'dublado')
    else:
        return config_mgr.get('modo_auto_filme', 'perguntar')


def eh_serie(path):
    """Verifica se o caminho contém padrão de série"""
    return bool(SERIE_RE.search(Path(path).name))