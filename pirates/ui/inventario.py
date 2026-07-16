"""inventario.py – Interface de inventário (porão) com cursor interativo."""

from __future__ import annotations

try:
    import curses as _curses
except ImportError:
    _curses = None  # type: ignore[assignment]

from ..core.porao import TIPOS_CARGA, CAPACIDADE_BARRIL, Porao
from .renderer import safe_addstr

_ICONE = {"polvora": "[P]", "bolas": "[O]", "tabuas": "[T]", "ouro": "[$]"}
_BARRIL_W = 7  # largura por barril no display


def abrir_inventario(stdscr, navio, loot_pendente: Porao | None = None) -> None:
    """Sub-loop de inventário: mostra barris, permite reorganizar e descartar.

    Auto-aloca loot_pendente nos slots vazios ao abrir; o que sobrar é
    perdido quando o jogador fecha (ESC/Enter).

    Controles:
        ESQ/DIR  — move cursor entre slots
        ESPACO   — pega/solta barril (swap)
        X        — descarta barril sob o cursor
        ESC/ENTER — fecha
    """
    if _curses is None:
        return

    # Auto-aloca loot pendente
    loot_info: list[str] = []
    if loot_pendente is not None and loot_pendente.barris:
        resto_barris = list(loot_pendente.barris)
        novos_barris: list = []
        for b in resto_barris:
            exc = navio.porao.adicionar(b.tipo, b.quantidade)
            if exc < b.quantidade - 1e-9:
                coletado = b.quantidade - exc
                loot_info.append(f"{coletado:.1f} {b.tipo}")
            if exc > 1e-9:
                import copy
                nb = copy.copy(b)
                nb.quantidade = exc
                novos_barris.append(nb)
        loot_pendente.barris = novos_barris

    p = navio.porao
    cursor = 0
    selecionado: int | None = None  # índice do barril "pego"
    msg = ""
    if loot_info:
        msg = f"Loot coletado: {', '.join(loot_info)}"

    stdscr.nodelay(False)
    while True:
        stdscr.erase()
        max_y, max_x = stdscr.getmaxyx()
        row = 0

        # Título
        titulo = f"INVENTARIO: {navio.tipo_nome.upper()} | {navio.nome}"
        safe_addstr(stdscr, row, 0, titulo, _curses.A_BOLD | _curses.A_UNDERLINE)
        row += 2

        cap = p.capacidade
        total_slots = cap
        safe_addstr(stdscr, row, 2, f"{len(p.barris)}/{cap} slots usados")
        row += 1

        # Renderiza até 7 barris por fileira
        COLS_POR_FILEIRA = 7
        for fileira in range((total_slots + COLS_POR_FILEIRA - 1) // COLS_POR_FILEIRA):
            ini = fileira * COLS_POR_FILEIRA
            fim = min(ini + COLS_POR_FILEIRA, total_slots)

            # Linha de quantidade
            qtd_linha = ""
            for i in range(ini, fim):
                if i < len(p.barris):
                    b = p.barris[i]
                    qtd_str = f"{b.quantidade:4.0f}/25"
                else:
                    qtd_str = "  --   "
                qtd_linha += qtd_str.center(_BARRIL_W)
            safe_addstr(stdscr, row, 2, qtd_linha)
            row += 1

            # Barril art (5 linhas)
            barrel_lines = [".-.  ", "|#|  ", "|#|  ", "| |  ", "'-'  "]
            empty_lines  = [".-.  ", "| |  ", "| |  ", "| |  ", "'-'  "]
            for li in range(5):
                linha = ""
                for i in range(ini, fim):
                    if i < len(p.barris):
                        b = p.barris[i]
                        fill = b.quantidade / CAPACIDADE_BARRIL
                        filled_rows = int(round(fill * 3))  # 0-3 linhas cheias (linhas 1-3)
                        if li == 0 or li == 4:
                            linha += barrel_lines[li]
                        elif (3 - li + 1) <= filled_rows:  # linhas de baixo p/ cima
                            linha += barrel_lines[li]
                        else:
                            linha += empty_lines[li]
                    else:
                        linha += empty_lines[li]
                safe_addstr(stdscr, row, 2, linha)
                row += 1

            # Ícone do tipo
            icone_linha = ""
            for i in range(ini, fim):
                if i < len(p.barris):
                    b = p.barris[i]
                    icone_linha += _ICONE.get(b.tipo, "[ ]").center(_BARRIL_W)
                else:
                    icone_linha += "[ ]".center(_BARRIL_W)
            safe_addstr(stdscr, row, 2, icone_linha)
            row += 1

            # Cursor
            cursor_linha = ""
            for i in range(ini, fim):
                if i == cursor:
                    cursor_linha += " ^ ".center(_BARRIL_W)
                elif i == selecionado:
                    cursor_linha += " * ".center(_BARRIL_W)
                else:
                    cursor_linha += "   ".center(_BARRIL_W)
            safe_addstr(stdscr, row, 2, cursor_linha)
            row += 1
            row += 1  # espaço entre fileiras

        # Loot pendente restante
        if loot_pendente and loot_pendente.barris:
            safe_addstr(stdscr, row, 0, "LOOT PENDENTE (nao coube):", _curses.A_BOLD)
            row += 1
            resumo = " | ".join(
                f"{b.tipo} {b.quantidade:.1f}" for b in loot_pendente.barris
            )
            safe_addstr(stdscr, row, 2, resumo)
            row += 1

        # Mensagem e rodapé
        if msg:
            safe_addstr(stdscr, max_y - 4, 0, msg)
        safe_addstr(stdscr, max_y - 3, 0, "-" * min(max_x - 1, 78))
        safe_addstr(stdscr, max_y - 2, 0,
                    "ESQ/DIR: selecionar  ESPACO: pegar/soltar  X: descartar  ESC/ENTER: fechar")

        stdscr.refresh()
        ch = stdscr.getch()

        if ch in (27, _curses.KEY_ENTER, 10, 13):
            break
        elif ch == _curses.KEY_LEFT:
            cursor = max(0, cursor - 1)
            msg = ""
        elif ch == _curses.KEY_RIGHT:
            cursor = min(total_slots - 1, cursor + 1)
            msg = ""
        elif ch in (ord('x'), ord('X')):
            if cursor < len(p.barris):
                b = p.barris.pop(cursor)
                msg = f"Barril de {b.tipo} jogado ao mar."
                if selecionado == cursor:
                    selecionado = None
                elif selecionado is not None and selecionado > cursor:
                    selecionado -= 1
                cursor = min(cursor, max(0, len(p.barris) - 1))
            else:
                msg = "Slot vazio."
        elif ch == ord(' '):
            if selecionado is None:
                if cursor < len(p.barris):
                    selecionado = cursor
                    msg = f"Barril {cursor + 1} pego."
                else:
                    msg = "Slot vazio — nada para pegar."
            else:
                if selecionado == cursor:
                    selecionado = None
                    msg = "Barril solto."
                else:
                    # Swap
                    while len(p.barris) <= cursor < cap:
                        # cursor em slot vazio → mover barril selecionado até aqui
                        break
                    if cursor < len(p.barris):
                        p.barris[selecionado], p.barris[cursor] = (
                            p.barris[cursor], p.barris[selecionado]
                        )
                        msg = "Barris trocados."
                    else:
                        # Move para slot vazio
                        b = p.barris.pop(selecionado)
                        p.barris.insert(cursor if cursor <= len(p.barris) else len(p.barris), b)
                        msg = "Barril movido."
                    selecionado = None

    # Loot pendente restante é perdido
    if loot_pendente and loot_pendente.barris:
        pass  # o caller vai limpar loot_pendente com base no que sobrou

    stdscr.nodelay(True)
