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
    IA_REAVALIACAO_CREW_SEG, IA_MARGEM_ARCO_GRAUS, IA_DIST_PERSEGUICAO_MULT,
    ARCO_TIRO_CENTRO, ARCO_TIRO_MIN, ARCO_TIRO_MAX,
)
from ..core.utils import clamp
from ..core.combat import distancia, rumo_para
from ..core.state import reconciliar_inimigo
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
    """Quantos canhões de *lado* podem disparar agora.

    Exige tripulação efetiva, não só o cooldown vencido: um canhão sem gente
    não recarrega (o cooldown fica congelado em
    combat.disparar_canhoes_navio), então contá-lo como 'pronto' faria a IA
    ficar trocando de bordo atrás de uma salva que nunca existiu.
    """
    return sum(
        1 for c in estado.inimigo.canhoes[lado]
        if c.efetivos >= 1 and estado.tempo >= c.proximo_tiro
    )


def _espera_lado(estado, lado: str) -> float:
    """Segundos até o primeiro canhão guarnecido de *lado* poder disparar.

    Retorna ``inf`` se não há ninguém naquele costado — canhão sem gente não
    recarrega, então a espera é indefinida.
    """
    esperas = [
        max(0.0, c.proximo_tiro - estado.tempo)
        for c in estado.inimigo.canhoes[lado]
        if c.efetivos >= 1
    ]
    return min(esperas) if esperas else math.inf


def _tempo_giro_bordada(estado) -> float:
    """Segundos para trocar o costado apresentado ao jogador.

    Apresentar o través oposto é um giro de 180°, e durante quase todo ele o
    jogador fica fora dos dois arcos (a proa e a popa varrem o alvo). Com
    GIRO_GRAUS_SEG_PADRAO baixo essa manobra custa várias salvas.
    """
    taxa = max(estado.inimigo.taxa_giro(), 0.01)
    return 2.0 * ARCO_TIRO_CENTRO / taxa


def _escolher_lado_bordada(estado) -> str:
    """Escolhe qual bordada apresentar ao jogador, com histerese.

    Mantém o lado atual enquanto ele tiver algum canhão carregado; troca para
    o oposto assim que o atual descarrega e o outro tem carga.

    Como 'ter carga' agora exige tripulação (ver `_lado_pronto`), a troca só
    acontece quando o inimigo tem gente suficiente para guarnecer os dois
    bordos. Com tripulação curta ele se compromete com um bordo e fica nele —
    que é o comportamento correto, já que o costado abandonado não recarrega.

    E não basta o outro bordo ter UM canhão pronto: ele precisa render uma
    bordada pelo menos tão boa quanto a atual. Sem essa exigência, a sobra de
    tripulação que `_crewar_canhoes` deixa do outro lado bastava para disparar
    a troca, e a IA passava o combate atravessando o convés de um lado para o
    outro.

    Por último, a troca só compensa se esperar a recarga do costado atual for
    mais lento do que o giro de 180° (`_tempo_giro_bordada`). Com o arco de
    tiro estreito e o leme lento, virar o navio custa mais do que uma recarga
    na maioria dos casos — e o navio passa esse tempo todo sem poder atirar de
    nenhum bordo.
    """
    atual = estado.ia_lado_bordada
    oposto = 'bombordo' if atual == 'estibordo' else 'estibordo'
    guarnecidos_atual = sum(
        1 for c in estado.inimigo.canhoes[atual] if c.efetivos >= 1
    )
    if (_lado_pronto(estado, atual) == 0
            and _lado_pronto(estado, oposto) >= max(1, guarnecidos_atual)
            and _espera_lado(estado, atual) > _tempo_giro_bordada(estado)):
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

    Comportamento normal, sempre em torno do costado escolhido por
    `_escolher_lado_bordada`:
    - Fora de alcance de canhão: persegue em rumo direto, velas cheias. Não há
      bordada a preservar quando nenhum tiro alcança.
    - Longe (>280m) mas dentro de alcance: aproxima em diagonal, mantendo o
      jogador na borda dianteira do arco (ARCO_TIRO_MIN + margem). Fecha
      distância mais devagar que o rumo direto, mas atirando o tempo todo.
    - Perto (<150m): afasta pela borda traseira do arco (ARCO_TIRO_MAX -
      margem), abrindo distância sem largar a bordada.
    - Faixa ideal (150-280m): circula com o jogador no través (ARCO_TIRO_CENTRO),
      onde `eficiencia_angular` é máxima, com velas a meio pau.

    Apontar a proa/popa no jogador para aproximar ou afastar — o que a versão
    anterior fazia — custava, com o arco estreitado, um giro de 60° só para
    voltar a ter linha de tiro: a velocidade de giro atual gasta mais que uma
    recarga inteira nisso.

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
    else:
        modo = _escolher_modo_movimento(estado, d)
        fora_de_alcance = (
            d > inimigo.alcance_canhao_efetivo() * IA_DIST_PERSEGUICAO_MULT
        )
        if modo == 'aproximar' and fora_de_alcance:
            inimigo.heading_alvo = r
            _ajustar_velas(inimigo, 2)
        else:
            # O ângulo relativo em que a IA quer manter o jogador. O heading
            # correspondente é r - angulo para estibordo (o arco de estibordo
            # fica à direita da proa) e r + angulo para bombordo.
            if modo == 'aproximar':
                angulo = ARCO_TIRO_MIN + IA_MARGEM_ARCO_GRAUS
            elif modo == 'afastar':
                angulo = ARCO_TIRO_MAX - IA_MARGEM_ARCO_GRAUS
            else:
                angulo = ARCO_TIRO_CENTRO
            lado = _escolher_lado_bordada(estado)
            sinal = -1.0 if lado == 'estibordo' else 1.0
            inimigo.heading_alvo = (r + sinal * angulo) % 360
            # Velas cheias para vencer a distância; meio pau na faixa de
            # bordada, onde a plataforma de tiro estável vale mais.
            _ajustar_velas(inimigo, 1 if modo == 'circular' else 2)
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
    """Distribui *restante* tripulantes pelos canhões do inimigo.

    Decide POR BORDO, não por canhão. A versão anterior ordenava os canhões
    por quem estava no arco naquele instante, e como o arco muda continuamente
    enquanto a IA circula, a alocação mudava a cada tick. Com o custo de
    trânsito (ver pirates/core/tripulacao.py) isso deixaria a tripulação
    inimiga permanentemente a caminho de algum lugar, sem nunca atirar.

    O bordo prioritário é `estado.ia_lado_bordada`, que já tem histerese
    própria (só troca quando o costado atual esgota a carga), então a alocação
    só muda quando a IA muda de ideia de verdade. A sobra vai para o bordo
    oposto, que assim paga o trânsito adiantado e chega pronto para a bordada
    seguinte.
    """
    min_c = estado.inimigo_min_crew_canhao
    lado_principal = estado.ia_lado_bordada
    lado_oposto = 'bombordo' if lado_principal == 'estibordo' else 'estibordo'

    canhoes = (
        list(inimigo.canhoes[lado_principal]) + list(inimigo.canhoes[lado_oposto])
    )
    for c in canhoes:
        if restante >= min_c:
            if c.tripulantes != min_c:
                c.tripulantes = min_c
            restante -= min_c
        elif c.tripulantes != 0:
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

    Os alvos de bomba e reparo só são reavaliados a cada
    IA_REAVALIACAO_CREW_SEG: sem esse throttle, o arredondamento do alvo de
    bomba oscila entre N e N+1 conforme a água sobe e desce, e cada oscilação
    custaria trânsito à tripulação (ver pirates/core/tripulacao.py).

    Args:
        estado: Estado atual do jogo.
    """
    inimigo = estado.inimigo
    total = estado.inimigo_crew_total

    pode_reavaliar = (
        estado.tempo - estado.ia_crew_reavaliado_em >= IA_REAVALIACAO_CREW_SEG
    )

    if pode_reavaliar:
        bomba_alvo = 0
        if inimigo.agua > estado.ia_limiar_agua:
            faixa = max(1.0, 100 - estado.ia_limiar_agua)
            gravidade = clamp((inimigo.agua - estado.ia_limiar_agua) / faixa, 0, 1)
            bomba_alvo = min(total, max(1, round(total * (0.35 + 0.35 * gravidade))))

        reparo_alvo = 0
        if inimigo.partes['casco'] < estado.ia_limiar_casco and total - bomba_alvo > 0:
            reparo_alvo = min(total - bomba_alvo, max(1, round(total * 0.3)))

        if (bomba_alvo != estado.inimigo_crew_bomba
                or reparo_alvo != estado.inimigo_crew_reparo.get('casco', 0)):
            estado.inimigo_crew_bomba = bomba_alvo
            for p in PARTES:
                estado.inimigo_crew_reparo[p] = reparo_alvo if p == 'casco' else 0
            estado.ia_crew_reavaliado_em = estado.tempo

    restante = total - estado.inimigo_crew_bomba - sum(estado.inimigo_crew_reparo.values())

    if estado.inimigo_em_fuga:
        for c in (c for lado in ('estibordo', 'bombordo') for c in inimigo.canhoes[lado]):
            if c.tripulantes != 0:
                c.tripulantes = 0
                c.dist_alvo = None
    else:
        _crewar_canhoes(estado, inimigo, restante)

    reconciliar_inimigo(estado)


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
            # Efetivos, não alocados: canhão cuja equipe ainda atravessa o
            # convés não tem quem mire.
            if c.efetivos < estado.inimigo_min_crew_canhao:
                continue
            if c.dist_alvo is None or estado.tempo >= c.proximo_tiro:
                novo = d_real + random.uniform(-erro, erro)
                c.dist_alvo = novo
                c.mira_atual = novo
