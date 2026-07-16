"""
renderer.py – Renderização curses do HUD de jogo em CLI PIRATES.

Contém safe_addstr (escrita segura em qualquer terminal) e desenhar_tela
(composição completa do HUD a cada frame).
"""

try:
    import curses as _curses
except ImportError:
    _curses = None  # type: ignore[assignment]

from ..constants import SIMB_TRIPULANTE, SIMB_CAPITAO, COR_AMARELO
from ..core.state import montar_tripulacao
from ..input.hotkeys import _descrever_foco
from .colors import cor_header, cor_tripulacao_livre, cor_log, cor_tarefa
from .hud import (
    build_navio_diagrama,
    build_canhoes_linhas,
    build_bussola_linhas,
    build_vista_linhas,
    build_mapa_linhas,
    build_adm_linhas,
    build_mapa_navegacao_linhas,
    build_mapa_mundo_linhas,
)

RIGHT_X = 36
"""Coluna de início do painel direito (canhões + tripulação)."""

ADM_X = 100
"""Coluna de início do painel ADM — bem à direita do HUD normal.
Terminal precisa de ~150+ colunas; caso contrário safe_addstr trunca silenciosamente."""


def safe_addstr(stdscr, y: int, x: int, text: str, attr: int = 0) -> None:
    """Escreve texto em curses ignorando silenciosamente erros de borda.

    Args:
        stdscr: Janela curses principal.
        y:      Linha (0-indexed).
        x:      Coluna inicial (0-indexed).
        text:   Texto a escrever.
        attr:   Atributo de cor/estilo curses.
    """
    if _curses is None:
        return
    max_y, max_x = stdscr.getmaxyx()
    if y < 0 or y >= max_y or x >= max_x:
        return
    try:
        stdscr.addstr(y, x, text[:max(0, max_x - x - 1)], attr)
    except _curses.error:
        pass


def desenhar_tela(stdscr, estado, buffer_entrada: str) -> None:
    """Redesenha a tela completa do jogo a partir do estado atual.

    Layout (de cima para baixo):
    1. Cabeçalho com tipo de navio, tempo e tripulação livre.
    2. Linha de hotkeys (se ativas).
    3. Colunas: status do navio (esq) | canhões + tripulação (dir).
    4. Minimapa.
    5. Bússola.
    6. Visão do capitão.
    7. Log (4 linhas mais recentes).
    8. Separador e prompt de entrada.

    Args:
        stdscr:         Janela curses principal.
        estado:         Estado atual do jogo.
        buffer_entrada: Texto atualmente digitado no prompt.
    """
    if _curses is None:
        return
    stdscr.erase()
    max_y, max_x = stdscr.getmaxyx()

    row = 0
    prefixo = (
        f"CLI PIRATES | {estado.jogador.tipo_nome.upper()} | "
        f"tempo: {estado.tempo:5.1f}s | tripulacao livre: "
    )
    numero_livre = f"{estado.crew_livre()}/{estado.crew_total}"
    safe_addstr(stdscr, row, 0, prefixo, cor_header(estado))
    safe_addstr(stdscr, row, len(prefixo), numero_livre, cor_tripulacao_livre(estado))
    if estado.modo_adm:
        adm_label = " | [ADM]"
        adm_col = len(prefixo) + len(numero_livre)
        attr_adm = (_curses.color_pair(COR_AMARELO) | _curses.A_BOLD) if _curses else 0
        safe_addstr(stdscr, row, adm_col, adm_label, attr_adm)
    row += 1
    safe_addstr(stdscr, row, 0, "-" * min(max_x - 1, 78))
    row += 1

    if estado.hotkeys_ativo:
        safe_addstr(
            stdscr, row, 0,
            "HOTKEYS: a/d leme  w/s vela  j/l canhao  i/k mira  espaco atirar/parar  "
            "u/h bomba  e/r reparo (e circula, r remove, espaco add) | foco: "
            + _descrever_foco(estado),
        )
        row += 1

    safe_addstr(stdscr, row, 0, f"SEU NAVIO ({estado.jogador.tipo_nome.upper()})",
                _curses.A_UNDERLINE)
    safe_addstr(stdscr, row, RIGHT_X, "CANHOES", _curses.A_UNDERLINE)
    row += 1
    topo_colunas = row

    esquerda = build_navio_diagrama(estado)
    canhoes_linhas = build_canhoes_linhas(estado)
    roster = montar_tripulacao(estado)
    direita = canhoes_linhas + [("", 0), ("TRIPULACAO:", 0)] + [
        (
            f"{SIMB_TRIPULANTE} {tid:4s} {tarefa:8s} {detalhe}",
            cor_tarefa(estado, tarefa),
        )
        for tid, tarefa, detalhe in roster
    ]

    maxlen = max(len(esquerda), len(direita))
    for i in range(maxlen):
        rowi = topo_colunas + i
        if i < len(esquerda):
            texto, attr = esquerda[i]
            safe_addstr(stdscr, rowi, 0, texto, attr)
        if i < len(direita):
            texto, attr = direita[i]
            safe_addstr(stdscr, rowi, RIGHT_X, texto, attr)

    if estado.modo_adm:
        for i, (texto, attr) in enumerate(build_adm_linhas(estado)):
            safe_addstr(stdscr, topo_colunas + i, ADM_X, texto, attr)

    row = topo_colunas + maxlen + 1
    safe_addstr(stdscr, row, 0, "== MAPA ==", _curses.A_UNDERLINE)
    row += 1
    for texto, attr, overlays in build_mapa_linhas(estado):
        safe_addstr(stdscr, row, 0, texto, attr)
        for col, segmento, attr_seg in overlays:
            safe_addstr(stdscr, row, col, segmento, attr_seg)
        row += 1
    row += 1

    safe_addstr(stdscr, row, 0, "BUSSOLA", _curses.A_UNDERLINE)
    row += 1
    for texto, attr, overlays in build_bussola_linhas(estado):
        safe_addstr(stdscr, row, 0, texto, attr)
        for col, segmento, attr_seg in overlays:
            safe_addstr(stdscr, row, col, segmento, attr_seg)
        row += 1
    row += 1

    safe_addstr(stdscr, row, 0, f"VISAO DO CAPITAO {SIMB_CAPITAO}", _curses.A_UNDERLINE)
    row += 1
    for texto, attr, overlays in build_vista_linhas(estado):
        safe_addstr(stdscr, row, 0, texto, attr)
        for col, segmento, attr_seg in overlays:
            safe_addstr(stdscr, row, col, segmento, attr_seg)
        row += 1

    log_lines = list(estado.log)[-4:]
    base = max_y - (2 + len(log_lines) + 2)
    safe_addstr(stdscr, base, 0, "LOG", _curses.A_UNDERLINE)
    for i, linha in enumerate(log_lines):
        safe_addstr(stdscr, base + 1 + i, 0, linha, cor_log(estado, linha))
    safe_addstr(stdscr, max_y - 2, 0, "-" * min(max_x - 1, 78))
    safe_addstr(stdscr, max_y - 1, 0, f"> {buffer_entrada}", _curses.A_REVERSE)

    stdscr.refresh()


def desenhar_tela_mundo(stdscr, estado, estado_mundo, buffer_entrada: str) -> None:
    """Redesenha a tela completa do HUD em modo de navegação livre.

    Layout:
    1. Cabeçalho com navio, tempo e tripulação livre.
    2. Colunas: status do navio (esq) | canhões + tripulação (dir).
    3. Mapa de navegação (centrado no jogador, zoom fixo).
    4. Bússola.
    5. Mapa mundo (se estado_mundo.mapa_mundo_visivel).
    6. Log + prompt.

    Args:
        stdscr:       Janela curses principal.
        estado:       Estado de jogo (contém navio do jogador e crew).
        estado_mundo: Estado do mundo aberto (posição, inimigos).
        buffer_entrada: Texto digitado no prompt.
    """
    if _curses is None:
        return
    stdscr.erase()
    max_y, max_x = stdscr.getmaxyx()

    row = 0
    prefixo = (
        f"CLI PIRATES | {estado.jogador.tipo_nome.upper()} | NAVEGACAO | "
        f"tempo: {estado.tempo:5.1f}s | tripulacao livre: "
    )
    numero_livre = f"{estado.crew_livre()}/{estado.crew_total}"
    safe_addstr(stdscr, row, 0, prefixo, cor_header(estado))
    safe_addstr(stdscr, row, len(prefixo), numero_livre, cor_tripulacao_livre(estado))
    if estado.modo_adm:
        adm_label = " | [ADM]"
        attr_adm = (_curses.color_pair(COR_AMARELO) | _curses.A_BOLD) if _curses else 0
        safe_addstr(stdscr, row, len(prefixo) + len(numero_livre), adm_label, attr_adm)
    row += 1
    safe_addstr(stdscr, row, 0, "-" * min(max_x - 1, 78))
    row += 1

    safe_addstr(stdscr, row, 0, f"SEU NAVIO ({estado.jogador.tipo_nome.upper()})",
                _curses.A_UNDERLINE)
    safe_addstr(stdscr, row, RIGHT_X, "CANHOES", _curses.A_UNDERLINE)
    row += 1
    topo_colunas = row

    esquerda = build_navio_diagrama(estado)
    canhoes_linhas = build_canhoes_linhas(estado)
    roster = montar_tripulacao(estado)
    direita = canhoes_linhas + [("", 0), ("TRIPULACAO:", 0)] + [
        (
            f"{SIMB_TRIPULANTE} {tid:4s} {tarefa:8s} {detalhe}",
            cor_tarefa(estado, tarefa),
        )
        for tid, tarefa, detalhe in roster
    ]
    maxlen = max(len(esquerda), len(direita))
    for i in range(maxlen):
        rowi = topo_colunas + i
        if i < len(esquerda):
            texto, attr = esquerda[i]
            safe_addstr(stdscr, rowi, 0, texto, attr)
        if i < len(direita):
            texto, attr = direita[i]
            safe_addstr(stdscr, rowi, RIGHT_X, texto, attr)

    row = topo_colunas + maxlen + 1
    safe_addstr(stdscr, row, 0, "== MAPA DE NAVEGACAO ==", _curses.A_UNDERLINE)
    row += 1
    for texto, attr, overlays in build_mapa_navegacao_linhas(estado_mundo, estado):
        safe_addstr(stdscr, row, 0, texto, attr)
        for col, segmento, attr_seg in overlays:
            safe_addstr(stdscr, row, col, segmento, attr_seg)
        row += 1
    row += 1

    safe_addstr(stdscr, row, 0, "BUSSOLA", _curses.A_UNDERLINE)
    row += 1
    for texto, attr, overlays in build_bussola_linhas(estado):
        safe_addstr(stdscr, row, 0, texto, attr)
        for col, segmento, attr_seg in overlays:
            safe_addstr(stdscr, row, col, segmento, attr_seg)
        row += 1
    row += 1

    safe_addstr(stdscr, row, 0, f"VISAO DO CAPITAO {SIMB_CAPITAO}", _curses.A_UNDERLINE)
    row += 1
    for texto, attr, overlays in build_vista_linhas(estado):
        safe_addstr(stdscr, row, 0, texto, attr)
        for col, segmento, attr_seg in overlays:
            safe_addstr(stdscr, row, col, segmento, attr_seg)
        row += 1

    if estado_mundo.mapa_mundo_visivel:
        row += 1
        for texto, attr, overlays in build_mapa_mundo_linhas(estado_mundo, estado):
            safe_addstr(stdscr, row, 0, texto, attr)
            for col, segmento, attr_seg in overlays:
                safe_addstr(stdscr, row, col, segmento, attr_seg)
            row += 1

    log_lines = list(estado.log)[-4:]
    base = max_y - (2 + len(log_lines) + 2)
    safe_addstr(stdscr, base, 0, "LOG", _curses.A_UNDERLINE)
    for i, linha in enumerate(log_lines):
        safe_addstr(stdscr, base + 1 + i, 0, linha, cor_log(estado, linha))
    safe_addstr(stdscr, max_y - 2, 0, "-" * min(max_x - 1, 78))
    safe_addstr(stdscr, max_y - 1, 0, f"> {buffer_entrada}", _curses.A_REVERSE)

    stdscr.refresh()
