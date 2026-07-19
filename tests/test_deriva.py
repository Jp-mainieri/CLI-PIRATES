"""Testes para deriva lateral em pirates/core/ship.py (doc09_deriva.md)."""

import pytest

from pirates.core.ship import Navio
from pirates.constants import NAVIO_TIPOS


class TestForcaCorrecaoDeriva:
    def test_chalupa(self):
        n = Navio("Teste", 0, 0, 0, velocidade_max_base=8.0, peso_casco=200.0)
        n.velocidade = 8.0
        assert n._forca_correcao_deriva() == pytest.approx(13.5)

    def test_brigantim(self):
        n = Navio("Teste", 0, 0, 0, velocidade_max_base=11.0, peso_casco=500.0)
        n.velocidade = 11.0
        assert n._forca_correcao_deriva() == pytest.approx(6.3)

    def test_galeao(self):
        n = Navio("Teste", 0, 0, 0, velocidade_max_base=14.0, peso_casco=1100.0)
        n.velocidade = 14.0
        assert n._forca_correcao_deriva() == pytest.approx(3.2727, rel=1e-3)


class TestGeracaoDeriva:
    def test_deriva_gerada_ao_virar_leme(self):
        n = Navio("Teste", 0, 0, heading=0, velocidade_max_base=10.0)
        n.velocidade = 5.0
        n.heading_alvo = 90.0
        n.atualizar_movimento(dt=0.1)
        assert n.velocidade_lateral != 0.0

    def test_deriva_zero_em_linha_reta(self):
        n = Navio("Teste", 0, 0, heading=0, velocidade_max_base=10.0)
        n.velocidade = 5.0
        n.heading_alvo = 0.0
        n.atualizar_movimento(dt=0.1)
        assert n.velocidade_lateral == pytest.approx(0.0)


class TestDecaimentoDeriva:
    def test_decai_em_direcao_a_zero(self):
        n = Navio("Teste", 0, 0, heading=0, velocidade_max_base=10.0)
        n.velocidade = 5.0
        n.heading_alvo = 90.0
        n.atualizar_movimento(dt=0.1)
        primeiro = abs(n.velocidade_lateral)
        n.heading_alvo = n.heading  # para de virar, só decai
        for _ in range(20):
            n.atualizar_movimento(dt=0.1)
        assert abs(n.velocidade_lateral) < primeiro

    def test_sem_overshoot_com_dt_grande(self):
        n = Navio("Teste", 0, 0, heading=0, velocidade_max_base=10.0)
        n.velocidade_lateral = 5.0
        n.heading_alvo = n.heading
        n.atualizar_movimento(dt=1000.0)
        assert n.velocidade_lateral == pytest.approx(0.0)
        assert n.velocidade_lateral >= 0.0

    def test_sem_overshoot_dt_grande_sinal_negativo(self):
        n = Navio("Teste", 0, 0, heading=0, velocidade_max_base=10.0)
        n.velocidade_lateral = -5.0
        n.heading_alvo = n.heading
        n.atualizar_movimento(dt=1000.0)
        assert n.velocidade_lateral == pytest.approx(0.0)
        assert n.velocidade_lateral <= 0.0


class TestComparativoTipos:
    def test_chalupa_decai_mais_rapido_que_galeao(self):
        params_chalupa = NAVIO_TIPOS["chalupa"]
        params_galeao = NAVIO_TIPOS["galeao"]

        chalupa = Navio(
            "Chalupa", 0, 0, heading=0,
            velocidade_max_base=params_chalupa["velocidade_max_base"],
            peso_casco=params_chalupa["peso_casco"],
        )
        galeao = Navio(
            "Galeao", 0, 0, heading=0,
            velocidade_max_base=params_galeao["velocidade_max_base"],
            peso_casco=params_galeao["peso_casco"],
        )
        chalupa.velocidade = 5.0
        galeao.velocidade = 5.0
        chalupa.heading_alvo = 90.0
        galeao.heading_alvo = 90.0

        chalupa.atualizar_movimento(dt=0.1)
        galeao.atualizar_movimento(dt=0.1)
        chalupa.heading_alvo = chalupa.heading
        galeao.heading_alvo = galeao.heading

        chalupa.atualizar_movimento(dt=0.5)
        galeao.atualizar_movimento(dt=0.5)

        assert abs(chalupa.velocidade_lateral) < abs(galeao.velocidade_lateral)
