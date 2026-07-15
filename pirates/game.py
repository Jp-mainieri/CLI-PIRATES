"""
game.py – Loop principal do jogo e inicialização curses de CLI PIRATES.

Contém jogo_loop() (loop de entrada+simulação+renderização) e main()
(setup curses + máquina de estados de telas).
"""

import locale
import time

try:
    import curses as _curses
except ImportError:
    _curses = None  # type: ignore[assignment]

from .constants import (
    SIM_TICK, POLL_MS,
    COR_VERDE, COR_AMARELO, COR_VERMELHO,
    COR_JOGADOR, COR_INIMIGO, COR_MAR,
    MODO_ADM_DISPONIVEL,
)
from .core.state import Estado
from .input.commands import processar_comando, obter_candidatos
from .input.hotkeys import processar_hotkey
from .core.simulation import atualizar_simulacao
from .ui.renderer import desenhar_tela
from .ui.menus import tela_menu, tela_como_jogar, tela_navio, tela_ajustes, tela_fim


def jogo_loop(stdscr, config: dict) -> str:
    """Loop principal de uma partida: lê entrada, simula e redesenha.

    O loop roda sem bloqueio (nodelay=True) com timeout de POLL_MS ms.
    A simulação é avançada quando o delta real acumulado supera SIM_TICK.

    Args:
        stdscr: Janela curses principal.
        config: Dict com as opções da sessão.

    Returns:
        Próxima tela a exibir: 'jogar', 'menu' ou 'sair'.
    """
    stdscr.nodelay(True)
    stdscr.timeout(POLL_MS)

    cores = config["cores"] and bool(_curses and _curses.has_colors())
    estado = Estado(
        tipo_navio=config["tipo_navio"],
        hotkeys=config["hotkeys"],
        cores=cores,
        graficos_unicode=config["unicode"],
    )
    buffer_entrada = ""
    last_tick = time.time()
    tab_estado: dict = {"ativo": False, "candidatos": [], "indice": 0, "prefixo": ""}

    while estado.rodando:
        ch = stdscr.getch()
        if ch != -1:
            if ch == 27:  # ESC
                estado.rodando = False
                estado.fim = estado.fim or "derrota"
            elif ch in (_curses.KEY_ENTER, 10, 13):
                if buffer_entrada.strip():
                    processar_comando(buffer_entrada.strip(), estado)
                    estado.ultimo_comando = buffer_entrada.strip()
                elif estado.ultimo_comando:
                    processar_comando(estado.ultimo_comando, estado)
                buffer_entrada = ""
                tab_estado["ativo"] = False
            elif ch in (_curses.KEY_BACKSPACE, 127, 8):
                buffer_entrada = buffer_entrada[:-1]
                tab_estado["ativo"] = False
            elif ch == 9:  # TAB
                if tab_estado["ativo"] and tab_estado["candidatos"]:
                    tab_estado["indice"] = (
                        (tab_estado["indice"] + 1) % len(tab_estado["candidatos"])
                    )
                else:
                    if buffer_entrada == "" or buffer_entrada.endswith(' '):
                        tokens_completos = [t for t in buffer_entrada.split(' ') if t != '']
                        partial = ''
                    else:
                        partes_buf = buffer_entrada.split(' ')
                        tokens_completos = [t for t in partes_buf[:-1] if t != '']
                        partial = partes_buf[-1]
                    prefixo = (' '.join(tokens_completos) + ' ') if tokens_completos else ''
                    candidatos = obter_candidatos(tokens_completos, partial, estado)
                    tab_estado.update({
                        "candidatos": candidatos,
                        "prefixo": prefixo,
                        "indice": 0,
                        "ativo": True,
                    })
                if tab_estado["candidatos"]:
                    buffer_entrada = (
                        tab_estado["prefixo"]
                        + tab_estado["candidatos"][tab_estado["indice"]]
                    )
            elif MODO_ADM_DISPONIVEL and ch == _curses.KEY_F12:
                estado.modo_adm = not estado.modo_adm
            elif estado.hotkeys_ativo and buffer_entrada == "" and processar_hotkey(ch, estado):
                pass
            elif 32 <= ch <= 126:
                buffer_entrada += chr(ch)
                tab_estado["ativo"] = False

        agora = time.time()
        if agora - last_tick >= SIM_TICK:
            atualizar_simulacao(estado, agora - last_tick)
            last_tick = agora

        desenhar_tela(stdscr, estado, buffer_entrada)

    if estado.fim is None:
        estado.fim = "derrota"
    return tela_fim(stdscr, estado)


def main(stdscr) -> None:
    """Configura curses e gerencia a máquina de estados de telas.

    Args:
        stdscr: Janela curses fornecida por curses.wrapper().
    """
    try:
        locale.setlocale(locale.LC_ALL, '')
    except locale.Error:
        pass

    _curses.curs_set(0)
    _curses.noecho()
    stdscr.keypad(True)

    if _curses.has_colors():
        _curses.start_color()
        try:
            _curses.use_default_colors()
            fundo = -1
        except _curses.error:
            fundo = _curses.COLOR_BLACK
        _curses.init_pair(COR_VERDE,    _curses.COLOR_GREEN,   fundo)
        _curses.init_pair(COR_AMARELO,  _curses.COLOR_YELLOW,  fundo)
        _curses.init_pair(COR_VERMELHO, _curses.COLOR_RED,     fundo)
        _curses.init_pair(COR_JOGADOR,  _curses.COLOR_CYAN,    fundo)
        _curses.init_pair(COR_INIMIGO,  _curses.COLOR_MAGENTA, fundo)
        _curses.init_pair(COR_MAR,      _curses.COLOR_BLUE,    fundo)

    config = {"tipo_navio": "normal", "hotkeys": False, "cores": False, "unicode": False}
    tela_atual = "menu"

    while tela_atual != "sair":
        if tela_atual == "menu":
            tela_atual = tela_menu(stdscr)
        elif tela_atual == "como_jogar":
            tela_como_jogar(stdscr)
            tela_atual = "menu"
        elif tela_atual == "navio":
            tela_navio(stdscr, config)
            tela_atual = "menu"
        elif tela_atual == "ajustes":
            tela_ajustes(stdscr, config)
            tela_atual = "menu"
        elif tela_atual == "jogar":
            tela_atual = jogo_loop(stdscr, config)
        else:
            tela_atual = "menu"


def run() -> None:
    """Ponto de entrada instalável via pyproject.toml [project.scripts]."""
    import sys
    try:
        _curses.wrapper(main)
    except KeyboardInterrupt:
        pass
    except _curses.error as e:
        print(f"Erro de terminal (talvez a janela esteja pequena demais): {e}")
        sys.exit(1)
