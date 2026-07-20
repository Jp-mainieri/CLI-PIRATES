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
from .colors import cor_header, cor_tipo_navio, cor_tripulacao_livre, cor_log, cor_tarefa
from .hud import (
    build_navio_diagrama,
    build_canhoes_linhas,
    build_bussola_linhas,
    build_vista_linhas,
    build_vista_mundo_linhas,
    build_mapa_linhas,
    build_adm_linhas,
    build_mapa_navegacao_linhas,
    build_mapa_mundo_linhas,
    build_vigia_linhas,
    build_vigia_mundo_linhas,
    build_porao_linhas,
    build_velas_linhas,
)

RIGHT_X = 36
"""Coluna de início do painel direito (canhões + tripulação)."""

VELAS_X = 70
"""Coluna de início do painel de velas no HUD."""

PORAO_X = 94
"""Coluna de início do painel de porão no HUD."""

ADM_X = 128
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
    col = 0
    parte1 = "CLI PIRATES | "
    safe_addstr(stdscr, row, col, parte1, cor_header(estado))
    col += len(parte1)
    tipo_nome = estado.jogador.tipo_nome.upper()
    safe_addstr(stdscr, row, col, tipo_nome, cor_tipo_navio(estado))
    col += len(tipo_nome)
    parte2 = f" | tempo: {estado.tempo:5.1f}s"
    safe_addstr(stdscr, row, col, parte2, cor_header(estado))
    col += len(parte2)
    if estado.modo_adm:
        attr_adm = (_curses.color_pair(COR_AMARELO) | _curses.A_BOLD) if _curses else 0
        safe_addstr(stdscr, row, col, " | [ADM]", attr_adm)
    row += 1
    safe_addstr(stdscr, row, 0, "-" * min(max_x - 1, 78))
    row += 1

    safe_addstr(stdscr, row, 0, "SEU NAVIO",
                _curses.A_UNDERLINE)
    safe_addstr(stdscr, row, RIGHT_X, "CANHOES", _curses.A_UNDERLINE)
    safe_addstr(stdscr, row, VELAS_X, "VELAS", _curses.A_UNDERLINE)
    safe_addstr(stdscr, row, PORAO_X, "PORAO", _curses.A_UNDERLINE)
    row += 1
    topo_colunas = row

    esquerda = build_navio_diagrama(estado)
    canhoes_linhas = build_canhoes_linhas(estado)
    roster = montar_tripulacao(estado)
    direita = canhoes_linhas + [("", 0), ("TRIPULACAO:", 0)] + [
        (
            f"{SIMB_TRIPULANTE} {tid:4s} {(tarefa + ': ' + detalhe) if detalhe else tarefa}",
            cor_tarefa(estado, tarefa),
        )
        for tid, tarefa, detalhe in roster
    ]
    porao_linhas = build_porao_linhas(estado.jogador)
    velas_linhas = build_velas_linhas(estado)

    maxlen = max(len(esquerda), len(direita), len(porao_linhas), len(velas_linhas))
    for i in range(maxlen):
        rowi = topo_colunas + i
        if i < len(esquerda):
            texto, attr, overlays = esquerda[i]
            safe_addstr(stdscr, rowi, 0, texto, attr)
            for col_o, segmento, attr_seg in overlays:
                safe_addstr(stdscr, rowi, col_o, segmento, attr_seg)
        if i < len(direita):
            texto, attr = direita[i]
            safe_addstr(stdscr, rowi, RIGHT_X, texto, attr)
        if i < len(porao_linhas):
            texto, attr = porao_linhas[i]
            safe_addstr(stdscr, rowi, PORAO_X, texto, attr)
        if i < len(velas_linhas):
            texto, attr = velas_linhas[i]
            safe_addstr(stdscr, rowi, VELAS_X, texto, attr)

    if estado.modo_adm:
        for i, (texto, attr) in enumerate(build_adm_linhas(estado)):
            safe_addstr(stdscr, topo_colunas + i, ADM_X, texto, attr)

    row = topo_colunas + maxlen + 1

    safe_addstr(stdscr, row, 0, f"VISAO DO CAPITAO {SIMB_CAPITAO}", _curses.A_UNDERLINE)
    row += 1
    for texto, attr, overlays in build_vista_linhas(estado):
        safe_addstr(stdscr, row, 0, texto, attr)
        for col, segmento, attr_seg in overlays:
            safe_addstr(stdscr, row, col, segmento, attr_seg)
        row += 1
    for texto, attr, overlays in build_bussola_linhas(estado):
        safe_addstr(stdscr, row, 0, texto, attr)
        for col, segmento, attr_seg in overlays:
            safe_addstr(stdscr, row, col, segmento, attr_seg)
        row += 1
    row += 1

    safe_addstr(stdscr, row, 0, "== MAPA ==", _curses.A_UNDERLINE)
    row += 1
    for texto, attr, overlays in build_mapa_linhas(estado):
        safe_addstr(stdscr, row, 0, texto, attr)
        for col, segmento, attr_seg in overlays:
            safe_addstr(stdscr, row, col, segmento, attr_seg)
        row += 1
    for texto, attr, overlays in build_vigia_linhas(estado):
        safe_addstr(stdscr, row, 0, texto, attr)
        row += 1

    log_lines = list(estado.log)[-4:]
    base = max_y - (2 + len(log_lines) + 2)
    safe_addstr(stdscr, base, 0, "LOG", _curses.A_UNDERLINE)
    for i, linha in enumerate(log_lines):
        safe_addstr(stdscr, base + 1 + i, 0, linha, cor_log(estado, linha))
    safe_addstr(stdscr, max_y - 2, 0, "-" * min(max_x - 1, 78))
    if estado.hotkeys_ativo:
        safe_addstr(stdscr, max_y - 2, 0, f"FOCO: {_descrever_foco(estado)}")
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
    col = 0
    parte1 = "CLI PIRATES | "
    safe_addstr(stdscr, row, col, parte1, cor_header(estado))
    col += len(parte1)
    tipo_nome = estado.jogador.tipo_nome.upper()
    safe_addstr(stdscr, row, col, tipo_nome, cor_tipo_navio(estado))
    col += len(tipo_nome)
    modo_label = " | COMBATE" if getattr(estado_mundo, 'em_combate', False) else " | NAVEGACAO"
    parte2 = f"{modo_label} | tempo: {estado.tempo:5.1f}s"
    safe_addstr(stdscr, row, col, parte2, cor_header(estado))
    col += len(parte2)
    from ..core.notoriedade import titulo as notoriedade_titulo, icone as notoriedade_icone
    notoriedade = getattr(estado_mundo, 'notoriedade', 0.0)
    icone_not = notoriedade_icone(notoriedade, unicode=estado.graficos_unicode)
    parte_not = f" | {icone_not} {notoriedade_titulo(notoriedade)} ({notoriedade:.0f})"
    safe_addstr(stdscr, row, col, parte_not, cor_header(estado))
    col += len(parte_not)
    if estado.modo_adm:
        attr_adm = (_curses.color_pair(COR_AMARELO) | _curses.A_BOLD) if _curses else 0
        safe_addstr(stdscr, row, col, " | [ADM]", attr_adm)
    row += 1
    safe_addstr(stdscr, row, 0, "-" * min(max_x - 1, 78))
    row += 1

    safe_addstr(stdscr, row, 0, "SEU NAVIO",
                _curses.A_UNDERLINE)
    safe_addstr(stdscr, row, RIGHT_X, "CANHOES", _curses.A_UNDERLINE)
    safe_addstr(stdscr, row, VELAS_X, "VELAS", _curses.A_UNDERLINE)
    safe_addstr(stdscr, row, PORAO_X, "PORAO", _curses.A_UNDERLINE)
    row += 1
    topo_colunas = row

    esquerda = build_navio_diagrama(estado)
    canhoes_linhas = build_canhoes_linhas(estado)
    roster = montar_tripulacao(estado)
    direita = canhoes_linhas + [("", 0), ("TRIPULACAO:", 0)] + [
        (
            f"{SIMB_TRIPULANTE} {tid:4s} {(tarefa + ': ' + detalhe) if detalhe else tarefa}",
            cor_tarefa(estado, tarefa),
        )
        for tid, tarefa, detalhe in roster
    ]
    porao_linhas = build_porao_linhas(estado.jogador)
    velas_linhas = build_velas_linhas(estado)
    maxlen = max(len(esquerda), len(direita), len(porao_linhas), len(velas_linhas))
    for i in range(maxlen):
        rowi = topo_colunas + i
        if i < len(esquerda):
            texto, attr, overlays = esquerda[i]
            safe_addstr(stdscr, rowi, 0, texto, attr)
            for col_o, segmento, attr_seg in overlays:
                safe_addstr(stdscr, rowi, col_o, segmento, attr_seg)
        if i < len(direita):
            texto, attr = direita[i]
            safe_addstr(stdscr, rowi, RIGHT_X, texto, attr)
        if i < len(porao_linhas):
            texto, attr = porao_linhas[i]
            safe_addstr(stdscr, rowi, PORAO_X, texto, attr)
        if i < len(velas_linhas):
            texto, attr = velas_linhas[i]
            safe_addstr(stdscr, rowi, VELAS_X, texto, attr)

    row = topo_colunas + maxlen + 1

    em_combate = getattr(estado_mundo, 'em_combate', False)

    safe_addstr(stdscr, row, 0, f"VISAO DO CAPITAO {SIMB_CAPITAO}", _curses.A_UNDERLINE)
    row += 1
    _vista_fn = build_vista_linhas if em_combate else build_vista_mundo_linhas
    _vista_args = (estado,) if em_combate else (estado_mundo, estado)
    for texto, attr, overlays in _vista_fn(*_vista_args):
        safe_addstr(stdscr, row, 0, texto, attr)
        for col, segmento, attr_seg in overlays:
            safe_addstr(stdscr, row, col, segmento, attr_seg)
        row += 1
    for texto, attr, overlays in build_bussola_linhas(estado):
        safe_addstr(stdscr, row, 0, texto, attr)
        for col, segmento, attr_seg in overlays:
            safe_addstr(stdscr, row, col, segmento, attr_seg)
        row += 1
    row += 1
    if estado_mundo.mapa_mundo_visivel:
        for texto, attr, overlays in build_mapa_mundo_linhas(estado_mundo, estado):
            safe_addstr(stdscr, row, 0, texto, attr)
            for col, segmento, attr_seg in overlays:
                safe_addstr(stdscr, row, col, segmento, attr_seg)
            row += 1
    elif em_combate:
        safe_addstr(stdscr, row, 0, "== MAPA ==", _curses.A_UNDERLINE)
        row += 1
        for texto, attr, overlays in build_mapa_linhas(estado):
            safe_addstr(stdscr, row, 0, texto, attr)
            for col, segmento, attr_seg in overlays:
                safe_addstr(stdscr, row, col, segmento, attr_seg)
            row += 1
        for texto, attr, overlays in build_vigia_linhas(estado):
            safe_addstr(stdscr, row, 0, texto, attr)
            row += 1
    else:
        safe_addstr(stdscr, row, 0, "== MAPA DE NAVEGACAO ==", _curses.A_UNDERLINE)
        row += 1
        for texto, attr, overlays in build_mapa_navegacao_linhas(estado_mundo, estado):
            safe_addstr(stdscr, row, 0, texto, attr)
            for col, segmento, attr_seg in overlays:
                safe_addstr(stdscr, row, col, segmento, attr_seg)
            row += 1
        for texto, attr, overlays in build_vigia_mundo_linhas(estado_mundo):
            safe_addstr(stdscr, row, 0, texto, attr)
            row += 1

    log_lines = list(estado.log)[-4:]
    base = max_y - (2 + len(log_lines) + 2)
    safe_addstr(stdscr, base, 0, "LOG", _curses.A_UNDERLINE)
    for i, linha in enumerate(log_lines):
        safe_addstr(stdscr, base + 1 + i, 0, linha, cor_log(estado, linha))
    safe_addstr(stdscr, max_y - 2, 0, "-" * min(max_x - 1, 78))
    if estado.hotkeys_ativo:
        safe_addstr(stdscr, max_y - 2, 0, f"FOCO: {_descrever_foco(estado)}")
    safe_addstr(stdscr, max_y - 1, 0, f"> {buffer_entrada}", _curses.A_REVERSE)

    stdscr.refresh()
