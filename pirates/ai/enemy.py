"""
enemy.py – Inteligência artificial do navio inimigo em CLI PIRATES.

A IA usa limiares aleatorizados por partida para criar variação sem
precisar de comportamento complexo. Ela gerencia movimento, alocação
de tripulação e mira de forma reativa ao estado atual do combate.
"""

import random

from ..constants import PARTES, NAVIO_TIPOS
from ..core.utils import clamp
from ..core.combat import distancia, rumo_para, dentro_do_arco


def atualizar_estado_fuga(estado) -> None:
    """Atualiza o flag de fuga do inimigo com base em histerese de moral.

    Entrada: moral cai abaixo de ia_limiar_fuga_entrada.
    Saída:   moral sobe acima de ia_limiar_fuga_saida.

    Args:
        estado: Estado atual do jogo.
    """
    inimigo = estado.inimigo
    if not estado.inimigo_em_fuga and inimigo.moral_atual <= estado.ia_limiar_fuga_entrada:
        estado.inimigo_em_fuga = True
        estado.log.append("O navio inimigo perde a moral e tenta fugir!")
    elif estado.inimigo_em_fuga and inimigo.moral_atual >= estado.ia_limiar_fuga_saida:
        estado.inimigo_em_fuga = False
        estado.tempo_fuga_longe = 0.0
        estado.log.append("O navio inimigo recupera a moral e volta a lutar!")


def atualizar_ia_movimento(estado, dt: float) -> None:
    """Atualiza o heading alvo e o nível de vela do navio inimigo.

    Comportamento normal:
    - Longe (>280m): aproxima em velocidade máxima.
    - Perto (<150m): afasta para manter distância de combate.
    - Faixa ideal (150-280m): circula lateralmente com estibordo ao jogador.

    Comportamento em fuga: foge na direção oposta ao jogador a todo vapor.

    Args:
        estado: Estado atual do jogo.
        dt:     Delta de tempo em segundos.
    """
    inimigo = estado.inimigo
    jogador = estado.jogador
    if inimigo.afundado:
        return
    d = distancia(inimigo, jogador)
    r = rumo_para(inimigo, jogador)

    if estado.inimigo_em_fuga:
        inimigo.heading_alvo = (r + 180) % 360
        inimigo.nivel_vela = 3
        return

    if d > 280:
        inimigo.heading_alvo = r
        inimigo.nivel_vela = 3
    elif d < 150:
        inimigo.heading_alvo = (r + 180) % 360
        inimigo.nivel_vela = 2
    else:  # 150-280m: circula lateralmente com estibordo voltado ao jogador
        inimigo.heading_alvo = (r + 90) % 360
        inimigo.nivel_vela = 2


def _crewar_canhoes(estado, inimigo, restante: int) -> None:
    """Distribui *restante* tripulantes pelos canhões do inimigo."""
    jogador = estado.jogador
    min_c = estado.min_crew_canhao
    lados_no_arco = [
        lado for lado in ('estibordo', 'bombordo')
        if dentro_do_arco(inimigo, jogador, lado)[0]
    ]

    def prioridade(c):
        if c.lado in lados_no_arco:
            return 0
        if c.dist_alvo is not None:
            return 1
        return 2

    canhoes = sorted(
        [c for lado in ('estibordo', 'bombordo') for c in inimigo.canhoes[lado]],
        key=prioridade,
    )
    for c in canhoes:
        if restante >= min_c:
            c.tripulantes = min_c
            restante -= min_c
        else:
            c.tripulantes = 0
            c.dist_alvo = None


def atualizar_ia_tripulacao(estado) -> None:
    """Aloca a tripulação finita do inimigo por prioridade.

    Em modo normal:
    1. Bombas — se água passar de ia_limiar_agua.
    2. Reparo do casco — se HP estiver abaixo de ia_limiar_casco.
    3. Canhões — preferindo o lado com o jogador no arco agora.

    Em modo fuga: toda tripulação disponível vai para bombas/reparo;
    canhões recebem no máximo um tripulante cada.

    Args:
        estado: Estado atual do jogo.
    """
    inimigo = estado.inimigo
    total = estado.crew_total
    min_c = estado.min_crew_canhao

    bomba_alvo = 0
    if inimigo.agua > estado.ia_limiar_agua:
        faixa = max(1.0, 100 - estado.ia_limiar_agua)
        gravidade = clamp((inimigo.agua - estado.ia_limiar_agua) / faixa, 0, 1)
        bomba_alvo = min(total, max(1, round(total * (0.35 + 0.35 * gravidade))))
    restante = total - bomba_alvo

    reparo_alvo = 0
    if inimigo.partes['casco'] < estado.ia_limiar_casco and restante > 0:
        reparo_alvo = min(restante, max(1, round(total * 0.3)))
    restante -= reparo_alvo

    estado.inimigo_crew_bomba = bomba_alvo
    for p in PARTES:
        estado.inimigo_crew_reparo[p] = reparo_alvo if p == 'casco' else 0

    if estado.inimigo_em_fuga:
        for c in (c for lado in ('estibordo', 'bombordo') for c in inimigo.canhoes[lado]):
            c.tripulantes = 0
            c.dist_alvo = None
        return

    _crewar_canhoes(estado, inimigo, restante)


def atualizar_ia_mira(estado) -> None:
    """Recalibra a mira dos canhões inimigos com erro aleatório por disparo.

    Simula o mesmo tipo de incerteza que um artilheiro humano teria,
    usando o parâmetro erro_mira do tipo de navio.

    Args:
        estado: Estado atual do jogo.
    """
    inimigo = estado.inimigo
    jogador = estado.jogador
    erro = NAVIO_TIPOS[estado.tipo_navio]["erro_mira"]
    d_real = distancia(inimigo, jogador)

    for lado in ('bombordo', 'estibordo'):
        for c in inimigo.canhoes[lado]:
            if c.tripulantes < estado.min_crew_canhao:
                continue
            if c.dist_alvo is None or estado.tempo >= c.proximo_tiro:
                novo = d_real + random.uniform(-erro, erro)
                c.dist_alvo = novo
                c.mira_atual = novo
