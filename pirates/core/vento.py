"""
vento.py – Estado e cálculo de vento de CLI PIRATES (doc08_vento.md).

Vento é global e compartilhado entre jogador e inimigo. Direção e
intensidade derivam lentamente ao longo do tempo em direção a um alvo
resorteado periodicamente. A eficiência de vento por navio é derivada do
loadout de vela fixo de cada tipo (ver NAVIO_TIPOS['eficiencia_vento']).
"""

import random

from ..constants import (
    NAVIO_TIPOS,
    VENTO_INTENSIDADE_MIN, VENTO_INTENSIDADE_MAX,
    VENTO_INTENSIDADE_LIMITE_FRACA, VENTO_INTENSIDADE_LIMITE_MODERADA,
    VENTO_MULT_INTENSIDADE_CALMARIA, VENTO_MULT_INTENSIDADE_PLENA,
    VENTO_MULT_INTENSIDADE_MAXIMA,
    VENTO_DERIVA_DIRECAO_GRAUS_SEG, VENTO_DERIVA_INTENSIDADE_SEG,
    VENTO_RESORTEIO_MIN_SEG, VENTO_RESORTEIO_MAX_SEG,
    VENTO_ZONAS_ANGULO_MEIO,
)

_ZONA_ORDEM = ["zona_morta", "bolina", "traves", "popa"]


def angulo_relativo_vento(heading_navio: float, vento_direcao: float) -> float:
    """Ângulo relativo (0-180) entre o rumo do navio e a direção de onde o
    vento sopra. 0° = vento vindo direto da proa (contra); 180° = vento
    vindo direto da popa (a favor)."""
    return abs((heading_navio - vento_direcao + 540) % 360 - 180)


def zona_vento(angulo_relativo: float) -> str:
    """Nome da zona (doc08_vento.md seção 2) pro ângulo relativo dado."""
    if angulo_relativo <= 45:
        return "zona_morta"
    if angulo_relativo <= 90:
        return "bolina"
    if angulo_relativo <= 135:
        return "traves"
    return "popa"


def eficiencia_vento(tipo_navio: str, angulo_relativo: float) -> float:
    """Eficiência de vento (fração, pode passar de 1.0) pro tipo de navio e
    ângulo relativo dados, por interpolação linear entre os pontos-chave
    (meio de cada zona), com platô nas pontas."""
    tabela = NAVIO_TIPOS[tipo_navio]["eficiencia_vento"]
    angulo = max(0.0, min(180.0, angulo_relativo))

    if angulo <= VENTO_ZONAS_ANGULO_MEIO["zona_morta"]:
        return tabela["zona_morta"]
    if angulo >= VENTO_ZONAS_ANGULO_MEIO["popa"]:
        return tabela["popa"]

    for a_key, b_key in zip(_ZONA_ORDEM, _ZONA_ORDEM[1:]):
        a_ang = VENTO_ZONAS_ANGULO_MEIO[a_key]
        b_ang = VENTO_ZONAS_ANGULO_MEIO[b_key]
        if a_ang <= angulo <= b_ang:
            t = (angulo - a_ang) / (b_ang - a_ang)
            return tabela[a_key] + t * (tabela[b_key] - tabela[a_key])

    return tabela["popa"]  # inalcançável, guarda de segurança


def fator_intensidade_vento(intensidade: float) -> float:
    """Multiplicador de teto de velocidade máxima pela intensidade do
    vento (doc08_vento.md seção 6), com transição suave (interpolação
    linear), sem degraus: sobe de calmaria (0.5) até potência plena (1.0)
    entre 0 e VENTO_INTENSIDADE_LIMITE_FRACA nós; platô em potência plena
    entre VENTO_INTENSIDADE_LIMITE_FRACA e VENTO_INTENSIDADE_LIMITE_MODERADA
    nós; sobe de novo até o teto de rajada (1.3) entre
    VENTO_INTENSIDADE_LIMITE_MODERADA e VENTO_INTENSIDADE_MAX nós. Não
    afeta aceleração nem giro – só o teto de velocidade máxima."""
    i = max(VENTO_INTENSIDADE_MIN, min(VENTO_INTENSIDADE_MAX, intensidade))

    if i <= VENTO_INTENSIDADE_LIMITE_FRACA:
        t = i / VENTO_INTENSIDADE_LIMITE_FRACA
        return VENTO_MULT_INTENSIDADE_CALMARIA + t * (
            VENTO_MULT_INTENSIDADE_PLENA - VENTO_MULT_INTENSIDADE_CALMARIA
        )

    if i <= VENTO_INTENSIDADE_LIMITE_MODERADA:
        return VENTO_MULT_INTENSIDADE_PLENA

    t = (i - VENTO_INTENSIDADE_LIMITE_MODERADA) / (
        VENTO_INTENSIDADE_MAX - VENTO_INTENSIDADE_LIMITE_MODERADA
    )
    return VENTO_MULT_INTENSIDADE_PLENA + t * (
        VENTO_MULT_INTENSIDADE_MAXIMA - VENTO_MULT_INTENSIDADE_PLENA
    )


def _sortear_alvo(direcao_atual: float) -> tuple[float, float, float]:
    """Sorteia (direcao_alvo, intensidade_alvo, segundos_ate_proximo_resorteio)."""
    direcao_alvo = (direcao_atual + random.uniform(-60.0, 60.0)) % 360
    intensidade_alvo = random.uniform(VENTO_INTENSIDADE_MIN, VENTO_INTENSIDADE_MAX)
    proximo = random.uniform(VENTO_RESORTEIO_MIN_SEG, VENTO_RESORTEIO_MAX_SEG)
    return direcao_alvo, intensidade_alvo, proximo


def atualizar_vento(estado, dt: float) -> None:
    """Avança a deriva de direção/intensidade do vento em *estado* por *dt*
    segundos, resorteando o alvo quando o temporizador expira."""
    estado.vento_proximo_resorteio_em -= dt
    if estado.vento_proximo_resorteio_em <= 0:
        (
            estado.vento_direcao_alvo,
            estado.vento_intensidade_alvo,
            estado.vento_proximo_resorteio_em,
        ) = _sortear_alvo(estado.vento_direcao)

    diff = (estado.vento_direcao_alvo - estado.vento_direcao + 540) % 360 - 180
    passo = VENTO_DERIVA_DIRECAO_GRAUS_SEG * dt
    if abs(diff) <= passo:
        estado.vento_direcao = estado.vento_direcao_alvo
    else:
        estado.vento_direcao = (
            estado.vento_direcao + (passo if diff > 0 else -passo)
        ) % 360

    passo_i = VENTO_DERIVA_INTENSIDADE_SEG * dt
    if estado.vento_intensidade < estado.vento_intensidade_alvo:
        estado.vento_intensidade = min(
            estado.vento_intensidade_alvo, estado.vento_intensidade + passo_i
        )
    else:
        estado.vento_intensidade = max(
            estado.vento_intensidade_alvo, estado.vento_intensidade - passo_i
        )
