"""scene.py – Cena do porto: navegação WASD, lojas e doca (Tier 3b)."""

from __future__ import annotations

try:
    import curses as _curses
except ImportError:
    _curses = None  # type: ignore[assignment]

from ..ui.renderer import safe_addstr
from ..ui.hud import build_porao_inventario_linhas, build_navio_diagrama
from .lojas import (
    preco_reparo, preco_reabastecer, preco_venda,
    preco_upgrade_nivel, nivel_atual_upgrade, nivel_max_upgrade,
    comprar_barril, reabastecer_barril, vender_barril, reparo_instantaneo,
    comprar_navio_loja, renomear_navio_loja, aplicar_upgrade,
    UPGRADE_NIVEIS_MAX,
)
from ..constants import (
    PRECO_NAVIO_NOVO, PRECO_BARRIL_NOVO, PRECO_RENOMEAR,
    NAVIO_TIPOS, SIMB_CAPITAO,
    COR_VERMELHO, COR_VERDE, COR_AMARELO, COR_JOGADOR,
)

# ---------------------------------------------------------------------------
# Layout da grade do porto (30×15)
# ---------------------------------------------------------------------------

GRID_W = 30
GRID_H = 15

# Posições (col, row) dos elementos fixos
_DOCA_COL, _DOCA_ROW = 14, 12
_CAP_INICIO_COL, _CAP_INICIO_ROW = 14, 9

# Entradas das lojas: capitão precisa chegar a distância ≤1 de uma destas posições
_ENTRADAS: dict[str, tuple[int, int]] = {
    "polvora": (9,  3),
    "bolas":   (19, 3),
    "tabuas":  (9,  10),
    "navios":  (19, 10),
}


def capitao_perto_de(cap_col: int, cap_row: int, alvo_col: int, alvo_row: int) -> bool:
    """True se o capitão está a distância ≤1 célula do alvo (Manhattan)."""
    return abs(cap_col - alvo_col) + abs(cap_row - alvo_row) <= 1


def _prox_entrada(cap_col: int, cap_row: int) -> str | None:
    for nome, (ec, er) in _ENTRADAS.items():
        if capitao_perto_de(cap_col, cap_row, ec, er):
            return nome
    return None


def _proxima_doca(cap_col: int, cap_row: int) -> bool:
    return capitao_perto_de(cap_col, cap_row, _DOCA_COL, _DOCA_ROW)


# ---------------------------------------------------------------------------
# Rendering da grade
# ---------------------------------------------------------------------------

_GRID_BG: list[str] = [
    "                              ",  # 0
    "        [P]       [O]         ",  # 1  lojas top  (col 9 e 19)
    "         |         |          ",  # 2
    "         *         *          ",  # 3  ← entradas polvora(9) e bolas(19)
    "         |         |          ",  # 4
    "         |         |          ",  # 5
    "         |         |          ",  # 6
    "         |         |          ",  # 7
    "         |         |          ",  # 8
    "         |         |          ",  # 9
    "         *         *          ",  # 10 ← entradas tabuas(9) e navios(19)
    "         |         |          ",  # 11
    "        [T]  ___  [N]         ",  # 12 lojas bottom + doca (col 14)
    "              |               ",  # 13
    "             DOCA             ",  # 14
]


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

    # Grade do porto com offset vertical
    base_row = 3
    for r, linha in enumerate(_GRID_BG):
        safe_addstr(stdscr, base_row + r, 4, linha)

    # Cores das lojas sobre o grid (col de string → visual col = 4 + col_string)
    # [P] polvora: string col 8-10, row 1  →  visual col 12, row base_row+1
    # [O] bolas:   string col 18-20, row 1 →  visual col 22, row base_row+1
    # [T] tabuas:  string col 8-10, row 12 →  visual col 12, row base_row+12
    # [N] navios:  string col 18-20, row 12→  visual col 22, row base_row+12
    _lojas_info = [
        ("[P]", base_row + 1,  12, COR_VERMELHO),
        ("[O]", base_row + 1,  22, None),          # bolas: só bold
        ("[T]", base_row + 12, 12, COR_VERDE),
        ("[N]", base_row + 12, 22, COR_JOGADOR),
    ]
    for texto, row, col, par in _lojas_info:
        if cores and par is not None:
            attr = _curses.color_pair(par) | _curses.A_BOLD
        else:
            attr = _curses.A_BOLD
        safe_addstr(stdscr, row, col, texto, attr)

    # Capitão (amarelo+bold)
    if cores:
        cap_attr = _curses.color_pair(COR_AMARELO) | _curses.A_BOLD
    else:
        cap_attr = _curses.A_BOLD
    safe_addstr(stdscr, base_row + cap_row, 4 + cap_col, SIMB_CAPITAO, cap_attr)

    # Painel inferior: HUD ou porão
    sep_row = base_row + GRID_H + 1
    label = "HUD" if vista == "hud" else "PORAO"
    safe_addstr(stdscr, sep_row, 0, f"[{label}]" + "-" * max(0, min(max_x - 1, 78) - 6 - len(label)))
    painel_row = sep_row + 1

    if vista == "hud":
        linhas = build_navio_diagrama(estado)[:6]   # casco/mastro/vela/roda/agua/moral
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
                "WASD: mover   DOCA: zarpar   TAB: alternar vista   ESC: zarpar")
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
                  rodape: str, estado, extra_linhas: list[str] | None = None) -> int:
    """Menu navegável com CIMA/BAIXO + ESPACO. Retorna índice da opção escolhida ou -1 (ESC)."""
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

        # Painel de porão
        pr = max_y - 10
        safe_addstr(stdscr, pr, 0, "-" * min(max_x - 1, 78))
        pr += 1
        cores = estado.cores_ativo and _curses is not None
        for texto, attr in build_porao_inventario_linhas(estado.jogador, cores=cores):
            if pr >= max_y - 5:
                break
            safe_addstr(stdscr, pr, 0, texto, attr)
            pr += 1

        ouro = estado.jogador.porao.total("ouro")
        safe_addstr(stdscr, max_y - 4, 0, f"Ouro disponivel: {ouro:.1f}")
        safe_addstr(stdscr, max_y - 3, 0, "-" * min(max_x - 1, 78))
        safe_addstr(stdscr, max_y - 2, 0, rodape)
        stdscr.refresh()

        ch = stdscr.getch()
        if ch == 27:
            return -1
        elif ch == _curses.KEY_UP:
            cursor = max(0, cursor - 1)
        elif ch == _curses.KEY_DOWN:
            cursor = min(len(opcoes) - 1, cursor + 1)
        elif ch in (ord(' '), _curses.KEY_ENTER, 10, 13):
            return cursor


def _loja_inventario_simples(stdscr, navio, tipo: str, estado) -> int | None:
    """Mostra o porão e pede ao jogador selecionar um barril do `tipo`. Retorna índice ou None."""
    from ..ui.inventario import abrir_inventario
    # Apenas abre o inventário para o jogador selecionar
    # Retorna o índice do primeiro barril do tipo com espaço (reabastecer)
    # ou qualquer barril do tipo (vender)
    barris_tipo = [(i, b) for i, b in enumerate(navio.porao.barris) if b.tipo == tipo]
    if not barris_tipo:
        return None
    # Retorna o índice do barril mais vazio (candidato para reabastecer)
    idx, _ = min(barris_tipo, key=lambda ib: ib[1].quantidade)
    return idx


def _loja_recurso(stdscr, navio, tipo: str, estado) -> None:
    """Sub-loop da loja de recurso (pólvora/bolas/tábuas)."""
    nome_exibido = {"polvora": "POLVORA", "bolas": "BOLAS", "tabuas": "TABUAS"}.get(tipo, tipo.upper())
    barril_sel: int | None = None
    msg = ""

    while True:
        navio_ativo = estado.jogador
        barril_sel_info = ""
        reab_str = "Reabastecer barril selecionado ........... (selecione um barril)"
        vend_str = "Vender barril selecionado ................. (selecione um barril)"
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

        extra = [f"Barril selecionado: {barril_sel_info}" if barril_sel_info else "Barril selecionado: (nenhum)"]
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
                barril_sel = _loja_inventario_simples(stdscr, navio_ativo, tipo, estado)
                if barril_sel is None:
                    msg = f"Nenhum barril de {tipo} no porcao."
                    continue
            ok, m = reabastecer_barril(navio_ativo, barril_sel, tipo)
            msg = m
            if ok:
                barril_sel = None

        elif escolha == 2:  # Vender
            if barril_sel is None or barril_sel >= len(navio_ativo.porao.barris):
                barril_sel = _loja_inventario_simples(stdscr, navio_ativo, tipo, estado)
                if barril_sel is None:
                    msg = f"Nenhum barril de {tipo} no porcao."
                    continue
            ok, m = vender_barril(navio_ativo, barril_sel)
            msg = m
            if ok:
                barril_sel = None

        elif tipo == "tabuas" and escolha == 3:  # Reparo instantâneo
            ok, m = reparo_instantaneo(navio_ativo)
            msg = m


def _loja_navios(stdscr, frota, porto_id: int, tipo_navio_atual: str, estado) -> None:
    """Sub-loop da loja de navios."""
    msg = ""
    while True:
        navio_ativo = estado.jogador
        ouro = navio_ativo.porao.total("ouro")
        opcoes = [
            "Comprar navio novo ......................................",
            "Trocar de navio ativo (frota) ...........................",
            f"Renomear navio atual .................................... {PRECO_RENOMEAR:.1f} ouro",
            "Upgrades do navio atual .................................",
            "[Voltar]",
        ]
        extra = [f">> {msg}"] if msg else None
        escolha = _menu_simples(
            stdscr, "LOJA DE NAVIOS", opcoes,
            "CIMA/BAIXO: navegar  ESPACO: confirmar  ESC: voltar",
            estado, extra_linhas=extra,
        )
        msg = ""
        if escolha in (-1, 4):
            return

        elif escolha == 0:  # Comprar navio novo
            msg = _fluxo_comprar_navio(stdscr, frota, porto_id, navio_ativo, estado)

        elif escolha == 1:  # Trocar de navio ativo
            msg = _fluxo_trocar_navio(stdscr, frota, porto_id, estado)

        elif escolha == 2:  # Renomear
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

        elif escolha == 3:  # Upgrades
            _loja_upgrades(stdscr, navio_ativo, tipo_navio_atual, estado)


def _fluxo_comprar_navio(stdscr, frota, porto_id: int, navio_ativo, estado) -> str:
    tipos = [
        ("facil",   f"Chalupa    .... {PRECO_NAVIO_NOVO['facil']:.0f} ouro"),
        ("normal",  f"Bergantim  .... {PRECO_NAVIO_NOVO['normal']:.0f} ouro"),
        ("dificil", f"Galeao     .... {PRECO_NAVIO_NOVO['dificil']:.0f} ouro"),
    ]
    opcoes = [t[1] for t in tipos] + ["[Voltar]"]
    escolha = _menu_simples(stdscr, "COMPRAR NAVIO NOVO", opcoes,
                            "CIMA/BAIXO: navegar  ESPACO: escolher  ESC: voltar", estado)
    if escolha in (-1, len(opcoes) - 1):
        return "Cancelado."
    tipo_escolhido, _ = tipos[escolha]
    preco = float(PRECO_NAVIO_NOVO[tipo_escolhido])
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


def _fluxo_trocar_navio(stdscr, frota, porto_id: int, estado) -> str:
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
    escolha = _menu_simples(stdscr, f"SUA FROTA EM PORTO", opcoes,
                            "CIMA/BAIXO: navegar  ESPACO: trocar  ESC: voltar", estado)
    if escolha in (-1, len(opcoes) - 1):
        return "Cancelado."
    idx_real = indices_reais[escolha]
    if idx_real == frota.indice_ativo:
        return "Ja e o navio ativo."
    ok = frota.trocar_ativo(idx_real, porto_id)
    if ok:
        novo = frota.ativo()
        # Atualiza estado.jogador para o novo navio
        if novo is not None:
            estado.jogador = novo.navio
        return f"Navio trocado para {frota.ativo().nome if frota.ativo() else '?'}."
    return "Nao foi possivel trocar o navio."


def _loja_upgrades(stdscr, navio, tipo_navio: str, estado) -> None:
    """Sub-loop de upgrades do navio."""
    CHAVES = ["casco_max", "cooldown", "porao_slot", "tripulante_extra",
              "velocidade_giro", "alcance_canhao"]
    LABELS = {
        "casco_max":        "+10 HP max de casco",
        "cooldown":         "-10% cooldown de canhao",
        "porao_slot":       "+1 slot de porao",
        "tripulante_extra": "+1 tripulante extra",
        "velocidade_giro":  "+10% velocidade/giro",
        "alcance_canhao":   "+50m alcance de canhao",
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

    # Registra navio inicial na frota se ainda não foi feito
    frota = estado.frota
    if frota.indice_ativo == -1:
        frota.adicionar(
            nome=estado.jogador.nome or "Navio Inicial",
            navio=estado.jogador,
            tipo=estado.tipo_navio,
            porto_id=porto_id,
        )
        frota.indice_ativo = 0

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
        elif ch == ord('\t'):  # TAB → alternar vista
            vista = "porao" if vista == "hud" else "hud"
            continue

        nova_col, nova_row = cap_col, cap_row
        if ch in (ord('w'), ord('W')):
            nova_row = max(0, cap_row - 1)
        elif ch in (ord('s'), ord('S')):
            nova_row = min(GRID_H - 1, cap_row + 1)
        elif ch in (ord('a'), ord('A')):
            nova_col = max(0, cap_col - 1)
        elif ch in (ord('d'), ord('D')):
            nova_col = min(GRID_W - 1, cap_col + 1)

        cap_col, cap_row = nova_col, nova_row

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
            _loja_navios(stdscr, frota, porto_id, estado.tipo_navio, estado)
            msg = "Saindo da loja de navios."

    stdscr.nodelay(True)
