"""Testes para pirates/core/vento.py."""

import pytest

from pirates.core.vento import (
    angulo_relativo_vento, zona_vento, eficiencia_zona, atualizar_vento,
    fator_intensidade_vento, empuxo_lateral_vento, empuxo_constante_vento,
)
from pirates.constants import TIPOS_VELA


class Estadinho:
    """Objeto mínimo com os campos que atualizar_vento precisa."""

    def __init__(self, direcao=0.0, intensidade=10.0, resorteio=999.0):
        self.vento_direcao = direcao
        self.vento_direcao_alvo = direcao
        self.vento_intensidade = intensidade
        self.vento_intensidade_alvo = intensidade
        self.vento_proximo_resorteio_em = resorteio


class TestAnguloRelativoVento:
    def test_navio_contra_vento(self):
        assert angulo_relativo_vento(0.0, 0.0) == pytest.approx(0.0)

    def test_navio_a_favor_vento(self):
        assert angulo_relativo_vento(180.0, 0.0) == pytest.approx(180.0)

    def test_simetria_bombordo_estibordo(self):
        a = angulo_relativo_vento(45.0, 0.0)
        b = angulo_relativo_vento(315.0, 0.0)
        assert a == pytest.approx(b)


class TestZonaVento:
    def test_limite_zona_morta(self):
        assert zona_vento(44.9) == "zona_morta"
        assert zona_vento(45.1) == "bolina"

    def test_limite_bolina(self):
        assert zona_vento(89.9) == "bolina"
        assert zona_vento(90.1) == "traves"

    def test_limite_traves(self):
        assert zona_vento(134.9) == "traves"
        assert zona_vento(135.1) == "popa"


class TestEficienciaZona:
    @pytest.mark.parametrize("tipo", TIPOS_VELA.keys())
    def test_pontos_chave_batem_com_tabela(self, tipo):
        tabela = TIPOS_VELA[tipo]["eficiencia_vento"]
        assert eficiencia_zona(tabela, 22.5) == pytest.approx(tabela["zona_morta"])
        assert eficiencia_zona(tabela, 67.5) == pytest.approx(tabela["bolina"])
        assert eficiencia_zona(tabela, 112.5) == pytest.approx(tabela["traves"])
        assert eficiencia_zona(tabela, 157.5) == pytest.approx(tabela["popa"])

    def test_interpolacao_linear_ponto_intermediario(self):
        tabela = TIPOS_VELA["latina"]["eficiencia_vento"]
        meio = (22.5 + 67.5) / 2
        esperado = (tabela["zona_morta"] + tabela["bolina"]) / 2
        assert eficiencia_zona(tabela, meio) == pytest.approx(esperado)

    def test_plato_antes_do_primeiro_ponto(self):
        tabela = TIPOS_VELA["quadrada"]["eficiencia_vento"]
        assert eficiencia_zona(tabela, 5.0) == pytest.approx(tabela["zona_morta"])

    def test_plato_depois_do_ultimo_ponto(self):
        tabela = TIPOS_VELA["quadrada"]["eficiencia_vento"]
        assert eficiencia_zona(tabela, 175.0) == pytest.approx(tabela["popa"])


class TestAtualizarVento:
    def test_direcao_converge_ao_alvo(self):
        estado = Estadinho(direcao=0.0, resorteio=1e9)
        estado.vento_direcao_alvo = 10.0
        for _ in range(2000):
            atualizar_vento(estado, dt=1.0)
        assert estado.vento_direcao == pytest.approx(10.0)

    def test_direcao_nao_ultrapassa_alvo(self):
        estado = Estadinho(direcao=0.0, resorteio=1e9)
        estado.vento_direcao_alvo = 10.0
        atualizar_vento(estado, dt=1e6)
        assert estado.vento_direcao == pytest.approx(10.0)

    def test_intensidade_converge_ao_alvo(self):
        estado = Estadinho(intensidade=5.0, resorteio=1e9)
        estado.vento_intensidade_alvo = 15.0
        for _ in range(2000):
            atualizar_vento(estado, dt=1.0)
        assert estado.vento_intensidade == pytest.approx(15.0)

    def test_intensidade_nao_ultrapassa_alvo(self):
        estado = Estadinho(intensidade=5.0, resorteio=1e9)
        estado.vento_intensidade_alvo = 15.0
        atualizar_vento(estado, dt=1e6)
        assert estado.vento_intensidade == pytest.approx(15.0)


class TestFatorIntensidadeVento:
    def test_ancoras_exatas(self):
        assert fator_intensidade_vento(0.0) == pytest.approx(0.5)
        assert fator_intensidade_vento(5.0) == pytest.approx(1.0)
        assert fator_intensidade_vento(15.0) == pytest.approx(1.0)
        assert fator_intensidade_vento(25.0) == pytest.approx(1.3)

    def test_interpolacao_subida_calmaria(self):
        assert fator_intensidade_vento(2.5) == pytest.approx(0.75)

    def test_interpolacao_subida_rajada(self):
        assert fator_intensidade_vento(20.0) == pytest.approx(1.15)

    def test_plato_potencia_plena(self):
        assert fator_intensidade_vento(10.0) == pytest.approx(1.0)


class TestEmpuxoLateralVento:
    def test_zero_em_zona_morta(self):
        assert empuxo_lateral_vento(3, 10.0, 0.0) == pytest.approx(0.0)

    def test_zero_em_popa(self):
        assert empuxo_lateral_vento(3, 10.0, 180.0) == pytest.approx(0.0)

    def test_maximo_em_traves(self):
        e90 = abs(empuxo_lateral_vento(3, 10.0, 90.0))
        e45 = abs(empuxo_lateral_vento(3, 10.0, 45.0))
        assert e90 > e45


class TestEmpuxoConstanteVento:
    def test_zero_sem_vento(self):
        assert empuxo_constante_vento(500.0, 16.0, 0.0) == pytest.approx(0.0)

    def test_cresce_com_intensidade_ao_quadrado(self):
        e10 = empuxo_constante_vento(500.0, 16.0, 10.0)
        e20 = empuxo_constante_vento(500.0, 16.0, 20.0)
        assert e20 == pytest.approx(e10 * 4)

    def test_diminui_com_peso(self):
        leve = empuxo_constante_vento(200.0, 16.0, 10.0)
        pesado = empuxo_constante_vento(1100.0, 16.0, 10.0)
        assert leve > pesado
