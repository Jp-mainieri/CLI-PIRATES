"""Testes para Navio.atualizar_movimento / velocidade_maxima e
pirates/core/movimento.py (equilíbrio físico, deriva, âncora)."""

import math

import pytest

from pirates.core.ship import Navio
from pirates.core.velas import gerar_slots_fabrica
from pirates.core.movimento import calcular_tick_fisica
from pirates.constants import PESO_CASCO, AREA_CASCO, K_ARRASTO_CASCO


def _navio(tipo="brigantim", **kwargs):
    params = dict(
        velocidade_max_base={"chalupa": 8.0, "brigantim": 11.0, "galeao": 14.0}[tipo],
        giro_graus_seg={"chalupa": 45.0, "brigantim": 25.0, "galeao": 12.0}[tipo],
        peso_casco=PESO_CASCO[tipo],
        area_casco=AREA_CASCO[tipo],
        slots_vela=gerar_slots_fabrica(tipo),
    )
    params.update(kwargs)
    return Navio("Teste", x=0, y=0, heading=0, **params)


class TestVelocidadeMaxima:
    def test_bate_com_formula_equilibrio(self):
        n = _navio("brigantim")
        n.eficiencia_vento_atual = 0.8
        n.fator_intensidade_vento_atual = 1.1
        from pirates.core.velas import bonus_fixo_vela_bruto
        empuxo = (
            n.velocidade_max_base
            * (1.0 + bonus_fixo_vela_bruto(n.slots_vela))
            * n.eficiencia_vento_atual
            * n.fator_intensidade_vento_atual
        )
        esperado = math.sqrt(empuxo / (K_ARRASTO_CASCO * n.area_casco))
        assert n.velocidade_maxima() == pytest.approx(esperado)

    def test_zero_sem_slots(self):
        n = _navio("brigantim", slots_vela=[])
        # eficiencia_vento_atual só reflete os slots depois de um tick de
        # atualizar_movimento (fica no default 1.0 antes disso).
        n.atualizar_movimento(dt=0.1, angulo_relativo_vento_atual=90.0, intensidade_vento_atual=10.0)
        assert n.velocidade_maxima() == 0.0

    def test_ancorado_zera(self):
        n = _navio("brigantim")
        n.eficiencia_vento_atual = 1.0
        n.fator_intensidade_vento_atual = 1.0
        n.ancorado = True
        assert n.velocidade_maxima() == 0.0

    def test_reduzida_por_dano_vela_e_mastro(self):
        n = _navio("brigantim")
        n.eficiencia_vento_atual = 1.0
        n.fator_intensidade_vento_atual = 1.0
        cheio = n.velocidade_maxima()
        n.partes['vela'] = 50.0
        assert n.velocidade_maxima() < cheio


class TestAtualizarMovimentoAncora:
    def test_ancorado_zera_velocidade_mas_gira(self):
        n = _navio("brigantim")
        n.velocidade = 10.0
        n.heading_alvo = 90.0
        n.ancorado = True
        for _ in range(50):
            n.atualizar_movimento(dt=1.0, angulo_relativo_vento_atual=67.5, intensidade_vento_atual=10.0)
        assert n.velocidade == pytest.approx(0.0)
        assert n.heading == pytest.approx(90.0)

    def test_ancorado_suprime_empuxos_de_vento(self):
        n = _navio("brigantim")
        n.heading_alvo = n.heading
        n.ancorado = True
        x0, y0 = n.x, n.y
        for _ in range(20):
            n.atualizar_movimento(dt=0.5, angulo_relativo_vento_atual=90.0, intensidade_vento_atual=20.0)
        # sem propulsao, sem deriva de traves, sem empuxo constante -> parado
        assert n.x == pytest.approx(x0)
        assert n.y == pytest.approx(y0)


class TestFreiaSemVela:
    def test_freia_ate_zero_quando_todos_slots_no_nivel_zero(self):
        n = _navio("brigantim")
        for slot in n.slots_vela:
            slot["nivel"] = 0
        n.velocidade = 10.0
        n.heading_alvo = n.heading
        for _ in range(200):
            n.atualizar_movimento(dt=0.5, angulo_relativo_vento_atual=67.5, intensidade_vento_atual=10.0)
        assert n.velocidade == pytest.approx(0.0)


class TestDerivaLateral:
    def test_gerada_ao_virar_leme(self):
        n = _navio("brigantim")
        n.velocidade = 5.0
        n.heading_alvo = 90.0
        n.atualizar_movimento(dt=0.1, angulo_relativo_vento_atual=90.0, intensidade_vento_atual=0.0)
        assert n.velocidade_lateral != 0.0

    def test_zero_em_linha_reta_sem_vento_de_traves(self):
        n = _navio("brigantim")
        n.velocidade = 5.0
        n.heading_alvo = n.heading
        # angulo 0 (zona morta) -> sin(0) = 0 -> sem empuxo lateral de traves
        n.atualizar_movimento(dt=0.1, angulo_relativo_vento_atual=0.0, intensidade_vento_atual=10.0)
        assert n.velocidade_lateral == pytest.approx(0.0)

    def test_traves_gera_deriva_mesmo_sem_virar(self):
        n = _navio("brigantim")
        n.heading_alvo = n.heading
        n.atualizar_movimento(dt=0.1, angulo_relativo_vento_atual=90.0, intensidade_vento_atual=10.0)
        assert n.velocidade_lateral != 0.0

    def test_nao_inverte_sinal_com_dt_grande(self):
        heading, velocidade, velocidade_lateral, dx, dy, eff, fi = calcular_tick_fisica(
            heading=0.0, heading_alvo=0.0, velocidade=0.0, velocidade_lateral=5.0,
            giro_graus_seg_base=25.0, velocidade_max_base=11.0,
            slots_vela=gerar_slots_fabrica("brigantim"),
            peso_casco=PESO_CASCO["brigantim"], area_casco=AREA_CASCO["brigantim"],
            num_velas=3, ancorado=False, fator_dano=1.0, dt=1000.0,
            angulo_relativo_vento_atual=0.0, intensidade_vento_atual=0.0,
            vento_direcao_atual=0.0,
        )
        assert velocidade_lateral == pytest.approx(0.0)
        assert velocidade_lateral >= 0.0
