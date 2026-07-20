"""
movimento.py – Física de movimento compartilhada entre combate e mundo
aberto (doc08_vento.md, doc09_deriva.md, doc10_customizacao_vela.md).

`calcular_tick_fisica` é uma função pura: não muta nada, não conhece
`Navio` nem `NavioMundo` — só recebe os escalares/listas necessários e
devolve o novo estado físico do tick. Isso deixa a mesma fórmula (giro,
propulsão por equilíbrio empuxo-vs-arrasto, deriva lateral por leme e
por través, empuxo constante de vento) reaproveitável tanto pelo
`Navio.atualizar_movimento` (coords de arena, clamp) quanto pelo tick de
navegação do mundo aberto (coords toroidais, `% MUNDO_TAMANHO`), sem
duplicar a física em dois lugares que podem divergir com o tempo.
"""

import math

from .velas import eficiencia_vento_bruta, bonus_fixo_vela_bruto, bonus_curva_vela_bruto
from .vento import empuxo_lateral_vento, empuxo_constante_vento, fator_intensidade_vento
from ..constants import (
    ACEL_VEL_SEG, K_ARRASTO_CASCO,
    BASE_ADERENCIA, VELOCIDADE_REFERENCIA_ADERENCIA, PESO_REFERENCIA_ADERENCIA,
)


def forca_correcao_deriva(velocidade: float, peso_casco: float) -> float:
    """Força de correção (aderência) da deriva lateral, em 1/segundo.
    Sobe com a velocidade atual (mais aderência em alta velocidade) e cai
    com o peso do casco (navios pesados corrigem mais devagar, deslizam
    mais – doc09_deriva.md §3)."""
    fator_velocidade = 1.0 + velocidade / VELOCIDADE_REFERENCIA_ADERENCIA
    fator_peso = peso_casco / PESO_REFERENCIA_ADERENCIA
    return BASE_ADERENCIA * fator_velocidade / fator_peso


def calcular_tick_fisica(
    heading: float,
    heading_alvo: float,
    velocidade: float,
    velocidade_lateral: float,
    giro_graus_seg_base: float,
    velocidade_max_base: float,
    slots_vela: list[dict],
    peso_casco: float,
    area_casco: float,
    num_velas: int,
    ancorado: bool,
    fator_dano: float,
    dt: float,
    angulo_relativo_vento_atual: float,
    intensidade_vento_atual: float,
    vento_direcao_atual: float,
    fator_vmax_extra: float = 1.0,
) -> tuple[float, float, float, float, float, float, float]:
    """Avança um tick de física de movimento.

    Args:
        heading, heading_alvo, velocidade, velocidade_lateral: Estado
            físico atual do navio.
        giro_graus_seg_base: Taxa de giro base do tipo de navio.
        velocidade_max_base: Velocidade base do tipo de navio.
        slots_vela: Lista de slots de vela da instância (ver velas.py).
        peso_casco, area_casco: Constantes físicas do tipo de navio.
        num_velas: Número de velas (proxy de área vélica pro empuxo
            lateral de través).
        ancorado: Se True, zera vmax e suprime os dois empuxos de vento
            (lateral de través e constante) — o leme continua girando.
        fator_dano: (partes['vela']/100)*(partes['mastro']/100), ou 1.0
            se o chamador não modela dano de vela/mastro (ex: IA do
            mundo aberto fora de combate).
        dt: Delta de tempo do tick, em segundos.
        angulo_relativo_vento_atual, intensidade_vento_atual,
            vento_direcao_atual: Estado do vento global no tick.
        fator_vmax_extra: Multiplicador extra sobre o teto físico de
            velocidade (1.0 = sem limite artificial). Usado só pela IA
            de patrulha do mundo aberto pra cruzar mais devagar que em
            fuga — não deve ser usado pro jogador em nenhum modo.

    Returns:
        (novo_heading, nova_velocidade, nova_velocidade_lateral, dx, dy,
        eficiencia_vento_bruta, fator_intensidade_vento) — dx/dy são o
        deslocamento do tick (quem chama decide clamp ou wraparound).
    """
    eficiencia_bruta = eficiencia_vento_bruta(slots_vela, angulo_relativo_vento_atual)
    fator_intensidade = fator_intensidade_vento(intensidade_vento_atual)

    # --- Giro ---
    diff = (heading_alvo - heading + 540) % 360 - 180
    giro_max = giro_graus_seg_base * (1.0 + bonus_curva_vela_bruto(slots_vela)) * dt
    if abs(diff) <= giro_max:
        delta_heading = diff
        novo_heading = heading_alvo
    else:
        delta_heading = giro_max if diff > 0 else -giro_max
        novo_heading = (heading + delta_heading) % 360

    # --- Propulsão: equilíbrio empuxo-vs-arrasto, sem teto artificial ---
    if ancorado:
        vmax = 0.0
    else:
        empuxo = (
            velocidade_max_base
            * (1.0 + bonus_fixo_vela_bruto(slots_vela))
            * eficiencia_bruta
            * fator_intensidade
            * fator_vmax_extra
        )
        if empuxo <= 0 or area_casco <= 0:
            vmax = 0.0
        else:
            vmax = math.sqrt(empuxo / (K_ARRASTO_CASCO * area_casco)) * fator_dano

    # Ganhar velocidade depende de vento/vela (eficiencia_bruta pode ser 0
    # com velas fechadas); perder velocidade é sempre o arrasto do casco
    # freando, independente de vela — senão o navio nunca desacelera
    # quando eficiencia_bruta == 0 (ex: todas as velas em 0%/vazias).
    if velocidade < vmax:
        nova_velocidade = min(vmax, velocidade + ACEL_VEL_SEG * dt * eficiencia_bruta)
    else:
        nova_velocidade = max(vmax, velocidade - ACEL_VEL_SEG * dt)

    # --- Deriva lateral: curva de leme (sempre) ---
    nova_velocidade_lateral = velocidade_lateral + nova_velocidade * math.sin(math.radians(delta_heading))

    # --- Deriva lateral: vento de través (suprimida se ancorado) ---
    if not ancorado:
        nova_velocidade_lateral += empuxo_lateral_vento(
            num_velas, intensidade_vento_atual, angulo_relativo_vento_atual,
        ) * dt

    forca_correcao = forca_correcao_deriva(nova_velocidade, peso_casco)
    fracao_removida = min(1.0, forca_correcao * dt)
    nova_velocidade_lateral *= (1.0 - fracao_removida)

    # --- Empuxo constante (suprimido se ancorado) ---
    if ancorado:
        vx_empuxo = 0.0
        vy_empuxo = 0.0
    else:
        mag_empuxo = empuxo_constante_vento(peso_casco, area_casco, intensidade_vento_atual)
        rad_empuxo = math.radians((vento_direcao_atual + 180.0) % 360)
        vx_empuxo = math.sin(rad_empuxo) * mag_empuxo
        vy_empuxo = math.cos(rad_empuxo) * mag_empuxo

    # --- Deslocamento do tick ---
    rad = math.radians(novo_heading)
    rad_lateral = math.radians(novo_heading + 90.0)
    dx = (
        math.sin(rad) * nova_velocidade
        + math.sin(rad_lateral) * nova_velocidade_lateral
        + vx_empuxo
    ) * dt
    dy = (
        math.cos(rad) * nova_velocidade
        + math.cos(rad_lateral) * nova_velocidade_lateral
        + vy_empuxo
    ) * dt

    return (
        novo_heading, nova_velocidade, nova_velocidade_lateral, dx, dy,
        eficiencia_bruta, fator_intensidade,
    )
