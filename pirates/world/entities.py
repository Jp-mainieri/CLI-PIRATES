"""entities.py – Entidades leves do mundo aberto (navios inimigos fora de combate)."""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from ..constants import MUNDO_TAMANHO

if TYPE_CHECKING:
    from ..core.porao import Porao


@dataclass
class Ilha:
    """Uma ilha no mundo aberto com forma orgânica harmônica.

    A borda é definida por:
        raio(θ) = raio_base * (1 + a1*sin(k1*θ+f1) + a2*sin(k2*θ+f2) + a3*sin(k3*θ+f3))
    """
    x: float
    y: float
    raio_base: float
    a1: float; a2: float; a3: float  # amplitudes harmônicas
    k1: int;   k2: int;   k3: int    # frequências harmônicas
    f1: float; f2: float; f3: float  # fases harmônicas

    @property
    def raio_maximo(self) -> float:
        """Raio máximo possível (envelope externo para coarse filter)."""
        return self.raio_base * (1.0 + max(self.a1, self.a2, self.a3))


def eh_solido_ilha(x: float, y: float, ilha: Ilha, mundo_tamanho: float = MUNDO_TAMANHO) -> bool:
    """Retorna True se (x, y) está dentro da ilha (usando forma harmônica).

    Passa mundo_tamanho=1e9 para desativar o wraparound toroidal (coords de arena).
    """
    dx = x - ilha.x
    dy = y - ilha.y
    if abs(dx) > mundo_tamanho / 2:
        dx -= math.copysign(mundo_tamanho, dx)
    if abs(dy) > mundo_tamanho / 2:
        dy -= math.copysign(mundo_tamanho, dy)
    dist = math.hypot(dx, dy)
    if dist >= ilha.raio_maximo:
        return False
    if dist == 0:
        return True
    theta = math.atan2(dy, dx)
    raio = ilha.raio_base * (
        1.0
        + ilha.a1 * math.sin(ilha.k1 * theta + ilha.f1)
        + ilha.a2 * math.sin(ilha.k2 * theta + ilha.f2)
        + ilha.a3 * math.sin(ilha.k3 * theta + ilha.f3)
    )
    return dist < raio


@dataclass
class Porto:
    """Um porto no mundo aberto.

    Attributes:
        x, y: Posição toroidal no mundo.
        nome: Nome exibido no HUD.
    """
    x: float
    y: float
    nome: str = "Porto Franco"


@dataclass
class NavioMundo:
    """Um navio inimigo existindo no mundo aberto, fora de combate.

    Attributes:
        x, y:         Posição no mundo (unidades de jogo, toroidal).
        heading:      Rumo atual em graus.
        heading_alvo: Rumo para o qual está virando.
        velocidade:   Velocidade atual (unidades/segundo).
        status:       'patrulha', 'fugindo' ou 'afundado'.
        moral_atual:  Preservado se já esteve em combate (status 'fugindo').
                      None se nunca combateu (spawna 'fresco' ao engajar).
        partes:       Dict parte->HP preservado se já esteve em combate.
                      None se nunca combateu.
        agua:         Água preservada se já esteve em combate. 0.0 se nunca.
        porao:        Porão preservado entre batalhas (None se nunca combateu).
        loot:         Porão-loot deixado ao afundar (None se já coletado).
        tipo_navio:   Chave de NAVIO_TIPOS sorteada no spawn ('chalupa'/'brigantim'/'galeao').
        elite:        True se este navio é uma variante elite (mais forte, mais loot).
        slots_vela:   Loadout de slots de vela (ver pirates/core/velas.py),
                      sorteado no spawn — sem loja pra NPCs, fica fixo.
        velocidade_lateral: Deriva lateral (doc09_deriva.md), persistida
                      tick a tick igual à de Navio.
    """
    x: float
    y: float
    heading: float = 0.0
    heading_alvo: float = 0.0
    velocidade: float = 0.0
    status: str = "patrulha"  # 'patrulha' | 'fugindo' | 'afundado'
    moral_atual: float | None = None
    partes: dict[str, float] | None = None
    agua: float = 0.0
    porao: Porao | None = None
    loot: Porao | None = None
    avoidance_mult: float = 2.0  # personalidade: evita ilha quando dist < raio_max * mult
    tipo_navio: str = "brigantim"
    elite: bool = False
    slots_vela: list[dict] = field(default_factory=list)
    velocidade_lateral: float = 0.0
