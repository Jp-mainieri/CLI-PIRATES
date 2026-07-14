"""
simulation.py – Loop de simulação por tick de CLI PIRATES.

Orquestra, na ordem correta, reparo, água, IA, tiros e movimento,
e verifica as condições de vitória/derrota a cada tick.
"""

from .combat import disparar_canhoes_navio, escolher_zoom, distancia
from .state import Estado
from ..ai.enemy import atualizar_ia_movimento, atualizar_ia_tripulacao, atualizar_ia_mira


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

    if not inimigo.afundado:
        atualizar_ia_movimento(estado, dt)
        atualizar_ia_tripulacao(estado)
        atualizar_ia_mira(estado)
        for parte, n in estado.inimigo_crew_reparo.items():
            inimigo.reparar(parte, n, dt)
        inimigo.atualizar_agua(estado.inimigo_crew_bomba, dt)

    if not inimigo.afundado:
        disparar_canhoes_navio(estado, jogador, inimigo)
    if not jogador.afundado:
        disparar_canhoes_navio(estado, inimigo, jogador)

    jogador.atualizar_movimento(dt)
    inimigo.atualizar_movimento(dt)

    _atualizar_zoom(estado)

    estado.tempo += dt

    if jogador.afundado and estado.fim is None:
        estado.log.append("Seu navio afundou! Fim de jogo.")
        estado.fim = "derrota"
        estado.rodando = False
    elif inimigo.afundado and estado.fim is None:
        estado.log.append("O navio inimigo afundou! Vitoria!")
        estado.fim = "vitoria"
        estado.rodando = False
