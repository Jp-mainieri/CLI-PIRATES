"""state.py – Estado do mundo aberto em navegação livre."""

import random

from ..constants import MUNDO_TAMANHO, MUNDO_NUM_INIMIGOS, MUNDO_ESPACAMENTO_MIN
from .entities import NavioMundo


class EstadoMundo:
    """Estado da navegação livre: posição do jogador no mundo + inimigos ativos.

    Attributes:
        tipo_navio:           Chave NAVIO_TIPOS usada pelos navios inimigos.
        jogador_x, jogador_y: Posição do jogador no mundo (toroidal).
        jogador_heading:      Rumo atual do jogador no mundo.
        jogador_heading_alvo: Rumo alvo (controle do leme).
        jogador_nivel_vela:   Nível de vela atual.
        jogador_velocidade:   Velocidade atual.
        inimigos:             Lista de NavioMundo (ativos, fugindo ou afundados).
        mapa_mundo_visivel:   Toggle de exibição do painel MAPA MUNDO.
    """

    def __init__(self, tipo_navio: str) -> None:
        self.tipo_navio = tipo_navio
        self.jogador_x: float = MUNDO_TAMANHO / 2
        self.jogador_y: float = MUNDO_TAMANHO / 2
        self.jogador_heading: float = 0.0
        self.jogador_heading_alvo: float = 0.0
        self.jogador_nivel_vela: int = 1
        self.jogador_velocidade: float = 0.0
        self.inimigos: list[NavioMundo] = []
        self.mapa_mundo_visivel: bool = False
        self.sortear_novo_lote()

    def sortear_novo_lote(self) -> None:
        """Remove navios não-afundados e sorteia MUNDO_NUM_INIMIGOS novos,
        respeitando espaçamento mínimo entre si e do jogador."""
        self.inimigos = [n for n in self.inimigos if n.status in ("afundado", "fugindo")]
        for _ in range(MUNDO_NUM_INIMIGOS):
            for _t in range(200):
                x = random.uniform(0, MUNDO_TAMANHO)
                y = random.uniform(0, MUNDO_TAMANHO)
                if self._distancia_toroidal(x, y, self.jogador_x, self.jogador_y) < MUNDO_ESPACAMENTO_MIN:
                    continue
                if any(
                    self._distancia_toroidal(x, y, n.x, n.y) < MUNDO_ESPACAMENTO_MIN
                    for n in self.inimigos
                    if n.status != "afundado"
                ):
                    continue
                self.inimigos.append(
                    NavioMundo(x=x, y=y, heading=random.uniform(0, 360))
                )
                break

    def _distancia_toroidal(self, x1: float, y1: float, x2: float, y2: float) -> float:
        """Distância euclidiana considerando o wraparound do mundo toroidal."""
        dx = abs(x1 - x2)
        dy = abs(y1 - y2)
        dx = min(dx, MUNDO_TAMANHO - dx)
        dy = min(dy, MUNDO_TAMANHO - dy)
        return (dx ** 2 + dy ** 2) ** 0.5
