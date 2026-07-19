"""
hud.py - Construtores de elementos HUD de CLI PIRATES.

Cada função ``build_*`` retorna uma lista de tuplas prontas para a camada
de renderização (renderer.py). O formato é:
    (texto: str, atributo_base: int, overlays: list[tuple[col, segmento, attr]])
"""

import math

try:
    import curses as _curses
except ImportError:
    _curses = None  # type: ignore[assignment]

from ..constants import (
    COOLDOWN_CANHAO, PARTES, SAIDA_BOMBA_SEG, TEMPO_FUGA_ESCAPE_SEG,
    MUNDO_TAMANHO, COR_VERDE, COR_AMARELO, COR_VERMELHO, COR_JOGADOR, COR_ILHA,
)
from ..core.utils import barra, clamp, seta_unicode_para_heading, seta_ascii_para_heading
from ..core.combat import distancia, rumo_para
from ..core.state import montar_tripulacao
from .colors import (
    cor_valor, cor_cooldown, cor_mar, cor_navio, cor_norte, cor_tarefa, cor_recurso,
)



def build_navio_diagrama(estado) -> list[tuple[str, int]]:
    """Constrói as linhas de status do navio do jogador (coluna esquerda).

    Returns:
        Lista de (texto, atributo_curses).
    """
    j = estado.jogador
    return [
        (
            f"CASCO [{barra(j.partes['casco'], 10)}] {j.partes['casco']:5.1f}%",
            cor_valor(estado, j.partes['casco']),
        ),
        (
            f"MASTRO[{barra(j.partes['mastro'], 10)}] {j.partes['mastro']:5.1f}%",
            cor_valor(estado, j.partes['mastro']),
        ),
        (
            f"VELA  [{barra(j.partes['vela'], 10)}] {j.partes['vela']:5.1f}%",
            cor_valor(estado, j.partes['vela']),
        ),
        (
            f"RODA  [{barra(j.partes['roda'], 10)}] {j.partes['roda']:5.1f}%",
            cor_valor(estado, j.partes['roda']),
        ),
        (
            f"AGUA  [{barra(j.agua, 10)}] {j.agua:5.1f}%",
            cor_valor(estado, j.agua, pior_se_alto=True),
        ),
        (
            f"MORAL [{barra(j.moral_atual, 10)}] {j.moral_atual:5.1f}%",
            cor_valor(estado, j.moral_atual),
        ),
        (f"RUMO {j.heading:5.1f} -> {j.heading_alvo:5.1f}", 0),
        (f"VEL  {j.velocidade:4.1f} / {j.velocidade_maxima():4.1f}", 0),
    ]


def build_canhoes_linhas(estado) -> list[tuple[str, int]]:
    """Constrói as linhas de status de todos os canhões do jogador.

    Returns:
        Lista de (texto, atributo_curses).
    """
    linhas: list[tuple[str, int]] = []
    for lado in ('estibordo', 'bombordo'):
        for c in estado.jogador.canhoes[lado]:
            if estado.tempo < c.proximo_tiro:
                restante = c.proximo_tiro - estado.tempo
                pct_cd = clamp(100 * (1 - restante / COOLDOWN_CANHAO), 0, 100)
                pronto = False
            else:
                restante = 0.0
                pct_cd = 100.0
                pronto = True

            bar_str = f"[{barra(pct_cd)}]"

            if c.dist_alvo is None:
                info = "sem mira"
                attr = 0
            elif pronto:
                info = f"mira:{c.dist_alvo:.0f}m PRONTO"
                attr = cor_cooldown(estado, pronto=True)
            else:
                info = f"mira:{c.dist_alvo:.0f}m {restante:.1f}s"
                attr = cor_cooldown(estado, pronto=False)

            linhas.append((f"{c.label} {bar_str} {info}", attr))
    return linhas


def build_bussola_linhas(estado, largura: int = 50) -> list[tuple]:
    """Constrói a bússola deslizante com a proa fixada no centro.

    Args:
        estado:  Estado atual do jogo.
        largura: Número de colunas da bússola.

    Returns:
        Lista de (texto, atributo_base, overlays).
    """
    jogador = estado.jogador
    linha = [' '] * largura
    marcos = {0: 'N', 45: 'NE', 90: 'E', 135: 'SE', 180: 'S', 225: 'SW', 270: 'W', 315: 'NW'}
    overlays: list[tuple] = []

    for graus, label in marcos.items():
        rel = (graus - jogador.heading + 540) % 360 - 180
        pos = clamp(int(round((rel + 180) / 360 * (largura - 1))), 0, largura - 1)
        ini = clamp(pos - len(label) // 2, 0, largura - len(label))
        for i, c in enumerate(label):
            linha[ini + i] = c
        if label == 'N':
            overlays.append((ini, label, cor_norte(estado)))

    diff = (jogador.heading_alvo - jogador.heading + 540) % 360 - 180
    ponteiro = [' '] * largura

    if abs(diff) >= 0.5:
        if abs(diff) < 10:
            n_arrows = 1
        elif abs(diff) < 30:
            n_arrows = 2
        elif abs(diff) < 60:
            n_arrows = 3
        elif abs(diff) < 90:
            n_arrows = 4
        else:
            n_arrows = 5
        pos_alvo = clamp(int(round((diff + 180) / 360 * (largura - 1))), 0, largura - 1)
        ponteiro[pos_alvo] = '|'
        if diff > 0:
            arrow_char = '>'
            for i in range(1, n_arrows + 1):
                p = pos_alvo - i
                if 0 <= p < largura:
                    ponteiro[p] = arrow_char
        else:
            arrow_char = '<'
            for i in range(1, n_arrows + 1):
                p = pos_alvo + i
                if 0 <= p < largura:
                    ponteiro[p] = arrow_char

    return [
        (''.join(linha), 0, overlays),
        (''.join(ponteiro), 0, []),
    ]


def build_vista_linhas(estado, inimigo_vista=None, jogador_vista=None) -> list[tuple]:
    """Constrói a visão horizontal do capitão mostrando o inimigo no horizonte.

    Args:
        inimigo_vista: Objeto com .afundado, .x, .y, .tipo_nome (opcional).
                       Se None, usa estado.inimigo (modo combate).
        jogador_vista: Objeto com .x, .y, .heading (opcional).
                       Se None, usa estado.jogador (modo combate).

    Returns:
        Lista de (texto, atributo_base, overlays).
    """
    jogador = jogador_vista if jogador_vista is not None else estado.jogador
    inimigo = inimigo_vista if inimigo_vista is not None else estado.inimigo
    largura = 50
    attr_mar = cor_mar(estado)

    modo_combate = inimigo_vista is None

    # Régua com overlays de cor por setor
    regua = [' '] * largura
    marcos_ruler = {-180: 'POPA', -90: 'BOMB', 0: 'PROA', 90: 'ESTIB', 180: 'POPA'}
    ruler_overlays: list[tuple] = []
    for graus, label in marcos_ruler.items():
        p = clamp(int(round((graus + 180) / 360 * (largura - 1))), 0, largura - 1)
        ini = clamp(p - len(label) // 2, 0, largura - len(label))
        for i, c in enumerate(label):
            regua[ini + i] = c
        if estado.cores_ativo and _curses is not None:
            if label == 'BOMB':
                ruler_overlays.append((ini, label, _curses.color_pair(COR_VERMELHO)))
            elif label == 'ESTIB':
                ruler_overlays.append((ini, label, _curses.color_pair(COR_VERDE)))
            elif label == 'POPA':
                ruler_overlays.append((ini, label, _curses.color_pair(COR_AMARELO)))
    ruler = ''.join(regua)

    # Horizonte base: marcadores | nos limites do arco dos canhões (só combate)
    # Estibordo: rel +20° a +160°; Bombordo: rel -160° a -20°
    horiz_base = list('~' * largura)
    if modo_combate:
        for deg in (-160, -20, 20, 160):
            p = clamp(int(round((deg + 180) / 360 * (largura - 1))), 0, largura - 1)
            horiz_base[p] = '|'
    horiz_str = ''.join(horiz_base)

    agua = [(horiz_str, attr_mar, []), (ruler, 0, ruler_overlays)]

    if inimigo.afundado:
        return agua

    d_real = distancia(jogador, inimigo)
    alcance_visual = 1800
    if d_real > alcance_visual:
        return agua

    rel = (rumo_para(jogador, inimigo) - jogador.heading + 540) % 360 - 180
    pos = clamp(int(round((rel + 180) / 360 * (largura - 1))), 0, largura - 1)

    tipo = getattr(inimigo, 'tipo_nome', '').lower()
    if 'galeao' in tipo or 'galeão' in tipo:
        icones = ("<[-(|||]>", "<[|||]>", "<|||>", "ooo", "...")
    elif 'bergantim' in tipo:
        icones = ("<[-(||]>", "<[||]>", "<||>", "oo", "..")
    else:
        icones = ("<[-(|]>", "<[|]>", "<|>", "o", ".")

    if d_real < 150:
        icone = icones[0]
    elif d_real < 300:
        icone = icones[1]
    elif d_real < 500:
        icone = icones[2]
    elif d_real < 700:
        icone = icones[3]
    else:
        icone = icones[4]

    # Inimigo sobrepõe os marcadores | (layer na frente)
    linha = list(horiz_str)
    inicio = clamp(pos - len(icone) // 2, 0, largura - len(icone))
    for i, ch in enumerate(icone):
        linha[inicio + i] = ch
    horizonte = ''.join(linha)
    overlay_navio = [(inicio, icone, cor_navio(estado, e_jogador=False))]

    return [(horizonte, attr_mar, overlay_navio), (ruler, 0, ruler_overlays)]


def build_mapa_linhas(estado) -> list[tuple]:
    """Constrói o minimapa de grade mostrando posição relativa dos navios.

    Returns:
        Lista de (texto, atributo_base, overlays).
    """
    jogador, inimigo = estado.jogador, estado.inimigo
    unicode_on = estado.graficos_unicode
    GRID_W, GRID_H = 13, 20

    cx = (jogador.x + inimigo.x) / 2
    cy = (jogador.y + inimigo.y) / 2
    half_range = estado.zoom_atual or 400

    def to_cell(nx: float, ny: float) -> tuple[int, int]:
        gx = (nx - cx) / (2 * half_range) * (GRID_W - 1) + (GRID_W - 1) / 2
        gy = (ny - cy) / (2 * half_range) * (GRID_H - 1) + (GRID_H - 1) / 2
        col = clamp(int(round(gx)), 0, GRID_W - 1)
        row = clamp(int(round((GRID_H - 1) - gy)), 0, GRID_H - 1)
        return col, row

    def celula(navio, e_jogador: bool) -> str:
        glifo = (seta_unicode_para_heading(navio.heading) if unicode_on
                 else seta_ascii_para_heading(navio.heading))
        return ('{' + glifo + '}') if e_jogador else ('[' + glifo + ']')

    largura_celula = 3
    filler = '~' * largura_celula
    grid = [[filler for _ in range(GRID_W)] for _ in range(GRID_H)]
    overlays_por_linha: dict[int, list] = {r: [] for r in range(GRID_H)}

    # Ilhas em coords de arena
    _ilhas_arena = getattr(estado, 'ilhas_arena', [])
    if _ilhas_arena:
        from ..world.entities import eh_solido_ilha as _esi_mapa
        _attr_ilha = (_curses.color_pair(COR_ILHA) if (estado.cores_ativo and _curses) else 0)
        for _ilha in _ilhas_arena:
            for _ri in range(GRID_H):
                for _ci in range(GRID_W):
                    _ax = cx + (_ci - (GRID_W - 1) / 2) * (2 * half_range) / (GRID_W - 1)
                    _ay = cy + ((GRID_H - 1) / 2 - _ri) * (2 * half_range) / (GRID_H - 1)
                    if _esi_mapa(_ax, _ay, _ilha, mundo_tamanho=1e9):
                        grid[_ri][_ci] = '###'
                        overlays_por_linha[_ri].append((_ci * largura_celula, '###', _attr_ilha))

    if inimigo.vivo():
        c, r = to_cell(inimigo.x, inimigo.y)
        texto_celula = celula(inimigo, False)
        grid[r][c] = texto_celula
        overlays_por_linha[r].append(
            (c * largura_celula, texto_celula, cor_navio(estado, e_jogador=False))
        )
    if jogador.vivo():
        c, r = to_cell(jogador.x, jogador.y)
        texto_celula = celula(jogador, True)
        grid[r][c] = texto_celula
        overlays_por_linha[r].append(
            (c * largura_celula, texto_celula, cor_navio(estado, e_jogador=True))
        )

    attr_mar = cor_mar(estado)
    linhas: list[tuple] = []
    for i, row in enumerate(grid):
        linhas.append((''.join(row), attr_mar, overlays_por_linha[i]))

    zoom_recente = (estado.tempo - estado.zoom_mudou_em) < 2.0
    attr_zoom = 0
    if _curses is not None:
        attr_zoom = _curses.A_BOLD | _curses.A_REVERSE if zoom_recente else 0
        if zoom_recente and estado.cores_ativo:
            attr_zoom |= _curses.color_pair(COR_AMARELO)
    linhas.append((f"ZOOM: ~{half_range}m", attr_zoom, []))
    return linhas


def build_vigia_linhas(estado) -> list[tuple]:
    """Estimativa de distância ao inimigo (modo combate). Snap a 25m para evitar oscilação."""
    inimigo = estado.inimigo
    if inimigo.afundado:
        return []
    d = distancia(estado.jogador, inimigo)
    if d > 1800:
        return []
    estimativa = round(d / 25) * 25
    return [(f'Vigia: "a {estimativa:.0f}m!"', 0, [])]


def build_vigia_mundo_linhas(estado_mundo) -> list[tuple]:
    """Estimativa de distância ao inimigo mais próximo (modo mundo). Snap a 25m."""
    jx, jy = estado_mundo.jogador_x, estado_mundo.jogador_y
    melhor_d = float('inf')
    for navio in estado_mundo.inimigos:
        if navio.status == "afundado":
            continue
        d = estado_mundo._distancia_toroidal(jx, jy, navio.x, navio.y)
        if d < melhor_d:
            melhor_d = d
    if melhor_d <= 1800:
        estimativa = round(melhor_d / 25) * 25
        return [(f'Vigia: "a {estimativa:.0f}m!"', 0, [])]
    return []


def build_adm_linhas(estado) -> list[tuple[str, int]]:
    """Painel de debug (Modo ADM) com o estado interno completo do inimigo.

    Só deve ser chamado quando estado.modo_adm é True.

    Returns:
        Lista de (texto, atributo_curses).
    """
    from ..core.ship import calcular_entrada_agua

    i = estado.inimigo
    j = estado.jogador
    linhas: list[tuple[str, int]] = []

    linhas.append((
        "=== [ADM] NAVIO INIMIGO ===",
        (_curses.A_BOLD | _curses.A_REVERSE) if _curses else 0,
    ))

    d = distancia(j, i)
    r = rumo_para(j, i)
    linhas.append((f"pos=({i.x:7.1f},{i.y:7.1f}) heading={i.heading:5.1f}->{i.heading_alvo:5.1f}", 0))
    linhas.append((
        f"dist_do_jogador={d:6.1f}m rumo={r:5.1f} "
        f"vel={i.velocidade:4.1f}/{i.velocidade_maxima():4.1f} vela={i.nivel_vela}/3",
        0,
    ))
    linhas.append((f"afundado={i.afundado}", 0))

    for p in PARTES:
        linhas.append((f"{p:8s}: {i.partes[p]:5.1f}%", cor_valor(estado, i.partes[p])))
    entrada_agua = calcular_entrada_agua(i.partes)
    saida_bomba = estado.inimigo_crew_bomba * SAIDA_BOMBA_SEG * i.multiplicador_moral()
    linhas.append((
        f"agua: {i.agua:5.1f}%  (entrada={entrada_agua:5.2f}/s saida={saida_bomba:5.2f}/s)",
        cor_valor(estado, i.agua, pior_se_alto=True),
    ))

    linhas.append((
        f"moral: atual={i.moral_atual:5.1f}% alvo={i.moral_alvo():5.1f}%"
        f" mult_efic={i.multiplicador_moral():.2f}",
        0,
    ))
    linhas.append((
        f"fuga: {'SIM' if estado.inimigo_em_fuga else 'nao'}  "
        f"limiar_entrada<={estado.ia_limiar_fuga_entrada:4.1f}%  "
        f"limiar_saida>={estado.ia_limiar_fuga_saida:4.1f}%",
        0,
    ))
    if estado.inimigo_em_fuga:
        linhas.append((
            f"tempo_fuga_longe: {estado.tempo_fuga_longe:4.1f}s / {TEMPO_FUGA_ESCAPE_SEG:.0f}s",
            0,
        ))

    linhas.append((
        f"personalidade: limiar_agua={estado.ia_limiar_agua:4.1f}%"
        f" limiar_casco={estado.ia_limiar_casco:4.1f}%",
        0,
    ))

    linhas.append((f"tripulacao total: {estado.crew_total}", 0))
    linhas.append((f"  bomba: {estado.inimigo_crew_bomba}", 0))
    for p in PARTES:
        n = estado.inimigo_crew_reparo.get(p, 0)
        if n > 0:
            linhas.append((f"  reparo {p}: {n}", 0))
    total_canhoes = sum(c.tripulantes for lado in i.canhoes.values() for c in lado)
    linhas.append((f"  canhoes (total trip.): {total_canhoes}", 0))

    for lado in ('estibordo', 'bombordo'):
        for c in i.canhoes[lado]:
            if c.dist_alvo is None:
                status = "sem mira"
            elif estado.tempo < c.proximo_tiro:
                status = f"cd {c.proximo_tiro - estado.tempo:4.1f}s"
            else:
                status = "PRONTO"
            linhas.append((
                f"  {c.label}: trip={c.tripulantes} mira={c.mira_atual:5.0f}m"
                f" dist_alvo={c.dist_alvo} armado={c.armado()} [{status}]",
                0,
            ))

    linhas.append((
        f"stats: tiros={estado.stats['tiros_inimigo']}"
        f" acertos={estado.stats['acertos_inimigo']}",
        0,
    ))

    return linhas


# ---------------------------------------------------------------------------
# Painel de porão
# ---------------------------------------------------------------------------

def build_porao_linhas(navio) -> list[tuple[str, int]]:
    """Constrói as linhas do painel de porão agrupadas por tipo.

    Returns:
        Lista de (texto, atributo_curses).
    """
    from ..core.porao import TIPOS_CARGA, capacidade_barril

    p = navio.porao
    slots = len(p.barris)
    cap = p.capacidade
    linhas: list[tuple[str, int]] = [(f"PORAO ({slots}/{cap} slots)", 0)]
    for tipo in TIPOS_CARGA:
        barris_tipo = [b for b in p.barris if b.tipo == tipo]
        n_barris = len(barris_tipo)
        total = sum(b.quantidade for b in barris_tipo)
        cap_tipo = capacidade_barril(tipo)
        if n_barris > 0:
            pct = total / (n_barris * cap_tipo)
            n_cheios = int(round(pct * 10))
            bar = "#" * n_cheios + "-" * (10 - n_cheios)
            max_u = int(n_barris * cap_tipo)
            linhas.append((f"  {tipo:7s} {n_barris}b [{bar}] {total:.0f}/{max_u}u", 0))
        else:
            linhas.append((f"  {tipo:7s} 0b [----------]  0u", 0))
    return linhas


def build_porao_inventario_linhas(navio, cores: bool = True) -> list[tuple[str, int]]:
    """Porão com listagem individual de barris (mesmo formato do inventário)."""
    from ..core.porao import capacidade_barril
    p = navio.porao
    cap = p.capacidade
    linhas: list[tuple[str, int]] = [
        (f"PORAO  {navio.tipo_nome.upper()} | {navio.nome}  [{len(p.barris)}/{cap} slots]", 0),
        ("  #   Tipo      Qtd / Max    [Barra      ]", 0),
    ]
    for i in range(cap):
        if i < len(p.barris):
            b = p.barris[i]
            cap_b = capacidade_barril(b.tipo)
            pct = b.quantidade / cap_b if cap_b > 0 else 0.0
            n_h = int(round(pct * 10))
            barra_str = "#" * n_h + "-" * (10 - n_h)
            texto = f"  {i+1:2d}.  {b.tipo:7s}  {b.quantidade:4.0f} / {cap_b:2.0f}u  [{barra_str}]"
            attr = cor_recurso(cores, b.tipo)
        else:
            texto = f"  {i+1:2d}.  [slot vazio]"
            attr = 0
        linhas.append((texto, attr))
    return linhas


# ---------------------------------------------------------------------------
# HUD de mundo aberto
# ---------------------------------------------------------------------------

def _cel_mar(x_mundo: float, y_mundo: float) -> str:
    """Char de mar determinístico por coordenada absoluta (grão de 100m)."""
    GRAO = 100
    xc = int(x_mundo // GRAO)
    yc = int(y_mundo // GRAO)
    # Mistura não-linear para evitar listras/clusters do XOR simples
    n = xc * 374761393 + yc * 668265263 + xc * yc * 1013904223
    n = n ^ (n >> 16)
    n = (n * 2246822519) & 0xFFFFFFFF
    n = n ^ (n >> 13)
    h = n % 1000
    if h < 55:     # ~5.5% → decoração rara: pedra, coral, onda
        return ('o', '*', 'v')[h % 3]
    elif h < 280:  # ~22.5% → variante abstrata
        return '-' if h & 1 else ' '
    return '~'     # ~72% → mar padrão


def _to_cell_mundo(nx: float, ny: float, cx: float, cy: float, half_range: float,
                   grid_w: int, grid_h: int) -> tuple[int, int]:
    """Converte coordenadas do mundo para célula da grade, considerando wrap toroidal."""
    dx = nx - cx
    dy = ny - cy
    if abs(dx) > MUNDO_TAMANHO / 2:
        dx -= math.copysign(MUNDO_TAMANHO, dx)
    if abs(dy) > MUNDO_TAMANHO / 2:
        dy -= math.copysign(MUNDO_TAMANHO, dy)
    gx = dx / (2 * half_range) * (grid_w - 1) + (grid_w - 1) / 2
    gy = dy / (2 * half_range) * (grid_h - 1) + (grid_h - 1) / 2
    col = clamp(int(round(gx)), 0, grid_w - 1)
    row = clamp(int(round((grid_h - 1) - gy)), 0, grid_h - 1)
    return col, row


def build_mapa_navegacao_linhas(estado_mundo, estado) -> list[tuple]:
    """Mapa de navegação centrado no jogador. Dimensões equivalentes ao mapa-mundo (39×20).

    Zoom fixo MUNDO_ZOOM_NAV_FIXO=800m. Ícones direcionais {↑}/{↓} para jogador,
    [↑]/[↓] para inimigos — mesmo padrão do mini-mapa de combate.
    Fora de combate: portos ( P ) e destroços ( x ) dentro do raio.
    Em combate: apenas inimigos (porto some, igual ao mapa-mundo).
    """
    from ..constants import MUNDO_ZOOM_NAV_FIXO

    GRID_W, GRID_H = 13, 20
    half_range = MUNDO_ZOOM_NAV_FIXO
    largura_celula = 3
    unicode_on = getattr(estado, 'graficos_unicode', False)

    jx = estado_mundo.jogador_x
    jy = estado_mundo.jogador_y
    em_combate = getattr(estado_mundo, 'em_combate', False)

    # Grid com textura de mar deslizante (coordenada absoluta → char determinístico)
    textura_ativa = getattr(estado, 'textura_mar', True)
    grid = [[''] * GRID_W for _ in range(GRID_H)]
    for _r in range(GRID_H):
        for _c in range(GRID_W):
            if textura_ativa:
                _dx = (_c - (GRID_W - 1) / 2) / (GRID_W - 1) * (2 * half_range)
                _dy = ((GRID_H - 1 - _r) - (GRID_H - 1) / 2) / (GRID_H - 1) * (2 * half_range)
                _wx = (jx + _dx) % MUNDO_TAMANHO
                _wy = (jy + _dy) % MUNDO_TAMANHO
                _c_mar = _cel_mar(_wx, _wy)
                grid[_r][_c] = f'~{_c_mar}~'
            else:
                grid[_r][_c] = '~~~'
    overlays_por_linha: dict[int, list] = {r: [] for r in range(GRID_H)}

    # Rastro do navio (pontos históricos, index 0=mais antigo, -1=mais recente)
    if getattr(estado, 'rastro_ativo', True):
        _rastro = getattr(estado_mundo, 'rastro_jogador', None)
        if _rastro:
            _pontos = list(_rastro)
            _n = len(_pontos)
            _mid = _n // 2
            for _i, (_px, _py) in enumerate(_pontos):
                _col, _row = _to_cell_mundo(_px, _py, jx, jy, half_range, GRID_W, GRID_H)
                _attr = (_curses.A_BOLD if _curses else 0) if _i >= _mid else cor_mar(estado)
                grid[_row][_col] = '~.~'
                overlays_por_linha[_row].append((_col * largura_celula, '~.~', _attr))

    if not em_combate:
        # Portos [P]
        for porto in getattr(estado_mundo, 'portos', []):
            if estado_mundo._distancia_toroidal(jx, jy, porto.x, porto.y) <= half_range:
                col, row = _to_cell_mundo(porto.x, porto.y, jx, jy, half_range, GRID_W, GRID_H)
                grid[row][col] = '[P]'
                attr = (_curses.color_pair(COR_VERDE)
                    if (estado.cores_ativo and _curses) else 0)
                overlays_por_linha[row].append((col * largura_celula, '[P]', attr))

        # Destroços do jogador [*]: vermelho = navio próprio afundado
        for wx, wy in getattr(estado_mundo, 'destrocos_jogador', []):
            if estado_mundo._distancia_toroidal(jx, jy, wx, wy) > half_range:
                continue
            col, row = _to_cell_mundo(wx, wy, jx, jy, half_range, GRID_W, GRID_H)
            grid[row][col] = '[*]'
            attr = (_curses.color_pair(COR_VERMELHO)
                    if (estado.cores_ativo and _curses) else 0)
            overlays_por_linha[row].append((col * largura_celula, '[*]', attr))

        # Destroços [x]: amarelo=não visitado (loot), ciano=visitado (sem loot)
        for navio in getattr(estado_mundo, 'inimigos', []):
            if navio.status != "afundado":
                continue
            if estado_mundo._distancia_toroidal(jx, jy, navio.x, navio.y) > half_range:
                continue
            col, row = _to_cell_mundo(navio.x, navio.y, jx, jy, half_range, GRID_W, GRID_H)
            grid[row][col] = '[x]'
            if navio.loot is not None:
                attr = (_curses.color_pair(COR_AMARELO)
                        if (estado.cores_ativo and _curses) else 0)
            else:
                attr = (_curses.color_pair(COR_JOGADOR)
                        if (estado.cores_ativo and _curses) else 0)
            overlays_por_linha[row].append((col * largura_celula, '[x]', attr))

    # Ilhas — varredura de células (aparece antes dos overlays de navios)
    _attr_ilha_nav = (_curses.color_pair(COR_ILHA) if (getattr(estado, 'cores_ativo', False) and _curses) else 0)
    from ..world.entities import eh_solido_ilha as _esi_nav
    for _ilha in getattr(estado_mundo, 'ilhas', []):
        if estado_mundo._distancia_toroidal(jx, jy, _ilha.x, _ilha.y) > half_range + _ilha.raio_maximo:
            continue
        for _ri in range(GRID_H):
            for _ci in range(GRID_W):
                _wx = (jx + (_ci - (GRID_W - 1) / 2) * (2 * half_range) / (GRID_W - 1)) % MUNDO_TAMANHO
                _wy = (jy - (_ri - (GRID_H - 1) / 2) * (2 * half_range) / (GRID_H - 1)) % MUNDO_TAMANHO
                if _esi_nav(_wx, _wy, _ilha):
                    grid[_ri][_ci] = '###'
                    overlays_por_linha[_ri].append((_ci * largura_celula, '###', _attr_ilha_nav))

    # Inimigos ativos — ícone direcional [glifo]
    for navio in getattr(estado_mundo, 'inimigos', []):
        if navio.status == "afundado":
            continue
        if estado_mundo._distancia_toroidal(jx, jy, navio.x, navio.y) > half_range:
            continue
        glifo = (seta_unicode_para_heading(navio.heading) if unicode_on
                 else seta_ascii_para_heading(navio.heading))
        celula_e = '[' + glifo + ']'
        attr = cor_navio(estado, e_jogador=False)
        col, row = _to_cell_mundo(navio.x, navio.y, jx, jy, half_range, GRID_W, GRID_H)
        grid[row][col] = celula_e
        overlays_por_linha[row].append((col * largura_celula, celula_e, attr))

    # Jogador {glifo} sempre no centro, desenhado por último para sobrepor
    glifo_j = (seta_unicode_para_heading(estado_mundo.jogador_heading) if unicode_on
               else seta_ascii_para_heading(estado_mundo.jogador_heading))
    celula_j = '{' + glifo_j + '}'
    cr, rr = GRID_W // 2, GRID_H // 2
    grid[rr][cr] = celula_j
    overlays_por_linha[rr].append((cr * largura_celula, celula_j, cor_navio(estado, e_jogador=True)))

    attr_mar = cor_mar(estado)
    linhas: list[tuple] = []
    for i, row_data in enumerate(grid):
        linhas.append((''.join(row_data), attr_mar, overlays_por_linha[i]))
    linhas.append((f"ZOOM: ~{half_range}m", 0, []))
    return linhas


def build_vista_mundo_linhas(estado_mundo, estado) -> list[tuple]:
    """Visão do capitão durante navegação livre: procura o inimigo mais próximo.

    Reutiliza build_vista_linhas com overrides de posição para evitar depender
    de estado.inimigo (que fica afundado=True durante a navegação).

    Returns:
        Lista de (texto, atributo_base, overlays).
    """
    from types import SimpleNamespace
    from ..constants import NAVIO_TIPOS

    ALCANCE_VISUAL = 1800.0
    jx = estado_mundo.jogador_x
    jy = estado_mundo.jogador_y

    jogador_vista = SimpleNamespace(
        x=jx,
        y=jy,
        heading=estado_mundo.jogador_heading,
    )

    melhor_navio = None
    melhor_d = float('inf')
    for navio in estado_mundo.inimigos:
        if navio.status == "afundado":
            continue
        d = estado_mundo._distancia_toroidal(jx, jy, navio.x, navio.y)
        if d < melhor_d:
            melhor_d = d
            melhor_navio = navio

    if melhor_navio is None or melhor_d > ALCANCE_VISUAL:
        inimigo_vista = SimpleNamespace(afundado=True, x=0.0, y=0.0, tipo_nome="")
    else:
        # Ajuste toroidal: posiciona o inimigo relativo ao jogador
        dx = melhor_navio.x - jx
        dy = melhor_navio.y - jy
        if abs(dx) > MUNDO_TAMANHO / 2:
            dx -= math.copysign(MUNDO_TAMANHO, dx)
        if abs(dy) > MUNDO_TAMANHO / 2:
            dy -= math.copysign(MUNDO_TAMANHO, dy)
        tipo_nome = NAVIO_TIPOS.get(estado_mundo.tipo_navio, {}).get('navio', 'Chalupa')
        inimigo_vista = SimpleNamespace(
            afundado=False,
            x=jx + dx,
            y=jy + dy,
            tipo_nome=tipo_nome,
        )

    linhas = build_vista_linhas(estado, inimigo_vista=inimigo_vista, jogador_vista=jogador_vista)

    # Porto na visão do capitão quando próximo (1000m)
    ALCANCE_VISUAL_PORTO = 1000.0
    if not getattr(estado_mundo, 'em_combate', False):
        from types import SimpleNamespace as _NS
        for porto in getattr(estado_mundo, 'portos', []):
            d_porto = estado_mundo._distancia_toroidal(jx, jy, porto.x, porto.y)
            if d_porto > ALCANCE_VISUAL_PORTO:
                continue
            pdx = porto.x - jx
            pdy = porto.y - jy
            if abs(pdx) > MUNDO_TAMANHO / 2:
                pdx -= math.copysign(MUNDO_TAMANHO, pdx)
            if abs(pdy) > MUNDO_TAMANHO / 2:
                pdy -= math.copysign(MUNDO_TAMANHO, pdy)
            porto_ns = _NS(x=jx + pdx, y=jy + pdy)
            largura = 50
            rel = (rumo_para(jogador_vista, porto_ns) - jogador_vista.heading + 540) % 360 - 180
            pos = clamp(int(round((rel + 180) / 360 * (largura - 1))), 0, largura - 1)
            icone = '[P]'
            inicio = clamp(pos - len(icone) // 2, 0, largura - len(icone))
            horizonte_chars = list(linhas[0][0])
            for i, ch in enumerate(icone):
                horizonte_chars[inicio + i] = ch
            attr = (_curses.color_pair(COR_VERDE)
                        if (estado.cores_ativo and _curses) else 0)
            overlays_h = list(linhas[0][2]) + [(inicio, icone, attr)]
            linhas = [(''.join(horizonte_chars), linhas[0][1], overlays_h)] + list(linhas[1:])
            linhas = list(linhas) + [(f'Porto: "{porto.nome} a {d_porto:.0f}m!"', 0, [])]
            break

    return linhas


def build_mapa_mundo_linhas(estado_mundo, estado) -> list[tuple]:
    """Grade fixa cobrindo os 8000×8000 inteiros.

    Em modo ADM mostra o jogador (@) e inimigos (E/e) sobre o oceano.

    Returns:
        Lista de (texto, atributo_base, overlays).
    """
    # 40×20 células de 1 char: visualmente quadrado (chars ~2× mais altos que largos)
    GRID_W, GRID_H = 40, 20

    grid = [['~'] * GRID_W for _ in range(GRID_H)]
    overlays_por_linha: dict[int, list] = {r: [] for r in range(GRID_H)}

    if estado_mundo is not None:
        def _world_to_cell(wx: float, wy: float) -> tuple[int, int]:
            col = int(wx / MUNDO_TAMANHO * GRID_W) % GRID_W
            row = int((1.0 - wy / MUNDO_TAMANHO) * GRID_H) % GRID_H
            return col, row

        # Portos [P] — visíveis fora do combate
        if not getattr(estado_mundo, 'em_combate', False):
            for porto in getattr(estado_mundo, 'portos', []):
                col, row = _world_to_cell(porto.x, porto.y)
                grid[row][col] = 'P'
                _attr_porto_mw = (_curses.color_pair(COR_VERDE) if (estado.cores_ativo and _curses) else 0)
                overlays_por_linha[row].append((max(0, col - 1), '[P]', _attr_porto_mw))

        # Ilhas [#] — sempre visíveis
        _attr_ilha_mw = (_curses.color_pair(COR_ILHA) if (estado.cores_ativo and _curses) else 0)
        for ilha in getattr(estado_mundo, 'ilhas', []):
            col, row = _world_to_cell(ilha.x, ilha.y)
            grid[row][col] = '#'
            overlays_por_linha[row].append((max(0, col - 1), '[#]', _attr_ilha_mw))

        # Jogador — sempre visível
        col, row = _world_to_cell(estado_mundo.jogador_x, estado_mundo.jogador_y)
        grid[row][col] = '@'
        overlays_por_linha[row].append((col, '@', cor_navio(estado, e_jogador=True)))

        # Inimigos — sempre visíveis
        for navio in estado_mundo.inimigos:
            col, row = _world_to_cell(navio.x, navio.y)
            if navio.status == "afundado":
                grid[row][col] = 'x'
                if navio.loot is not None:
                    attr = (_curses.color_pair(COR_AMARELO)
                            if (estado.cores_ativo and _curses) else 0)
                else:
                    attr = (_curses.color_pair(COR_JOGADOR)
                            if (estado.cores_ativo and _curses) else 0)
                overlays_por_linha[row].append((max(0, col - 1), 'x', attr))
            elif navio.status == "fugindo":
                glifo, attr = 'e', cor_navio(estado, e_jogador=False)
                grid[row][col] = glifo
                overlays_por_linha[row].append((col, glifo, attr))
            else:
                glifo, attr = 'E', cor_navio(estado, e_jogador=False)
                grid[row][col] = glifo
                overlays_por_linha[row].append((col, glifo, attr))

    # Destroços do jogador [*] no mapa mundo — vermelho
    for wx, wy in getattr(estado_mundo, 'destrocos_jogador', []):
        col, row = _world_to_cell(wx, wy)
        grid[row][col] = '*'
        attr = (_curses.color_pair(COR_VERMELHO)
                if (estado.cores_ativo and _curses) else 0)
        overlays_por_linha[row].append((max(0, col - 1), '*', attr))

    # W/E nos lados da linha central
    mid = GRID_H // 2
    grid[mid][0] = 'W'
    grid[mid][GRID_W - 1] = 'E'

    attr_mar = cor_mar(estado)
    if getattr(estado_mundo, 'em_combate', False):
        titulo_mapa = "=== MAPA MUNDO — COMBATE  [@ voce  E inimigo] ==="
    else:
        titulo_mapa = "=== MAPA MUNDO (8km×8km)  [@ voce  E inimigo  e fugindo  [x] afundado  [*] seu navio  [P] porto  [#] ilha] ==="
    linhas: list[tuple] = [(titulo_mapa, 0, [])]
    linhas.append(("N".center(GRID_W), 0, []))
    for i, row in enumerate(grid):
        linhas.append((''.join(row), attr_mar, overlays_por_linha[i]))
    linhas.append(("S".center(GRID_W), 0, []))
    linhas.append(("[M] fecha", 0, []))
    return linhas
