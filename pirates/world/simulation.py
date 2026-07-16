"""simulation.py – Tick do mundo aberto e transformações de coordenadas."""

import math
import random

from ..constants import (
    MUNDO_TAMANHO, MUNDO_ALCANCE_VISAO_FUGA, NAVIO_TIPOS, ACEL_VEL_SEG,
)
from .entities import NavioMundo
from .state import EstadoMundo


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
) -> tuple[float, float, float, float]:
    """Aplica física de giro + propulsão com wraparound toroidal.

    Idêntica à física de Navio.atualizar_movimento, mas com
    ``% MUNDO_TAMANHO`` no lugar do clamp(-MAPA_TAMANHO, MAPA_TAMANHO).

    Returns:
        (x, y, heading, velocidade) atualizados.
    """
    diff = (heading_alvo - heading + 540) % 360 - 180
    giro_max = giro_graus_seg * dt
    if abs(diff) <= giro_max:
        heading = heading_alvo
    else:
        heading = (heading + (giro_max if diff > 0 else -giro_max)) % 360

    acel = ACEL_VEL_SEG * dt
    if velocidade < velocidade_max:
        velocidade = min(velocidade_max, velocidade + acel)
    else:
        velocidade = max(velocidade_max, velocidade - acel)

    rad = math.radians(heading)
    x = (x + math.sin(rad) * velocidade * dt) % MUNDO_TAMANHO
    y = (y + math.cos(rad) * velocidade * dt) % MUNDO_TAMANHO
    return x, y, heading, velocidade


# ---------------------------------------------------------------------------
# IA do mundo
# ---------------------------------------------------------------------------

def atualizar_ia_mundo(estado_mundo: EstadoMundo, dt: float) -> None:
    """Atualiza movimento de todos os NavioMundo não-afundados.

    Comportamento de patrulha: a cada tick com 5% de chance sorteia novo heading.
    Comportamento de fuga: se dentro de MUNDO_ALCANCE_VISAO_FUGA, corre na
    direção oposta ao jogador. Fora disso, comportamento de patrulha (mas
    mantém status 'fugindo' para preservar partes/agua/moral).
    """
    params = NAVIO_TIPOS[estado_mundo.tipo_navio]
    vmax_patrulha = params["velocidade_max_base"] * 1 / 3
    vmax_fuga = params["velocidade_max_base"] * 3 / 3

    for navio in estado_mundo.inimigos:
        if navio.status == "afundado":
            continue

        dx, dy = delta_toroidal(
            navio.x, navio.y,
            estado_mundo.jogador_x, estado_mundo.jogador_y,
        )
        d = (dx ** 2 + dy ** 2) ** 0.5

        if navio.status == "fugindo" and d < MUNDO_ALCANCE_VISAO_FUGA:
            rumo_pro_jogador = math.degrees(math.atan2(dx, dy)) % 360
            navio.heading_alvo = (rumo_pro_jogador + 180) % 360
            velocidade_max = vmax_fuga
        else:
            if random.random() < 0.05:
                navio.heading_alvo = random.uniform(0, 360)
            velocidade_max = vmax_patrulha

        navio.x, navio.y, navio.heading, navio.velocidade = atualizar_posicao_toroidal(
            navio.x, navio.y,
            navio.heading, navio.heading_alvo,
            navio.velocidade, velocidade_max,
            params["giro_graus_seg"],
            dt,
        )


def atualizar_jogador_mundo(estado_mundo: EstadoMundo, params: dict, dt: float) -> None:
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
