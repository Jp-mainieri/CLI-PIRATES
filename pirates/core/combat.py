"""
combat.py – Geometria, combate e zoom do mapa em CLI PIRATES.

Funções de cálculo de distância/rumo, verificação de arcos de tiro,
resolução de dano e o sistema de zoom adaptativo do minimapa.
"""

import math
import random

from ..constants import (
    COOLDOWN_CANHAO,
    ZOOM_NIVEIS, ZOOM_HISTERESE,
    NAVIO_TIPOS,
)
from .utils import clamp


# ---------------------------------------------------------------------------
# Geometria
# ---------------------------------------------------------------------------

def distancia(a, b) -> float:
    """Distância euclidiana entre dois navios (ou quaisquer objetos com x, y).

    Args:
        a: Objeto com atributos ``x`` e ``y``.
        b: Objeto com atributos ``x`` e ``y``.

    Returns:
        Distância em unidades de jogo.
    """
    return math.hypot(a.x - b.x, a.y - b.y)


def rumo_para(a, b) -> float:
    """Rumo em graus de *a* em direção a *b* (Norte = 0, sentido horário).

    Args:
        a: Navio de origem.
        b: Navio de destino.

    Returns:
        Ângulo em graus no intervalo [0, 360).
    """
    dx = b.x - a.x
    dy = b.y - a.y
    return math.degrees(math.atan2(dx, dy)) % 360


def dentro_do_arco(atirador, alvo, lado: str) -> tuple[bool, float]:
    """Verifica se *alvo* está dentro do arco de tiro de *lado* de *atirador*.

    Arcos:
    - Estibordo: ângulo relativo 20° a 160°.
    - Bombordo:  ângulo relativo 200° a 340°.

    Args:
        atirador: Navio que vai atirar.
        alvo:     Navio alvo.
        lado:     'estibordo' ou 'bombordo'.

    Returns:
        Tupla (dentro_do_arco: bool, distancia: float).
    """
    d = distancia(atirador, alvo)
    if d > atirador.alcance_canhao:
        return False, d
    r = rumo_para(atirador, alvo)
    rel = (r - atirador.heading) % 360
    if lado == 'estibordo':
        ok = 20 <= rel <= 160
    else:
        ok = 200 <= rel <= 340
    return ok, d


# ---------------------------------------------------------------------------
# Resolução de dano
# ---------------------------------------------------------------------------

def escolher_parte_atingida() -> str:
    """Seleciona aleatoriamente qual parte do navio foi atingida.

    Returns:
        Nome da parte atingida ('casco', 'mastro', 'vela' ou 'roda').
    """
    pesos = {'casco': 45, 'mastro': 20, 'vela': 20, 'roda': 15}
    partes = list(pesos.keys())
    return random.choices(partes, weights=[pesos[p] for p in partes], k=1)[0]


def disparar_canhao_unico(atirador, alvo, canhao, log) -> str | bool:
    """Executa o disparo de um único canhão contra o alvo.

    A chance de acerto depende do erro de estimativa de distância, da
    instabilidade causada pelo dano no casco e da distância real.

    Args:
        atirador: Navio que atira.
        alvo:     Navio alvo.
        canhao:   Objeto Canhao sendo disparado.
        log:      Deque de log para registrar o resultado.

    Returns:
        'acerto', 'erro', ou False se o alvo estiver fora de arco/alcance.
    """
    ok, d = dentro_do_arco(atirador, alvo, canhao.lado)
    if not ok:
        return False

    erro_estimativa = abs(canhao.dist_alvo - d)
    instabilidade = (100 - atirador.partes['casco']) / 100 * 35
    chance_base = clamp(88 - erro_estimativa * 0.18 - instabilidade - d * 0.03, 4, 92)
    chance_acerto = chance_base * atirador.multiplicador_moral()

    if random.uniform(0, 100) < chance_acerto:
        parte = escolher_parte_atingida()
        dano = random.uniform(9, 19)
        alvo.partes[parte] = clamp(alvo.partes[parte] - dano, 0, 100)
        log.append(
            f"[ACERTO] Canhao {canhao.label} acerta {alvo.nome} no(a) {parte} (-{dano:.0f}%)"
        )
        atirador.registrar_acerto_moral()
        return "acerto"
    else:
        log.append(f"[ERRO] Canhao {canhao.label} erra o alvo")
        return "erro"


def disparar_canhoes_navio(estado, atirador, alvo) -> None:
    """Dispara todos os canhões armados de *atirador* contra *alvo*.

    Respeita arco, alcance e cooldown individual de cada canhão.

    Args:
        estado:   Estado atual do jogo.
        atirador: Navio que atira.
        alvo:     Navio alvo.
    """
    e_jogador = atirador is estado.jogador
    cooldown_mult_base = 1.0 if e_jogador else NAVIO_TIPOS[estado.tipo_navio]["cooldown_mult"]
    mult_moral = max(atirador.multiplicador_moral(), 0.05)
    cooldown_mult = cooldown_mult_base / mult_moral

    for lado in ('bombordo', 'estibordo'):
        for c in atirador.canhoes[lado]:
            if not c.armado():
                continue
            if estado.tempo < c.proximo_tiro:
                continue
            ok, _ = dentro_do_arco(atirador, alvo, lado)
            if not ok:
                continue
            resultado = disparar_canhao_unico(atirador, alvo, c, estado.log)
            if resultado in ("acerto", "erro"):
                if e_jogador:
                    estado.stats["tiros_jogador"] += 1
                    if resultado == "acerto":
                        estado.stats["acertos_jogador"] += 1
                else:
                    estado.stats["tiros_inimigo"] += 1
                    if resultado == "acerto":
                        estado.stats["acertos_inimigo"] += 1
                c.proximo_tiro = (
                    estado.tempo + COOLDOWN_CANHAO * cooldown_mult
                    + random.uniform(-0.5, 0.8)
                )


# ---------------------------------------------------------------------------
# Zoom adaptativo do mapa
# ---------------------------------------------------------------------------

def escolher_zoom(d: float, zoom_atual: int | None) -> int:
    """Seleciona o nível de zoom mais adequado para a distância *d*.

    Usa histerese (ZOOM_HISTERESE) para evitar alternância rápida entre
    níveis quando os navios estão na fronteira.

    Args:
        d:          Distância atual entre os navios.
        zoom_atual: Nível de zoom em uso (None na primeira chamada).

    Returns:
        O nível de zoom escolhido (um dos valores em ZOOM_NIVEIS).
    """
    alvo = d * 0.75
    if zoom_atual is None:
        for n in ZOOM_NIVEIS:
            if n >= alvo:
                return n
        return ZOOM_NIVEIS[-1]

    idx_atual = ZOOM_NIVEIS.index(zoom_atual)
    if alvo > zoom_atual and idx_atual < len(ZOOM_NIVEIS) - 1:
        return ZOOM_NIVEIS[idx_atual + 1]
    if idx_atual > 0:
        nivel_abaixo = ZOOM_NIVEIS[idx_atual - 1]
        if alvo < nivel_abaixo * ZOOM_HISTERESE:
            return nivel_abaixo
    return zoom_atual
