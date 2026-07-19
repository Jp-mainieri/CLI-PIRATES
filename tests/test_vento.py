"""Testes para pirates/core/vento.py."""

import pytest

from pirates.core.ship import Navio
from pirates.core.vento import (
    angulo_relativo_vento, zona_vento, eficiencia_vento, atualizar_vento,
    fator_intensidade_vento,
)
from pirates.constants import NAVIO_TIPOS


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


class TestEficienciaVento:
    @pytest.mark.parametrize("tipo", NAVIO_TIPOS.keys())
    def test_pontos_chave_batem_com_tabela(self, tipo):
        tabela = NAVIO_TIPOS[tipo]["eficiencia_vento"]
        assert eficiencia_vento(tipo, 22.5) == pytest.approx(tabela["zona_morta"])
        assert eficiencia_vento(tipo, 67.5) == pytest.approx(tabela["bolina"])
        assert eficiencia_vento(tipo, 112.5) == pytest.approx(tabela["traves"])
        assert eficiencia_vento(tipo, 157.5) == pytest.approx(tabela["popa"])

    def test_interpolacao_linear_ponto_intermediario(self):
        tabela = NAVIO_TIPOS["brigantim"]["eficiencia_vento"]
        meio = (22.5 + 67.5) / 2
        esperado = (tabela["zona_morta"] + tabela["bolina"]) / 2
        assert eficiencia_vento("brigantim", meio) == pytest.approx(esperado)

    def test_plato_antes_do_primeiro_ponto(self):
        tabela = NAVIO_TIPOS["galeao"]["eficiencia_vento"]
        assert eficiencia_vento("galeao", 5.0) == pytest.approx(tabela["zona_morta"])

    def test_plato_depois_do_ultimo_ponto(self):
        tabela = NAVIO_TIPOS["galeao"]["eficiencia_vento"]
        assert eficiencia_vento("galeao", 175.0) == pytest.approx(tabela["popa"])


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


class TestIntegracaoNavio:
    def test_velocidade_maxima_varia_com_eficiencia_vento(self):
        n = Navio("Teste", 0, 0, 0, velocidade_max_base=10.0)
        n.eficiencia_vento_atual = 1.0
        vmax_normal = n.velocidade_maxima()
        n.eficiencia_vento_atual = 0.5
        vmax_reduzida = n.velocidade_maxima()
        assert vmax_reduzida == pytest.approx(vmax_normal * 0.5)

    def test_velocidade_maxima_varia_com_fator_intensidade_vento(self):
        n = Navio("Teste", 0, 0, 0, velocidade_max_base=10.0)
        n.fator_intensidade_vento_atual = 1.0
        vmax_normal = n.velocidade_maxima()
        n.fator_intensidade_vento_atual = 1.3
        vmax_rajada = n.velocidade_maxima()
        assert vmax_rajada == pytest.approx(vmax_normal * 1.3)

    def test_taxa_giro_nao_depende_de_vento(self):
        n = Navio(
            "Teste", 0, 0, 0,
            giro_graus_seg=20.0, bonus_curva_vela=0.1,
        )
        antes = n.taxa_giro()
        n.eficiencia_vento_atual = 0.2
        depois = n.taxa_giro()
        assert antes == pytest.approx(depois)
        assert antes == pytest.approx(20.0 * 1.1)
