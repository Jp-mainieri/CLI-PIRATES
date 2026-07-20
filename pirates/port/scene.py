"""scene.py – Cena do porto: navegação WASD, lojas e doca (Tier 3b)."""

from __future__ import annotations

try:
    import curses as _curses
except ImportError:
    _curses = None  # type: ignore[assignment]

from ..ui.renderer import safe_addstr
from ..ui.hud import build_porao_linhas, build_porao_inventario_linhas, build_navio_diagrama
from .lojas import (
    preco_reparo, preco_reabastecer, preco_venda,
    preco_upgrade_nivel, nivel_atual_upgrade, nivel_max_upgrade,
    comprar_barril, reabastecer_barril, vender_barril, reparo_instantaneo,
    comprar_navio_loja, renomear_navio_loja, aplicar_upgrade, comprar_item_topo,
    transferir_barril_frota, trocar_vela, instalar_vela_auxiliar,
    UPGRADE_NIVEIS_MAX,
)
from ..constants import (
    PRECO_NAVIO_NOVO, PRECO_BARRIL_NOVO, PRECO_RENOMEAR,
    PRECO_TRANSFERENCIA_FROTA,
    NAVIO_TIPOS, SIMB_CAPITAO, POLL_MS,
    COR_VERMELHO, COR_VERDE, COR_AMARELO, COR_JOGADOR, COR_MAR,
    PRECO_ITENS_TOPO, FAIXA_MINIMA_ITEM_TOPO,
    TIPOS_VELA, PRECO_TROCA_VELA, PRECO_INSTALAR_AUX,
)
from ..core.notoriedade import faixa_index
from ..core.state import sincronizar_crew_com_navio_ativo

# ---------------------------------------------------------------------------
# Layout da grade do porto
#
# GRID_W = 10 células lógicas de 3 chars cada → 30 chars visuais
# GRID_H = 12 linhas
# Célula k → string cols k*3 .. k*3+2 → visual col base+k*3 .. base+k*3+2
# Paredes: col 0 (esquerda) e col 9 (direita) — bloqueiam movimento
# Jogador: cols 1..8, rows 1..10
# ---------------------------------------------------------------------------

GRID_W = 5   # células lógicas
GRID_H = 12   # linhas

# Posições lógicas dos elementos fixos
_DOCA_COL, _DOCA_ROW     = 2,10 
_CAP_INICIO_COL, _CAP_INICIO_ROW = 2, 8

# Entradas das lojas: posição lógica exata onde o capitão aciona a loja
_ENTRADAS: dict[str, tuple[int, int]] = {
    "polvora": (1, 3),   # à direita de [P] (célula 0, linha 1)
    "bolas":   (3, 3),   # à esquerda de [O] (célula 9, linha 1)
    "tabuas":  (1, 6),   # à direita de [T] (célula 0, linha 4)
    "navios":  (3, 6),   # à esquerda de [N] (célula 9, linha 4)
}

# ---------------------------------------------------------------------------
# Grid background  (cada linha tem exatamente 30 chars = 10 células × 3)
# ---------------------------------------------------------------------------
#
#  Legenda de células:
#    [P]/[O]/[T]/[N]  – loja embutida na parede
#     * (centro da célula 1 e 8) – entrada da loja, dentro da praça
#   | |  – parede sólida (bloqueia movimento)
#   ___  – casco do navio na doca (célula 4, linha 8)
#    |   – caminho até a doca (célula 4, linhas 9-10)
#
_GRID_BG: list[str] = [
    "               ",  # 12 fundo (padding)
    "|=============|",  # 0  topo (padding)
    "| |         | |",  # 0  topo (padding)
    "[P] *     * [O]",  # 1  lojas top + entradas (* em cell 1 e 8)
    "| |         | |",  # 2  paredes
    "| |         | |",  # 3  praça (capitão começa aqui)
    "[T] *     * [N]",  # 4  lojas bottom + entradas (mais para cima)
    "| |         | |",  # 5  paredes
    "| |         | |",  # 6  praça
    "| |    *    | |",  # 9  caminho doca
    "|=====[Z]=====|",  # 10 rótulo doca
    "~~~~~~/^\\~~~~~~",  # 11 fundo (mar)
]


def capitao_perto_de(cap_col: int, cap_row: int, alvo_col: int, alvo_row: int) -> bool:
    """True se o capitão está a distância ≤1 célula do alvo (Manhattan)."""
    return abs(cap_col - alvo_col) + abs(cap_row - alvo_row) <= 1


def _prox_entrada(cap_col: int, cap_row: int) -> str | None:
    """Entrada exata: o capitão deve estar NA célula da entrada."""
    for nome, (ec, er) in _ENTRADAS.items():
        if cap_col == ec and cap_row == er:
            return nome
    return None


def _proxima_doca(cap_col: int, cap_row: int) -> bool:
    return capitao_perto_de(cap_col, cap_row, _DOCA_COL, _DOCA_ROW)


# ---------------------------------------------------------------------------
# Rendering da grade
# ---------------------------------------------------------------------------

def _desenhar_porto(stdscr, cap_col: int, cap_row: int, porto_nome: str,
                    navio_nome: str, msg: str, estado, vista: str = "hud") -> None:
    if _curses is None:
        return
    stdscr.erase()
    max_y, max_x = stdscr.getmaxyx()
    cores = estado.cores_ativo and _curses is not None

    # Título
    titulo = f"CLI PIRATES -- PORTO DE {porto_nome.upper()}"
    navio_info = f"Navio ativo: {navio_nome}"
    safe_addstr(stdscr, 0, 0, "-" * min(max_x - 1, 78))
    safe_addstr(stdscr, 1, 2, titulo, _curses.A_BOLD)
    safe_addstr(stdscr, 1, max_x - len(navio_info) - 2, navio_info)
    safe_addstr(stdscr, 2, 0, "-" * min(max_x - 1, 78))

    # Grade
    base_row = 3
    base_col = 4
    for r, linha in enumerate(_GRID_BG):
        safe_addstr(stdscr, base_row + r, base_col, linha)

    # Cores das lojas: visual col = base_col + célula_lógica * 3
    # [P] e [T] em célula 0 → visual col base_col + 0 = 4
    # [O] e [N] em célula 9 → visual col base_col + 27 = 31
    _lojas_info = [
        ("[P]", base_row + 3,  base_col + 0,  COR_VERMELHO),
        ("[O]", base_row + 3,  base_col + 12, None),           # bolas: só bold
        ("[T]", base_row + 6,  base_col + 0,  COR_VERDE),
        ("[N]", base_row + 6,  base_col + 12, COR_JOGADOR),
        ("[Z]", base_row + 10,  base_col + 6, COR_MAR),
    ]
    for texto, row, col, par in _lojas_info:
        if cores and par is not None:
            attr = _curses.color_pair(par) | _curses.A_BOLD
        else:
            attr = _curses.A_BOLD
        safe_addstr(stdscr, row, col, texto, attr)

    # Capitão em amarelo+bold; cada célula = 3 chars → visual col = base_col + cap_col*3
    cap_attr = (_curses.color_pair(COR_AMARELO) | _curses.A_BOLD) if cores else _curses.A_BOLD
    safe_addstr(stdscr, base_row + cap_row, base_col + cap_col * 3, SIMB_CAPITAO, cap_attr)

    # Painel inferior: HUD ou porão
    sep_row = base_row + GRID_H + 1
    label = "HUD" if vista == "hud" else "PORAO"
    safe_addstr(stdscr, sep_row, 0, f"[{label}]" + "-" * max(0, min(max_x - 1, 78) - 6 - len(label)))
    painel_row = sep_row + 1

    if vista == "hud":
        # casco/mastro/vela/roda/agua/moral — descarta overlays (nao usados aqui)
        linhas = [(t, a) for t, a, _ov in build_navio_diagrama(estado)[:6]]
    else:
        linhas = build_porao_inventario_linhas(estado.jogador, cores=cores)

    for texto, attr in linhas:
        if painel_row >= max_y - 4:
            break
        safe_addstr(stdscr, painel_row, 0, texto, attr)
        painel_row += 1

    # Mensagem + rodapé
    log_row = max_y - 4
    safe_addstr(stdscr, log_row, 0, "-" * min(max_x - 1, 78))
    if msg:
        safe_addstr(stdscr, log_row + 1, 2, msg)
    safe_addstr(stdscr, max_y - 2, 0, "-" * min(max_x - 1, 78))
    safe_addstr(stdscr, max_y - 1, 0,
                "WASD: mover   TAB: alternar vista   ESC|[Z]: zarpar")
    stdscr.refresh()


# ---------------------------------------------------------------------------
# Sub-loops de loja
# ---------------------------------------------------------------------------

def _input_texto(stdscr, prompt: str, max_y: int, max_x: int) -> str:
    """Campo de texto simples (ENTER confirma, ESC cancela → '')."""
    buf = ""
    _curses.curs_set(1)
    while True:
        safe_addstr(stdscr, max_y - 3, 0, " " * min(max_x - 1, 78))
        safe_addstr(stdscr, max_y - 3, 0, f"{prompt}{buf}_")
        stdscr.refresh()
        ch = stdscr.getch()
        if ch in (_curses.KEY_ENTER, 10, 13):
            break
        elif ch == 27:
            buf = ""
            break
        elif ch in (_curses.KEY_BACKSPACE, 127, 8):
            buf = buf[:-1]
        elif 32 <= ch <= 126:
            buf += chr(ch)
    _curses.curs_set(0)
    return buf.strip()


def _menu_simples(stdscr, titulo: str, opcoes: list[str],
                  rodape: str, estado, extra_linhas: list[str] | None = None,
                  linha_hover_fn=None) -> int:
    """Menu navegável. TAB abre inventário completo. Retorna índice ou -1 (ESC).

    Args:
        linha_hover_fn: Se fornecida, chamada a cada frame com o índice do
            cursor atual (`int -> list[str]`) — retorno é exibido abaixo
            das opções, atualizado conforme o jogador navega. Diferente
            de `extra_linhas` (estático, calculado uma vez antes do loop).
    """
    cursor = 0
    while True:
        stdscr.erase()
        max_y, max_x = stdscr.getmaxyx()
        safe_addstr(stdscr, 0, 0, "-" * min(max_x - 1, 78))
        safe_addstr(stdscr, 1, 2, titulo, _curses.A_BOLD)
        safe_addstr(stdscr, 2, 0, "-" * min(max_x - 1, 78))

        row = 4
        for i, op in enumerate(opcoes):
            prefixo = "> " if i == cursor else "  "
            attr = _curses.A_REVERSE if i == cursor else 0
            safe_addstr(stdscr, row, 4, prefixo + op, attr)
            row += 1

        if extra_linhas:
            row += 1
            for linha in extra_linhas:
                safe_addstr(stdscr, row, 4, linha)
                row += 1

        if linha_hover_fn is not None:
            row += 1
            for linha in linha_hover_fn(cursor):
                safe_addstr(stdscr, row, 4, linha)
                row += 1

        # Painel de porão (formato resumido para caber no espaço)
        pr = max_y - 9
        safe_addstr(stdscr, pr, 0, "-" * min(max_x - 1, 78))
        pr += 1
        for texto, attr in build_porao_linhas(estado.jogador):
            if pr >= max_y - 5:
                break
            safe_addstr(stdscr, pr, 0, texto, attr)
            pr += 1

        ouro = estado.jogador.porao.total("ouro")
        safe_addstr(stdscr, max_y - 4, 0, f"Ouro disponivel: {ouro:.1f}")
        safe_addstr(stdscr, max_y - 3, 0, "-" * min(max_x - 1, 78))
        safe_addstr(stdscr, max_y - 2, 0,
                    rodape + "   TAB: inventario")
        stdscr.refresh()

        ch = stdscr.getch()
        if ch == 27:
            return -1
        elif ch == ord('\t'):
            from ..ui.inventario import abrir_inventario
            abrir_inventario(stdscr, estado.jogador, cores=estado.cores_ativo)
        elif ch == _curses.KEY_UP:
            cursor = max(0, cursor - 1)
        elif ch == _curses.KEY_DOWN:
            cursor = min(len(opcoes) - 1, cursor + 1)
        elif ch in (ord(' '), _curses.KEY_ENTER, 10, 13):
            return cursor


def _selecionar_barril(stdscr, navio, tipo: str, estado) -> int | None:
    """Inventário interativo: seleciona barril do `tipo`. Retorna índice real ou None."""
    barris_tipo = [(i, b) for i, b in enumerate(navio.porao.barris) if b.tipo == tipo]
    if not barris_tipo:
        return None
    from ..core.porao import capacidade_barril
    from ..ui.colors import cor_recurso
    cores = estado.cores_ativo and _curses is not None
    cap_b = capacidade_barril(tipo)
    cursor = 0
    while True:
        stdscr.erase()
        max_y, max_x = stdscr.getmaxyx()
        safe_addstr(stdscr, 0, 0, "-" * min(max_x - 1, 78))
        safe_addstr(stdscr, 1, 2, f"SELECIONAR BARRIL DE {tipo.upper()}", _curses.A_BOLD)
        safe_addstr(stdscr, 2, 0, "-" * min(max_x - 1, 78))
        row = 4
        for ci, (i, b) in enumerate(barris_tipo):
            prefixo = " > " if ci == cursor else "   "
            sel_attr = _curses.A_REVERSE if ci == cursor else 0
            pct = b.quantidade / cap_b if cap_b > 0 else 0.0
            n_h = int(round(pct * 10))
            barra_str = "#" * n_h + "-" * (10 - n_h)
            linha = f"{prefixo}{i+1:2d}.  {b.tipo:7s}  {b.quantidade:4.0f} / {cap_b:2.0f}u  [{barra_str}]"
            cor = cor_recurso(cores, b.tipo)
            safe_addstr(stdscr, row, 0, linha, sel_attr | cor if not sel_attr else sel_attr)
            row += 1
        safe_addstr(stdscr, max_y - 2, 0,
                    "CIMA/BAIXO: navegar   ENTER/ESPACO: selecionar   ESC: cancelar")
        stdscr.refresh()
        ch = stdscr.getch()
        if ch == 27:
            return None
        elif ch == _curses.KEY_UP:
            cursor = max(0, cursor - 1)
        elif ch == _curses.KEY_DOWN:
            cursor = min(len(barris_tipo) - 1, cursor + 1)
        elif ch in (ord(' '), _curses.KEY_ENTER, 10, 13):
            return barris_tipo[cursor][0]


def _selecionar_barril_qualquer_tipo(stdscr, navio, estado) -> int | None:
    """Inventário interativo: seleciona qualquer barril do navio (sem
    filtro de tipo). Retorna índice real ou None."""
    barris = list(enumerate(navio.porao.barris))
    if not barris:
        return None
    from ..core.porao import capacidade_barril
    from ..ui.colors import cor_recurso
    cores = estado.cores_ativo and _curses is not None
    cursor = 0
    while True:
        stdscr.erase()
        max_y, max_x = stdscr.getmaxyx()
        safe_addstr(stdscr, 0, 0, "-" * min(max_x - 1, 78))
        safe_addstr(stdscr, 1, 2, "SELECIONAR BARRIL PARA TRANSFERIR", _curses.A_BOLD)
        safe_addstr(stdscr, 2, 0, "-" * min(max_x - 1, 78))
        row = 4
        for ci, (i, b) in enumerate(barris):
            cap_b = capacidade_barril(b.tipo)
            prefixo = " > " if ci == cursor else "   "
            sel_attr = _curses.A_REVERSE if ci == cursor else 0
            pct = b.quantidade / cap_b if cap_b > 0 else 0.0
            n_h = int(round(pct * 10))
            barra_str = "#" * n_h + "-" * (10 - n_h)
            linha = f"{prefixo}{i+1:2d}.  {b.tipo:7s}  {b.quantidade:4.0f} / {cap_b:2.0f}u  [{barra_str}]"
            cor = cor_recurso(cores, b.tipo)
            safe_addstr(stdscr, row, 0, linha, sel_attr | cor if not sel_attr else sel_attr)
            row += 1
        safe_addstr(stdscr, max_y - 2, 0,
                    "CIMA/BAIXO: navegar   ENTER/ESPACO: selecionar   ESC: cancelar")
        stdscr.refresh()
        ch = stdscr.getch()
        if ch == 27:
            return None
        elif ch == _curses.KEY_UP:
            cursor = max(0, cursor - 1)
        elif ch == _curses.KEY_DOWN:
            cursor = min(len(barris) - 1, cursor + 1)
        elif ch in (ord(' '), _curses.KEY_ENTER, 10, 13):
            return barris[cursor][0]


def _loja_recurso(stdscr, navio, tipo: str, estado) -> None:
    """Sub-loop da loja de recurso (pólvora/bolas/tábuas)."""
    nome_exibido = {"polvora": "POLVORA", "bolas": "BOLAS", "tabuas": "TABUAS"}.get(tipo, tipo.upper())
    barril_sel: int | None = None
    msg = ""

    while True:
        navio_ativo = estado.jogador
        barril_sel_info = ""
        reab_str = "Reabastecer barril selecionado ........... (TAB: escolher)"
        vend_str = "Vender barril selecionado ................. (TAB: escolher)"
        if barril_sel is not None and barril_sel < len(navio_ativo.porao.barris):
            b = navio_ativo.porao.barris[barril_sel]
            if b.tipo == tipo:
                falta = 25.0 - b.quantidade
                custo_reab = preco_reabastecer(falta)
                custo_venda = preco_venda(b)
                barril_sel_info = f"{tipo} #{barril_sel + 1} ({b.quantidade:.1f}/25)"
                reab_str = f"Reabastecer barril selecionado ........... {custo_reab:.1f} ouro"
                vend_str = f"Vender barril selecionado ................. {custo_venda:.1f} ouro"
            else:
                barril_sel = None

        opcoes = [
            f"Comprar barril novo cheio ................. {PRECO_BARRIL_NOVO:.1f} ouro",
            reab_str,
            vend_str,
        ]
        if tipo == "tabuas":
            preco_r = preco_reparo(navio_ativo)
            opcoes.append(f"Reparo instantaneo completo ............... {preco_r:.1f} ouro")
        opcoes.append("[Voltar]")

        extra = [f"Barril selecionado: {barril_sel_info}" if barril_sel_info else "Barril selecionado: (nenhum — use TAB)"]
        if msg:
            extra.append(f">> {msg}")

        escolha = _menu_simples(
            stdscr, f"LOJA DE {nome_exibido}", opcoes,
            "CIMA/BAIXO: navegar  ESPACO: confirmar  ESC: voltar",
            estado, extra_linhas=extra,
        )
        msg = ""

        if escolha == -1 or escolha == len(opcoes) - 1:
            return

        elif escolha == 0:  # Comprar barril novo
            ok, m = comprar_barril(navio_ativo, tipo)
            msg = m

        elif escolha == 1:  # Reabastecer
            if barril_sel is None or barril_sel >= len(navio_ativo.porao.barris):
                barril_sel = _selecionar_barril(stdscr, navio_ativo, tipo, estado)
                if barril_sel is None:
                    msg = f"Nenhum barril de {tipo} selecionado."
                    continue
            ok, m = reabastecer_barril(navio_ativo, barril_sel, tipo)
            msg = m
            if ok:
                barril_sel = None

        elif escolha == 2:  # Vender
            if barril_sel is None or barril_sel >= len(navio_ativo.porao.barris):
                barril_sel = _selecionar_barril(stdscr, navio_ativo, tipo, estado)
                if barril_sel is None:
                    msg = f"Nenhum barril de {tipo} selecionado."
                    continue
            ok, m = vender_barril(navio_ativo, barril_sel)
            msg = m
            if ok:
                barril_sel = None

        elif tipo == "tabuas" and escolha == 3:  # Reparo instantâneo
            ok, m = reparo_instantaneo(navio_ativo)
            msg = m


def _loja_navios(stdscr, frota, porto_id: int, tipo_navio_atual: str, estado, estado_mundo) -> None:
    """Sub-loop da loja de navios."""
    msg = ""
    while True:
        navio_ativo = estado.jogador
        opcoes = [
            "Comprar navio novo ......................................",
            "Trocar de navio ativo (frota) ...........................",
            f"Transferir carga entre navios (frota) .................. {PRECO_TRANSFERENCIA_FROTA:.0f} ouro",
            f"Renomear navio atual .................................... {PRECO_RENOMEAR:.1f} ouro",
            "Upgrades do navio atual .................................",
            "Itens de topo ............................................",
            "Velas do navio atual .....................................",
            "[Voltar]",
        ]
        extra = [f">> {msg}"] if msg else None
        escolha = _menu_simples(
            stdscr, "LOJA DE NAVIOS", opcoes,
            "CIMA/BAIXO: navegar  ESPACO: confirmar  ESC: voltar",
            estado, extra_linhas=extra,
        )
        msg = ""
        if escolha in (-1, len(opcoes) - 1):
            return

        elif escolha == 0:
            msg = _fluxo_comprar_navio(stdscr, frota, porto_id, navio_ativo, estado)

        elif escolha == 1:
            msg = _fluxo_trocar_navio(stdscr, frota, porto_id, estado, estado_mundo)

        elif escolha == 2:
            msg = _fluxo_transferir_carga(stdscr, frota, porto_id, estado)

        elif escolha == 3:  # Renomear
            stdscr.erase()
            max_y, max_x = stdscr.getmaxyx()
            safe_addstr(stdscr, 1, 2, "RENOMEAR NAVIO", _curses.A_BOLD)
            stdscr.refresh()
            novo_nome = _input_texto(stdscr, "Novo nome: ", max_y, max_x)
            if novo_nome:
                idx = frota.indice_ativo
                ok, m = renomear_navio_loja(frota, idx, novo_nome, navio_ativo)
                msg = m
                if ok and frota.ativo() is not None:
                    navio_ativo.nome = novo_nome
            else:
                msg = "Cancelado."

        elif escolha == 4:
            _loja_upgrades(stdscr, navio_ativo, tipo_navio_atual, estado)

        elif escolha == 5:
            _loja_itens_topo(stdscr, navio_ativo, estado_mundo, estado)

        elif escolha == 6:
            _loja_velas(stdscr, navio_ativo, tipo_navio_atual, estado)


def _fluxo_comprar_navio(stdscr, frota, porto_id: int, navio_ativo, estado) -> str:
    def _preco_atual(tipo: str) -> float:
        navios_do_tipo = sum(1 for n in frota.navios if n.tipo == tipo)
        return float(PRECO_NAVIO_NOVO[tipo]) * (1.4 ** navios_do_tipo)

    tipos = [
        ("chalupa",   f"Chalupa    .... {_preco_atual('chalupa'):.0f} ouro"),
        ("brigantim", f"Brigantim  .... {_preco_atual('brigantim'):.0f} ouro"),
        ("galeao",    f"Galeao     .... {_preco_atual('galeao'):.0f} ouro"),
    ]
    opcoes = [t[1] for t in tipos] + ["[Voltar]"]
    escolha = _menu_simples(stdscr, "COMPRAR NAVIO NOVO", opcoes,
                            "CIMA/BAIXO: navegar  ESPACO: escolher  ESC: voltar", estado)
    if escolha in (-1, len(opcoes) - 1):
        return "Cancelado."
    tipo_escolhido, _ = tipos[escolha]
    preco = _preco_atual(tipo_escolhido)
    if navio_ativo.porao.total("ouro") < preco:
        return f"Ouro insuficiente (precisa {preco:.0f})."
    stdscr.erase()
    max_y, max_x = stdscr.getmaxyx()
    safe_addstr(stdscr, 1, 2, "COMPRAR NAVIO NOVO", _curses.A_BOLD)
    safe_addstr(stdscr, 3, 4,
                f"Navio escolhido: {NAVIO_TIPOS[tipo_escolhido]['navio']} ({preco:.0f} ouro)")
    stdscr.refresh()
    nome = _input_texto(stdscr, "Nome do navio: ", max_y, max_x)
    if not nome:
        return "Cancelado."
    ok, m = comprar_navio_loja(frota, tipo_escolhido, nome, porto_id, navio_ativo)
    return m


def _fluxo_trocar_navio(stdscr, frota, porto_id: int, estado, estado_mundo) -> str:
    navios_porto = frota.navios_no_porto(porto_id)
    if not navios_porto:
        return "Nenhum outro navio ancorado aqui."
    opcoes = []
    indices_reais = []
    for np_obj in navios_porto:
        idx_real = frota.navios.index(np_obj)
        casco = np_obj.navio.partes.get('casco', 100.0)
        ativo_str = " [ATIVO]" if idx_real == frota.indice_ativo else ""
        opcoes.append(f"{np_obj.nome} ({NAVIO_TIPOS.get(np_obj.tipo, {}).get('navio', '?')}) casco {casco:.0f}%{ativo_str}")
        indices_reais.append(idx_real)
    opcoes.append("[Voltar]")
    escolha = _menu_simples(stdscr, "SUA FROTA EM PORTO", opcoes,
                            "CIMA/BAIXO: navegar  ESPACO: trocar  ESC: voltar", estado)
    if escolha in (-1, len(opcoes) - 1):
        return "Cancelado."
    idx_real = indices_reais[escolha]
    if idx_real == frota.indice_ativo:
        return "Ja e o navio ativo."
    ok = frota.trocar_ativo(idx_real, porto_id)
    if ok:
        novo = frota.ativo()
        if novo is not None:
            estado.jogador = novo.navio
            sincronizar_crew_com_navio_ativo(estado, novo.tipo)
            estado_mundo.tipo_navio = novo.tipo
        return f"Navio trocado para {frota.ativo().nome if frota.ativo() else '?'}."
    return "Nao foi possivel trocar o navio."


def _fluxo_transferir_carga(stdscr, frota, porto_id: int, estado) -> str:
    navio_ativo = estado.jogador
    navios_porto = frota.navios_no_porto(porto_id)
    if not navios_porto:
        return "Nenhum outro navio ancorado aqui pra transferir carga."

    opcoes = [
        f"{np_obj.nome} ({NAVIO_TIPOS.get(np_obj.tipo, {}).get('navio', '?')})"
        for np_obj in navios_porto
    ]
    opcoes.append("[Voltar]")
    escolha = _menu_simples(stdscr, "TRANSFERIR CARGA — ESCOLHA O OUTRO NAVIO", opcoes,
                            "CIMA/BAIXO: navegar  ESPACO: escolher  ESC: voltar", estado)
    if escolha in (-1, len(opcoes) - 1):
        return "Cancelado."
    outro_nome = navios_porto[escolha].nome
    outro_navio = navios_porto[escolha].navio

    opcoes_dir = [
        f"Enviar para {outro_nome} (do navio ativo)",
        f"Receber de {outro_nome} (para o navio ativo)",
        "[Voltar]",
    ]
    dir_escolha = _menu_simples(stdscr, "DIRECAO DA TRANSFERENCIA", opcoes_dir,
                                "CIMA/BAIXO: navegar  ESPACO: escolher  ESC: voltar", estado)
    if dir_escolha in (-1, 2):
        return "Cancelado."
    origem, destino = (navio_ativo, outro_navio) if dir_escolha == 0 else (outro_navio, navio_ativo)

    idx = _selecionar_barril_qualquer_tipo(stdscr, origem, estado)
    if idx is None:
        return "Nenhum barril selecionado."

    ok, m = transferir_barril_frota(origem, destino, idx)
    return m


def _loja_upgrades(stdscr, navio, tipo_navio: str, estado) -> None:
    """Sub-loop de upgrades do navio."""
    CHAVES = ["casco_max", "cooldown", "porao_slot", "tripulante_extra",
              "velocidade_giro", "alcance_canhao", "capacidade_barril_ouro"]
    LABELS = {
        "casco_max":              "+10 HP max de casco",
        "cooldown":               "-10% cooldown de canhao",
        "porao_slot":             "+1 slot de porao",
        "tripulante_extra":       "+1 tripulante extra",
        "velocidade_giro":        "+10% velocidade/giro",
        "alcance_canhao":         "+50m alcance de canhao",
        "capacidade_barril_ouro": "+10 capacidade barril de ouro",
    }
    msg = ""
    while True:
        opcoes = []
        for chave in CHAVES:
            nivel = nivel_atual_upgrade(navio, chave)
            max_n = nivel_max_upgrade(tipo_navio, chave)
            if nivel >= max_n:
                opcoes.append(f"{LABELS[chave]} ... Nivel {nivel}/{max_n} (MAX)  ---")
            else:
                preco = preco_upgrade_nivel(chave, nivel)
                opcoes.append(
                    f"{LABELS[chave]} ... Nivel {nivel}/{max_n} -> {nivel+1}/{max_n}  {preco:.1f} ouro"
                )
        opcoes.append("[Voltar]")
        extra = [f">> {msg}"] if msg else None
        escolha = _menu_simples(
            stdscr, f"UPGRADES: {navio.tipo_nome.upper()}", opcoes,
            "CIMA/BAIXO: navegar  ESPACO: comprar  ESC: voltar",
            estado, extra_linhas=extra,
        )
        msg = ""
        if escolha in (-1, len(opcoes) - 1):
            return
        chave = CHAVES[escolha]
        ok, m = aplicar_upgrade(navio, tipo_navio, chave, estado)
        msg = m


def _loja_velas(stdscr, navio, tipo_navio: str, estado) -> None:
    """Sub-loop de troca/instalação de velas (doc10_customizacao_vela.md)."""
    msg = ""
    while True:
        opcoes = []
        for i, slot in enumerate(navio.slots_vela):
            tipo_atual = slot["tipo"] or "vazio"
            opcoes.append(f"[{i}] {slot['local']}: {tipo_atual}")
        opcoes.append("[Voltar]")
        extra = [f">> {msg}"] if msg else None
        escolha = _menu_simples(
            stdscr, f"VELAS: {navio.tipo_nome.upper()}", opcoes,
            "CIMA/BAIXO: navegar  ESPACO: escolher slot  ESC: voltar",
            estado, extra_linhas=extra,
        )
        msg = ""
        if escolha in (-1, len(opcoes) - 1):
            return

        slot = navio.slots_vela[escolha]
        e_aux = slot["local"].startswith("aux")
        tipos_validos = [
            t for t, d in TIPOS_VELA.items() if d["auxiliar"] == e_aux
        ]

        def _preco(t: str) -> float:
            return PRECO_INSTALAR_AUX[t] if e_aux else PRECO_TROCA_VELA[tipo_navio]

        sub_opcoes = [
            f"{'Instalar' if e_aux else 'Trocar para'} {t} .... {_preco(t):.0f} ouro"
            for t in tipos_validos
        ]
        sub_opcoes.append("[Voltar]")

        def _hover(idx: int, _tipos=tipos_validos) -> list[str]:
            if not (0 <= idx < len(_tipos)):
                return []
            d = TIPOS_VELA[_tipos[idx]]
            ef = d["eficiencia_vento"]
            return [
                f"zona morta {ef['zona_morta']:.2f}  bolina {ef['bolina']:.2f}  "
                f"traves {ef['traves']:.2f}  popa {ef['popa']:.2f}",
                f"bonus fixo +{d['bonus_fixo']*100:.0f}%  bonus curva +{d['bonus_curva']*100:.0f}%",
            ]

        sub_escolha = _menu_simples(
            stdscr, f"SLOT {escolha}: {slot['local']}", sub_opcoes,
            "CIMA/BAIXO: navegar  ESPACO: comprar  ESC: voltar", estado,
            linha_hover_fn=_hover,
        )
        if sub_escolha in (-1, len(sub_opcoes) - 1):
            continue
        novo_tipo = tipos_validos[sub_escolha]
        if e_aux:
            ok, m = instalar_vela_auxiliar(navio, escolha, novo_tipo)
        else:
            ok, m = trocar_vela(navio, tipo_navio, escolha, novo_tipo)
        msg = m


def _loja_itens_topo(stdscr, navio, estado_mundo, estado) -> None:
    """Sub-loop dos itens de topo, desbloqueados por faixa de notoriedade.

    Itens abaixo da faixa mínima nem aparecem listados.
    """
    CHAVES = ["casco_lendario", "alcance_lendario", "porao_lendario"]
    LABELS = {
        "casco_lendario":   "Casco Reforcado Lendario (+50% resistencia)",
        "alcance_lendario": "Luneta Lendaria (+120m alcance)",
        "porao_lendario":   "Porao Lendario (+3 slots)",
    }
    msg = ""
    while True:
        faixa_atual = faixa_index(getattr(estado_mundo, 'notoriedade', 0.0))
        disponiveis = [c for c in CHAVES if faixa_atual >= FAIXA_MINIMA_ITEM_TOPO[c]]
        if not disponiveis:
            extra = ["Nenhum item de topo disponivel na sua faixa de notoriedade atual."]
            _menu_simples(
                stdscr, "ITENS DE TOPO", ["[Voltar]"],
                "ESPACO/ESC: voltar", estado, extra_linhas=extra,
            )
            return

        opcoes = []
        for chave in disponiveis:
            if navio.itens_topo.get(chave, False):
                opcoes.append(f"{LABELS[chave]} ... (COMPRADO)  ---")
            else:
                preco = PRECO_ITENS_TOPO[chave]
                opcoes.append(f"{LABELS[chave]} ... {preco:.1f} ouro")
        opcoes.append("[Voltar]")
        extra = [f">> {msg}"] if msg else None
        escolha = _menu_simples(
            stdscr, "ITENS DE TOPO", opcoes,
            "CIMA/BAIXO: navegar  ESPACO: comprar  ESC: voltar",
            estado, extra_linhas=extra,
        )
        msg = ""
        if escolha in (-1, len(opcoes) - 1):
            return
        chave = disponiveis[escolha]
        ok, m = comprar_item_topo(navio, chave, faixa_atual)
        msg = m


# ---------------------------------------------------------------------------
# Loop principal do porto
# ---------------------------------------------------------------------------

def porto_loop(stdscr, estado, estado_mundo, porto_id: int) -> None:
    """Loop de navegação dentro do porto.

    Retorna quando o jogador pisa na doca (zarpa) ou pressiona ESC.
    Modifica estado.jogador e estado.frota in-place.
    """
    if _curses is None:
        return

    porto = estado_mundo.portos[porto_id]
    porto_nome = porto.nome

    frota = estado.frota

    cap_col = _CAP_INICIO_COL
    cap_row = _CAP_INICIO_ROW
    msg = f"Voce atracou em {porto_nome}. Ande ate uma loja ou ate o navio na doca pra zarpar."
    vista = "hud"

    stdscr.nodelay(False)
    while True:
        navio_nome = frota.ativo().nome if frota.ativo() else estado.jogador.nome
        _desenhar_porto(stdscr, cap_col, cap_row, porto_nome, navio_nome, msg, estado, vista)
        msg = ""

        ch = stdscr.getch()
        if ch == 27:  # ESC → zarpar
            break
        elif ch == ord('\t'):  # TAB → alternar vista HUD / porão
            vista = "porao" if vista == "hud" else "hud"
            continue

        pos_antes = (cap_col, cap_row)
        nova_col, nova_row = cap_col, cap_row
        if ch in (ord('w'), ord('W')):
            nova_row -= 1
        elif ch in (ord('s'), ord('S')):
            nova_row += 1
        elif ch in (ord('a'), ord('A')):
            nova_col -= 1
        elif ch in (ord('d'), ord('D')):
            nova_col += 1

        # Colisão com paredes: mantém dentro de cols 1..GRID_W-2 e rows 1..GRID_H-2
        nova_col = max(1, min(GRID_W - 2, nova_col))
        nova_row = max(1, min(GRID_H - 2, nova_row))
        cap_col, cap_row = nova_col, nova_row
        moveu = (cap_col, cap_row) != pos_antes

        # Doca/lojas só disparam na chegada (posição mudou nesse tick) — evita
        # reabrir a mesma loja a cada tecla enquanto o capitão fica parado
        # sobre a entrada (ex: ESPAÇO/ENTER, ou WASD contra uma parede).
        if not moveu:
            continue

        # Verifica doca (zarpar)
        if _proxima_doca(cap_col, cap_row):
            msg = "Zarpando..."
            _desenhar_porto(stdscr, cap_col, cap_row, porto_nome, navio_nome, msg, estado)
            break

        # Verifica entradas de loja
        loja = _prox_entrada(cap_col, cap_row)
        if loja == "polvora":
            _loja_recurso(stdscr, estado.jogador, "polvora", estado)
            msg = "Saindo da loja de polvora."
        elif loja == "bolas":
            _loja_recurso(stdscr, estado.jogador, "bolas", estado)
            msg = "Saindo da loja de bolas."
        elif loja == "tabuas":
            _loja_recurso(stdscr, estado.jogador, "tabuas", estado)
            msg = "Saindo da loja de tabuas."
        elif loja == "navios":
            _loja_navios(stdscr, frota, porto_id, estado.tipo_navio, estado, estado_mundo)
            msg = "Saindo da loja de navios."

    stdscr.nodelay(True)
    stdscr.timeout(POLL_MS)
