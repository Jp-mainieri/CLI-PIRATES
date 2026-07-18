"""porao.py – Sistema de carga física (pólvora, bolas, tábuas, ouro)."""

from __future__ import annotations

import random
from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .ship import Navio

TIPOS_CARGA = ("polvora", "bolas", "tabuas", "ouro")
CAPACIDADE_BARRIL = 25.0
CAPACIDADE_BARRIL_OURO = 50.0  # barril de ouro é maior


def capacidade_barril(tipo: str) -> float:
    """Retorna a capacidade máxima de um barril conforme o tipo de carga."""
    return CAPACIDADE_BARRIL_OURO if tipo == "ouro" else CAPACIDADE_BARRIL


@dataclass
class Barril:
    """Um barril de carga física.

    Attributes:
        tipo:       Um de TIPOS_CARGA.
        quantidade: 0 a capacidade (25 para recursos, 50 para ouro).
    """
    tipo: str
    quantidade: float

    @property
    def capacidade(self) -> float:
        return CAPACIDADE_BARRIL_OURO if self.tipo == "ouro" else CAPACIDADE_BARRIL

    @property
    def cheio(self) -> bool:
        return self.quantidade >= self.capacidade

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
        cap = capacidade_barril(tipo)
        restante = quantidade
        existentes = sorted(
            (b for b in self.barris if b.tipo == tipo and not b.cheio),
            key=lambda b: b.quantidade,
        )
        for b in existentes:
            espaco = b.capacidade - b.quantidade
            usado = min(espaco, restante)
            b.quantidade += usado
            restante -= usado
            if restante <= 1e-9:
                return 0.0
        while restante > 1e-9 and self.slots_livres() > 0:
            usado = min(cap, restante)
            self.barris.append(Barril(tipo=tipo, quantidade=usado))
            restante -= usado
        return max(0.0, restante)

    def remover_barril(self, indice: int) -> 'Barril | None':
        """Remove e retorna o barril num índice (usado por vender/descartar)."""
        if 0 <= indice < len(self.barris):
            return self.barris.pop(indice)
        return None


def estoque_inicial_jogador(capacidade: int) -> Porao:
    """Porão inicial do jogador: 1 barril de cada recurso por nível de navio, sem ouro.

    Deixa slots vazios para o jogador comprar no porto.
    Chalupa (6): 1/1/1 → 3 slots usados, 3 vazios.
    Bergantim (9): 2/2/2 → 6 usados, 3 vazios.
    Galeão (14): 3/3/3 → 9 usados, 5 vazios.
    """
    p = Porao(capacidade)
    n_por_tipo = max(1, round(capacidade / 5))
    for tipo in ("polvora", "bolas", "tabuas"):
        for _ in range(n_por_tipo):
            p.barris.append(Barril(tipo=tipo, quantidade=CAPACIDADE_BARRIL))
    return p


def _sortear_quantidade_carga(tipo: str, faixa: tuple[float, float]) -> float:
    """Sorteia a quantidade de um barril dentro de `faixa` (fração de 25u).

    Ouro/pólvora/bolas nascem como valores inteiros (mais legível na UI e no
    loot); tábuas continuam fracionárias, já que o reparo as consome em
    frações (FATOR_TABUAS_POR_HP)."""
    minimo, maximo = faixa[0] * 25, faixa[1] * 25
    if tipo == "tabuas":
        return random.uniform(minimo, maximo)
    return float(random.randint(round(minimo), round(maximo)))


def gerar_porao_inimigo(capacidade: int, elite: bool = False) -> Porao:
    """Porão aleatório de um inimigo recém-spawnado: 1 barril de ouro
    garantido, mínimo 1 pólvora + 1 bolas garantidos, resto aleatório.

    Navios elite têm 30% mais capacidade e um conteúdo médio bem mais
    cheio (nenhum slot fica vazio)."""
    if elite:
        capacidade = round(capacidade * 1.3)
    p = Porao(capacidade)
    p.barris.append(Barril("ouro", float(random.randint(5, int(CAPACIDADE_BARRIL_OURO)))))

    faixa = (0.8, 1.0) if elite else (0.2, 1.0)
    slots_restantes = capacidade - 1
    for tipo in ("polvora", "bolas", "tabuas"):
        if slots_restantes <= 0:
            break
        p.barris.append(Barril(tipo, _sortear_quantidade_carga(tipo, faixa)))
        slots_restantes -= 1

    while slots_restantes > 0:
        slots_restantes -= 1
        if not elite and random.random() < 0.3:  # 30% de chance de slot vazio
            continue
        tipo = random.choice(["polvora", "bolas", "tabuas"])
        p.barris.append(Barril(tipo, _sortear_quantidade_carga(tipo, faixa)))

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
