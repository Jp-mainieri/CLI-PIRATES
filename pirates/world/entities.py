"""entities.py – Entidades leves do mundo aberto (navios inimigos fora de combate)."""

from dataclasses import dataclass, field


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
