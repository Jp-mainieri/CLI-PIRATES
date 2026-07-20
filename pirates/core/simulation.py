"""
simulation.py – Loop de simulação por tick de CLI PIRATES.

Orquestra, na ordem correta, reparo, água, IA, tiros e movimento,
e verifica as condições de vitória/derrota a cada tick.
"""

from .combat import disparar_canhoes_navio, escolher_zoom, distancia
from .state import Estado
from ..ai.enemy import (
    atualizar_ia_movimento, atualizar_ia_tripulacao, atualizar_ia_mira,
    atualizar_estado_fuga,
)
from ..constants import ALCANCE_FUGA_ESCAPE, TEMPO_FUGA_ESCAPE_SEG
from .vento import atualizar_vento, angulo_relativo_vento, zona_vento


def _atualizar_zoom(estado: Estado) -> None:
    """Recalcula o nível de zoom do minimapa e registra mudanças no log."""
    d = distancia(estado.jogador, estado.inimigo)
    novo = escolher_zoom(d, estado.zoom_atual)
    if estado.zoom_atual is not None and novo != estado.zoom_atual:
        estado.log.append(f"Mapa: zoom ajustado para ~{novo}m")
        estado.zoom_mudou_em = estado.tempo
    estado.zoom_atual = novo


def atualizar_simulacao(estado: Estado, dt: float) -> None:
    """Avança a simulação completa do jogo por *dt* segundos.

    Ordem de operações:
    1. Reparo e água do jogador.
    2. IA do inimigo (movimento, tripulação, mira) + reparo e água do inimigo.
    3. Tiros de ambos os navios.
    4. Movimento de ambos os navios.
    5. Zoom do mapa.
    6. Avanço do relógio.
    7. Verificação de condições de fim de jogo.

    Args:
        estado: Estado atual do jogo (modificado in-place).
        dt:     Delta de tempo em segundos desde o último tick.
    """
    jogador = estado.jogador
    inimigo = estado.inimigo

    for parte, n in estado.crew_reparo.items():
        jogador.reparar(parte, n, dt)
    jogador.atualizar_agua(estado.crew_bomba, dt)
    jogador.atualizar_moral(dt)

    if not inimigo.afundado:
        atualizar_ia_movimento(estado, dt)
        atualizar_ia_tripulacao(estado)
        atualizar_ia_mira(estado)
        for parte, n in estado.inimigo_crew_reparo.items():
            inimigo.reparar(parte, n, dt)
        inimigo.atualizar_agua(estado.inimigo_crew_bomba, dt)
        inimigo.atualizar_moral(dt)
        atualizar_estado_fuga(estado)

    if not inimigo.afundado:
        disparar_canhoes_navio(estado, jogador, inimigo)
    if not jogador.afundado:
        disparar_canhoes_navio(estado, inimigo, jogador)

    atualizar_vento(estado, dt)

    ang_jogador = angulo_relativo_vento(jogador.heading, estado.vento_direcao)
    jogador.atualizar_movimento(dt, ang_jogador, estado.vento_intensidade, estado.vento_direcao)

    ang_inimigo = angulo_relativo_vento(inimigo.heading, estado.vento_direcao)
    inimigo.atualizar_movimento(dt, ang_inimigo, estado.vento_intensidade, estado.vento_direcao)

    zona_jogador = zona_vento(ang_jogador)
    if (
        estado.vento_zona_anterior_jogador is not None
        and zona_jogador != estado.vento_zona_anterior_jogador
    ):
        estado.log.append(f"Vento: mudou para {zona_jogador.replace('_', ' ')}")
    estado.vento_zona_anterior_jogador = zona_jogador

    _atualizar_zoom(estado)

    estado.tempo += dt

    if estado.inimigo_em_fuga and not inimigo.afundado:
        d = distancia(jogador, inimigo)
        if d > ALCANCE_FUGA_ESCAPE:
            estado.tempo_fuga_longe += dt
            if estado.tempo_fuga_longe >= TEMPO_FUGA_ESCAPE_SEG and estado.fim is None:
                estado.log.append("O navio inimigo escapou no horizonte!")
                estado.fim = "fuga"
                estado.rodando = False
        else:
            estado.tempo_fuga_longe = 0.0

    if (
        estado.jogador_tentando_fugir
        and not jogador.afundado
        and not inimigo.afundado
        and estado.fim is None
    ):
        if estado.inimigo_em_fuga:
            # Inimigo comecou a fugir por conta propria: nao faz sentido
            # contabilizar fuga do jogador ao mesmo tempo.
            estado.tempo_fuga_jogador = 0.0
        else:
            d = distancia(jogador, inimigo)
            if d > ALCANCE_FUGA_ESCAPE:
                estado.tempo_fuga_jogador += dt
                if estado.tempo_fuga_jogador >= TEMPO_FUGA_ESCAPE_SEG:
                    estado.log.append("Voce escapou no horizonte!")
                    estado.fim = "fuga_jogador"
                    estado.rodando = False
            else:
                estado.tempo_fuga_jogador = 0.0

    if jogador.afundado and estado.fim is None:
        estado.log.append("Seu navio afundou! Fim de jogo.")
        estado.fim = "derrota"
        estado.rodando = False
    elif inimigo.afundado and estado.fim is None:
        estado.log.append("O navio inimigo afundou! Vitoria!")
        estado.fim = "vitoria"
        estado.rodando = False
