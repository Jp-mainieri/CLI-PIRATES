"""
hud.py – Construtores de elementos HUD de CLI PIRATES.

Cada função ``build_*`` retorna uma lista de tuplas prontas para a camada
de renderização (renderer.py). O formato é:
    (texto: str, atributo_base: int, overlays: list[tuple[col, segmento, attr]])
"""

import random

try:
    import curses as _curses
except ImportError:
    _curses = None  # type: ignore[assignment]

from ..constants import COOLDOWN_CANHAO
from ..core.utils import barra, clamp, seta_unicode_para_heading, seta_ascii_para_heading
from ..core.combat import distancia, rumo_para
from ..core.state import montar_tripulacao
from .colors import (
    cor_valor, cor_cooldown, cor_mar, cor_navio, cor_norte, cor_tarefa,
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
            f"VELA  [{barra(j.partes['vela'], 10)}] {j.partes['vela']:5.1f}%  "
            f"({j.num_velas} velas)",
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
            f"Rumo {j.heading:5.1f}->{j.heading_alvo:5.1f} "
            f"Vel {j.velocidade:4.1f}/{j.velocidade_maxima():4.1f} Vela {j.nivel_vela}/3",
            0,
        ),
    ]


def build_canhoes_linhas(estado) -> list[tuple[str, int]]:
    """Constrói as linhas de status de todos os canhões do jogador.

    Returns:
        Lista de (texto, atributo_curses).
    """
    linhas: list[tuple[str, int]] = []
    for lado in ('estibordo', 'bombordo'):
        for c in estado.jogador.canhoes[lado]:
            if not c.operacional():
                linhas.append((f"{c.label} [DESTRUIDO]", cor_valor(estado, 0)))
                continue
            hp_txt = f"{c.label} hp[{barra(c.hp)}]{c.hp:3.0f}% trip:{c.tripulantes}"
            if c.dist_alvo is None:
                status = "sem mira" if c.tripulantes >= estado.min_crew_canhao else "sem trip."
                linhas.append((f"{hp_txt} {status}", cor_valor(estado, c.hp)))
            elif estado.tempo < c.proximo_tiro:
                restante = c.proximo_tiro - estado.tempo
                pct_cd = clamp(100 * (1 - restante / COOLDOWN_CANHAO), 0, 100)
                linhas.append((hp_txt, cor_valor(estado, c.hp)))
                linhas.append((
                    f"   cd[{barra(pct_cd)}] {restante:4.1f}s mira:{c.dist_alvo:.0f}m",
                    cor_cooldown(estado, pronto=False),
                ))
            else:
                linhas.append((hp_txt, cor_valor(estado, c.hp)))
                linhas.append((
                    f"   cd[{barra(100)}] pronto  mira:{c.dist_alvo:.0f}m",
                    cor_cooldown(estado, pronto=True),
                ))
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

    ponteiro = [' '] * largura
    ponteiro[largura // 2] = '|'

    diff = (jogador.heading_alvo - jogador.heading + 540) % 360 - 180
    if abs(diff) < 0.5:
        sentido = "(parado)"
    elif diff > 0:
        sentido = ">>> virando p/ bombordo"
    else:
        sentido = "<<< virando p/ estibordo"

    return [
        (''.join(linha), 0, overlays),
        (''.join(ponteiro), 0, []),
        (f"Rumo atual: {jogador.heading:.0f} graus {sentido}", 0, []),
    ]


def build_vista_linhas(estado) -> list[tuple]:
    """Constrói a visão horizontal do capitão mostrando o inimigo no horizonte.

    Returns:
        Lista de (texto, atributo_base, overlays).
    """
    jogador, inimigo = estado.jogador, estado.inimigo
    largura = 50
    if inimigo.afundado:
        return [("Nenhum navio inimigo a vista.", 0, [])]

    d_real = distancia(jogador, inimigo)
    alcance_visual = 900
    attr_mar = cor_mar(estado)
    if d_real > alcance_visual:
        return [("~" * largura, attr_mar, []), ("O horizonte esta vazio.", 0, [])]

    rel = (rumo_para(jogador, inimigo) - jogador.heading + 540) % 360 - 180
    pos = clamp(int(round((rel + 180) / 360 * (largura - 1))), 0, largura - 1)

    if d_real < 150:
        icone = "#[SHIP]#"
    elif d_real < 400:
        icone = "[SHIP]"
    else:
        icone = "."
    linha = list('~' * largura)
    inicio = clamp(pos - len(icone) // 2, 0, largura - len(icone))
    for i, ch in enumerate(icone):
        linha[inicio + i] = ch
    horizonte = ''.join(linha)
    overlay_navio = [(inicio, icone, cor_navio(estado, e_jogador=False))]

    regua = [' '] * largura
    marcos = {-180: 'POPA', -90: 'BOMB', 0: 'PROA', 90: 'ESTIB', 180: 'POPA'}
    for graus, label in marcos.items():
        p = clamp(int(round((graus + 180) / 360 * (largura - 1))), 0, largura - 1)
        ini = clamp(p - len(label) // 2, 0, largura - len(label))
        for i, c in enumerate(label):
            regua[ini + i] = c
    ruler = ''.join(regua)

    erro_vigia = random.uniform(-0.1, 0.1) * d_real
    vigia = f'Vigia: "a {d_real + erro_vigia:.0f}m!"'

    return [(horizonte, attr_mar, overlay_navio), (ruler, 0, []), (vigia, 0, [])]


def build_mapa_linhas(estado) -> list[tuple]:
    """Constrói o minimapa de grade mostrando posição relativa dos navios.

    Returns:
        Lista de (texto, atributo_base, overlays).
    """
    jogador, inimigo = estado.jogador, estado.inimigo
    unicode_on = estado.graficos_unicode
    GRID_W, GRID_H = 20, 8

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

    d = distancia(jogador, inimigo)
    attr_mar = cor_mar(estado)
    linhas: list[tuple] = [("  N", 0, [])]
    for i, row in enumerate(grid):
        linhas.append((''.join(row), attr_mar, overlays_por_linha[i]))
    linhas.append(("  S", 0, []))

    zoom_recente = (estado.tempo - estado.zoom_mudou_em) < 2.0
    attr_zoom = 0
    if _curses is not None:
        attr_zoom = _curses.A_BOLD | _curses.A_REVERSE if zoom_recente else 0
        if zoom_recente and estado.cores_ativo:
            from ..constants import COR_AMARELO
            attr_zoom |= _curses.color_pair(COR_AMARELO)
    linhas.append((f"ZOOM: ~{half_range}m | dist real: {d:.0f}m", attr_zoom, []))
    return linhas
