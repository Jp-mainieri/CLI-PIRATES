"""simulation.py – Tick do mundo aberto e transformações de coordenadas."""

import math
import random

from ..constants import (
    MUNDO_TAMANHO, MUNDO_ALCANCE_VISAO_FUGA, NAVIO_TIPOS, ACEL_VEL_SEG,
)
from .entities import NavioMundo
from .state import EstadoMundo
from ..core.vento import angulo_relativo_vento, eficiencia_vento as _eficiencia_vento


# ---------------------------------------------------------------------------
# Física toroidal
# ---------------------------------------------------------------------------

def delta_toroidal(x1: float, y1: float, x2: float, y2: float) -> tuple[float, float]:
    """Retorna (dx, dy) no menor caminho toroidal de (x1,y1) para (x2,y2)."""
    dx = x2 - x1
    dy = y2 - y1
    if abs(dx) > MUNDO_TAMANHO / 2:
        dx -= math.copysign(MUNDO_TAMANHO, dx)
    if abs(dy) > MUNDO_TAMANHO / 2:
        dy -= math.copysign(MUNDO_TAMANHO, dy)
    return dx, dy


def atualizar_posicao_toroidal(
    x: float,
    y: float,
    heading: float,
    heading_alvo: float,
    velocidade: float,
    velocidade_max: float,
    giro_graus_seg: float,
    dt: float,
    eficiencia_vento: float = 1.0,
    fator_intensidade_vento: float = 1.0,
) -> tuple[float, float, float, float]:
    """Aplica física de giro + propulsão com wraparound toroidal.

    Idêntica à física de Navio.atualizar_movimento, mas com
    ``% MUNDO_TAMANHO`` no lugar do clamp(-MAPA_TAMANHO, MAPA_TAMANHO).
    Aceita os mesmos fatores de vento de doc08_vento.md: eficiencia_vento
    (ângulo relativo, afeta teto e aceleração) e fator_intensidade_vento
    (curva de intensidade, só afeta o teto).

    Returns:
        (x, y, heading, velocidade) atualizados.
    """
    diff = (heading_alvo - heading + 540) % 360 - 180
    giro_max = giro_graus_seg * dt
    if abs(diff) <= giro_max:
        heading = heading_alvo
    else:
        heading = (heading + (giro_max if diff > 0 else -giro_max)) % 360

    vmax_efetivo = velocidade_max * eficiencia_vento * fator_intensidade_vento
    acel = ACEL_VEL_SEG * dt * eficiencia_vento
    if velocidade < vmax_efetivo:
        velocidade = min(vmax_efetivo, velocidade + acel)
    else:
        velocidade = max(vmax_efetivo, velocidade - acel)

    rad = math.radians(heading)
    x = (x + math.sin(rad) * velocidade * dt) % MUNDO_TAMANHO
    y = (y + math.cos(rad) * velocidade * dt) % MUNDO_TAMANHO
    return x, y, heading, velocidade


# ---------------------------------------------------------------------------
# IA do mundo
# ---------------------------------------------------------------------------

def atualizar_ia_mundo(
    estado_mundo: EstadoMundo, dt: float,
    vento_direcao: float | None = None,
    fator_intensidade_vento: float = 1.0,
) -> None:
    """Atualiza movimento de todos os NavioMundo não-afundados.

    Comportamento de patrulha: a cada tick com 5% de chance sorteia novo heading.
    Comportamento de fuga: se dentro de MUNDO_ALCANCE_VISAO_FUGA, corre na
    direção oposta ao jogador. Fora disso, comportamento de patrulha (mas
    mantém status 'fugindo' para preservar partes/agua/moral).

    Args:
        vento_direcao: Direção atual do vento (doc08_vento.md), ou None
            pra não aplicar nenhum efeito de vento (retrocompatibilidade).
        fator_intensidade_vento: Fator de intensidade já resolvido (ver
            pirates/core/vento.py:fator_intensidade_vento), aplicado a
            todos os inimigos junto da eficiência angular individual.
    """
    for navio in estado_mundo.inimigos:
        if navio.status == "afundado":
            continue

        params = NAVIO_TIPOS[navio.tipo_navio]
        vmax_patrulha = params["velocidade_max_base"] * 1 / 3
        vmax_fuga = params["velocidade_max_base"] * 3 / 3

        dx, dy = delta_toroidal(
            navio.x, navio.y,
            estado_mundo.jogador_x, estado_mundo.jogador_y,
        )
        d = (dx ** 2 + dy ** 2) ** 0.5

        if navio.status == "fugindo":
            # Sempre foge na direção oposta ao jogador, sem limite de distância
            rumo_pro_jogador = math.degrees(math.atan2(dx, dy)) % 360
            navio.heading_alvo = (rumo_pro_jogador + 180) % 360
            velocidade_max = vmax_fuga
        else:
            if random.random() < 0.05:
                navio.heading_alvo = random.uniform(0, 360)
            velocidade_max = vmax_patrulha

        # Evasão de ilhas (personalidade via avoidance_mult)
        for ilha in getattr(estado_mundo, 'ilhas', []):
            d_ilha = estado_mundo._distancia_toroidal(navio.x, navio.y, ilha.x, ilha.y)
            if d_ilha < ilha.raio_maximo * navio.avoidance_mult:
                _idx = navio.x - ilha.x
                _idy = navio.y - ilha.y
                if abs(_idx) > MUNDO_TAMANHO / 2:
                    _idx -= math.copysign(MUNDO_TAMANHO, _idx)
                if abs(_idy) > MUNDO_TAMANHO / 2:
                    _idy -= math.copysign(MUNDO_TAMANHO, _idy)
                navio.heading_alvo = math.degrees(math.atan2(_idx, _idy)) % 360
                break

        if vento_direcao is not None:
            ang = angulo_relativo_vento(navio.heading, vento_direcao)
            eff = _eficiencia_vento(navio.tipo_navio, ang)
        else:
            eff = 1.0

        navio.x, navio.y, navio.heading, navio.velocidade = atualizar_posicao_toroidal(
            navio.x, navio.y,
            navio.heading, navio.heading_alvo,
            navio.velocidade, velocidade_max,
            params["giro_graus_seg"],
            dt,
            eficiencia_vento=eff,
            fator_intensidade_vento=fator_intensidade_vento,
        )


def atualizar_jogador_mundo(
    estado_mundo: EstadoMundo, params: dict, dt: float,
    eficiencia_vento: float = 1.0,
    fator_intensidade_vento: float = 1.0,
) -> None:
    """Aplica física de movimento do jogador no mundo aberto com wrap toroidal."""
    velocidade_max = params["velocidade_max_base"] * estado_mundo.jogador_nivel_vela / 3
    (
        estado_mundo.jogador_x,
        estado_mundo.jogador_y,
        estado_mundo.jogador_heading,
        estado_mundo.jogador_velocidade,
    ) = atualizar_posicao_toroidal(
        estado_mundo.jogador_x,
        estado_mundo.jogador_y,
        estado_mundo.jogador_heading,
        estado_mundo.jogador_heading_alvo,
        estado_mundo.jogador_velocidade,
        velocidade_max,
        params["giro_graus_seg"],
        dt,
        eficiencia_vento=eficiencia_vento,
        fator_intensidade_vento=fator_intensidade_vento,
    )


# ---------------------------------------------------------------------------
# Transformação mundo ↔ arena
# ---------------------------------------------------------------------------

def mundo_para_arena(estado_mundo: EstadoMundo, navio_engajado: NavioMundo) -> tuple[float, float, float, float]:
    """Calcula o offset do navio engajado em coordenadas de arena.

    O jogador fica na origem; o inimigo fica no delta toroidal.

    Returns:
        (inimigo_x, inimigo_y, world_offset_x, world_offset_y)
    """
    world_offset_x = estado_mundo.jogador_x
    world_offset_y = estado_mundo.jogador_y
    dx, dy = delta_toroidal(
        estado_mundo.jogador_x, estado_mundo.jogador_y,
        navio_engajado.x, navio_engajado.y,
    )
    return dx, dy, world_offset_x, world_offset_y


def arena_para_mundo(
    world_offset_x: float,
    world_offset_y: float,
    arena_x: float,
    arena_y: float,
) -> tuple[float, float]:
    """Converte posição de arena de volta para coordenadas do mundo."""
    wx = (world_offset_x + arena_x) % MUNDO_TAMANHO
    wy = (world_offset_y + arena_y) % MUNDO_TAMANHO
    return wx, wy
