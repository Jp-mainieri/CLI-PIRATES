"""simulation.py – Tick do mundo aberto e transformações de coordenadas."""

import math
import random

from ..constants import MUNDO_TAMANHO, NAVIO_TIPOS, PESO_CASCO, AREA_CASCO
from .entities import NavioMundo
from .state import EstadoMundo
from ..core.movimento import calcular_tick_fisica
from ..core.vento import angulo_relativo_vento


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


# ---------------------------------------------------------------------------
# IA do mundo
# ---------------------------------------------------------------------------

def atualizar_ia_mundo(
    estado_mundo: EstadoMundo, dt: float,
    vento_direcao: float | None = None,
    vento_intensidade: float = 0.0,
) -> None:
    """Atualiza movimento de todos os NavioMundo não-afundados.

    Usa a mesma física de vento/slots de vela/deriva do combate (ver
    pirates/core/movimento.py), com wraparound toroidal no lugar de
    clamp. Comportamento de patrulha: a cada tick com 5% de chance sorteia
    novo heading e cruza mais devagar (1/3 do teto físico via
    `fator_vmax_extra`). Comportamento de fuga: se dentro de
    MUNDO_ALCANCE_VISAO_FUGA, corre na direção oposta ao jogador em
    velocidade física plena. Fora disso, comportamento de patrulha (mas
    mantém status 'fugindo' para preservar partes/agua/moral).

    Args:
        vento_direcao: Direção atual do vento (doc08_vento.md), ou None
            pra usar um ângulo neutro (retrocompatibilidade/testes).
        vento_intensidade: Intensidade atual do vento, em nós.
    """
    for navio in estado_mundo.inimigos:
        if navio.status == "afundado":
            continue

        params = NAVIO_TIPOS[navio.tipo_navio]

        dx, dy = delta_toroidal(
            navio.x, navio.y,
            estado_mundo.jogador_x, estado_mundo.jogador_y,
        )

        if navio.status == "fugindo":
            # Sempre foge na direção oposta ao jogador, sem limite de distância
            rumo_pro_jogador = math.degrees(math.atan2(dx, dy)) % 360
            navio.heading_alvo = (rumo_pro_jogador + 180) % 360
            fator_vmax_extra = 1.0
        else:
            if random.random() < 0.05:
                navio.heading_alvo = random.uniform(0, 360)
            fator_vmax_extra = 1.0 / 3.0

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
            direcao = vento_direcao
        else:
            ang = 90.0
            direcao = 0.0

        (
            navio.heading, navio.velocidade, navio.velocidade_lateral, mov_dx, mov_dy,
            _eff, _fator_int,
        ) = calcular_tick_fisica(
            navio.heading, navio.heading_alvo, navio.velocidade, navio.velocidade_lateral,
            params["giro_graus_seg"], params["velocidade_max_base"], navio.slots_vela,
            PESO_CASCO[navio.tipo_navio], AREA_CASCO[navio.tipo_navio], params["num_velas"],
            False, 1.0, dt,
            ang, vento_intensidade, direcao,
            fator_vmax_extra=fator_vmax_extra,
        )
        navio.x = (navio.x + mov_dx) % MUNDO_TAMANHO
        navio.y = (navio.y + mov_dy) % MUNDO_TAMANHO


def atualizar_jogador_mundo(
    estado_mundo: EstadoMundo, jogador, dt: float,
    angulo_relativo_vento_atual: float = 90.0,
    intensidade_vento_atual: float = 0.0,
    vento_direcao_atual: float = 0.0,
) -> None:
    """Aplica física de movimento do jogador no mundo aberto com wrap
    toroidal, usando os campos reais do `Navio` (slots de vela, peso/área
    de casco, âncora) — mesma física do combate (ver
    pirates/core/movimento.py). Muta `jogador` in-place (heading,
    velocidade, velocidade_lateral, eficiencia_vento_atual,
    fator_intensidade_vento_atual) e sincroniza os espelhos de
    `estado_mundo.jogador_*`.
    """
    fator_dano = (jogador.partes['vela'] / 100) * (jogador.partes['mastro'] / 100)
    fator_upgrade = 1.0 + jogador.upgrades.get('velocidade_giro', 0.0)

    (
        jogador.heading, jogador.velocidade, jogador.velocidade_lateral, dx, dy,
        jogador.eficiencia_vento_atual, jogador.fator_intensidade_vento_atual,
    ) = calcular_tick_fisica(
        jogador.heading, jogador.heading_alvo, jogador.velocidade, jogador.velocidade_lateral,
        jogador.giro_graus_seg, jogador.velocidade_max_base, jogador.slots_vela,
        jogador.peso_casco, jogador.area_casco, jogador.num_velas, jogador.ancorado,
        fator_dano, dt,
        angulo_relativo_vento_atual, intensidade_vento_atual, vento_direcao_atual,
        fator_vmax_extra=fator_upgrade,
    )

    estado_mundo.jogador_x = (estado_mundo.jogador_x + dx) % MUNDO_TAMANHO
    estado_mundo.jogador_y = (estado_mundo.jogador_y + dy) % MUNDO_TAMANHO
    estado_mundo.jogador_heading = jogador.heading
    estado_mundo.jogador_velocidade = jogador.velocidade


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
