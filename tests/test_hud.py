"""Testes de regressão para o refactor de calcular_entrada_agua (Mudança 3 do Modo ADM)."""

import math
import pytest
from pirates.core.ship import calcular_entrada_agua
from pirates.constants import PARTES, AGUA_BASE, AGUA_K, PARTES_CRITICAS


def _entrada_original(partes: dict) -> float:
    """Replicação exata do loop inline que existia em Navio.atualizar_agua antes do refactor."""
    entrada = 0.0
    for p in PARTES_CRITICAS:
        dano_frac = (100 - partes[p]) / 100
        entrada += AGUA_BASE * (math.exp(AGUA_K * dano_frac) - 1)
    return entrada


class TestCalcularEntradaAgua:
    def test_sem_dano_equivale_ao_original(self):
        partes = {p: 100.0 for p in PARTES}
        assert calcular_entrada_agua(partes) == pytest.approx(_entrada_original(partes))

    def test_casco_destruido_equivale_ao_original(self):
        partes = {p: 100.0 for p in PARTES}
        partes['casco'] = 0.0
        assert calcular_entrada_agua(partes) == pytest.approx(_entrada_original(partes))

    def test_casco_medio_equivale_ao_original(self):
        partes = {p: 100.0 for p in PARTES}
        partes['casco'] = 50.0
        assert calcular_entrada_agua(partes) == pytest.approx(_entrada_original(partes))

    def test_sem_dano_entrada_zero(self):
        partes = {p: 100.0 for p in PARTES}
        assert calcular_entrada_agua(partes) == pytest.approx(0.0)

    def test_com_dano_entrada_positiva(self):
        partes = {p: 100.0 for p in PARTES}
        partes['casco'] = 50.0
        assert calcular_entrada_agua(partes) > 0.0

    def test_entrada_cresce_com_dano(self):
        partes_leve = {p: 100.0 for p in PARTES}
        partes_leve['casco'] = 80.0
        partes_grave = {p: 100.0 for p in PARTES}
        partes_grave['casco'] = 20.0
        assert calcular_entrada_agua(partes_grave) > calcular_entrada_agua(partes_leve)

    def test_outras_partes_nao_afetam_entrada(self):
        base = {p: 100.0 for p in PARTES}
        base['casco'] = 60.0
        variante = dict(base)
        variante['mastro'] = 0.0
        variante['vela'] = 0.0
        assert calcular_entrada_agua(base) == pytest.approx(calcular_entrada_agua(variante))
