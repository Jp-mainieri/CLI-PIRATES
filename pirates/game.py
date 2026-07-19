"""
game.py – Loop principal do jogo e inicialização curses de CLI PIRATES.

Contém jogo_loop() (loop de entrada+simulação+renderização) e main()
(setup curses + máquina de estados de telas).
"""

import locale
import math
import signal
import time

try:
    import curses as _curses
except ImportError:
    _curses = None  # type: ignore[assignment]

from .constants import (
    SIM_TICK, POLL_MS,
    COR_VERDE, COR_AMARELO, COR_VERMELHO,
    COR_JOGADOR, COR_INIMIGO, COR_MAR, COR_ILHA,
    MODO_ADM_DISPONIVEL,
    PARTES, NAVIO_TIPOS,
    MUNDO_TAMANHO, MAPA_TAMANHO,
    MUNDO_TICK, MUNDO_GATILHO_COMBATE, MUNDO_RAIO_COLETA_LOOT, MUNDO_RAIO_ATRACACAO,
    DANO_COLISAO_BASE, DANO_COLISAO_K, DANO_COLISAO_V_REF,
)
from .core.state import Estado, sincronizar_crew_com_navio_ativo
from .core.ship import criar_canhoes
from .core.porao import gerar_porao_inimigo, coletar_loot
from .core.notoriedade import (
    sortear_bonus_elite, pontos_por_afundamento, pontos_perdidos_por_fuga,
    bloqueios_mundo, bloqueios_arena,
)
from .input.commands import processar_comando, obter_candidatos
from .input.hotkeys import processar_hotkey
from .core.simulation import atualizar_simulacao
from .ui.renderer import desenhar_tela, desenhar_tela_mundo
from .saves import (
    criar_novo_save, salvar, carregar, restaurar_estado,
    listar_saves_ativos, listar_historico,
    salvar_resultado_arena, listar_arena_historico,
    melhor_faixa_notoriedade_alcancada, melhor_vitorias_arena,
)
from .ui.menus import (
    tela_menu, tela_como_jogar, tela_navio, tela_ajustes, tela_fim,
    tela_mundo_menu, tela_novo_capitao, tela_continuar, tela_historico,
    tela_fim_mundo, tela_arena_menu, tela_arena_historico, tela_fim_arena,
)
from .world.state import EstadoMundo
from .world.simulation import (
    atualizar_ia_mundo, atualizar_jogador_mundo,
    mundo_para_arena, arena_para_mundo,
)
from .port.scene import porto_loop


# Contexto global para o handler de SIGINT salvar antes de sair.
_save_ctx: list = []  # [estado, estado_mundo, slug] quando em mundo_loop


def _sigint_handler(_sig, _frame) -> None:
    if _save_ctx:
        try:
            salvar(_save_ctx[0], _save_ctx[1], _save_ctx[2])
        except Exception:
            pass
    raise SystemExit(0)


def _tentar_respawn(estado, estado_mundo):
    """Verifica frota e faz respawn no porto mais próximo com o próximo navio.

    Retorna o Porto de respawn, ou None se a frota estiver vazia.
    """
    frota = estado.frota
    candidatos = [
        (i, n) for i, n in enumerate(frota.navios)
        if n.porto_ancorado is not None and not n.navio.afundado
    ]
    if not candidatos:
        return None

    pos_afundamento = (estado_mundo.jogador_x, estado_mundo.jogador_y)
    estado_mundo.destrocos_jogador.append(pos_afundamento)
    estado.jogador.porao.barris.clear()

    idx_real, novo = candidatos[0]
    novo.porto_ancorado = None
    frota.indice_ativo = idx_real
    estado.jogador = novo.navio
    sincronizar_crew_com_navio_ativo(estado, novo.tipo)
    estado_mundo.tipo_navio = novo.tipo

    porto = min(
        estado_mundo.portos,
        key=lambda p: estado_mundo._distancia_toroidal(
            pos_afundamento[0], pos_afundamento[1], p.x, p.y,
        ),
    )

    estado_mundo.jogador_x = porto.x
    estado_mundo.jogador_y = porto.y
    estado_mundo.jogador_velocidade = 0.0
    estado_mundo.jogador_heading = 0.0
    estado_mundo.jogador_heading_alvo = 0.0
    estado_mundo.jogador_nivel_vela = 0

    estado.fim = None
    estado.jogador.afundado = False
    estado_mundo.em_combate = False
    estado_mundo.inimigo_engajado = None

    estado.log.clear()
    estado.log.append(
        f"Navio afundou! Voltou a {porto.nome} com '{novo.nome}'."
    )
    return porto


def _processar_morte_mundo(stdscr, estado, estado_mundo, slug, causa: str) -> str:
    """Game over definitivo: migra save para histórico e mostra tela de derrota."""
    _save_ctx.clear()
    nome_capitao = ""
    if slug:
        try:
            data = carregar(slug)
            nome_capitao = data.get("nome_capitao", "")
            from .saves import mover_para_historico
            mover_para_historico(slug, {
                "causa_morte": causa,
                "notoriedade_maxima": getattr(estado_mundo, "notoriedade_maximo", 0),
                "duracao_segundos": int(getattr(estado, "tempo", 0)),
            })
        except Exception:
            pass
    return tela_fim_mundo(stdscr, estado, estado_mundo, nome_capitao)


def _parar_jogador_mundo(estado, estado_mundo) -> None:
    """Zera a inércia do jogador antes de abrir uma cena bloqueante."""
    estado_mundo.jogador_velocidade = 0.0
    estado_mundo.jogador_heading_alvo = estado_mundo.jogador_heading
    estado.jogador.velocidade = 0.0
    estado.jogador.heading_alvo = estado.jogador.heading


def jogo_loop(
    stdscr,
    config: dict,
    estado: 'Estado | None' = None,
    exibir_fim: bool = True,
    estado_mundo=None,
    arena_ox: float = 0.0,
    arena_oy: float = 0.0,
) -> str:
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
            textura_mar=config.get("textura_mar", True),
            rastro_ativo=config.get("rastro", True),
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
            elif (estado_mundo is not None and buffer_entrada == ""
                  and ch in (ord('M'), ord('m'))):
                estado_mundo.mapa_mundo_visivel = not estado_mundo.mapa_mundo_visivel
            elif estado.hotkeys_ativo and buffer_entrada == "" and processar_hotkey(ch, estado):
                pass
            elif 32 <= ch <= 126:
                buffer_entrada += chr(ch)
                tab_estado["ativo"] = False

        agora = time.time()
        if agora - last_tick >= SIM_TICK:
            atualizar_simulacao(estado, agora - last_tick)
            last_tick = agora
            if estado_mundo is not None:
                estado_mundo.jogador_x = (arena_ox + estado.jogador.x) % MUNDO_TAMANHO
                estado_mundo.jogador_y = (arena_oy + estado.jogador.y) % MUNDO_TAMANHO
                if estado_mundo.inimigo_engajado is not None:
                    estado_mundo.inimigo_engajado.x = (arena_ox + estado.inimigo.x) % MUNDO_TAMANHO
                    estado_mundo.inimigo_engajado.y = (arena_oy + estado.inimigo.y) % MUNDO_TAMANHO

                # --- Colisão com ilhas no combate (usa coords arena via ilhas_arena) ---
                from .world.entities import eh_solido_ilha as _esi_cmb
                for _ai in getattr(estado, 'ilhas_arena', []):
                    if math.hypot(estado.jogador.x - _ai.x, estado.jogador.y - _ai.y) <= _ai.raio_maximo:
                        if _esi_cmb(estado.jogador.x, estado.jogador.y, _ai, mundo_tamanho=1e9):
                            _v = estado.jogador.velocidade
                            _d = DANO_COLISAO_BASE * (math.exp(DANO_COLISAO_K * _v / DANO_COLISAO_V_REF) - 1)
                            estado.jogador.partes['casco'] = max(0.0, estado.jogador.partes['casco'] - _d)
                            estado.jogador.velocidade *= 0.7
                            if not estado_mundo.em_colisao_ilha:
                                _cdx = estado.jogador.x - _ai.x
                                _cdy = estado.jogador.y - _ai.y
                                _cdist = math.hypot(_cdx, _cdy)
                                if _cdist > 0:
                                    _jbear = math.degrees(math.atan2(_cdx, _cdy)) % 360
                                    estado.jogador.heading = _jbear
                                    estado.jogador.heading_alvo = (_jbear + 25.0) % 360
                                    estado.jogador.velocidade = 0.0
                                if _d > 0.1:
                                    estado.log.append(f"[COLISAO] Bateu em ilha! (-{_d:.0f}% casco)")
                            estado_mundo.em_colisao_ilha = True
                            break
                else:
                    estado_mundo.em_colisao_ilha = False

                if not estado.inimigo.afundado:
                    for _ai in getattr(estado, 'ilhas_arena', []):
                        if math.hypot(estado.inimigo.x - _ai.x, estado.inimigo.y - _ai.y) <= _ai.raio_maximo:
                            if _esi_cmb(estado.inimigo.x, estado.inimigo.y, _ai, mundo_tamanho=1e9):
                                _v = estado.inimigo.velocidade
                                _d = DANO_COLISAO_BASE * (math.exp(DANO_COLISAO_K * _v / DANO_COLISAO_V_REF) - 1)
                                estado.inimigo.partes['casco'] = max(0.0, estado.inimigo.partes['casco'] - _d)
                                estado.inimigo.velocidade *= 0.7
                                if not estado.em_colisao_ilha_inimigo:
                                    _cdx = estado.inimigo.x - _ai.x
                                    _cdy = estado.inimigo.y - _ai.y
                                    _cdist = math.hypot(_cdx, _cdy)
                                    if _cdist > 0:
                                        _ibear = math.degrees(math.atan2(_cdx, _cdy)) % 360
                                        estado.inimigo.heading = _ibear
                                        estado.inimigo.heading_alvo = (_ibear + 25.0) % 360
                                        estado.inimigo.velocidade = 0.0
                                estado.em_colisao_ilha_inimigo = True
                                break
                    else:
                        estado.em_colisao_ilha_inimigo = False

        if estado_mundo is not None:
            desenhar_tela_mundo(stdscr, estado, estado_mundo, buffer_entrada)
        else:
            desenhar_tela(stdscr, estado, buffer_entrada)

    if estado.fim is None:
        estado.fim = "derrota"
    if not exibir_fim:
        return estado.fim
    return tela_fim(stdscr, estado)


def mundo_loop(
    stdscr,
    config: dict,
    slug: str | None = None,
    seed_mundo: int | None = None,
) -> str:
    """Loop de navegação livre no mundo aberto.

    Cria e mantém um Estado persistente do jogador (dano, tripulação, moral) e
    um EstadoMundo para os navios inimigos. Quando um inimigo se aproxima a
    menos de MUNDO_GATILHO_COMBATE, transforma coordenadas e chama jogo_loop
    com o Estado já configurado. Ao terminar a batalha, transforma de volta.

    Args:
        stdscr:      Janela curses principal.
        config:      Dict com opções da sessão.
        slug:        Slug do save ativo (None = sem persistência).
        seed_mundo:  Seed para geração determinística do mundo (None = carregar do save).

    Returns:
        Próxima tela: 'menu' ou 'sair'.
    """
    stdscr.nodelay(True)
    stdscr.timeout(POLL_MS)

    cores = config["cores"] and bool(_curses and _curses.has_colors())

    if slug is not None and seed_mundo is None:
        # Continuar save existente
        data = carregar(slug)
        seed_mundo = data["seed_mundo"]
        estado, estado_mundo = restaurar_estado(data, config)
        params = NAVIO_TIPOS[estado_mundo.tipo_navio]
    else:
        tipo_navio = config["tipo_navio"]
        params = NAVIO_TIPOS[tipo_navio]
        estado = Estado(
            tipo_navio=tipo_navio,
            hotkeys=config["hotkeys"],
            cores=cores,
            graficos_unicode=config["unicode"],
            textura_mar=config.get("textura_mar", True),
            rastro_ativo=config.get("rastro", True),
        )
        estado_mundo = EstadoMundo(tipo_navio, seed=seed_mundo)
        estado_mundo.jogador_heading = estado.jogador.heading

    # Sem inimigo em cena durante a navegação; visão do capitão mostra apenas água.
    estado.inimigo.afundado = True
    estado.log.clear()
    estado.log.append(
        f"Navegando no mundo aberto. [{params['navio'].upper()}] "
        f"Use M para o mapa-mundo. Gatilho de combate: 750m."
    )

    # Registra contexto para SIGINT/SIGTERM salvar antes de sair.
    if slug:
        _save_ctx.clear()
        _save_ctx.extend([estado, estado_mundo, slug])

    buffer_entrada = ""
    last_tick = time.time()
    tab_estado: dict = {"ativo": False, "candidatos": [], "indice": 0, "prefixo": ""}

    # Mantém tempo acumulado para exibição no header
    estado.tempo = 0.0

    while True:
        ch = stdscr.getch()
        if ch != -1:
            if ch == 27:  # ESC → menu
                if slug:
                    salvar(estado, estado_mundo, slug)
                return "menu"
            elif ch in (ord('M'), ord('m')):
                estado_mundo.mapa_mundo_visivel = not estado_mundo.mapa_mundo_visivel
            elif ch in (ord('V'), ord('v')) and buffer_entrada == "":
                from .ui.inventario import abrir_inventario
                _parar_jogador_mundo(estado, estado_mundo)
                abrir_inventario(stdscr, estado.jogador, estado_mundo.loot_pendente, cores=estado.cores_ativo)
                if estado_mundo.loot_pendente is not None:
                    if not estado_mundo.loot_pendente.barris:
                        estado_mundo.loot_pendente = None
                    else:
                        for b in estado_mundo.loot_pendente.barris:
                            estado.log.append(f"{b.quantidade:.1f} de {b.tipo} se perdeu nos destrocos.")
                        estado_mundo.loot_pendente = None
            elif ch in (ord('N'), ord('n')) and buffer_entrada == "":
                _processar_cmd_mundo("atracar", estado, estado_mundo, stdscr, slug)
            elif MODO_ADM_DISPONIVEL and ch == _curses.KEY_F12:
                estado.modo_adm = not estado.modo_adm
            elif ch in (_curses.KEY_ENTER, 10, 13):
                cmd = buffer_entrada.strip()
                if cmd:
                    _processar_cmd_mundo(cmd, estado, estado_mundo, stdscr, slug)
                    estado.ultimo_comando = cmd
                elif estado.ultimo_comando:
                    _processar_cmd_mundo(estado.ultimo_comando, estado, estado_mundo, stdscr, slug)
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
            dt = min(agora - last_tick, MUNDO_TICK)
            last_tick = agora
            estado.tempo += dt
            estado_mundo.acumular_horas_faixa8(dt)

            # Sync controles do jogador para o mundo
            estado_mundo.jogador_heading_alvo = estado.jogador.heading_alvo
            estado_mundo.jogador_nivel_vela = estado.jogador.nivel_vela

            atualizar_jogador_mundo(estado_mundo, params, dt)

            # --- Colisão com ilha (navegação) ---
            from .world.entities import eh_solido_ilha as _esi_nav
            _jx, _jy = estado_mundo.jogador_x, estado_mundo.jogador_y
            _ilha_col = None
            for _ilha in estado_mundo.ilhas:
                if estado_mundo._distancia_toroidal(_jx, _jy, _ilha.x, _ilha.y) <= _ilha.raio_maximo:
                    if _esi_nav(_jx, _jy, _ilha):
                        _ilha_col = _ilha
                        break
            if _ilha_col is not None:
                _v = estado_mundo.jogador_velocidade
                _dano = DANO_COLISAO_BASE * (math.exp(DANO_COLISAO_K * _v / DANO_COLISAO_V_REF) - 1)
                estado.jogador.partes['casco'] = max(0.0, estado.jogador.partes['casco'] - _dano)
                estado_mundo.jogador_velocidade *= 0.7
                if not estado_mundo.em_colisao_ilha:
                    _cdx = _jx - _ilha_col.x
                    _cdy = _jy - _ilha_col.y
                    if abs(_cdx) > MUNDO_TAMANHO / 2:
                        _cdx -= math.copysign(MUNDO_TAMANHO, _cdx)
                    if abs(_cdy) > MUNDO_TAMANHO / 2:
                        _cdy -= math.copysign(MUNDO_TAMANHO, _cdy)
                    _cdist = math.hypot(_cdx, _cdy)
                    if _cdist > 0:
                        _theta = math.atan2(_cdy, _cdx)
                        _raio_s = _ilha_col.raio_base * (
                            1 + _ilha_col.a1 * math.sin(_ilha_col.k1 * _theta + _ilha_col.f1)
                              + _ilha_col.a2 * math.sin(_ilha_col.k2 * _theta + _ilha_col.f2)
                              + _ilha_col.a3 * math.sin(_ilha_col.k3 * _theta + _ilha_col.f3)
                        )
                        _empurra = _raio_s + 2.0
                        estado_mundo.jogador_x = (_ilha_col.x + (_cdx / _cdist) * _empurra) % MUNDO_TAMANHO
                        estado_mundo.jogador_y = (_ilha_col.y + (_cdy / _cdist) * _empurra) % MUNDO_TAMANHO
                        _bear = math.degrees(math.atan2(_cdx, _cdy)) % 360
                        estado_mundo.jogador_heading = _bear
                        estado_mundo.jogador_heading_alvo = (_bear + 25.0) % 360
                        estado_mundo.jogador_velocidade = 0.0
                    if _dano > 0.1:
                        estado.log.append(f"[COLISAO] Bateu em ilha! (-{_dano:.0f}% casco)")
                estado_mundo.em_colisao_ilha = True
            else:
                estado_mundo.em_colisao_ilha = False

            if not estado_mundo.em_combate:
                estado_mundo.rastro_jogador.append(
                    (estado_mundo.jogador_x, estado_mundo.jogador_y)
                )
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
                porto = _tentar_respawn(estado, estado_mundo)
                if porto is None:
                    estado.fim = "derrota"
                    return _processar_morte_mundo(
                        stdscr, estado, estado_mundo, slug, "afundou na navegacao"
                    )
                # tem frota → continua com novo navio no porto mais próximo

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

                # Configura estado.inimigo a partir do NavioMundo (perfil por
                # navio: tipo_navio individual, nao mais o tipo global do mundo)
                params_inimigo = NAVIO_TIPOS[inimigo_engajado.tipo_navio]
                estado.inimigo.x = inimigo_dx
                estado.inimigo.y = inimigo_dy
                estado.inimigo.heading = inimigo_engajado.heading
                estado.inimigo.heading_alvo = inimigo_engajado.heading
                estado.inimigo.velocidade = inimigo_engajado.velocidade
                estado.inimigo.afundado = False
                estado.inimigo.tipo_nome = params_inimigo['navio']
                estado.inimigo.velocidade_max_base = params_inimigo['velocidade_max_base']
                estado.inimigo.giro_graus_seg = params_inimigo['giro_graus_seg']
                estado.inimigo.reparo_mult = params_inimigo['reparo_mult']
                estado.inimigo.num_velas = params_inimigo['num_velas']
                estado.inimigo_tipo_navio = inimigo_engajado.tipo_navio
                estado.inimigo_min_crew_canhao = params_inimigo['min_crew_canhao']
                if inimigo_engajado.partes is not None:
                    estado.inimigo.partes = dict(inimigo_engajado.partes)
                    estado.inimigo.agua = inimigo_engajado.agua
                    estado.inimigo.moral_atual = inimigo_engajado.moral_atual or 100.0
                else:
                    for p in PARTES:
                        estado.inimigo.partes[p] = 100.0
                    estado.inimigo.agua = 0.0
                    estado.inimigo.moral_atual = 100.0

                # Bonus de status do inimigo elite (sorteado por engajamento,
                # nao persiste entre combates): +casco (via resistencia
                # efetiva), +tripulacao, -cooldown.
                if inimigo_engajado.elite:
                    bonus_elite = sortear_bonus_elite(estado_mundo.notoriedade)
                else:
                    bonus_elite = {"casco": 0.0, "tripulacao": 0.0, "cooldown": 0.0}
                estado.inimigo.upgrades['resistencia_casco'] = bonus_elite['casco']
                estado.inimigo_crew_total = math.ceil(
                    params_inimigo['crew_total'] * (1.0 + bonus_elite['tripulacao'])
                )
                estado.inimigo_cooldown_bonus = bonus_elite['cooldown']

                cap = params_inimigo["porao_capacidade"]
                if inimigo_engajado.porao is not None:
                    estado.inimigo.porao = inimigo_engajado.porao
                else:
                    estado.inimigo.porao = gerar_porao_inimigo(
                        cap, inimigo_engajado.tipo_navio, estado_mundo.notoriedade,
                        elite=inimigo_engajado.elite,
                    )
                    inimigo_engajado.porao = estado.inimigo.porao

                # Recria os canhoes do inimigo no numero certo pro tipo dele
                # (canhoes_lado varia por tipo de navio).
                estado.inimigo.canhoes = criar_canhoes(params_inimigo['canhoes_lado'])

                for lado in ('bombordo', 'estibordo'):
                    for c in estado.jogador.canhoes[lado]:
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
                estado.jogador_tentando_fugir = False
                estado.tempo_fuga_jogador = 0.0
                estado.stats = {
                    "tiros_jogador": 0, "acertos_jogador": 0,
                    "tiros_inimigo": 0, "acertos_inimigo": 0,
                }
                estado.log.clear()
                d_ini = (inimigo_dx ** 2 + inimigo_dy ** 2) ** 0.5
                estado.log.append(f"Combate! Inimigo a {d_ini:.0f}m. Prepare-se!")

                # Popula ilhas_arena com ilhas em coords relativas à origem da arena
                import dataclasses as _dc
                estado.ilhas_arena = []
                for _ilha in estado_mundo.ilhas:
                    _adx = _ilha.x - ox
                    _ady = _ilha.y - oy
                    if abs(_adx) > MUNDO_TAMANHO / 2:
                        _adx -= math.copysign(MUNDO_TAMANHO, _adx)
                    if abs(_ady) > MUNDO_TAMANHO / 2:
                        _ady -= math.copysign(MUNDO_TAMANHO, _ady)
                    if abs(_adx) < MAPA_TAMANHO + _ilha.raio_maximo and abs(_ady) < MAPA_TAMANHO + _ilha.raio_maximo:
                        estado.ilhas_arena.append(_dc.replace(_ilha, x=_adx, y=_ady))
                estado.em_colisao_ilha_inimigo = False

                # Corre o loop de combate no mesmo mapa (sem exibir tela_fim)
                estado_mundo.em_combate = True
                estado_mundo.inimigo_engajado = inimigo_engajado
                jogo_loop(
                    stdscr, config, estado=estado, exibir_fim=False,
                    estado_mundo=estado_mundo, arena_ox=ox, arena_oy=oy,
                )
                estado_mundo.em_combate = False
                estado_mundo.inimigo_engajado = None

                # Transformação arena → mundo (posição final preservada)
                estado_mundo.jogador_x, estado_mundo.jogador_y = arena_para_mundo(
                    ox, oy, estado.jogador.x, estado.jogador.y,
                )
                estado_mundo.jogador_heading = estado.jogador.heading
                estado_mundo.jogador_velocidade = estado.jogador.velocidade

                if estado.fim == "derrota":
                    if estado.jogador.afundado:
                        porto = _tentar_respawn(estado, estado_mundo)
                        if porto is None:
                            return _processar_morte_mundo(
                                stdscr, estado, estado_mundo, slug, "afundou em combate"
                            )
                        # tem frota → continua com novo navio no porto mais próximo
                    else:
                        # ESC durante combate → menu principal diretamente
                        return "menu"

                elif estado.fim == "vitoria":
                    inimigo_engajado.status = "afundado"
                    inimigo_engajado.x, inimigo_engajado.y = arena_para_mundo(
                        ox, oy, estado.inimigo.x, estado.inimigo.y,
                    )
                    inimigo_engajado.loot = estado.inimigo.porao
                    inimigo_engajado.porao = None
                    pontos = pontos_por_afundamento(inimigo_engajado.tipo_navio, inimigo_engajado.elite)
                    estado_mundo.notoriedade += pontos
                    estado_mundo.notoriedade_maximo = max(
                        estado_mundo.notoriedade_maximo, estado_mundo.notoriedade,
                    )
                    estado.log.append(f"+{pontos:.0f} notoriedade!")

                elif estado.fim == "fuga":
                    inimigo_engajado.status = "fugindo"
                    inimigo_engajado.x, inimigo_engajado.y = arena_para_mundo(
                        ox, oy, estado.inimigo.x, estado.inimigo.y,
                    )
                    inimigo_engajado.moral_atual = estado.inimigo.moral_atual
                    inimigo_engajado.partes = dict(estado.inimigo.partes)
                    inimigo_engajado.agua = estado.inimigo.agua
                    inimigo_engajado.porao = estado.inimigo.porao

                elif estado.fim == "fuga_jogador":
                    # O inimigo nao fugiu, foi o jogador quem escapou: continua
                    # em patrulha normal, mas com o dano sofrido preservado.
                    inimigo_engajado.x, inimigo_engajado.y = arena_para_mundo(
                        ox, oy, estado.inimigo.x, estado.inimigo.y,
                    )
                    inimigo_engajado.moral_atual = estado.inimigo.moral_atual
                    inimigo_engajado.partes = dict(estado.inimigo.partes)
                    inimigo_engajado.agua = estado.inimigo.agua
                    inimigo_engajado.porao = estado.inimigo.porao
                    perda = pontos_perdidos_por_fuga(inimigo_engajado.tipo_navio, inimigo_engajado.elite)
                    estado_mundo.notoriedade = max(0.0, estado_mundo.notoriedade - perda)
                    estado.log.append(f"-{perda:.0f} notoriedade por fugir do combate.")

                # Reset do aviso de munição dos canhões do jogador
                for lado in ('bombordo', 'estibordo'):
                    for c in estado.jogador.canhoes[lado]:
                        c.aviso_sem_municao = False

                # Reabastece lote (mantém afundados + fugindo, adiciona novos)
                estado_mundo.sortear_novo_lote()

                # Reseta estado de combate; visão do capitão volta a mostrar água.
                estado.inimigo.afundado = True
                estado.rodando = True
                estado.fim = None
                estado.tempo = 0.0
                if not estado.log:
                    estado.log.append("Batalha encerrada. Navegando novamente.")

        # Notifica proximidade de porto ou destroço lootável
        if not estado_mundo.em_combate:
            jx, jy = estado_mundo.jogador_x, estado_mundo.jogador_y
            log_recente = list(estado.log)
            for porto in estado_mundo.portos:
                d = estado_mundo._distancia_toroidal(jx, jy, porto.x, porto.y)
                if d < MUNDO_RAIO_ATRACACAO:
                    if not any(porto.nome in m for m in log_recente):
                        estado.log.append(
                            f"Possivel atracar em {porto.nome} ({d:.0f}m). [N]"
                        )
                    break
            for navio_loot in estado_mundo.inimigos:
                if navio_loot.status == "afundado" and navio_loot.loot is not None:
                    d = estado_mundo._distancia_toroidal(jx, jy, navio_loot.x, navio_loot.y)
                    if d < MUNDO_RAIO_COLETA_LOOT:
                        if not any("destroco" in m.lower() for m in log_recente):
                            estado.log.append(
                                f"Destroco com loot proximo ({d:.0f}m). [N] para coletar."
                            )
                        break

        desenhar_tela_mundo(stdscr, estado, estado_mundo, buffer_entrada)


def _processar_cmd_mundo(
    texto: str,
    estado: 'Estado',
    estado_mundo: 'EstadoMundo',
    stdscr=None,
    slug: str | None = None,
) -> None:
    """Processa comando no modo navegação.

    Intercepta 'mapa', 'radar', 'atracar' e 'inventario'.
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
    elif cmd == "atracar":
        if stdscr is None:
            estado.log.append("Erro interno: stdscr nao disponivel para 'atracar'.")
            return
        # Porto próximo?
        porto_proximo = None
        porto_idx = -1
        for i, porto in enumerate(estado_mundo.portos):
            d = estado_mundo._distancia_toroidal(
                estado_mundo.jogador_x, estado_mundo.jogador_y,
                porto.x, porto.y,
            )
            if d < MUNDO_RAIO_ATRACACAO:
                porto_proximo = porto
                porto_idx = i
                break
        if porto_proximo is not None:
            estado.log.append(f"Atracando em {porto_proximo.nome}...")
            _parar_jogador_mundo(estado, estado_mundo)
            porto_loop(stdscr, estado, estado_mundo, porto_idx)
            if slug:
                salvar(estado, estado_mundo, slug)
            estado_mundo.rastro_jogador.clear()
            if estado_mundo.loot_pendente is not None and not estado_mundo.loot_pendente.barris:
                estado_mundo.loot_pendente = None
            estado.log.append(f"Zarpou de {porto_proximo.nome}.")
            return
        # Destroço com loot próximo?
        navio_destroco = None
        for navio in estado_mundo.inimigos:
            if navio.status == "afundado" and navio.loot is not None:
                d = estado_mundo._distancia_toroidal(
                    estado_mundo.jogador_x, estado_mundo.jogador_y,
                    navio.x, navio.y,
                )
                if d < MUNDO_RAIO_COLETA_LOOT:
                    navio_destroco = navio
                    break
        if navio_destroco is not None:
            estado.log.append("Coletando destrocos do navio afundado...")
            from .ui.inventario import abrir_inventario
            _parar_jogador_mundo(estado, estado_mundo)
            abrir_inventario(stdscr, estado.jogador, navio_destroco.loot, cores=estado.cores_ativo)
            navio_destroco.loot = None  # loot coletado ou descartado
            estado.log.append("Destrocos processados.")
        else:
            estado.log.append("Nenhum porto ou destroco por perto para atracar.")
    elif cmd == "inventario":
        if stdscr is None:
            estado.log.append("Erro interno: stdscr nao disponivel para 'inventario'.")
            return
        from .ui.inventario import abrir_inventario
        _parar_jogador_mundo(estado, estado_mundo)
        abrir_inventario(stdscr, estado.jogador, estado_mundo.loot_pendente, cores=estado.cores_ativo)
        if estado_mundo.loot_pendente is not None:
            if not estado_mundo.loot_pendente.barris:
                estado_mundo.loot_pendente = None
            else:
                tipos_perdidos = {}
                for b in estado_mundo.loot_pendente.barris:
                    tipos_perdidos[b.tipo] = tipos_perdidos.get(b.tipo, 0) + b.quantidade
                for tipo, qtd in tipos_perdidos.items():
                    estado.log.append(f"{qtd:.1f} unidades de {tipo} se perderam nos destrocos.")
                estado_mundo.loot_pendente = None
        estado.log.append("Inventario fechado.")
    else:
        processar_comando(texto, estado)


def _mundo_menu_loop(stdscr, config: dict) -> str:
    """Sub-menu do Mundo Aberto: cria/carrega capitão e lança mundo_loop."""
    while True:
        tem_saves = bool(listar_saves_ativos())
        tem_hist = bool(listar_historico())
        escolha = tela_mundo_menu(stdscr, tem_saves, tem_hist)
        if escolha == "voltar":
            return "menu"
        elif escolha == "novo":
            nome = tela_novo_capitao(stdscr)
            if nome is None:
                continue
            bloqueios = bloqueios_mundo(melhor_faixa_notoriedade_alcancada())
            tipo = tela_navio(stdscr, bloqueios=bloqueios)
            if tipo is None:
                continue
            slug, seed = criar_novo_save(nome, tipo)
            resultado = mundo_loop(stdscr, config, slug=slug, seed_mundo=seed)
            return "sair" if resultado == "sair" else "menu"
        elif escolha == "continuar":
            slug = tela_continuar(stdscr, listar_saves_ativos())
            if slug is None:
                continue
            resultado = mundo_loop(stdscr, config, slug=slug, seed_mundo=None)
            return "sair" if resultado == "sair" else "menu"
        elif escolha == "historico":
            tela_historico(stdscr, listar_historico())


def _arena_menu_loop(stdscr, config: dict) -> str:
    """Sub-menu da Arena: inicia uma campanha nova ou mostra campanhas passadas."""
    while True:
        tem_hist = bool(listar_arena_historico())
        escolha = tela_arena_menu(stdscr, tem_hist)
        if escolha == "voltar":
            return "menu"
        elif escolha == "nova":
            nome = tela_novo_capitao(stdscr)
            if nome is None:
                continue
            bloqueios = bloqueios_arena(melhor_vitorias_arena())
            tipo = tela_navio(stdscr, bloqueios=bloqueios)
            if tipo is None:
                continue
            return _arena_campanha_loop(stdscr, config, nome, tipo)
        elif escolha == "historico":
            tela_arena_historico(stdscr, listar_arena_historico())


def _arena_campanha_loop(stdscr, config: dict, nome_capitao: str, tipo_navio: str) -> str:
    """Roda uma campanha de Arena: batalhas 1x1 sucessivas até derrota/fuga
    ou o jogador optar por encerrar. Cada rodada usa um Estado novo e fresco
    — não mexe em nada da simulação de combate em si (jogo_loop intocado).
    """
    cores = config["cores"] and bool(_curses and _curses.has_colors())
    rodada = 1
    rodadas_vencidas = 0
    inicio = time.time()
    while True:
        estado = Estado(
            tipo_navio=tipo_navio,
            hotkeys=config["hotkeys"],
            cores=cores,
            graficos_unicode=config["unicode"],
            textura_mar=config.get("textura_mar", True),
            rastro_ativo=config.get("rastro", True),
        )
        jogo_loop(stdscr, config, estado=estado, exibir_fim=False)
        if estado.fim == "vitoria":
            rodadas_vencidas += 1
        escolha = tela_fim_arena(stdscr, estado, rodada)
        if estado.fim == "vitoria" and escolha == "proxima":
            rodada += 1
            continue
        salvar_resultado_arena(
            nome_capitao, tipo_navio, rodadas_vencidas, estado.fim,
            int(time.time() - inicio),
        )
        return "sair" if escolha == "sair" else "menu"


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
        _curses.init_pair(COR_ILHA,     _curses.COLOR_WHITE,  fundo)

    config = {"tipo_navio": "brigantim", "hotkeys": True, "cores": True, "unicode": True,
              "textura_mar": True, "rastro": True}
    tela_atual = "menu"

    while tela_atual != "sair":
        if tela_atual == "menu":
            tela_atual = tela_menu(stdscr)
        elif tela_atual == "como_jogar":
            tela_como_jogar(stdscr)
            tela_atual = "menu"
        elif tela_atual == "navio":
            tela_navio(stdscr)
            tela_atual = "menu"
        elif tela_atual == "ajustes":
            tela_ajustes(stdscr, config)
            tela_atual = "menu"
        elif tela_atual == "jogar":
            tela_atual = _arena_menu_loop(stdscr, config)
        elif tela_atual == "mundo":
            tela_atual = _mundo_menu_loop(stdscr, config)
        else:
            tela_atual = "menu"


def run() -> None:
    """Ponto de entrada instalável via pyproject.toml [project.scripts]."""
    import sys
    signal.signal(signal.SIGINT, _sigint_handler)
    signal.signal(signal.SIGTERM, _sigint_handler)
    try:
        _curses.wrapper(main)
    except (KeyboardInterrupt, SystemExit):
        pass
    except _curses.error as e:
        print(f"Erro de terminal (talvez a janela esteja pequena demais): {e}")
        sys.exit(1)
