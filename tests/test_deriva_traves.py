"""Testes para empuxo lateral de vento de través (doc09_deriva.md seção 5)."""

import pytest

from pirates.core.ship import Navio
from pirates.core.vento import empuxo_lateral_vento
from pirates.constants import NAVIO_TIPOS


class TestEmpuxoLateralVento:
    def test_zero_em_zona_morta(self):
        assert empuxo_lateral_vento(3, 10.0, 0.0) == pytest.approx(0.0)

    def test_zero_em_popa(self):
        assert empuxo_lateral_vento(3, 10.0, 180.0) == pytest.approx(0.0)

    def test_maximo_em_traves(self):
        e0 = abs(empuxo_lateral_vento(3, 10.0, 45.0))
        e90 = abs(empuxo_lateral_vento(3, 10.0, 90.0))
        e135 = abs(empuxo_lateral_vento(3, 10.0, 135.0))
        assert e90 > e0
        assert e90 > e135

    def test_cresce_linear_com_intensidade(self):
        e10 = empuxo_lateral_vento(1, 10.0, 90.0)
        e20 = empuxo_lateral_vento(1, 20.0, 90.0)
        assert e20 == pytest.approx(e10 * 2)

    def test_cresce_linear_com_num_velas(self):
        e1 = empuxo_lateral_vento(1, 10.0, 90.0)
        e2 = empuxo_lateral_vento(2, 10.0, 90.0)
        assert e2 == pytest.approx(e1 * 2)


class TestIntegracaoEmpuxoLateral:
    def test_navio_parado_ganha_deriva_sob_vento_de_traves(self):
        n = Navio("Teste", 0, 0, heading=0.0, velocidade_max_base=0.0)
        n.heading_alvo = n.heading  # não vira o leme
        n.velocidade_lateral = 0.0
        for _ in range(5):
            n.atualizar_movimento(
                dt=0.1,
                angulo_relativo_vento_atual=90.0,
                intensidade_vento_atual=10.0,
            )
        assert n.velocidade_lateral > 0.0

    def test_deriva_converge_sob_vento_constante(self):
        n = Navio("Teste", 0, 0, heading=0.0, velocidade_max_base=0.0)
        n.heading_alvo = n.heading
        for _ in range(200):
            n.atualizar_movimento(
                dt=0.1,
                angulo_relativo_vento_atual=90.0,
                intensidade_vento_atual=10.0,
            )
        v_penultimo = n.velocidade_lateral
        n.atualizar_movimento(
            dt=0.1, angulo_relativo_vento_atual=90.0, intensidade_vento_atual=10.0,
        )
        assert n.velocidade_lateral == pytest.approx(v_penultimo, rel=1e-2)


class TestComparativoTipos:
    def test_galeao_converge_para_deriva_maior_que_chalupa(self):
        params_chalupa = NAVIO_TIPOS["chalupa"]
        params_galeao = NAVIO_TIPOS["galeao"]

        chalupa = Navio(
            "Chalupa", 0, 0, heading=0.0, velocidade_max_base=0.0,
            peso_casco=params_chalupa["peso_casco"],
        )
        chalupa.num_velas = params_chalupa["num_velas"]

        galeao = Navio(
            "Galeao", 0, 0, heading=0.0, velocidade_max_base=0.0,
            peso_casco=params_galeao["peso_casco"],
        )
        galeao.num_velas = params_galeao["num_velas"]

        for n in (chalupa, galeao):
            n.heading_alvo = n.heading

        for _ in range(300):
            chalupa.atualizar_movimento(
                dt=0.1, angulo_relativo_vento_atual=90.0, intensidade_vento_atual=10.0,
            )
            galeao.atualizar_movimento(
                dt=0.1, angulo_relativo_vento_atual=90.0, intensidade_vento_atual=10.0,
            )

        assert galeao.velocidade_lateral > chalupa.velocidade_lateral
