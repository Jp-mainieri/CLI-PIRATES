"""lojas.py – Lógica pura das lojas do porto (Tier 3b).

Todas as funções aqui são puras (sem curses, sem IO): recebem/modificam
Navio, Porao, Frota e retornam bool + mensagem de resultado. A camada de
UI em scene.py chama estas funções e exibe o retorno.
"""

from __future__ import annotations

from ..constants import (
    PRECO_BARRIL_NOVO, PRECO_REABASTECER_POR_UNIDADE,
    PRECO_VENDA_BARRIL_CHEIO, PRECO_REPARO_POR_PONTO_DANO,
    PRECO_NAVIO_NOVO, PRECO_RENOMEAR, PRECO_UPGRADE,
    NAVIO_TIPOS, PARTES,
)
from ..core.porao import Barril, Porao, CAPACIDADE_BARRIL


# ---------------------------------------------------------------------------
# Funções de preço (exportadas para UI e testes)
# ---------------------------------------------------------------------------

def preco_reabastecer(unidades: float) -> float:
    """Custo em ouro para reabastecer *unidades* de qualquer recurso."""
    return unidades * PRECO_REABASTECER_POR_UNIDADE


def preco_venda(barril: Barril) -> float:
    """Valor de venda de um barril proporcional ao conteúdo."""
    return (barril.quantidade / CAPACIDADE_BARRIL) * PRECO_VENDA_BARRIL_CHEIO


def preco_reparo(navio) -> float:
    """Custo total de reparo instantâneo do navio (soma de dano de todas as partes)."""
    dano_total = sum(100.0 - navio.partes[p] for p in PARTES)
    return dano_total * PRECO_REPARO_POR_PONTO_DANO


def preco_upgrade_nivel(chave: str, nivel_atual: int) -> float:
    """Preço do próximo nível de upgrade: base * 1.5^nivel_atual."""
    base = PRECO_UPGRADE.get(chave, 0.0)
    return base * (1.5 ** nivel_atual)


# ---------------------------------------------------------------------------
# Teto de upgrades por tipo de navio
# ---------------------------------------------------------------------------

UPGRADE_NIVEIS_MAX: dict[str, dict[str, int]] = {
    "facil":   {"casco_max": 2, "cooldown": 1, "porao_slot": 1,
                "tripulante_extra": 1, "velocidade_giro": 1, "alcance_canhao": 1},
    "normal":  {"casco_max": 3, "cooldown": 2, "porao_slot": 2,
                "tripulante_extra": 1, "velocidade_giro": 2, "alcance_canhao": 2},
    "dificil": {"casco_max": 4, "cooldown": 3, "porao_slot": 3,
                "tripulante_extra": 2, "velocidade_giro": 3, "alcance_canhao": 3},
}


def nivel_max_upgrade(tipo: str, chave: str) -> int:
    return UPGRADE_NIVEIS_MAX.get(tipo, {}).get(chave, 0)


def nivel_atual_upgrade(navio, chave: str) -> int:
    return navio.upgrade_niveis.get(chave, 0)


# ---------------------------------------------------------------------------
# Operações de loja de recurso
# ---------------------------------------------------------------------------

def _ouro_disponivel(navio) -> float:
    return navio.porao.total("ouro")


def _debitar_ouro(navio, valor: float) -> bool:
    """Debita `valor` de ouro do porão. Retorna False se insuficiente (sem alterar)."""
    if _ouro_disponivel(navio) < valor - 1e-9:
        return False
    navio.porao.consumir("ouro", valor)
    return True


def comprar_barril(navio, tipo: str) -> tuple[bool, str]:
    """Compra um barril novo cheio do `tipo`. Debita PRECO_BARRIL_NOVO de ouro."""
    if navio.porao.slots_livres() <= 0:
        return False, "Porcao lotado — sem slots livres."
    preco = PRECO_BARRIL_NOVO
    if not _debitar_ouro(navio, preco):
        return False, f"Ouro insuficiente (precisa {preco:.1f})."
    navio.porao.barris.append(Barril(tipo=tipo, quantidade=CAPACIDADE_BARRIL))
    return True, f"Barril de {tipo} comprado por {preco:.1f} ouro."


def reabastecer_barril(navio, indice: int, tipo: str) -> tuple[bool, str]:
    """Reabastece o barril no `indice` (deve ser do `tipo`) até 25u.

    Cobra preco_reabastecer(unidades_faltando) de ouro.
    """
    p = navio.porao
    if not (0 <= indice < len(p.barris)):
        return False, "Barril nao encontrado."
    b = p.barris[indice]
    if b.tipo != tipo:
        return False, f"Barril e de {b.tipo}, nao de {tipo}."
    falta = CAPACIDADE_BARRIL - b.quantidade
    if falta <= 1e-9:
        return False, "Barril ja esta cheio."
    preco = preco_reabastecer(falta)
    if not _debitar_ouro(navio, preco):
        return False, f"Ouro insuficiente (precisa {preco:.1f})."
    b.quantidade = CAPACIDADE_BARRIL
    return True, f"Barril reabastecido por {preco:.1f} ouro."


def vender_barril(navio, indice: int) -> tuple[bool, str]:
    """Vende o barril no `indice`. Credita ouro proporcional ao conteúdo."""
    p = navio.porao
    if not (0 <= indice < len(p.barris)):
        return False, "Barril nao encontrado."
    b = p.barris[indice]
    valor = preco_venda(b)
    p.barris.pop(indice)
    excedente = navio.porao.adicionar("ouro", valor)
    if excedente > 1e-9:
        return True, f"Barril vendido por {valor:.1f} ouro (excedente {excedente:.1f} perdido — porcao cheio)."
    return True, f"Barril de {b.tipo} vendido por {valor:.1f} ouro."


def reparo_instantaneo(navio) -> tuple[bool, str]:
    """Repara todas as partes para 100% pagando em ouro.

    Falha atomicamente se ouro insuficiente.
    """
    preco = preco_reparo(navio)
    if preco <= 1e-9:
        return False, "Navio ja esta intacto."
    if not _debitar_ouro(navio, preco):
        return False, f"Ouro insuficiente (precisa {preco:.1f})."
    for p in PARTES:
        navio.partes[p] = 100.0
    return True, f"Navio reparado por {preco:.1f} ouro."


# ---------------------------------------------------------------------------
# Operações da loja de navios
# ---------------------------------------------------------------------------

def comprar_navio_loja(frota, tipo: str, nome: str, porto_id: int, navio_ativo) -> tuple[bool, str]:
    """Debita ouro do navio ativo e chama comprar_navio da frota."""
    from ..core.frota import comprar_navio
    if tipo not in NAVIO_TIPOS:
        return False, f"Tipo de navio invalido: {tipo}."
    preco = float(PRECO_NAVIO_NOVO[tipo])
    if not _debitar_ouro(navio_ativo, preco):
        return False, f"Ouro insuficiente (precisa {preco:.0f})."
    ok = comprar_navio(frota, tipo, nome, porto_id, preco)
    if not ok:
        navio_ativo.porao.adicionar("ouro", preco)  # estorna
        return False, "Erro ao criar navio."
    return True, f"{nome} ({NAVIO_TIPOS[tipo]['navio']}) comprado por {preco:.0f} ouro."


def renomear_navio_loja(frota, indice: int, novo_nome: str, navio_ativo) -> tuple[bool, str]:
    """Debita PRECO_RENOMEAR e renomeia o navio no índice."""
    from ..core.frota import renomear_navio
    preco = PRECO_RENOMEAR
    if not _debitar_ouro(navio_ativo, preco):
        return False, f"Ouro insuficiente (precisa {preco:.0f})."
    ok = renomear_navio(frota, indice, novo_nome)
    if not ok:
        navio_ativo.porao.adicionar("ouro", preco)
        return False, "Indice de navio invalido."
    return True, f"Navio renomeado para '{novo_nome}' por {preco:.0f} ouro."


# ---------------------------------------------------------------------------
# Upgrades
# ---------------------------------------------------------------------------

def aplicar_upgrade(navio, tipo_navio: str, chave: str, estado=None) -> tuple[bool, str]:
    """Aplica um nível de upgrade no navio, debitando ouro.

    Modifica navio.upgrade_niveis[chave] e o efeito correspondente.
    """
    nivel = nivel_atual_upgrade(navio, chave)
    max_nivel = nivel_max_upgrade(tipo_navio, chave)
    if nivel >= max_nivel:
        return False, f"Upgrade '{chave}' ja esta no maximo (nivel {nivel})."
    preco = preco_upgrade_nivel(chave, nivel)
    if not _debitar_ouro(navio, preco):
        return False, f"Ouro insuficiente (precisa {preco:.1f})."

    navio.upgrade_niveis[chave] = nivel + 1

    # Aplica o efeito do upgrade
    if chave == "casco_max":
        # +10 HP máx: restaura 10 pontos no casco
        navio.partes['casco'] = min(100.0, navio.partes['casco'] + 10.0)
    elif chave == "cooldown":
        # Armazena fração de redução; combat.py usa upgrades.get('cooldown', 0)
        navio.upgrades['cooldown'] = navio.upgrades.get('cooldown', 0.0) + 0.1
    elif chave == "porao_slot":
        navio.porao.capacidade += 1
    elif chave == "tripulante_extra":
        if estado is not None:
            estado.crew_total += 1
            tid = f"T{estado.crew_total}"
            estado.tripulante_ids.append(tid)
    elif chave == "velocidade_giro":
        navio.upgrades['velocidade_giro'] = navio.upgrades.get('velocidade_giro', 0.0) + 0.1
    elif chave == "alcance_canhao":
        navio.upgrades['alcance_canhao'] = navio.upgrades.get('alcance_canhao', 0.0) + 50.0

    return True, f"Upgrade '{chave}' nivel {nivel + 1} aplicado por {preco:.1f} ouro."
