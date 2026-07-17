"""inventario.py – Interface de inventário (porão) com cursor interativo."""

from __future__ import annotations

try:
    import curses as _curses
except ImportError:
    _curses = None  # type: ignore[assignment]

from ..core.porao import TIPOS_CARGA, capacidade_barril, Porao
from .renderer import safe_addstr
from .colors import cor_recurso


def _barra(quantidade: float, capacidade: float, largura: int = 10) -> str:
    pct = quantidade / capacidade if capacidade > 0 else 0.0
    n = int(round(pct * largura))
    return "#" * n + "-" * (largura - n)


def abrir_inventario(stdscr, navio, loot_pendente: Porao | None = None, cores: bool = True) -> None:
    """Sub-loop de inventário: mostra barris com barras, permite reorganizar e descartar.

    Se loot_pendente for fornecido, tenta auto-alocar nos slots livres ao abrir.
    O que sobrar fica visível como "LOOT NAO COUBE" e é descartado ao fechar.

    Controles:
        CIMA/BAIXO (ou ESQ/DIR) — move cursor entre slots
        ESPACO   — pega/solta barril (swap)
        X        — descarta barril sob o cursor
        ESC/ENTER — fecha
    """
    if _curses is None:
        return

    # Auto-aloca loot pendente nos slots livres
    loot_info: list[str] = []
    if loot_pendente is not None and loot_pendente.barris:
        resto_barris = list(loot_pendente.barris)
        novos_barris: list = []
        for b in resto_barris:
            exc = navio.porao.adicionar(b.tipo, b.quantidade)
            coletado = b.quantidade - exc
            if coletado > 1e-9:
                loot_info.append(f"{coletado:.0f}u {b.tipo}")
            if exc > 1e-9:
                import copy
                nb = copy.copy(b)
                nb.quantidade = exc
                novos_barris.append(nb)
        loot_pendente.barris = novos_barris

    p = navio.porao
    cursor = 0
    selecionado: int | None = None
    msg = ""
    if loot_info:
        msg = f"Coletado: {', '.join(loot_info)}"

    stdscr.nodelay(False)
    while True:
        stdscr.erase()
        max_y, max_x = stdscr.getmaxyx()
        row = 0

        titulo = f"INVENTARIO  {navio.tipo_nome.upper()} | {navio.nome}  [{len(p.barris)}/{p.capacidade} slots]"
        safe_addstr(stdscr, row, 0, titulo, _curses.A_BOLD)
        row += 2

        # Cabeçalho da tabela
        safe_addstr(stdscr, row, 0, "  #   Tipo      Qtd / Max    [Barra      ]")
        row += 1

        cap = p.capacidade
        for i in range(cap):
            if row >= max_y - 6:
                safe_addstr(stdscr, row, 2, f"... ({cap - i} slots mais, rola para baixo)")
                row += 1
                break

            if i == cursor and i == selecionado:
                prefixo = "[*]"
                attr = _curses.A_REVERSE | _curses.A_BOLD
            elif i == cursor:
                prefixo = " > "
                attr = _curses.A_REVERSE
            elif i == selecionado:
                prefixo = " * "
                attr = _curses.A_BOLD
            else:
                prefixo = "   "
                attr = 0

            if i < len(p.barris):
                b = p.barris[i]
                cap_b = capacidade_barril(b.tipo)
                barra_str = _barra(b.quantidade, cap_b)
                linha = (
                    f"{prefixo}{i+1:2d}.  {b.tipo:7s}  "
                    f"{b.quantidade:4.0f} / {cap_b:2.0f}u  [{barra_str}]"
                )
                cor = cor_recurso(cores, b.tipo)
                attr = attr | cor if cor and not (attr & _curses.A_REVERSE) else attr
            else:
                linha = f"{prefixo}{i+1:2d}.  [slot vazio]"

            safe_addstr(stdscr, row, 0, linha, attr)
            row += 1

        row += 1

        # Loot que não coube
        if loot_pendente and loot_pendente.barris:
            safe_addstr(stdscr, row, 0, "LOOT NAO COUBE (sera descartado ao fechar):", _curses.A_BOLD)
            row += 1
            for b in loot_pendente.barris:
                cap_b = capacidade_barril(b.tipo)
                barra_str = _barra(b.quantidade, cap_b)
                safe_addstr(
                    stdscr, row, 2,
                    f"{b.tipo:7s}  {b.quantidade:4.0f} / {cap_b:2.0f}u  [{barra_str}]",
                    cor_recurso(cores, b.tipo),
                )
                row += 1

        if msg:
            safe_addstr(stdscr, max_y - 4, 0, msg[: max_x - 1])
        safe_addstr(stdscr, max_y - 3, 0, "-" * min(max_x - 1, 78))
        safe_addstr(
            stdscr, max_y - 2, 0,
            "CIMA/BAIXO: selecionar  ESPACO: pegar/soltar  X: descartar  ESC/ENTER: fechar",
        )

        stdscr.refresh()
        ch = stdscr.getch()

        if ch in (27, _curses.KEY_ENTER, 10, 13):
            break
        elif ch in (_curses.KEY_UP, _curses.KEY_LEFT):
            cursor = max(0, cursor - 1)
            msg = ""
        elif ch in (_curses.KEY_DOWN, _curses.KEY_RIGHT):
            cursor = min(cap - 1, cursor + 1)
            msg = ""
        elif ch in (ord('x'), ord('X')):
            if cursor < len(p.barris):
                b = p.barris.pop(cursor)
                msg = f"Barril de {b.tipo} ({b.quantidade:.0f}u) jogado ao mar."
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
                    msg = f"Barril {cursor + 1} pego ({p.barris[cursor].tipo})."
                else:
                    msg = "Slot vazio — nada para pegar."
            else:
                if selecionado == cursor:
                    selecionado = None
                    msg = "Barril solto."
                else:
                    if cursor < len(p.barris):
                        p.barris[selecionado], p.barris[cursor] = (
                            p.barris[cursor], p.barris[selecionado]
                        )
                        msg = "Barris trocados."
                    else:
                        b = p.barris.pop(selecionado)
                        insert_at = min(cursor, len(p.barris))
                        p.barris.insert(insert_at, b)
                        msg = "Barril movido."
                    selecionado = None

    stdscr.nodelay(True)
