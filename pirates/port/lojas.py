"""lojas.py – Lógica pura das lojas do porto (Tier 3b).

Todas as funções aqui são puras (sem curses, sem IO): recebem/modificam
Navio, Porao, Frota e retornam bool + mensagem de resultado. A camada de
UI em scene.py chama estas funções e exibe o retorno.
"""

from __future__ import annotations

from ..constants import (
    PRECO_BARRIL_NOVO, PRECO_NAVIO_NOVO, PRECO_RENOMEAR, PRECO_UPGRADE,
    PRECO_TRANSFERENCIA_FROTA,
    NAVIO_TIPOS, PARTES, PRECO_ITENS_TOPO, FAIXA_MINIMA_ITEM_TOPO,
    TAXA_CRESCIMENTO_UPGRADE,
    PRECO_TROCA_VELA, PRECO_INSTALAR_AUX, TIPOS_VELA,
)
from ..core.porao import (
    Barril, Porao, CAPACIDADE_BARRIL, capacidade_barril_ouro_efetiva,
    preco_reabastecer, preco_venda, preco_reparo,  # re-exportadas do core
)
from ..core.velas import trocar_tipo_slot, instalar_ou_trocar_aux


def preco_upgrade_nivel(chave: str, nivel_atual: int) -> float:
    """Preço do próximo nível de upgrade: base * taxa^nivel_atual.

    A maioria dos upgrades usa taxa 1.5; algumas chaves (ver
    TAXA_CRESCIMENTO_UPGRADE) têm taxa própria, mais suave, porque têm
    muito mais níveis disponíveis."""
    base = PRECO_UPGRADE.get(chave, 0.0)
    taxa = TAXA_CRESCIMENTO_UPGRADE.get(chave, 1.5)
    return base * (taxa ** nivel_atual)


# ---------------------------------------------------------------------------
# Teto de upgrades por tipo de navio
# ---------------------------------------------------------------------------

UPGRADE_NIVEIS_MAX: dict[str, dict[str, int]] = {
    "chalupa":   {"casco_max": 2, "cooldown": 1, "porao_slot": 1,
                "tripulante_extra": 1, "velocidade_giro": 1, "alcance_canhao": 1,
                "capacidade_barril_ouro": 4},
    "brigantim": {"casco_max": 3, "cooldown": 2, "porao_slot": 2,
                "tripulante_extra": 1, "velocidade_giro": 2, "alcance_canhao": 2,
                "capacidade_barril_ouro": 8},
    "galeao":    {"casco_max": 4, "cooldown": 3, "porao_slot": 3,
                "tripulante_extra": 2, "velocidade_giro": 3, "alcance_canhao": 3,
                "capacidade_barril_ouro": 16},
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
    excedente = navio.porao.adicionar("ouro", valor, capacidade=capacidade_barril_ouro_efetiva(navio))
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
    """Debita ouro do navio ativo e chama comprar_navio da frota.

    Preço escala por quantos navios DESSE TIPO o jogador já possui:
    preco_base[tipo] * 1.4 ** (navios_do_tipo_ja_possuidos).
    """
    from ..core.frota import comprar_navio
    if tipo not in NAVIO_TIPOS:
        return False, f"Tipo de navio invalido: {tipo}."
    navios_do_tipo = sum(1 for n in frota.navios if n.tipo == tipo)
    preco = float(PRECO_NAVIO_NOVO[tipo]) * (1.4 ** navios_do_tipo)
    if not _debitar_ouro(navio_ativo, preco):
        return False, f"Ouro insuficiente (precisa {preco:.0f})."
    ok = comprar_navio(frota, tipo, nome, porto_id, preco)
    if not ok:
        navio_ativo.porao.adicionar("ouro", preco, capacidade=capacidade_barril_ouro_efetiva(navio_ativo))  # estorna
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
        navio_ativo.porao.adicionar("ouro", preco, capacidade=capacidade_barril_ouro_efetiva(navio_ativo))
        return False, "Indice de navio invalido."
    return True, f"Navio renomeado para '{novo_nome}' por {preco:.0f} ouro."


def transferir_barril_frota(origem, destino, indice_barril: int) -> tuple[bool, str]:
    """Transfere um barril inteiro do porão de `origem` pro de `destino`.

    Cobra PRECO_TRANSFERENCIA_FROTA de ouro:
      - Barril de ouro: a taxa sai do próprio barril sendo movido.
      - Qualquer outro recurso: tenta debitar de `origem`, senão de
        `destino`.
    Falha atomicamente (sem alterar nada) se: índice inválido, destino sem
    slot livre, ou nenhum dos dois lados cobre a taxa.
    """
    p_origem = origem.porao
    if not (0 <= indice_barril < len(p_origem.barris)):
        return False, "Barril nao encontrado."
    barril = p_origem.barris[indice_barril]

    if destino.porao.slots_livres() <= 0:
        return False, "Porao de destino lotado — sem slots livres."

    preco = PRECO_TRANSFERENCIA_FROTA
    pago_do_proprio_barril = False
    if barril.tipo == "ouro":
        if barril.quantidade < preco - 1e-9:
            return False, f"Barril de ouro nao cobre a taxa (precisa {preco:.0f} ouro)."
        pago_do_proprio_barril = True
    else:
        if not _debitar_ouro(origem, preco) and not _debitar_ouro(destino, preco):
            return False, f"Nenhum dos navios tem ouro para a taxa ({preco:.0f})."

    p_origem.barris.pop(indice_barril)
    if pago_do_proprio_barril:
        barril.quantidade -= preco
    if barril.vazio:
        return True, f"Barril de ouro esvaziado pela taxa de transferencia ({preco:.0f} ouro)."

    destino.porao.barris.append(barril)
    return True, f"Barril de {barril.tipo} transferido por {preco:.0f} ouro."


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
    elif chave == "capacidade_barril_ouro":
        navio.upgrades['capacidade_barril_ouro'] = (
            navio.upgrades.get('capacidade_barril_ouro', 0.0) + 10.0
        )
        # Retroativo: barris de ouro ja existentes ganham a capacidade nova na hora
        # (mesmo padrao que casco_max ja usa, restaurando HP na hora da compra).
        nova_capacidade = capacidade_barril_ouro_efetiva(navio)
        for b in navio.porao.barris:
            if b.tipo == "ouro":
                b.capacidade = nova_capacidade

    return True, f"Upgrade '{chave}' nivel {nivel + 1} aplicado por {preco:.1f} ouro."


# ---------------------------------------------------------------------------
# Itens de topo (desbloqueados por faixa de notoriedade)
# ---------------------------------------------------------------------------

def comprar_item_topo(navio, chave: str, faixa_notoriedade: int) -> tuple[bool, str]:
    """Compra um item de topo (permanente, ligado ao navio, nao empilha nivel).

    Args:
        navio:              Navio que recebe o item.
        chave:              Chave em PRECO_ITENS_TOPO.
        faixa_notoriedade:  Indice 0-7 de notoriedade.NOTORIEDADE_FAIXAS.
    """
    if chave not in PRECO_ITENS_TOPO:
        return False, f"Item de topo '{chave}' nao existe."
    if navio.itens_topo.get(chave, False):
        return False, "Item ja comprado neste navio."
    if faixa_notoriedade < FAIXA_MINIMA_ITEM_TOPO[chave]:
        return False, "Notoriedade insuficiente para este item."

    preco = PRECO_ITENS_TOPO[chave]
    if not _debitar_ouro(navio, preco):
        return False, f"Ouro insuficiente (precisa {preco:.1f})."

    navio.itens_topo[chave] = True
    if chave == "casco_lendario":
        navio.upgrades['resistencia_casco'] = navio.upgrades.get('resistencia_casco', 0.0) + 0.5
    elif chave == "alcance_lendario":
        navio.upgrades['alcance_canhao'] = navio.upgrades.get('alcance_canhao', 0.0) + 120.0
    elif chave == "porao_lendario":
        navio.porao.capacidade += 3

    return True, f"Item de topo '{chave}' comprado por {preco:.1f} ouro."


# ---------------------------------------------------------------------------
# Loja de velas (doc10_customizacao_vela.md)
# ---------------------------------------------------------------------------

def trocar_vela(navio, tipo_navio: str, indice_slot: int, novo_tipo: str) -> tuple[bool, str]:
    """Troca o tipo de um slot de proa/mastro/popa já existente
    (doc10_customizacao_vela.md §4). Não vale pra slots auxiliares."""
    if not (0 <= indice_slot < len(navio.slots_vela)):
        return False, "Slot invalido."
    slot = navio.slots_vela[indice_slot]
    if slot["local"].startswith("aux"):
        return False, "Use a opcao de velas auxiliares para esse slot."
    if novo_tipo not in TIPOS_VELA or TIPOS_VELA[novo_tipo]["auxiliar"]:
        return False, "Tipo de vela invalido para esse slot."

    preco = PRECO_TROCA_VELA[tipo_navio]
    if not _debitar_ouro(navio, preco):
        return False, "Ouro insuficiente."
    trocar_tipo_slot(navio.slots_vela, indice_slot, novo_tipo)
    return True, f"Vela trocada para {novo_tipo} ({preco:.0f} ouro)."


def instalar_vela_auxiliar(navio, indice_slot: int, novo_tipo: str) -> tuple[bool, str]:
    """Instala (slot vazio) ou troca (slot ocupado) uma vela auxiliar
    (doc10_customizacao_vela.md §6). Nunca cria slot novo."""
    if not (0 <= indice_slot < len(navio.slots_vela)):
        return False, "Slot invalido."
    slot = navio.slots_vela[indice_slot]
    if not slot["local"].startswith("aux"):
        return False, "Esse slot nao e auxiliar."
    if novo_tipo not in TIPOS_VELA or not TIPOS_VELA[novo_tipo]["auxiliar"]:
        return False, "Tipo de vela auxiliar invalido."

    preco = PRECO_INSTALAR_AUX[novo_tipo]
    if not _debitar_ouro(navio, preco):
        return False, "Ouro insuficiente."
    instalar_ou_trocar_aux(navio.slots_vela, indice_slot, novo_tipo)
    return True, f"{novo_tipo} instalada ({preco:.0f} ouro)."
