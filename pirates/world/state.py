"""state.py – Estado do mundo aberto em navegação livre."""

import random
from collections import deque

import math

from ..constants import (
    MUNDO_TAMANHO, MUNDO_NUM_INIMIGOS, MUNDO_ESPACAMENTO_MIN,
    MUNDO_NUM_PORTOS, MUNDO_NUM_ILHAS, ILHA_RAIO_MIN, ILHA_RAIO_MAX, ILHA_PORTO_EXCLUSAO,
)
from .entities import NavioMundo, Porto, Ilha, eh_solido_ilha
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

    def __init__(self, tipo_navio: str, seed: int | None = None) -> None:
        self.tipo_navio = tipo_navio
        if seed is None:
            seed = random.randint(0, 2**31 - 1)
        self.seed_mundo: int = seed
        self._rng = random.Random(seed)
        self.notoriedade: int = 0
        self.portos_visitados: list[int] = []
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
        self.rastro_jogador: deque[tuple[float, float]] = deque(maxlen=128)
        self.destrocos_jogador: list[tuple[float, float]] = []
        self.ilhas: list[Ilha] = []
        self.em_colisao_ilha: bool = False
        self._sortear_portos()
        self._sortear_ilhas()
        self.sortear_novo_lote()

    def _sortear_portos(self) -> None:
        """Sorteia posições dos portos fixos de forma determinística via self._rng."""
        self.portos = []
        for _ in range(MUNDO_NUM_PORTOS):
            for _t in range(200):
                x = self._rng.uniform(0, MUNDO_TAMANHO)
                y = self._rng.uniform(0, MUNDO_TAMANHO)
                if self._distancia_toroidal(x, y, self.jogador_x, self.jogador_y) < MUNDO_ESPACAMENTO_MIN:
                    continue
                if any(
                    self._distancia_toroidal(x, y, p.x, p.y) < MUNDO_ESPACAMENTO_MIN
                    for p in self.portos
                ):
                    continue
                self.portos.append(Porto(x=x, y=y))
                break

    def _sortear_ilhas(self) -> None:
        """Sorteia ilhas deterministicamente via self._rng (mesma seed → mesmo layout)."""
        self.ilhas = []
        for _ in range(MUNDO_NUM_ILHAS):
            for _t in range(200):
                x = self._rng.uniform(0, MUNDO_TAMANHO)
                y = self._rng.uniform(0, MUNDO_TAMANHO)
                raio_base = self._rng.uniform(ILHA_RAIO_MIN, ILHA_RAIO_MAX)
                candidata_max = raio_base * 1.30
                # Exclusão vs spawn e portos
                if self._distancia_toroidal(x, y, self.jogador_x, self.jogador_y) < ILHA_PORTO_EXCLUSAO:
                    continue
                if any(self._distancia_toroidal(x, y, p.x, p.y) < ILHA_PORTO_EXCLUSAO
                       for p in self.portos):
                    continue
                # Separação mínima entre ilhas (sem sobreposição + buffer)
                if any(self._distancia_toroidal(x, y, ilha.x, ilha.y) < ilha.raio_maximo + candidata_max + 50
                       for ilha in self.ilhas):
                    continue
                a1 = self._rng.uniform(0.15, 0.30)
                a2 = self._rng.uniform(0.15, 0.30)
                a3 = self._rng.uniform(0.15, 0.30)
                k1 = self._rng.randint(2, 6)
                k2 = self._rng.randint(2, 6)
                k3 = self._rng.randint(2, 6)
                f1 = self._rng.uniform(0, 2 * math.pi)
                f2 = self._rng.uniform(0, 2 * math.pi)
                f3 = self._rng.uniform(0, 2 * math.pi)
                self.ilhas.append(Ilha(
                    x=x, y=y, raio_base=raio_base,
                    a1=a1, a2=a2, a3=a3,
                    k1=k1, k2=k2, k3=k3,
                    f1=f1, f2=f2, f3=f3,
                ))
                break

    def sortear_novo_lote(self) -> None:
        """Remove navios patrulhando e sorteia MUNDO_NUM_INIMIGOS novos,
        respeitando espaçamento mínimo entre si, do jogador, dos portos e das ilhas."""
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
                if any(eh_solido_ilha(x, y, ilha) for ilha in self.ilhas):
                    continue
                self.inimigos.append(
                    NavioMundo(x=x, y=y, heading=random.uniform(0, 360),
                               avoidance_mult=random.uniform(1.5, 3.0))
                )
                break

    def _distancia_toroidal(self, x1: float, y1: float, x2: float, y2: float) -> float:
        """Distância euclidiana considerando o wraparound do mundo toroidal."""
        dx = abs(x1 - x2)
        dy = abs(y1 - y2)
        dx = min(dx, MUNDO_TAMANHO - dx)
        dy = min(dy, MUNDO_TAMANHO - dy)
        return (dx ** 2 + dy ** 2) ** 0.5
