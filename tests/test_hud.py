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


class TestCanhaoEmTransito:
    """O painel de canhões não pode anunciar PRONTO com a equipe a caminho."""

    def _estado_com_transito(self):
        from pirates.core.state import Estado
        from pirates.input.commands import processar_comando
        e = Estado(tipo_navio="brigantim")
        e.crew_total = 1
        e.tripulacao.redimensionar(["T1"])
        e.jogador.heading = 0.0
        e.inimigo.x, e.inimigo.y = 200.0, 0.0
        processar_comando("canhao e1 200", e)
        processar_comando("canhao b1 200", e)
        return e

    def test_mostra_tempo_de_chegada(self):
        from pirates.ui.hud import build_canhoes_linhas
        e = self._estado_com_transito()
        linhas = [texto for texto, _ in build_canhoes_linhas(e)]
        b1 = next(t for t in linhas if t.strip().startswith("B1"))
        assert "trip a caminho" in b1
        assert "PRONTO" not in b1

    def test_canhao_abandonado_fica_sem_mira(self):
        from pirates.ui.hud import build_canhoes_linhas
        e = self._estado_com_transito()
        linhas = [texto for texto, _ in build_canhoes_linhas(e)]
        e1 = next(t for t in linhas if t.strip().startswith("E1"))
        assert "sem mira" in e1

    def test_uma_linha_por_canhao(self):
        from pirates.ui.hud import build_canhoes_linhas
        e = self._estado_com_transito()
        assert len(build_canhoes_linhas(e)) == 2 * e.canhoes_lado
