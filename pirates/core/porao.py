"""porao.py – Sistema de carga física (pólvora, bolas, tábuas, ouro)."""

from __future__ import annotations

import random
from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .ship import Navio

TIPOS_CARGA = ("polvora", "bolas", "tabuas", "ouro")
CAPACIDADE_BARRIL = 25.0


@dataclass
class Barril:
    """Um barril de carga física.

    Attributes:
        tipo:       Um de TIPOS_CARGA.
        quantidade: 0 a CAPACIDADE_BARRIL.
    """
    tipo: str
    quantidade: float

    @property
    def cheio(self) -> bool:
        return self.quantidade >= CAPACIDADE_BARRIL

    @property
    def vazio(self) -> bool:
        return self.quantidade <= 0


class Porao:
    """Porão de um navio: lista de barris até um limite de slots.

    Attributes:
        capacidade: Número máximo de slots (barris) simultâneos.
        barris:     Lista de Barril atualmente a bordo (len <= capacidade).
    """

    def __init__(self, capacidade: int) -> None:
        self.capacidade = capacidade
        self.barris: list[Barril] = []

    def slots_livres(self) -> int:
        return self.capacidade - len(self.barris)

    def total(self, tipo: str) -> float:
        return sum(b.quantidade for b in self.barris if b.tipo == tipo)

    def consumir(self, tipo: str, quantidade: float) -> float:
        """Consome `quantidade` do tipo dado, dos barris existentes
        (esvaziando sequencialmente, o primeiro barril daquele tipo na
        lista primeiro). Remove barris que zerarem automaticamente.

        Returns:
            Quanto NÃO conseguiu consumir (0 se conseguiu tudo).
        """
        restante = quantidade
        i = 0
        while restante > 1e-9 and i < len(self.barris):
            b = self.barris[i]
            if b.tipo == tipo and not b.vazio:
                usado = min(b.quantidade, restante)
                b.quantidade -= usado
                restante -= usado
            i += 1
        self.barris = [b for b in self.barris if not b.vazio]
        return max(0.0, restante)

    def adicionar(self, tipo: str, quantidade: float) -> float:
        """Adiciona `quantidade` do tipo dado: primeiro nos barris
        existentes desse tipo com mais espaço livre (mais vazio primeiro),
        depois cria barris novos em slots livres.

        Returns:
            Excedente que não coube (0 se coube tudo).
        """
        restante = quantidade
        existentes = sorted(
            (b for b in self.barris if b.tipo == tipo and not b.cheio),
            key=lambda b: b.quantidade,
        )
        for b in existentes:
            espaco = CAPACIDADE_BARRIL - b.quantidade
            usado = min(espaco, restante)
            b.quantidade += usado
            restante -= usado
            if restante <= 1e-9:
                return 0.0
        while restante > 1e-9 and self.slots_livres() > 0:
            usado = min(CAPACIDADE_BARRIL, restante)
            self.barris.append(Barril(tipo=tipo, quantidade=usado))
            restante -= usado
        return max(0.0, restante)

    def remover_barril(self, indice: int) -> 'Barril | None':
        """Remove e retorna o barril num índice (usado por vender/descartar)."""
        if 0 <= indice < len(self.barris):
            return self.barris.pop(indice)
        return None


def estoque_inicial_jogador(capacidade: int) -> Porao:
    """Porão inicial do jogador: ~40% pólvora / 40% bolas / 20% tábuas, 0% ouro."""
    p = Porao(capacidade)
    n_polvora = max(1, round(capacidade * 0.4))
    n_bolas = max(1, round(capacidade * 0.4))
    n_tabuas = max(0, capacidade - n_polvora - n_bolas)
    for _ in range(n_polvora):
        p.barris.append(Barril("polvora", CAPACIDADE_BARRIL))
    for _ in range(n_bolas):
        p.barris.append(Barril("bolas", CAPACIDADE_BARRIL))
    for _ in range(n_tabuas):
        p.barris.append(Barril("tabuas", CAPACIDADE_BARRIL))
    return p


def gerar_porao_inimigo(capacidade: int) -> Porao:
    """Porão aleatório de um inimigo recém-spawnado: 1 barril de ouro
    garantido, mínimo 1 pólvora + 1 bolas garantidos, resto aleatório."""
    p = Porao(capacidade)
    p.barris.append(Barril("ouro", random.uniform(5, 25)))

    slots_restantes = capacidade - 1
    for tipo in ("polvora", "bolas"):
        if slots_restantes <= 0:
            break
        p.barris.append(Barril(tipo, random.uniform(5, 25)))
        slots_restantes -= 1

    while slots_restantes > 0:
        tipo = random.choice(["polvora", "bolas", "tabuas"])
        p.barris.append(Barril(tipo, random.uniform(5, 25)))
        slots_restantes -= 1

    return p


# ---------------------------------------------------------------------------
# Funções de preço (puras) — exportadas para Tier 3b e testes
# ---------------------------------------------------------------------------

def preco_reabastecer(unidades: float) -> float:
    """Custo em ouro para reabastecer `unidades` de qualquer recurso."""
    from ..constants import PRECO_REABASTECER_POR_UNIDADE
    return unidades * PRECO_REABASTECER_POR_UNIDADE


def preco_venda(barril: Barril) -> float:
    """Valor de venda de um barril proporcional ao conteúdo."""
    from ..constants import PRECO_VENDA_BARRIL_CHEIO
    return (barril.quantidade / CAPACIDADE_BARRIL) * PRECO_VENDA_BARRIL_CHEIO


def preco_reparo(navio: Navio) -> float:
    """Custo total de reparo instantâneo do navio (soma de dano de todas as partes)."""
    from ..constants import PRECO_REPARO_POR_PONTO_DANO, PARTES
    dano_total = sum(100.0 - navio.partes[p] for p in PARTES)
    return dano_total * PRECO_REPARO_POR_PONTO_DANO


def coletar_loot(porao_jogador: Porao, loot: Porao) -> Porao:
    """Tenta despejar todo o loot no porão do jogador.

    Returns:
        Porão 'resto' com o que não coube (pode estar vazio).
        Modifica porao_jogador in-place.
    """
    resto = Porao(capacidade=0)
    for barril in loot.barris:
        excedente = porao_jogador.adicionar(barril.tipo, barril.quantidade)
        if excedente > 1e-9:
            resto.barris.append(Barril(barril.tipo, excedente))
    return resto
