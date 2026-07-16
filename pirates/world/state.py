"""state.py – Estado do mundo aberto em navegação livre."""

import random

from ..constants import (
    MUNDO_TAMANHO, MUNDO_NUM_INIMIGOS, MUNDO_ESPACAMENTO_MIN,
    MUNDO_NUM_PORTOS,
)
from .entities import NavioMundo, Porto
from ..core.porao import Porao


class EstadoMundo:
    """Estado da navegação livre: posição do jogador no mundo + inimigos + portos.

    Attributes:
        tipo_navio:           Chave NAVIO_TIPOS usada pelos navios inimigos.
        jogador_x, jogador_y: Posição do jogador no mundo (toroidal).
        jogador_heading:      Rumo atual do jogador no mundo.
        jogador_heading_alvo: Rumo alvo (controle do leme).
        jogador_nivel_vela:   Nível de vela atual.
        jogador_velocidade:   Velocidade atual.
        inimigos:             Lista de NavioMundo (ativos, fugindo ou afundados).
        portos:               Lista de Porto fixos no mundo.
        mapa_mundo_visivel:   Toggle de exibição do painel MAPA MUNDO.
        loot_pendente:        Porão com loot que não coube ao coletar (Tier 3b consome).
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
        self.portos: list[Porto] = []
        self.mapa_mundo_visivel: bool = False
        self.loot_pendente: Porao | None = None
        self.em_combate: bool = False
        self.inimigo_engajado = None  # NavioMundo | None durante combate
        self._sortear_portos()
        self.sortear_novo_lote()

    def _sortear_portos(self) -> None:
        """Sorteia posições dos portos fixos respeitando MUNDO_ESPACAMENTO_MIN."""
        self.portos = []
        for _ in range(MUNDO_NUM_PORTOS):
            for _t in range(200):
                x = random.uniform(0, MUNDO_TAMANHO)
                y = random.uniform(0, MUNDO_TAMANHO)
                if self._distancia_toroidal(x, y, self.jogador_x, self.jogador_y) < MUNDO_ESPACAMENTO_MIN:
                    continue
                if any(
                    self._distancia_toroidal(x, y, p.x, p.y) < MUNDO_ESPACAMENTO_MIN
                    for p in self.portos
                ):
                    continue
                self.portos.append(Porto(x=x, y=y))
                break

    def sortear_novo_lote(self) -> None:
        """Remove navios patrulhando e sorteia MUNDO_NUM_INIMIGOS novos,
        respeitando espaçamento mínimo entre si, do jogador e dos portos."""
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
                if any(
                    self._distancia_toroidal(x, y, p.x, p.y) < MUNDO_ESPACAMENTO_MIN
                    for p in self.portos
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
