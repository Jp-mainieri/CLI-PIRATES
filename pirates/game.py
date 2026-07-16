"""
game.py – Loop principal do jogo e inicialização curses de CLI PIRATES.

Contém jogo_loop() (loop de entrada+simulação+renderização) e main()
(setup curses + máquina de estados de telas).
"""

import locale
import math
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
    PARTES, NAVIO_TIPOS,
    MUNDO_TICK, MUNDO_GATILHO_COMBATE, MUNDO_RAIO_COLETA_LOOT,
)
from .core.state import Estado
from .core.ship import Canhao
from .core.porao import gerar_porao_inimigo, coletar_loot
from .input.commands import processar_comando, obter_candidatos
from .input.hotkeys import processar_hotkey
from .core.simulation import atualizar_simulacao
from .ui.renderer import desenhar_tela, desenhar_tela_mundo
from .ui.menus import tela_menu, tela_como_jogar, tela_navio, tela_ajustes, tela_fim
from .world.state import EstadoMundo
from .world.simulation import (
    atualizar_ia_mundo, atualizar_jogador_mundo,
    mundo_para_arena, arena_para_mundo,
)


def jogo_loop(stdscr, config: dict, estado: 'Estado | None' = None) -> str:
    """Loop principal de uma partida: lê entrada, simula e redesenha.

    O loop roda sem bloqueio (nodelay=True) com timeout de POLL_MS ms.
    A simulação é avançada quando o delta real acumulado supera SIM_TICK.

    Args:
        stdscr: Janela curses principal.
        config: Dict com as opções da sessão.
        estado: Estado de combate pré-configurado (passado pelo mundo_loop).
                Se None, cria um novo Estado internamente.

    Returns:
        Próxima tela a exibir: 'jogar', 'menu' ou 'sair'.
    """
    stdscr.nodelay(True)
    stdscr.timeout(POLL_MS)

    cores = config["cores"] and bool(_curses and _curses.has_colors())
    if estado is None:
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


def mundo_loop(stdscr, config: dict) -> str:
    """Loop de navegação livre no mundo aberto.

    Cria e mantém um Estado persistente do jogador (dano, tripulação, moral) e
    um EstadoMundo para os navios inimigos. Quando um inimigo se aproxima a
    menos de MUNDO_GATILHO_COMBATE, transforma coordenadas e chama jogo_loop
    com o Estado já configurado. Ao terminar a batalha, transforma de volta.

    Args:
        stdscr: Janela curses principal.
        config: Dict com opções da sessão.

    Returns:
        Próxima tela: 'menu' ou 'sair'.
    """
    stdscr.nodelay(True)
    stdscr.timeout(POLL_MS)

    cores = config["cores"] and bool(_curses and _curses.has_colors())
    tipo_navio = config["tipo_navio"]
    params = NAVIO_TIPOS[tipo_navio]

    # Estado persistente do jogador (Navio + crew assignments vivem aqui)
    estado = Estado(
        tipo_navio=tipo_navio,
        hotkeys=config["hotkeys"],
        cores=cores,
        graficos_unicode=config["unicode"],
    )
    # Sem inimigo em cena durante a navegação; visão do capitão mostra apenas água.
    estado.inimigo.afundado = True
    estado.log.clear()
    estado.log.append(
        f"Navegando no mundo aberto. [{params['navio'].upper()}] "
        f"Use M para o mapa-mundo. Gatilho de combate: 750m."
    )

    # Estado do mundo aberto (posicoes, inimigos NavioMundo)
    estado_mundo = EstadoMundo(tipo_navio)
    estado_mundo.jogador_heading = estado.jogador.heading

    buffer_entrada = ""
    last_tick = time.time()
    tab_estado: dict = {"ativo": False, "candidatos": [], "indice": 0, "prefixo": ""}

    # Mantém tempo acumulado para exibição no header
    estado.tempo = 0.0

    while True:
        ch = stdscr.getch()
        if ch != -1:
            if ch == 27:  # ESC → menu
                return "menu"
            elif ch in (ord('M'), ord('m')):
                estado_mundo.mapa_mundo_visivel = not estado_mundo.mapa_mundo_visivel
            elif MODO_ADM_DISPONIVEL and ch == _curses.KEY_F12:
                estado.modo_adm = not estado.modo_adm
            elif ch in (_curses.KEY_ENTER, 10, 13):
                cmd = buffer_entrada.strip()
                if cmd:
                    _processar_cmd_mundo(cmd, estado, estado_mundo)
                    estado.ultimo_comando = cmd
                elif estado.ultimo_comando:
                    _processar_cmd_mundo(estado.ultimo_comando, estado, estado_mundo)
                buffer_entrada = ""
                tab_estado["ativo"] = False
            elif ch in (_curses.KEY_BACKSPACE, 127, 8):
                buffer_entrada = buffer_entrada[:-1]
                tab_estado["ativo"] = False
            elif ch == 9:  # TAB
                if tab_estado["ativo"] and tab_estado["candidatos"]:
                    tab_estado["indice"] = (tab_estado["indice"] + 1) % len(tab_estado["candidatos"])
                else:
                    if buffer_entrada == "" or buffer_entrada.endswith(' '):
                        tokens_completos = [t for t in buffer_entrada.split(' ') if t]
                        partial = ''
                    else:
                        partes_buf = buffer_entrada.split(' ')
                        tokens_completos = [t for t in partes_buf[:-1] if t]
                        partial = partes_buf[-1]
                    prefixo = (' '.join(tokens_completos) + ' ') if tokens_completos else ''
                    candidatos = obter_candidatos(tokens_completos, partial, estado)
                    tab_estado.update({"candidatos": candidatos, "prefixo": prefixo,
                                       "indice": 0, "ativo": True})
                if tab_estado["candidatos"]:
                    buffer_entrada = tab_estado["prefixo"] + tab_estado["candidatos"][tab_estado["indice"]]
            elif estado.hotkeys_ativo and buffer_entrada == "" and processar_hotkey(ch, estado):
                # Sync leme/vela do estado.jogador para estado_mundo
                estado_mundo.jogador_heading_alvo = estado.jogador.heading_alvo
                estado_mundo.jogador_nivel_vela = estado.jogador.nivel_vela
            elif 32 <= ch <= 126:
                buffer_entrada += chr(ch)
                tab_estado["ativo"] = False

        agora = time.time()
        if agora - last_tick >= MUNDO_TICK:
            dt = agora - last_tick
            last_tick = agora
            estado.tempo += dt

            # Sync controles do jogador para o mundo
            estado_mundo.jogador_heading_alvo = estado.jogador.heading_alvo
            estado_mundo.jogador_nivel_vela = estado.jogador.nivel_vela

            atualizar_jogador_mundo(estado_mundo, params, dt)
            atualizar_ia_mundo(estado_mundo, dt)

            # Sync heading/velocidade de volta pro navio (usado na bussola e HUD)
            estado.jogador.heading = estado_mundo.jogador_heading
            estado.jogador.velocidade = estado_mundo.jogador_velocidade

            # Reparo, água e moral durante navegação
            for parte, n in estado.crew_reparo.items():
                estado.jogador.reparar(parte, n, dt)
            estado.jogador.atualizar_agua(estado.crew_bomba, dt)
            estado.jogador.atualizar_moral(dt)

            if estado.jogador.afundado:
                estado.log.append("Seu navio afundou durante a navegacao!")
                estado.fim = "derrota"
                return tela_fim(stdscr, estado)

            # Verificar gatilho de combate
            inimigo_engajado = None
            for navio in estado_mundo.inimigos:
                if navio.status == "afundado":
                    continue
                d = estado_mundo._distancia_toroidal(
                    estado_mundo.jogador_x, estado_mundo.jogador_y,
                    navio.x, navio.y,
                )
                if d < MUNDO_GATILHO_COMBATE:
                    inimigo_engajado = navio
                    break

            if inimigo_engajado is not None:
                # Despawna navios não-engajados
                estado_mundo.inimigos = [
                    n for n in estado_mundo.inimigos
                    if n is inimigo_engajado or n.status == "afundado"
                ]

                # Transformação mundo → arena
                inimigo_dx, inimigo_dy, ox, oy = mundo_para_arena(estado_mundo, inimigo_engajado)

                # Configura estado.jogador na origem da arena
                estado.jogador.x = 0.0
                estado.jogador.y = 0.0

                # Configura estado.inimigo a partir do NavioMundo
                estado.inimigo.x = inimigo_dx
                estado.inimigo.y = inimigo_dy
                estado.inimigo.heading = inimigo_engajado.heading
                estado.inimigo.heading_alvo = inimigo_engajado.heading
                estado.inimigo.velocidade = inimigo_engajado.velocidade
                estado.inimigo.afundado = False
                if inimigo_engajado.partes is not None:
                    estado.inimigo.partes = dict(inimigo_engajado.partes)
                    estado.inimigo.agua = inimigo_engajado.agua
                    estado.inimigo.moral_atual = inimigo_engajado.moral_atual or 100.0
                else:
                    for p in PARTES:
                        estado.inimigo.partes[p] = 100.0
                    estado.inimigo.agua = 0.0
                    estado.inimigo.moral_atual = 100.0

                cap = params["porao_capacidade"]
                if inimigo_engajado.porao is not None:
                    estado.inimigo.porao = inimigo_engajado.porao
                else:
                    estado.inimigo.porao = gerar_porao_inimigo(cap)
                    inimigo_engajado.porao = estado.inimigo.porao

                for lado in ('bombordo', 'estibordo'):
                    for c in estado.inimigo.canhoes[lado]:
                        c.tripulantes = 0
                        c.dist_alvo = None
                        c.proximo_tiro = 0.0
                        c.aviso_sem_municao = False

                # Reset do estado de combate
                estado.rodando = True
                estado.fim = None
                estado.tempo = 0.0
                estado.zoom_atual = None
                estado.zoom_mudou_em = -999.0
                estado.inimigo_em_fuga = False
                estado.tempo_fuga_longe = 0.0
                estado.stats = {
                    "tiros_jogador": 0, "acertos_jogador": 0,
                    "tiros_inimigo": 0, "acertos_inimigo": 0,
                }
                estado.log.clear()
                d_ini = (inimigo_dx ** 2 + inimigo_dy ** 2) ** 0.5
                estado.log.append(f"Combate! Inimigo a {d_ini:.0f}m. Prepare-se!")

                # Corre o loop de combate com o estado já configurado
                resultado = jogo_loop(stdscr, config, estado=estado)

                # Transformação arena → mundo
                estado_mundo.jogador_x, estado_mundo.jogador_y = arena_para_mundo(
                    ox, oy, estado.jogador.x, estado.jogador.y,
                )
                estado_mundo.jogador_heading = estado.jogador.heading
                estado_mundo.jogador_velocidade = estado.jogador.velocidade

                if estado.fim == "derrota":
                    return resultado

                elif estado.fim == "vitoria":
                    inimigo_engajado.status = "afundado"
                    inimigo_engajado.x, inimigo_engajado.y = arena_para_mundo(
                        ox, oy, estado.inimigo.x, estado.inimigo.y,
                    )
                    inimigo_engajado.loot = estado.inimigo.porao
                    inimigo_engajado.porao = None

                elif estado.fim == "fuga":
                    inimigo_engajado.status = "fugindo"
                    inimigo_engajado.x, inimigo_engajado.y = arena_para_mundo(
                        ox, oy, estado.inimigo.x, estado.inimigo.y,
                    )
                    inimigo_engajado.moral_atual = estado.inimigo.moral_atual
                    inimigo_engajado.partes = dict(estado.inimigo.partes)
                    inimigo_engajado.agua = estado.inimigo.agua
                    inimigo_engajado.porao = estado.inimigo.porao

                # Reset do aviso de munição dos canhões do jogador
                for lado in ('bombordo', 'estibordo'):
                    for c in estado.jogador.canhoes[lado]:
                        c.aviso_sem_municao = False

                # Reabastece lote (mantém afundados + fugindo, adiciona novos)
                estado_mundo.sortear_novo_lote()

                # Reseta tempo e log para navegação; visão do capitão volta a mostrar água.
                estado.inimigo.afundado = True
                estado.rodando = True
                estado.fim = None
                estado.tempo = 0.0
                estado.log.clear()
                estado.log.append("Batalha encerrada. Navegando novamente.")

        # Coleta automática de loot de destroços próximos
        for navio_loot in estado_mundo.inimigos:
            if navio_loot.status == "afundado" and navio_loot.loot is not None:
                d_loot = estado_mundo._distancia_toroidal(
                    estado_mundo.jogador_x, estado_mundo.jogador_y,
                    navio_loot.x, navio_loot.y,
                )
                if d_loot < MUNDO_RAIO_COLETA_LOOT:
                    resto = coletar_loot(estado.jogador.porao, navio_loot.loot)
                    if not resto.barris:
                        navio_loot.loot = None
                        estado.log.append("Voce coletou os destrocos!")
                    else:
                        estado_mundo.loot_pendente = resto
                        navio_loot.loot = None
                        estado.log.append("Porcao coletada! Porcao restante no inventario pendente.")
                    break

        desenhar_tela_mundo(stdscr, estado, estado_mundo, buffer_entrada)


def _processar_cmd_mundo(texto: str, estado: 'Estado', estado_mundo: 'EstadoMundo') -> None:
    """Processa comando no modo navegação.

    Intercepta 'mapa' e 'radar' (comportamento específico do mundo).
    Demais comandos são delegados a processar_comando normalmente.
    """
    partes = texto.strip().lower().split()
    if not partes:
        return
    cmd = partes[0]
    if cmd == "mapa":
        estado_mundo.mapa_mundo_visivel = not estado_mundo.mapa_mundo_visivel
        estado.log.append(
            f"Mapa mundo: {'visivel' if estado_mundo.mapa_mundo_visivel else 'oculto'}"
        )
    elif cmd == "radar":
        min_d = float('inf')
        for navio in estado_mundo.inimigos:
            if navio.status != "afundado":
                d = estado_mundo._distancia_toroidal(
                    estado_mundo.jogador_x, estado_mundo.jogador_y,
                    navio.x, navio.y,
                )
                if d < min_d:
                    min_d = d
        if min_d < float('inf'):
            estado.log.append(f"RADAR: inimigo mais proximo a {min_d:.0f}m")
        else:
            estado.log.append("RADAR: nenhum inimigo detectado")
    else:
        processar_comando(texto, estado)


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
        elif tela_atual == "mundo":
            tela_atual = mundo_loop(stdscr, config)
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
