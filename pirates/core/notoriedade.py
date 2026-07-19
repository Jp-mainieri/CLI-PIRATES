"""notoriedade.py – Sistema de notoriedade do capitão (Tier 3c).

Funções puras, sem IO, seguindo o padrão de porao.py/lojas.py: faixas de
notoriedade (título + ícone), distribuição do tipo de navio sorteado no
mundo aberto e chance de navio elite, ambos por faixa.
"""

from __future__ import annotations

import math
import random

NOTORIEDADE_FAIXAS: list[dict] = [
    {"nome": "Desconhecido",           "minimo": 0,     "ascii": ".", "unicode": "·"},
    {"nome": "Rosto Novo no Porto",    "minimo": 100,   "ascii": "o", "unicode": "○"},
    {"nome": "Nome nas Tavernas",      "minimo": 300,   "ascii": "*", "unicode": "★"},
    {"nome": "Temido nas Rotas",       "minimo": 700,   "ascii": "#", "unicode": "▲"},
    {"nome": "Marcado por Recompensa", "minimo": 1500,  "ascii": "A", "unicode": "☠"},
    {"nome": "Cacado pela Coroa",      "minimo": 3000,  "ascii": "X", "unicode": "✕"},
    {"nome": "Terror dos Sete Mares",  "minimo": 6000,  "ascii": "%", "unicode": "⚔"},
    {"nome": "Lenda Viva",             "minimo": 12000, "ascii": "W", "unicode": "♛"},
]

PONTOS_POR_TIPO = {"chalupa": 10, "brigantim": 25, "galeao": 50}  # chaves = NAVIO_TIPOS

# faixa minima de notoriedade (0-7) exigida pra criar um mundo aberto NOVO
# com esse tipo de navio (nao afeta compra no porto, so criacao de mundo)
DESBLOQUEIO_MUNDO_FAIXA = {"brigantim": 2, "galeao": 4}

# vitorias minimas numa unica campanha de Arena exigidas pra iniciar uma
# campanha NOVA com esse tipo de navio (nao afeta compra no porto)
DESBLOQUEIO_ARENA_VITORIAS = {"brigantim": 10, "galeao": 30}

# (min, max) do sorteio de ouro base por tipo de navio, antes do
# multiplicador MULT_OURO_POR_FAIXA.
GOLD_BASE_POR_TIPO = {"chalupa": (5, 20), "brigantim": (12, 35), "galeao": (20, 50)}

MULT_ELITE_PONTOS = 2.5
BONUS_ELITE_PONTOS = 30.0

# índice da faixa (0-7) -> chance de elite
CHANCE_ELITE_POR_FAIXA = [0.0, 0.0, 0.06, 0.12, 0.18, 0.24, 0.30, 0.35]

# índice da faixa (0-7) -> multiplicador aplicado ao ouro sorteado no loot
MULT_OURO_POR_FAIXA = [0.35, 0.55, 0.75, 1.0, 1.3, 1.6, 2.0, 2.5]

# índice da faixa (0-7) -> pesos de sorteio (facil, normal, dificil), somam 1.0
DISTRIBUICAO_TIPO_POR_FAIXA = [
    (0.70, 0.25, 0.05),
    (0.60, 0.30, 0.10),
    (0.50, 0.35, 0.15),
    (0.40, 0.40, 0.20),
    (0.30, 0.40, 0.30),
    (0.20, 0.40, 0.40),
    (0.10, 0.35, 0.55),
    (0.05, 0.25, 0.70),
]

# Faixa (índice) do bônus de status do elite -> (min, max) fração de bônus.
# Só faixas 2 em diante têm elite (0% nas faixas 0-1, ver CHANCE_ELITE_POR_FAIXA).
ELITE_BONUS_STATUS_POR_FAIXA = {
    2: (0.10, 0.20), 3: (0.10, 0.20),
    4: (0.20, 0.30), 5: (0.20, 0.30),
    6: (0.25, 0.35),
    7: (0.30, 0.45),
}
# Aplicado a: +HP casco, +tripulacao (arredondar pra cima), -cooldown canhao
# (cooldown usa o MESMO fator, mas subtraindo em vez de somando).

FAIXA8_ELITE_TAXA_CRESCIMENTO = 0.02  # fração por hora de jogo na faixa 8
FAIXA8_ELITE_TETO = 0.65              # teto assintótico, nunca passa disso

FRACAO_PERDA_FUGA_JOGADOR = 0.5
"""Fração dos pontos que o jogador teria ganho afundando o inimigo, perdida
ao invés disso quando o jogador foge do combate."""


def faixa_index(pontos: float) -> int:
    """Retorna 0-7: a maior faixa cujo mínimo <= pontos."""
    idx = 0
    for i, faixa in enumerate(NOTORIEDADE_FAIXAS):
        if pontos >= faixa["minimo"]:
            idx = i
        else:
            break
    return idx


def titulo(pontos: float) -> str:
    return NOTORIEDADE_FAIXAS[faixa_index(pontos)]["nome"]


def icone(pontos: float, unicode: bool) -> str:
    faixa = NOTORIEDADE_FAIXAS[faixa_index(pontos)]
    return faixa["unicode"] if unicode else faixa["ascii"]


def chance_elite(pontos: float, horas_na_faixa8: float = 0.0) -> float:
    idx = faixa_index(pontos)
    base = CHANCE_ELITE_POR_FAIXA[idx]
    if idx != 7:
        return base
    crescimento = (FAIXA8_ELITE_TETO - base) * (
        1 - math.exp(-FAIXA8_ELITE_TAXA_CRESCIMENTO * horas_na_faixa8)
    )
    return min(FAIXA8_ELITE_TETO, base + crescimento)


def sortear_tipo_navio(pontos: float) -> str:
    chaves = ("chalupa", "brigantim", "galeao")
    pesos = DISTRIBUICAO_TIPO_POR_FAIXA[faixa_index(pontos)]
    return random.choices(chaves, weights=pesos, k=1)[0]


def bloqueios_mundo(melhor_faixa: int) -> dict[str, str | None]:
    """Tipo->motivo de bloqueio (None se liberado) pra criar um mundo aberto
    NOVO, dado a maior faixa de notoriedade ja alcancada em qualquer capitao."""
    bloqueios: dict[str, str | None] = {}
    for tipo in ("chalupa", "brigantim", "galeao"):
        exigido = DESBLOQUEIO_MUNDO_FAIXA.get(tipo)
        if exigido is None or melhor_faixa >= exigido:
            bloqueios[tipo] = None
        else:
            bloqueios[tipo] = f"requer faixa {exigido} de notoriedade (atual: {melhor_faixa})"
    return bloqueios


def bloqueios_arena(melhor_vitorias: int) -> dict[str, str | None]:
    """Tipo->motivo de bloqueio (None se liberado) pra iniciar uma campanha
    de Arena NOVA, dado o maior numero de vitorias numa campanha passada."""
    bloqueios: dict[str, str | None] = {}
    for tipo in ("chalupa", "brigantim", "galeao"):
        exigido = DESBLOQUEIO_ARENA_VITORIAS.get(tipo)
        if exigido is None or melhor_vitorias >= exigido:
            bloqueios[tipo] = None
        else:
            bloqueios[tipo] = f"requer {exigido} vitorias em uma campanha de Arena (atual: {melhor_vitorias})"
    return bloqueios


def sortear_bonus_elite(pontos: float) -> dict[str, float]:
    idx = faixa_index(pontos)
    faixa_min, faixa_max = ELITE_BONUS_STATUS_POR_FAIXA.get(idx, (0.0, 0.0))
    fator = random.uniform(faixa_min, faixa_max)
    return {"casco": fator, "tripulacao": fator, "cooldown": fator}


def pontos_por_afundamento(tipo: str, elite: bool) -> float:
    valor = PONTOS_POR_TIPO[tipo]
    if elite:
        return valor * MULT_ELITE_PONTOS + BONUS_ELITE_PONTOS
    return float(valor)


def pontos_perdidos_por_fuga(tipo: str, elite: bool) -> float:
    """Notoriedade perdida quando o jogador foge de um combate contra este
    inimigo, em vez de afundá-lo: uma fração dos pontos que teria ganho."""
    return pontos_por_afundamento(tipo, elite) * FRACAO_PERDA_FUGA_JOGADOR
