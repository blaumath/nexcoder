"""
Análise de streams de vídeo (áudio, legendas)
"""
import re
import json
import subprocess
from pathlib import Path
from functools import lru_cache

LANGS_PTBR = {'pb', 'pob', 'pt-br', 'ptbr', 'pt_br'}
LANGS_PT = {'por', 'pt'}
LANGS_EN = {'eng', 'en'}
TITLES_DUB = ['português', 'portugu', 'dublado', 'dub pt', 'dub br', 'pt-br', 'ptbr', 'brasil', 'brazilian']
TITLES_BR = ['brazilian', 'brasil', 'br', 'pt-br', 'ptbr', 'pt_br']
TITLES_PT = ['european', 'portugal', 'pt-pt', 'ptpt']
TITLES_EN = ['english', 'inglês', 'ingles', 'original', 'en', 'eng']

@lru_cache(maxsize=50)
def analisar_video(arq_str):
    info = {
        'audio_pt': False, 'audio_pt_idx': '', 'audio_total': 0,
        'audio_en_idx': '', 'tem_sub_pt': False, 'tem_sub_forcado': False,
        'sub_pt_level': 0, 'idx_sub_pt': '', 'idx_sub_pt_rel': '0',
        'idx_sub_pt_nao_forcado': '', 'idx_sub_pt_nao_forcado_rel': '',
        'srt_externo': '', 'diag_audio': 'nenhum', 'diag_subs': 'nenhum',
    }
    
    arq = Path(arq_str)
    try:
        r = subprocess.run(
            ['ffprobe', '-v', 'quiet', '-print_format', 'json', '-show_streams', str(arq)],
            capture_output=True, text=True, timeout=30
        )
        streams = json.loads(r.stdout).get('streams', [])
    except:
        return info

    aud_d, sub_d = [], []
    sub_rel_counter = 0

    for s in streams:
        lang = s.get('tags', {}).get('language', '').lower().strip()
        title = s.get('tags', {}).get('title', '').lower().strip()
        ctype = s.get('codec_type', '')
        forced = int(s.get('disposition', {}).get('forced', 0))
        idx = str(s.get('index', ''))

        if ctype == 'audio':
            info['audio_total'] += 1
            is_ptbr = lang in LANGS_PTBR or any(x in title for x in TITLES_DUB)
            is_pt = lang in LANGS_PT
            is_en = lang in LANGS_EN or any(x in title for x in TITLES_EN)
            
            if (is_ptbr or is_pt) and not info['audio_pt_idx']:
                info['audio_pt'] = True
                info['audio_pt_idx'] = idx
            if is_en and not info['audio_en_idx']:
                info['audio_en_idx'] = idx
            aud_d.append(f"{lang}:{title}" if title else lang or '?')

        if ctype == 'subtitle':
            is_ptbr_lang = lang in LANGS_PTBR
            is_pt_lang = lang in LANGS_PT
            is_br_title = any(x in title for x in TITLES_BR)
            is_pt_title = any(x in title for x in ['portugu', 'legendado'])
            is_euro_title = any(x in title for x in TITLES_PT)

            level = 0
            if is_ptbr_lang or (is_pt_lang and is_br_title) or \
               (is_pt_lang and not is_euro_title and is_pt_title):
                level = 2
            elif is_pt_lang or is_pt_title:
                level = 1

            if level > 0:
                if not forced and not info['idx_sub_pt_nao_forcado']:
                    info['idx_sub_pt_nao_forcado'] = idx
                    info['idx_sub_pt_nao_forcado_rel'] = str(sub_rel_counter)
                if level > info['sub_pt_level'] or \
                   (level == info['sub_pt_level'] and forced and not info['tem_sub_forcado']):
                    info['sub_pt_level'] = level
                    info['idx_sub_pt'] = idx
                    info['idx_sub_pt_rel'] = str(sub_rel_counter)
                    if forced:
                        info['tem_sub_forcado'] = True
                info['tem_sub_pt'] = True

            flag = '[F]' if forced else ''
            sub_d.append(f"{lang}:{title}{flag}" if title else f"{lang or '?'}{flag}")
            sub_rel_counter += 1

    info['diag_audio'] = ', '.join(aud_d) or 'nenhum'
    info['diag_subs'] = ', '.join(sub_d) or 'nenhum'

    # SRT externo
    pasta = arq.parent
    nb = arq.stem.lower()
    EN_PAT = re.compile(r'(?:^|[.\-_ \[\](])(?:en|eng|english)(?:$|[.\-_ \[\])])', re.I)
    PTBR_PAT = re.compile(r'pt.?br|ptbr|pb|pob|brasil', re.I)
    
    for f in sorted(pasta.iterdir()):
        if f.suffix.lower() not in {'.srt', '.ass', '.ssa'}:
            continue
        if EN_PAT.search(f.name):
            continue
        fl = f.name.lower()
        if PTBR_PAT.search(fl) or nb[:20] in fl:
            info['srt_externo'] = str(f)
            break

    return info


def decidir_modo_audio(arq, tipo_conteudo='filme', config_mgr=None):
    """
    Decide modo de áudio baseado no tipo de conteúdo detectado.
    """
    from .utils import G, Y, C, BO, DM, NC, ask, R
    from .detector import sugerir_modo_audio
    
    print(f"\n  {C}[🔎] Analisando: {Path(arq).name}{NC}")
    v = analisar_video(arq)
    print(f"  {DM}Áudio   : {v['diag_audio']}{NC}")
    print(f"  {DM}Legendas: {v['diag_subs']}{NC}")
    
    if config_mgr:
        preferencia = sugerir_modo_audio(tipo_conteudo, config_mgr)
    else:
        preferencia = 'perguntar'
    
    if preferencia == 'perguntar':
        print(f"\n  {BO}Modo de saída:{NC}")
        print(f"  {C}[1]{NC} 🎙️  {BO}Dublado{NC}    {DM}áudio PT-BR · legenda forçada opcional{NC}")
        print(f"  {C}[2]{NC} 💬  {BO}Legendado{NC}  {DM}áudio EN · legenda PT-BR embutida no vídeo{NC}")
        while True:
            modo = input(f"  {BO}Opção [1/2]: {NC}").strip()
            if modo in ("1", "2"):
                break
            print(f"  {R}Digite 1 ou 2.{NC}")
    else:
        modo = '1' if preferencia == 'dublado' else '2'
        tipo_str = {'anime': '🌸 Anime', 'serie': '📺 Série', 'filme': '🎬 Filme'}.get(tipo_conteudo, '🎬 Filme')
        modo_str = {'1': 'Dublado 🎙️', '2': 'Legendado 💬'}.get(modo, '?')
        print(f"  {C}[🤖] {tipo_str} detectado → modo automático: {modo_str}{NC}")

    sub_action = "none"
    sub_file = ""
    audio_pt_idx = v['audio_pt_idx']
    audio_total = v['audio_total']
    audio_en_idx = v['audio_en_idx']

    if modo == "1":
        if v['audio_pt']:
            print(f"  {G}[✓] Áudio PT-BR — faixa #{v['audio_pt_idx']}{NC}")
        else:
            print(f"  {Y}[!] Nenhum áudio PT-BR encontrado — usando faixa padrão{NC}")

        if v['tem_sub_forcado']:
            print(f"  {C}     Legenda forçada detectada (faixa #{v['idx_sub_pt']}){NC}")
            sub_action = "burn_internal" if ask("Embutir legenda forçada no vídeo?") else "none"
        elif v['tem_sub_pt']:
            print(f"  {C}     Legenda PT interna (faixa #{v['idx_sub_pt']}){NC}")
            sub_action = "burn_internal" if ask("Embutir legenda no vídeo?") else "none"
        else:
            sub_action = "none"

        return {
            'sub_action': sub_action,
            'sub_file': sub_file,
            'idx_sub_pt': v['idx_sub_pt'],
            'idx_sub_pt_rel': v['idx_sub_pt_rel'],
            'audio_pt_idx': audio_pt_idx,
            'audio_total': audio_total,
            'audio_override_idx': '',
        }
    else:
        if audio_en_idx:
            print(f"  {G}[✓] Áudio EN — faixa #{audio_en_idx}{NC}")
        else:
            print(f"  {Y}[!] Áudio EN não detectado — usando primeira faixa disponível{NC}")

        idx_sub_leg = v['idx_sub_pt_nao_forcado'] or v['idx_sub_pt']

        if v['srt_externo']:
            print(f"  {G}[✓] SRT externo PT-BR: {Y}{Path(v['srt_externo']).name}{NC}")
            sub_action = "burn_external"
            sub_file = v['srt_externo']
        elif idx_sub_leg:
            print(f"  {G}[✓] Legenda PT interna (faixa #{idx_sub_leg}) — será embutida{NC}")
            sub_action = "burn_internal"
        else:
            print(f"  {Y}[!] Nenhuma legenda PT encontrada — saída sem legenda{NC}")
            sub_action = "none"

        return {
            'sub_action': sub_action,
            'sub_file': sub_file,
            'idx_sub_pt': idx_sub_leg,
            'idx_sub_pt_rel': v['idx_sub_pt_nao_forcado_rel'],
            'audio_pt_idx': '',
            'audio_total': audio_total,
            'audio_override_idx': audio_en_idx,
        }


def _modo_audio_batch(arq, modo):
    """Versão para batch - sem interação com usuário"""
    v = analisar_video(arq)
    
    if modo == "1":
        sub_action = "burn_internal" if v['tem_sub_forcado'] else "none"
        idx_sub = v['idx_sub_pt'] if v['tem_sub_forcado'] else ''
        idx_rel = v.get('idx_sub_pt_rel', '0') if v['tem_sub_forcado'] else v.get('idx_sub_pt_rel', '0')
        return {
            'sub_action': sub_action,
            'sub_file': '',
            'idx_sub_pt': idx_sub,
            'idx_sub_pt_rel': idx_rel,
            'audio_pt_idx': v['audio_pt_idx'],
            'audio_total': v['audio_total'],
            'audio_override_idx': '',
        }
    else:
        idx_sub_leg = v['idx_sub_pt_nao_forcado'] or v['idx_sub_pt']
        if v['srt_externo']:
            sub_action, sub_file = "burn_external", v['srt_externo']
        elif idx_sub_leg:
            sub_action, sub_file = "burn_internal", ''
        else:
            sub_action, sub_file = "none", ''
        idx_leg_rel = v.get('idx_sub_pt_nao_forcado_rel') or v.get('idx_sub_pt_rel', '0')
        return {
            'sub_action': sub_action,
            'sub_file': sub_file,
            'idx_sub_pt': idx_sub_leg,
            'idx_sub_pt_rel': idx_leg_rel,
            'audio_pt_idx': '',
            'audio_total': v['audio_total'],
            'audio_override_idx': v['audio_en_idx'],
        }