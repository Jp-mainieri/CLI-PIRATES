"""
menus.py – Telas de menu, configuração e fim de jogo de CLI PIRATES.

Cada função ``tela_*`` bloqueia até o usuário fazer uma escolha e retorna
a próxima tela (string) ou modifica o dict de config in-place.
"""

try:
    import curses as _curses
except ImportError:
    _curses = None  # type: ignore[assignment]

from ..constants import (
    TITULO_ARTE, ARTE_VITORIA, ARTE_DERROTA, ARTE_FUGA, ARTE_FUGA_JOGADOR, COMO_JOGAR_TEXTO,
    TIPOS_NAVIO, NAVIO_TIPOS, PARTES,
    COR_VERDE, COR_VERMELHO, COR_AMARELO,
    VENTO_ZONAS_ANGULO_MEIO,
)
from ..core.utils import barra
from ..core.velas import gerar_slots_fabrica, eficiencia_vento_bruta
from .renderer import safe_addstr


def tela_menu(stdscr) -> str:
    """Exibe o menu principal e retorna a opção escolhida.

    Returns:
        Uma das strings: 'jogar', 'como_jogar', 'navio', 'ajustes', 'sair'.
    """
    opcoes = [
        ("Mundo Aberto", "mundo"),
        ("Arena", "jogar"),
        ("Como jogar", "como_jogar"),
        ("Tipos de Navio", "navio"),
        ("Ajustes", "ajustes"),
        ("Sair", "sair"),
    ]
    idx = 0
    stdscr.nodelay(False)
    stdscr.timeout(-1)
    while True:
        stdscr.erase()
        for i, l in enumerate(TITULO_ARTE):
            safe_addstr(stdscr, i, 2, l)
        row = len(TITULO_ARTE) + 2
        for i, (label, _) in enumerate(opcoes):
            marcador = "> " if i == idx else "  "
            attr = _curses.A_REVERSE if i == idx else 0
            safe_addstr(stdscr, row + i, 2, f"{marcador}[{i + 1}] {label}", attr)
        safe_addstr(
            stdscr, row + len(opcoes) + 2, 2,
            "Use as setas + ENTER, ou digite o numero da opcao.",
        )
        stdscr.refresh()

        ch = stdscr.getch()
        if ch == _curses.KEY_UP:
            idx = (idx - 1) % len(opcoes)
        elif ch == _curses.KEY_DOWN:
            idx = (idx + 1) % len(opcoes)
        elif ch in (_curses.KEY_ENTER, 10, 13):
            return opcoes[idx][1]
        elif ord('1') <= ch <= ord(str(len(opcoes))):
            return opcoes[ch - ord('1')][1]


def tela_como_jogar(stdscr) -> None:
    """Exibe a tela de instruções completas do jogo, com scroll.

    SETA CIMA/BAIXO ou J/K rolam uma linha; PAGE UP/DOWN rolam uma tela
    inteira. ESC ou Q voltam ao menu.
    """
    stdscr.nodelay(False)
    stdscr.timeout(-1)
    offset = 0
    total = len(COMO_JOGAR_TEXTO)
    while True:
        stdscr.erase()
        max_y, max_x = stdscr.getmaxyx()
        visiveis = max(1, max_y - 1)
        offset = max(0, min(offset, max(0, total - visiveis)))
        for i, l in enumerate(COMO_JOGAR_TEXTO[offset:offset + visiveis]):
            safe_addstr(stdscr, i, 2, l)
        rodape = "SETAS/J-K: rolar  PGUP/PGDN: pagina  ESC/Q: voltar"
        safe_addstr(stdscr, max_y - 1, 2, rodape, _curses.A_REVERSE)
        stdscr.refresh()

        ch = stdscr.getch()
        if ch in (27, ord('q'), ord('Q')):
            return
        elif ch in (_curses.KEY_UP, ord('k'), ord('K')):
            offset -= 1
        elif ch in (_curses.KEY_DOWN, ord('j'), ord('J')):
            offset += 1
        elif ch == _curses.KEY_PPAGE:
            offset -= visiveis
        elif ch == _curses.KEY_NPAGE:
            offset += visiveis


def tela_navio(stdscr, bloqueios: dict[str, str | None] | None = None) -> str | None:
    """Tela de tipos de navio (←→ alterna, ENTER escolhe, ESC cancela).

    Serve tanto como vitrine informativa (menu principal, retorno descartado,
    sem `bloqueios`) quanto como seletor real (fluxos de Novo Capitão /
    Iniciar Campanha, que usam o retorno pra decidir o tipo do navio criado
    e passam `bloqueios` pra impedir a escolha de tipos ainda não
    desbloqueados por progressão).

    Args:
        bloqueios: Dict tipo->motivo (None se liberado). Quando None, nenhum
            tipo é bloqueado (uso como vitrine informativa).

    Returns:
        Chave do tipo escolhido (ENTER, só se não estiver bloqueado), ou
        None se ESC foi pressionado.
    """
    idx = TIPOS_NAVIO.index("brigantim")
    stdscr.nodelay(False)
    stdscr.timeout(-1)
    while True:
        stdscr.erase()
        safe_addstr(stdscr, 0, 2, "TIPOS DE NAVIO", _curses.A_BOLD)
        safe_addstr(stdscr, 1, 2, "-" * 44)

        chave = TIPOS_NAVIO[idx]
        p = NAVIO_TIPOS[chave]
        nivel = TIPOS_NAVIO.index(chave) + 1
        motivo_bloqueio = bloqueios.get(chave) if bloqueios else None
        safe_addstr(stdscr, 3, 2, f"<  {p['navio'].upper()}  >", _curses.A_BOLD)
        safe_addstr(stdscr, 4, 2, f"   dificuldade {nivel} para gerenciar o navio")
        if motivo_bloqueio:
            safe_addstr(stdscr, 5, 2, f"   BLOQUEADO: {motivo_bloqueio}", _curses.A_BOLD)
        safe_addstr(stdscr, 6, 2, f"   Tripulacao total .... {p['crew_total']}")
        safe_addstr(
            stdscr, 7, 2,
            f"   Canhoes por lado .... {p['canhoes_lado']} ({p['canhoes_lado']*2} no total)",
        )
        safe_addstr(stdscr, 8, 2, f"   Velas ............... {p['num_velas']}")
        safe_addstr(stdscr, 9, 2,
                    f"   Tripulantes minimos/canhao ... {p['min_crew_canhao']}")
        safe_addstr(stdscr, 10, 2, f"   Velocidade base ...... {p['velocidade_max_base']:.0f}")
        safe_addstr(stdscr, 11, 2,
                    f"   Taxa de giro ......... {p['giro_graus_seg']:.0f} graus/s")
        safe_addstr(stdscr, 12, 2, f"   Capacidade do porao .. {p['porao_capacidade']} slots")
        zona_label = {
            'zona_morta': 'Zona Morta', 'bolina': 'Bolina',
            'traves': 'Traves', 'popa': 'Popa',
        }
        slots_fabrica = gerar_slots_fabrica(chave)
        eficiencias_por_zona = {
            zona: eficiencia_vento_bruta(slots_fabrica, angulo)
            for zona, angulo in VENTO_ZONAS_ANGULO_MEIO.items()
        }
        melhor_zona, melhor_mult = max(eficiencias_por_zona.items(), key=lambda kv: kv[1])
        safe_addstr(
            stdscr, 13, 2,
            f"   Vento ideal .......... {zona_label[melhor_zona]} ({melhor_mult*100:.0f}% vel.)",
        )
        safe_addstr(
            stdscr, 14, 2,
            f"   Zona morta (evite) ... {eficiencias_por_zona['zona_morta']*100:.0f}% vel.",
        )
        safe_addstr(stdscr, 16, 2, "SETA ESQUERDA/DIREITA muda | ENTER escolhe | ESC volta")
        stdscr.refresh()

        ch = stdscr.getch()
        if ch == _curses.KEY_LEFT:
            idx = (idx - 1) % len(TIPOS_NAVIO)
        elif ch == _curses.KEY_RIGHT:
            idx = (idx + 1) % len(TIPOS_NAVIO)
        elif ch in (_curses.KEY_ENTER, 10, 13):
            if motivo_bloqueio:
                continue
            return TIPOS_NAVIO[idx]
        elif ch == 27:
            return None


def tela_ajustes(stdscr, config: dict) -> None:
    """Tela de ajustes (hotkeys, cores, Unicode). ESC volta ao menu.

    Args:
        stdscr: Janela curses principal.
        config: Dict de configuração da sessão (modificado in-place).
    """
    itens = [
        ("Hotkeys", "hotkeys"),
        ("Cores", "cores"),
        ("Graficos Unicode", "unicode"),
        ("Textura do mar", "textura_mar"),
        ("Rastro do navio", "rastro"),
    ]
    idx = 0
    stdscr.nodelay(False)
    stdscr.timeout(-1)
    cores_disponiveis = bool(_curses and _curses.has_colors())
    while True:
        stdscr.erase()
        safe_addstr(stdscr, 0, 2, "AJUSTES", _curses.A_BOLD)
        safe_addstr(stdscr, 1, 2, "-" * 44)
        for i, (label, chave) in enumerate(itens):
            estado_txt = "LIGADO" if config[chave] else "DESLIGADO"
            marcador = "> " if i == idx else "  "
            attr = _curses.A_REVERSE if i == idx else 0
            safe_addstr(stdscr, 3 + i, 2, f"{marcador}{label:18s} <  {estado_txt}  >", attr)
        if not cores_disponiveis:
            safe_addstr(stdscr, 3 + len(itens), 2,
                        "(este terminal nao parece suportar cores)")

        row = 3 + len(itens) + 2
        safe_addstr(stdscr, row, 2,
                    "Com hotkeys LIGADO, teclas soltas controlam o navio sem")
        safe_addstr(stdscr, row + 1, 2,
                    "precisar digitar comando + ENTER (ver 'Como jogar').")
        safe_addstr(stdscr, row + 2, 2,
                    "Obs: com hotkeys ligado, 'a', 'l' e 'r' no prompt vazio")
        safe_addstr(stdscr, row + 3, 2,
                    "viram hotkeys em vez de iniciar 'ajuda'/'leme'/'reparar'.")
        safe_addstr(stdscr, row + 4, 2,
                    "Use TAB no prompt vazio pra digitar esses comandos mesmo assim.")
        safe_addstr(stdscr, row + 6, 2,
                    "Graficos Unicode troca o codigo de bussola do mapa por")
        safe_addstr(stdscr, row + 7, 2,
                    "setas unicode entre {chaves} (voce) / [colchetes] (inimigo).")
        safe_addstr(stdscr, row + 9, 2,
                    "SETA CIMA/BAIXO move | ESQUERDA/DIREITA ou ENTER alterna")
        safe_addstr(stdscr, row + 10, 2, "ESC volta ao menu")
        stdscr.refresh()

        ch = stdscr.getch()
        if ch == _curses.KEY_UP:
            idx = (idx - 1) % len(itens)
        elif ch == _curses.KEY_DOWN:
            idx = (idx + 1) % len(itens)
        elif ch in (_curses.KEY_LEFT, _curses.KEY_RIGHT, _curses.KEY_ENTER, 10, 13):
            chave = itens[idx][1]
            config[chave] = not config[chave]
        elif ch == 27:
            return


def tela_fim_mundo(stdscr, estado, estado_mundo, nome_capitao: str = "") -> str:
    """Tela de derrota do modo mundo aberto (frota vazia).

    Returns:
        'mundo' (novo capitão) | 'menu' | 'sair'
    """
    from ..core.utils import barra
    opcoes = [("Novo Capitao", "mundo"), ("Menu principal", "menu"), ("Sair", "sair")]
    idx = 0
    stdscr.nodelay(False)
    stdscr.timeout(-1)
    notoriedade = getattr(estado_mundo, "notoriedade", 0)
    attr_arte = _curses.color_pair(COR_VERMELHO) if (estado.cores_ativo and _curses) else 0
    while True:
        stdscr.erase()
        arte = list(ARTE_DERROTA)
        for i, l in enumerate(arte):
            safe_addstr(stdscr, i, 2, l, attr_arte)
        row = len(arte) + 1
        if nome_capitao:
            safe_addstr(stdscr, row, 2, f"Capitao: {nome_capitao:<20s}  Notoriedade: {notoriedade}")
        else:
            safe_addstr(stdscr, row, 2, f"Notoriedade: {notoriedade}")
        row += 2
        safe_addstr(stdscr, row, 2, "Estado final do navio:")
        row += 1
        for p in PARTES:
            safe_addstr(
                stdscr, row, 4,
                f"{p:8s} [{barra(estado.jogador.partes[p], 10)}] {estado.jogador.partes[p]:5.1f}%",
            )
            row += 1
        safe_addstr(
            stdscr, row, 4,
            f"{'moral':8s} [{barra(estado.jogador.moral_atual, 10)}] {estado.jogador.moral_atual:5.1f}%",
        )
        row += 2
        barris = estado.jogador.porao.barris
        if barris:
            resumo = "   ".join(f"{b.tipo}: {b.quantidade:.0f}u" for b in barris)
            safe_addstr(stdscr, row, 2, f"Porao ao afundar: {resumo}")
        else:
            safe_addstr(stdscr, row, 2, "Porao ao afundar: (vazio)")
        row += 2
        for i, (label, _) in enumerate(opcoes):
            marcador = "> " if i == idx else "  "
            attr = _curses.A_REVERSE if i == idx else 0
            safe_addstr(stdscr, row + i, 2, f"{marcador}[{i + 1}] {label}", attr)
        stdscr.refresh()
        ch = stdscr.getch()
        if ch == _curses.KEY_UP:
            idx = (idx - 1) % len(opcoes)
        elif ch == _curses.KEY_DOWN:
            idx = (idx + 1) % len(opcoes)
        elif ch in (_curses.KEY_ENTER, 10, 13):
            return opcoes[idx][1]
        elif ord('1') <= ch <= ord(str(len(opcoes))):
            return opcoes[ch - ord('1')][1]


def tela_mundo_menu(stdscr, tem_saves_ativos: bool, tem_historico: bool) -> str:
    """Sub-menu do Mundo Aberto: novo capitão, continuar, histórico ou voltar.

    As opções variam conforme o que já existe: 'Continuar' só aparece (e vem
    primeiro) se houver saves ativos; 'Capitaes Caidos' só aparece se houver
    histórico.

    Returns:
        'novo' | 'continuar' | 'historico' | 'voltar'
    """
    opcoes = []
    if tem_saves_ativos:
        opcoes.append(("Continuar", "continuar"))
    opcoes.append(("Novo Capitao", "novo"))
    if tem_historico:
        opcoes.append(("Capitaes Caidos", "historico"))
    opcoes.append(("Voltar", "voltar"))
    idx = 0
    stdscr.nodelay(False)
    stdscr.timeout(-1)
    while True:
        stdscr.erase()
        for i, l in enumerate(TITULO_ARTE):
            safe_addstr(stdscr, i, 2, l)
        row = len(TITULO_ARTE) + 1
        safe_addstr(stdscr, row, 2, "── Mundo Aberto ──────────────────────")
        row += 1
        for i, (label, _) in enumerate(opcoes):
            marcador = "> " if i == idx else "  "
            attr = _curses.A_REVERSE if i == idx else 0
            safe_addstr(stdscr, row + i, 2, f"{marcador}[{i + 1}] {label}", attr)
        stdscr.refresh()
        ch = stdscr.getch()
        if ch == _curses.KEY_UP:
            idx = (idx - 1) % len(opcoes)
        elif ch == _curses.KEY_DOWN:
            idx = (idx + 1) % len(opcoes)
        elif ch in (_curses.KEY_ENTER, 10, 13):
            return opcoes[idx][1]
        elif ch == 27:
            return "voltar"
        elif ord('1') <= ch <= ord(str(len(opcoes))):
            return opcoes[ch - ord('1')][1]


def tela_novo_capitao(stdscr) -> str | None:
    """Tela de entrada do nome do capitão.

    Returns:
        Nome digitado (str) ou None se ESC foi pressionado.
    """
    buf = ""
    msg = ""
    stdscr.nodelay(False)
    stdscr.timeout(-1)
    while True:
        stdscr.erase()
        for i, l in enumerate(TITULO_ARTE):
            safe_addstr(stdscr, i, 2, l)
        row = len(TITULO_ARTE) + 1
        safe_addstr(stdscr, row, 2, "── Novo Capitao ──────────────────────")
        safe_addstr(stdscr, row + 2, 2, "Nome do capitao:")
        safe_addstr(stdscr, row + 3, 4, f"{buf}_", _curses.A_BOLD)
        if msg:
            safe_addstr(stdscr, row + 5, 2, msg)
        safe_addstr(stdscr, row + 7, 2, "ENTER confirma  |  ESC cancela")
        stdscr.refresh()
        ch = stdscr.getch()
        if ch == 27:
            return None
        elif ch in (_curses.KEY_ENTER, 10, 13):
            nome = buf.strip()
            if len(nome) < 2:
                msg = "Nome muito curto (minimo 2 caracteres)."
            else:
                return nome
        elif ch in (_curses.KEY_BACKSPACE, 127, 8):
            buf = buf[:-1]
            msg = ""
        elif 32 <= ch <= 126 and len(buf) < 30:
            buf += chr(ch)
            msg = ""


def tela_continuar(stdscr, saves: list[dict]) -> str | None:
    """Lista saves ativos para o jogador escolher.

    Args:
        saves: Lista de dicts com 'slug', 'nome_capitao', 'tipo_navio', 'atualizado_em'.

    Returns:
        slug selecionado ou None (ESC / lista vazia).
    """
    stdscr.nodelay(False)
    stdscr.timeout(-1)
    if not saves:
        while True:
            stdscr.erase()
            safe_addstr(stdscr, 0, 2, "CONTINUAR", _curses.A_BOLD)
            safe_addstr(stdscr, 2, 2, "Nenhum capitao encontrado.")
            safe_addstr(stdscr, 4, 2, "ESC/ENTER para voltar.")
            stdscr.refresh()
            ch = stdscr.getch()
            if ch in (27, _curses.KEY_ENTER, 10, 13):
                return None
    idx = 0
    while True:
        stdscr.erase()
        safe_addstr(stdscr, 0, 2, "CONTINUAR", _curses.A_BOLD)
        safe_addstr(stdscr, 1, 2, "-" * 60)
        for i, s in enumerate(saves):
            marcador = "> " if i == idx else "  "
            attr = _curses.A_REVERSE if i == idx else 0
            linha = (
                f"{marcador}{s['nome_capitao']:<22s}"
                f"  [{s['tipo_navio']:6s}]"
                f"  {s['atualizado_em'][:16]}"
            )
            safe_addstr(stdscr, 2 + i, 2, linha, attr)
        safe_addstr(stdscr, 2 + len(saves) + 1, 2, "SETA CIMA/BAIXO: selecionar  ENTER: carregar  ESC: voltar")
        stdscr.refresh()
        ch = stdscr.getch()
        if ch == _curses.KEY_UP:
            idx = (idx - 1) % len(saves)
        elif ch == _curses.KEY_DOWN:
            idx = (idx + 1) % len(saves)
        elif ch in (_curses.KEY_ENTER, 10, 13):
            return saves[idx]["slug"]
        elif ch == 27:
            return None


def tela_historico(stdscr, historico: list[dict]) -> None:
    """Tela read-only de capitães caídos."""
    stdscr.nodelay(False)
    stdscr.timeout(-1)
    while True:
        stdscr.erase()
        safe_addstr(stdscr, 0, 2, "CAPITAES CAIDOS", _curses.A_BOLD)
        safe_addstr(stdscr, 1, 2, "-" * 60)
        if not historico:
            safe_addstr(stdscr, 3, 2, "Nenhum capitao caido ainda.")
        else:
            for i, h in enumerate(historico):
                duracao = h.get("duracao_segundos", 0)
                minutos = duracao // 60
                segundos = duracao % 60
                causa = h.get("causa_morte") or "desconhecida"
                not_max = h.get("notoriedade_maxima", 0)
                linha = (
                    f"{h['nome_capitao']:<20s}  "
                    f"Causa: {causa:<14s}  "
                    f"Not.: {not_max:4d}  "
                    f"Tempo: {minutos:02d}:{segundos:02d}"
                )
                safe_addstr(stdscr, 2 + i, 2, linha)
        safe_addstr(stdscr, max(4, 3 + len(historico)) + 1, 2, "ESC/ENTER para voltar.")
        stdscr.refresh()
        ch = stdscr.getch()
        if ch in (27, _curses.KEY_ENTER, 10, 13):
            return


def tela_arena_menu(stdscr, tem_historico: bool) -> str:
    """Sub-menu da Arena: iniciar campanha, campanhas anteriores ou voltar.

    'Campanhas Anteriores' só aparece se houver histórico (mesma regra do
    sub-menu do Mundo Aberto).

    Returns:
        'nova' | 'historico' | 'voltar'
    """
    opcoes = [("Iniciar Campanha", "nova")]
    if tem_historico:
        opcoes.append(("Campanhas Anteriores", "historico"))
    opcoes.append(("Voltar", "voltar"))
    idx = 0
    stdscr.nodelay(False)
    stdscr.timeout(-1)
    while True:
        stdscr.erase()
        for i, l in enumerate(TITULO_ARTE):
            safe_addstr(stdscr, i, 2, l)
        row = len(TITULO_ARTE) + 1
        safe_addstr(stdscr, row, 2, "── Arena ──────────────────────────────")
        row += 1
        for i, (label, _) in enumerate(opcoes):
            marcador = "> " if i == idx else "  "
            attr = _curses.A_REVERSE if i == idx else 0
            safe_addstr(stdscr, row + i, 2, f"{marcador}[{i + 1}] {label}", attr)
        stdscr.refresh()
        ch = stdscr.getch()
        if ch == _curses.KEY_UP:
            idx = (idx - 1) % len(opcoes)
        elif ch == _curses.KEY_DOWN:
            idx = (idx + 1) % len(opcoes)
        elif ch in (_curses.KEY_ENTER, 10, 13):
            return opcoes[idx][1]
        elif ch == 27:
            return "voltar"
        elif ord('1') <= ch <= ord(str(len(opcoes))):
            return opcoes[ch - ord('1')][1]


def tela_arena_historico(stdscr, historico: list[dict]) -> None:
    """Tela read-only de campanhas de Arena já finalizadas."""
    stdscr.nodelay(False)
    stdscr.timeout(-1)
    while True:
        stdscr.erase()
        safe_addstr(stdscr, 0, 2, "CAMPANHAS ANTERIORES", _curses.A_BOLD)
        safe_addstr(stdscr, 1, 2, "-" * 60)
        if not historico:
            safe_addstr(stdscr, 3, 2, "Nenhuma campanha finalizada ainda.")
        else:
            for i, h in enumerate(historico):
                duracao = h.get("duracao_segundos", 0)
                minutos = duracao // 60
                segundos = duracao % 60
                causa = h.get("causa_fim") or "desconhecida"
                rodadas = h.get("rodadas_vencidas", 0)
                linha = (
                    f"{h['nome_capitao']:<20s}  "
                    f"[{h.get('tipo_navio', '?'):6s}]  "
                    f"Rodadas: {rodadas:3d}  "
                    f"Fim: {causa:<12s}  "
                    f"Tempo: {minutos:02d}:{segundos:02d}"
                )
                safe_addstr(stdscr, 2 + i, 2, linha)
        safe_addstr(stdscr, max(4, 3 + len(historico)) + 1, 2, "ESC/ENTER para voltar.")
        stdscr.refresh()
        ch = stdscr.getch()
        if ch in (27, _curses.KEY_ENTER, 10, 13):
            return


def tela_fim(stdscr, estado) -> str:
    """Tela de fim de jogo com estatísticas e opções de continuidade.

    Args:
        stdscr: Janela curses principal.
        estado: Estado finalizado da partida.

    Returns:
        'jogar' (nova partida), 'menu' (menu principal) ou 'sair'.
    """
    stdscr.nodelay(False)
    stdscr.timeout(-1)
    opcoes = [("Jogar novamente", "jogar"), ("Menu principal", "menu"), ("Sair", "sair")]
    idx = 0
    while True:
        stdscr.erase()
        if estado.fim == "vitoria":
            arte = list(ARTE_VITORIA)
            attr_arte = _curses.color_pair(COR_VERDE) if (estado.cores_ativo and _curses) else 0
        elif estado.fim == "fuga":
            arte = list(ARTE_FUGA)
            attr_arte = _curses.color_pair(COR_AMARELO) if (estado.cores_ativo and _curses) else 0
        elif estado.fim == "fuga_jogador":
            arte = list(ARTE_FUGA_JOGADOR)
            attr_arte = _curses.color_pair(COR_AMARELO) if (estado.cores_ativo and _curses) else 0
        else:
            arte = list(ARTE_DERROTA)
            attr_arte = _curses.color_pair(COR_VERMELHO) if (estado.cores_ativo and _curses) else 0

        linhas = [""]
        linhas.append(
            f"Navio: {estado.jogador.tipo_nome}   "
            f"Tempo de batalha: {estado.tempo:.1f}s"
        )
        linhas.append(
            f"Tiros disparados: {estado.stats['tiros_jogador']}  "
            f"Acertos: {estado.stats['acertos_jogador']}"
        )
        linhas.append(
            f"Tiros recebidos:  {estado.stats['tiros_inimigo']}  "
            f"Acertos do inimigo: {estado.stats['acertos_inimigo']}"
        )
        linhas.append("")
        linhas.append("Estado final do seu navio:")
        for p in PARTES:
            linhas.append(
                f"  {p:8s}[{barra(estado.jogador.partes[p], 10)}] "
                f"{estado.jogador.partes[p]:5.1f}%"
            )
        linhas.append(
            f"  moral   [{barra(estado.jogador.moral_atual, 10)}] "
            f"{estado.jogador.moral_atual:5.1f}%"
        )
        linhas.append("")

        for i, l in enumerate(arte):
            safe_addstr(stdscr, i, 2, l, attr_arte)
        for i, l in enumerate(linhas):
            safe_addstr(stdscr, len(arte) + i, 2, l)
        total_linhas = len(arte) + len(linhas)
        base = total_linhas + 1
        for i, (label, _) in enumerate(opcoes):
            marcador = "> " if i == idx else "  "
            attr = _curses.A_REVERSE if i == idx else 0
            safe_addstr(stdscr, base + i, 2, f"{marcador}[{i + 1}] {label}", attr)
        stdscr.refresh()

        ch = stdscr.getch()
        if ch == _curses.KEY_UP:
            idx = (idx - 1) % len(opcoes)
        elif ch == _curses.KEY_DOWN:
            idx = (idx + 1) % len(opcoes)
        elif ch in (_curses.KEY_ENTER, 10, 13):
            return opcoes[idx][1]
        elif ord('1') <= ch <= ord(str(len(opcoes))):
            return opcoes[ch - ord('1')][1]


def tela_fim_arena(stdscr, estado, rodada: int) -> str:
    """Tela de fim de rodada da Arena: mesma arte/stats de tela_fim, mas com
    a opção de avançar pra próxima rodada da mesma campanha em caso de vitória.

    Args:
        stdscr: Janela curses principal.
        estado: Estado finalizado da rodada de combate.
        rodada:  Número da rodada atual (1-based).

    Returns:
        'proxima' (só possível em vitória), 'menu' ou 'sair'.
    """
    stdscr.nodelay(False)
    stdscr.timeout(-1)
    if estado.fim == "vitoria":
        opcoes = [("Proxima batalha", "proxima"), ("Encerrar campanha", "menu"), ("Sair", "sair")]
    else:
        opcoes = [("Encerrar campanha", "menu"), ("Sair", "sair")]
    idx = 0
    while True:
        stdscr.erase()
        if estado.fim == "vitoria":
            arte = list(ARTE_VITORIA)
            attr_arte = _curses.color_pair(COR_VERDE) if (estado.cores_ativo and _curses) else 0
        elif estado.fim == "fuga":
            arte = list(ARTE_FUGA)
            attr_arte = _curses.color_pair(COR_AMARELO) if (estado.cores_ativo and _curses) else 0
        elif estado.fim == "fuga_jogador":
            arte = list(ARTE_FUGA_JOGADOR)
            attr_arte = _curses.color_pair(COR_AMARELO) if (estado.cores_ativo and _curses) else 0
        else:
            arte = list(ARTE_DERROTA)
            attr_arte = _curses.color_pair(COR_VERMELHO) if (estado.cores_ativo and _curses) else 0

        linhas = [""]
        linhas.append(f"Arena — Rodada {rodada}")
        linhas.append(
            f"Navio: {estado.jogador.tipo_nome}   "
            f"Tempo de batalha: {estado.tempo:.1f}s"
        )
        linhas.append(
            f"Tiros disparados: {estado.stats['tiros_jogador']}  "
            f"Acertos: {estado.stats['acertos_jogador']}"
        )
        linhas.append(
            f"Tiros recebidos:  {estado.stats['tiros_inimigo']}  "
            f"Acertos do inimigo: {estado.stats['acertos_inimigo']}"
        )
        linhas.append("")

        for i, l in enumerate(arte):
            safe_addstr(stdscr, i, 2, l, attr_arte)
        for i, l in enumerate(linhas):
            safe_addstr(stdscr, len(arte) + i, 2, l)
        total_linhas = len(arte) + len(linhas)
        base = total_linhas + 1
        for i, (label, _) in enumerate(opcoes):
            marcador = "> " if i == idx else "  "
            attr = _curses.A_REVERSE if i == idx else 0
            safe_addstr(stdscr, base + i, 2, f"{marcador}[{i + 1}] {label}", attr)
        stdscr.refresh()

        ch = stdscr.getch()
        if ch == _curses.KEY_UP:
            idx = (idx - 1) % len(opcoes)
        elif ch == _curses.KEY_DOWN:
            idx = (idx + 1) % len(opcoes)
        elif ch in (_curses.KEY_ENTER, 10, 13):
            return opcoes[idx][1]
        elif ord('1') <= ch <= ord(str(len(opcoes))):
            return opcoes[ch - ord('1')][1]
