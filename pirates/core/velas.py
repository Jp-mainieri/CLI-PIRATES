"""
velas.py – Sistema de slots de vela por navio: soma pura (sem teto) de
eficiência/bônus a partir dos slots abertos de cada instância de Navio
(doc10_customizacao_vela.md).
"""

import copy

from .vento import eficiencia_zona
from ..constants import TIPOS_VELA, LOADOUT_VELA_FABRICA


def gerar_slots_fabrica(tipo_navio: str) -> list[dict]:
    """Retorna uma cópia independente do loadout de fábrica do tipo
    (nunca compartilhar a mesma lista entre navios!)."""
    return copy.deepcopy(LOADOUT_VELA_FABRICA[tipo_navio])


def eficiencia_vento_bruta(slots_vela: list[dict], angulo_relativo: float) -> float:
    """Soma pura (sem teto) da contribuição de cada slot aberto e
    preenchido, exceto slots do tipo 'estai'."""
    total = 0.0
    for slot in slots_vela:
        tipo = slot["tipo"]
        if tipo is None or tipo == "estai":
            continue
        nivel_frac = slot["nivel"] / 2.0
        if nivel_frac <= 0:
            continue
        e_i = eficiencia_zona(TIPOS_VELA[tipo]["eficiencia_vento"], angulo_relativo)
        total += e_i * nivel_frac
    return total


def bonus_fixo_vela_bruto(slots_vela: list[dict]) -> float:
    total = 0.0
    for slot in slots_vela:
        tipo = slot["tipo"]
        if tipo is None or tipo == "estai":
            continue
        nivel_frac = slot["nivel"] / 2.0
        total += TIPOS_VELA[tipo]["bonus_fixo"] * nivel_frac
    return total


def bonus_curva_vela_bruto(slots_vela: list[dict]) -> float:
    """Soma TODOS os slots preenchidos, inclusive estai."""
    total = 0.0
    for slot in slots_vela:
        tipo = slot["tipo"]
        if tipo is None:
            continue
        nivel_frac = slot["nivel"] / 2.0
        total += TIPOS_VELA[tipo]["bonus_curva"] * nivel_frac
    return total


def indice_slot_principal_inicial(slots_vela: list[dict]) -> int:
    """Índice do primeiro slot 'principal' (não proa/popa/aux) — usado
    como seleção padrão ao criar o navio (doc10 §3.3)."""
    for i, slot in enumerate(slots_vela):
        if slot["local"].startswith("principal"):
            return i
    return 0  # fallback, não deveria acontecer


def trocar_tipo_slot(slots_vela: list[dict], indice: int, novo_tipo: str) -> None:
    """Troca o tipo de um slot de proa/mastro/popa (não auxiliar) e o
    deixa no nível 2 (100%) — doc10_customizacao_vela.md §4."""
    slots_vela[indice]["tipo"] = novo_tipo
    slots_vela[indice]["nivel"] = 2


def instalar_ou_trocar_aux(slots_vela: list[dict], indice: int, novo_tipo: str) -> None:
    """Instala (slot vazio) ou troca (slot ocupado) uma vela auxiliar,
    sempre entrando no nível 2 (100%) — doc10_customizacao_vela.md §6."""
    slots_vela[indice]["tipo"] = novo_tipo
    slots_vela[indice]["nivel"] = 2
