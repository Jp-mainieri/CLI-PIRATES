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


def _resolve(cursor: int, p, loot: Porao | None):
    """Resolve cursor para (barril_ou_None, lista, idx_na_lista).

    Posições 0..cap-1 → porão; posições cap..cap+len(loot)-1 → loot.
    Retorna (None, None, -1) se cursor aponta para fora de qualquer lista válida.
    """
    if cursor < p.capacidade:
        if cursor < len(p.barris):
            return p.barris[cursor], p.barris, cursor
        return None, p.barris, cursor  # slot vazio do porão
    else:
        loot_idx = cursor - p.capacidade
        if loot is not None and loot_idx < len(loot.barris):
            return loot.barris[loot_idx], loot.barris, loot_idx
        return None, None, -1


def abrir_inventario(stdscr, navio, loot_pendente: Porao | None = None, cores: bool = True) -> None:
    """Sub-loop de inventário: mostra barris com barras, permite reorganizar e descartar.

    Se loot_pendente for fornecido, tenta auto-alocar nos slots livres ao abrir.
    O que sobrar fica visível na seção LOOT e pode ser trocado com o porão.
    Barris restantes no loot ao fechar são descartados.

    Controles:
        CIMA/BAIXO (ou ESQ/DIR) — move cursor entre slots (porão + loot)
        ESPACO   — pega/solta barril (swap ou fusão se mesmo tipo)
        X        — descarta barril do porão sob o cursor
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

        # Seção de loot com cursor navegável
        if loot_pendente and loot_pendente.barris:
            safe_addstr(stdscr, row, 0, "LOOT DO DESTROCO (restante descartado ao fechar):", _curses.A_BOLD)
            row += 1
            for li, b in enumerate(loot_pendente.barris):
                loot_cursor = cap + li

                if loot_cursor == cursor and loot_cursor == selecionado:
                    prefixo = "[*]"
                    loot_attr = _curses.A_REVERSE | _curses.A_BOLD
                elif loot_cursor == cursor:
                    prefixo = " > "
                    loot_attr = _curses.A_REVERSE
                elif loot_cursor == selecionado:
                    prefixo = " * "
                    loot_attr = _curses.A_BOLD
                else:
                    prefixo = "   "
                    loot_attr = 0

                cap_b = capacidade_barril(b.tipo)
                barra_str = _barra(b.quantidade, cap_b)
                cor = cor_recurso(cores, b.tipo)
                merged_attr = loot_attr | (cor if not (loot_attr & _curses.A_REVERSE) else 0)
                safe_addstr(
                    stdscr, row, 0,
                    f"{prefixo}{b.tipo:7s}  {b.quantidade:4.0f} / {cap_b:2.0f}u  [{barra_str}]",
                    merged_attr,
                )
                row += 1

        if msg:
            safe_addstr(stdscr, max_y - 4, 0, msg[: max_x - 1])
        safe_addstr(stdscr, max_y - 3, 0, "-" * min(max_x - 1, 78))
        safe_addstr(
            stdscr, max_y - 2, 0,
            "CIMA/BAIXO: cursor  ESPACO: pegar/trocar/fundir  X: descartar (porao)  ESC/ENTER: fechar",
        )

        stdscr.refresh()
        ch = stdscr.getch()

        # Limite máximo do cursor
        loot_n = len(loot_pendente.barris) if loot_pendente else 0
        max_cursor = cap - 1 + loot_n

        if ch in (27, _curses.KEY_ENTER, 10, 13):
            break
        elif ch in (_curses.KEY_UP, _curses.KEY_LEFT):
            cursor = max(0, cursor - 1)
            msg = ""
        elif ch in (_curses.KEY_DOWN, _curses.KEY_RIGHT):
            cursor = min(max_cursor, cursor + 1)
            msg = ""
        elif ch in (ord('x'), ord('X')):
            # X só descarta barris do porão (não do loot)
            if cursor < cap:
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
            else:
                msg = "Use ESPACO para mover barris do loot."
        elif ch == ord(' '):
            if selecionado is None:
                b, _, _ = _resolve(cursor, p, loot_pendente)
                if b is not None:
                    selecionado = cursor
                    msg = f"Barril pego ({b.tipo})."
                else:
                    msg = "Slot vazio — nada para pegar."
            elif selecionado == cursor:
                selecionado = None
                msg = "Barril solto."
            else:
                b_src, src_list, src_idx = _resolve(selecionado, p, loot_pendente)
                b_dst, dst_list, dst_idx = _resolve(cursor, p, loot_pendente)

                if b_src is None:
                    selecionado = None
                    msg = "Barril de origem inválido."
                elif b_dst is None and dst_list is p.barris:
                    # Move para slot vazio do porão
                    src_list.pop(src_idx)
                    insert_at = min(cursor, len(p.barris))
                    p.barris.insert(insert_at, b_src)
                    msg = f"Barril movido para slot {cursor + 1}."
                    selecionado = None
                elif b_dst is not None and b_src.tipo == b_dst.tipo:
                    # Fusão de barris do mesmo tipo
                    cap_b = capacidade_barril(b_dst.tipo)
                    espaco = cap_b - b_dst.quantidade
                    if espaco >= b_src.quantidade:
                        b_dst.quantidade += b_src.quantidade
                        src_list.pop(src_idx)
                        msg = f"Barris fundidos: {b_dst.tipo} {b_dst.quantidade:.0f}/{cap_b:.0f}u."
                    else:
                        b_dst.quantidade = cap_b
                        b_src.quantidade -= espaco
                        msg = f"Barril cheio. Restam {b_src.quantidade:.0f}u."
                    selecionado = None
                elif b_dst is not None:
                    # Swap entre seções ou dentro da mesma seção (tipos diferentes)
                    src_list[src_idx], dst_list[dst_idx] = dst_list[dst_idx], src_list[src_idx]
                    msg = "Barris trocados."
                    selecionado = None
                else:
                    msg = "Destino inválido."

                # Recalcula max_cursor e clamp após modificações
                loot_n = len(loot_pendente.barris) if loot_pendente else 0
                cursor = min(cursor, max(0, cap - 1 + loot_n))

    stdscr.nodelay(True)
