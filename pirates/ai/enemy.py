"""
enemy.py – Inteligência artificial do navio inimigo em CLI PIRATES.

A IA usa limiares aleatorizados por partida para criar variação sem
precisar de comportamento complexo. Ela gerencia movimento, alocação
de tripulação e mira de forma reativa ao estado atual do combate.
"""

import math
import random

from ..constants import (
    PARTES, NAVIO_TIPOS,
    IA_VENTO_MARGEM_SAIDA_GRAUS, IA_VENTO_CORRECAO_MAX_GRAUS,
    IA_VENTO_CORRECAO_MAX_FUGA_GRAUS,
    IA_DIST_APROXIMAR, IA_DIST_AFASTAR, IA_DIST_HISTERESE, IA_ILHA_HISTERESE,
)
from ..core.utils import clamp
from ..core.combat import distancia, rumo_para, dentro_do_arco
from ..core.vento import angulo_relativo_vento


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


def _ajustar_heading_vento(
    heading_alvo: float, vento_direcao: float, correcao_max: float,
) -> float:
    """Ajusta *heading_alvo* pra se afastar da zona morta de vento (0-45°
    de ângulo relativo), sem exceder *correcao_max* graus de correção.

    A correção é parcial: se o heading original está bem no meio da zona
    morta e correcao_max não é suficiente pra sair completamente, aplica
    o máximo permitido em vez de não fazer nada (doc08_vento.md seção 8).
    """
    ang = angulo_relativo_vento(heading_alvo, vento_direcao)
    if ang > 45.0:
        return heading_alvo

    alvo_saida = 45.0 + IA_VENTO_MARGEM_SAIDA_GRAUS
    correcao = min(alvo_saida - ang, correcao_max)
    if correcao <= 0:
        return heading_alvo

    candidato_mais = (heading_alvo + correcao) % 360
    candidato_menos = (heading_alvo - correcao) % 360
    ang_mais = angulo_relativo_vento(candidato_mais, vento_direcao)
    ang_menos = angulo_relativo_vento(candidato_menos, vento_direcao)
    return candidato_mais if ang_mais >= ang_menos else candidato_menos


def _lado_pronto(estado, lado: str) -> int:
    """Quantos canhões de *lado* já estão fora do cooldown."""
    return sum(
        1 for c in estado.inimigo.canhoes[lado]
        if estado.tempo >= c.proximo_tiro
    )


def _escolher_lado_bordada(estado) -> str:
    """Escolhe qual bordada apresentar ao jogador, com histerese.

    Mantém o lado atual enquanto ele tiver algum canhão carregado; troca
    para o lado oposto assim que o atual descarrega e o outro tem carga.
    Isso faz o inimigo virar de bordo entre as salvas em vez de expor a
    vida inteira o mesmo costado (o que deixava metade dos canhões
    permanentemente ociosos).
    """
    atual = estado.ia_lado_bordada
    oposto = 'bombordo' if atual == 'estibordo' else 'estibordo'
    if _lado_pronto(estado, atual) == 0 and _lado_pronto(estado, oposto) > 0:
        estado.ia_lado_bordada = oposto
    return estado.ia_lado_bordada


def _escolher_modo_movimento(estado, d: float) -> str:
    """Decide entre 'aproximar', 'circular' e 'afastar' com histerese.

    Os limiares de entrada são IA_DIST_APROXIMAR/IA_DIST_AFASTAR, mas pra
    voltar a 'circular' a distância precisa cruzar IA_DIST_HISTERESE metros
    além do limiar. Sem isso um navio parado em cima do limiar alterna de
    modo a cada tick e nunca completa a manobra.
    """
    modo = estado.ia_modo_movimento
    if modo == 'aproximar':
        if d <= IA_DIST_APROXIMAR - IA_DIST_HISTERESE:
            modo = 'circular'
    elif modo == 'afastar':
        if d >= IA_DIST_AFASTAR + IA_DIST_HISTERESE:
            modo = 'circular'
    else:
        if d > IA_DIST_APROXIMAR:
            modo = 'aproximar'
        elif d < IA_DIST_AFASTAR:
            modo = 'afastar'
    estado.ia_modo_movimento = modo
    return modo


def _ajustar_velas(navio, nivel: int) -> None:
    """Coloca todos os slots de vela equipados de *navio* em *nivel* (0-2).

    Slots vazios (``tipo is None``) são ignorados.
    """
    for slot in navio.slots_vela:
        if slot["tipo"] is not None:
            slot["nivel"] = nivel


def atualizar_ia_movimento(estado, dt: float) -> None:
    """Atualiza o heading alvo e o nível de vela do navio inimigo.

    Comportamento normal:
    - Longe (>280m): aproxima em velocidade máxima (velas cheias).
    - Perto (<150m): afasta para manter distância de combate (velas cheias).
    - Faixa ideal (150-280m): circula lateralmente apresentando ao jogador
      a bordada carregada (ver `_escolher_lado_bordada`), com velas a meio
      pau para manter a plataforma de tiro estável.

    Comportamento em fuga: foge na direção oposta ao jogador a todo vapor
    (velas cheias), desviando de ilhas no caminho.

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
        _ajustar_velas(inimigo, 2)
        correcao_max = IA_VENTO_CORRECAO_MAX_FUGA_GRAUS
    elif _escolher_modo_movimento(estado, d) == 'aproximar':
        inimigo.heading_alvo = r
        _ajustar_velas(inimigo, 2)
        correcao_max = IA_VENTO_CORRECAO_MAX_GRAUS
    elif estado.ia_modo_movimento == 'afastar':
        inimigo.heading_alvo = (r + 180) % 360
        _ajustar_velas(inimigo, 2)
        correcao_max = IA_VENTO_CORRECAO_MAX_GRAUS
    else:
        # Faixa de bordada: circula apresentando o costado que ainda tem carga.
        # Estibordo é o centro do arco em rel=90 (combat.eficiencia_angular),
        # logo o heading precisa ser r-90; bombordo é r+90.
        lado = _escolher_lado_bordada(estado)
        offset = -90 if lado == 'estibordo' else 90
        inimigo.heading_alvo = (r + offset) % 360
        _ajustar_velas(inimigo, 1)
        correcao_max = IA_VENTO_CORRECAO_MAX_GRAUS

    inimigo.heading_alvo = _ajustar_heading_vento(
        inimigo.heading_alvo, estado.vento_direcao, correcao_max,
    )

    # Evasão de ilhas em combate (personalidade via ia_island_avoidance_mult).
    # Histerese: enquanto já estiver evadindo uma ilha, o raio de gatilho é
    # ampliado por IA_ILHA_HISTERESE, senão a IA entra e sai da evasão a cada
    # tick na borda do raio e fica oscilando de rumo sem se afastar.
    evadindo = None
    for idx, ilha in enumerate(getattr(estado, 'ilhas_arena', [])):
        _idx = inimigo.x - ilha.x
        _idy = inimigo.y - ilha.y
        dist_ilha = math.hypot(_idx, _idy)
        raio = ilha.raio_maximo * estado.ia_island_avoidance_mult
        if idx == estado.ia_ilha_evadindo:
            raio *= IA_ILHA_HISTERESE
        if dist_ilha < raio:
            inimigo.heading_alvo = math.degrees(math.atan2(_idx, _idy)) % 360
            evadindo = idx
            break
    estado.ia_ilha_evadindo = evadindo


def _crewar_canhoes(estado, inimigo, restante: int) -> None:
    """Distribui *restante* tripulantes pelos canhões do inimigo."""
    jogador = estado.jogador
    min_c = estado.inimigo_min_crew_canhao
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
    total = estado.inimigo_crew_total
    min_c = estado.inimigo_min_crew_canhao

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
    erro = NAVIO_TIPOS[estado.inimigo_tipo_navio]["erro_mira"]
    d_real = distancia(inimigo, jogador)

    for lado in ('bombordo', 'estibordo'):
        for c in inimigo.canhoes[lado]:
            if c.tripulantes < estado.inimigo_min_crew_canhao:
                continue
            if c.dist_alvo is None or estado.tempo >= c.proximo_tiro:
                novo = d_real + random.uniform(-erro, erro)
                c.dist_alvo = novo
                c.mira_atual = novo
