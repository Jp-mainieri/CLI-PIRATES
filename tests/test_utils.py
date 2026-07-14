"""Testes para pirates/core/utils.py (funções puras, sem curses)."""

import pytest
from pirates.core.utils import clamp, barra, nivel_cor, seta_ascii_para_heading


class TestClamp:
    def test_dentro_do_intervalo(self):
        assert clamp(5.0, 0.0, 10.0) == 5.0

    def test_abaixo_do_minimo(self):
        assert clamp(-1.0, 0.0, 10.0) == 0.0

    def test_acima_do_maximo(self):
        assert clamp(15.0, 0.0, 10.0) == 10.0

    def test_no_limite_inferior(self):
        assert clamp(0.0, 0.0, 10.0) == 0.0

    def test_no_limite_superior(self):
        assert clamp(10.0, 0.0, 10.0) == 10.0

    def test_inteiros(self):
        assert clamp(3, 1, 5) == 3


class TestBarra:
    def test_vazia(self):
        assert barra(0, 6) == "------"

    def test_cheia(self):
        assert barra(100, 6) == "######"

    def test_metade(self):
        assert barra(50, 6) == "###---"

    def test_largura_padrao(self):
        b = barra(100)
        assert len(b) == 6

    def test_largura_customizada(self):
        b = barra(50, largura=10)
        assert len(b) == 10

    def test_valor_acima_de_100_e_clampado(self):
        assert barra(200, 4) == "####"

    def test_valor_negativo_e_clampado(self):
        assert barra(-10, 4) == "----"


class TestNivelCor:
    def test_alto_e_verde(self):
        assert nivel_cor(80) == 'verde'

    def test_medio_e_amarelo(self):
        assert nivel_cor(40) == 'amarelo'

    def test_baixo_e_vermelho(self):
        assert nivel_cor(10) == 'vermelho'

    def test_fronteira_verde_amarelo(self):
        assert nivel_cor(61) == 'verde'
        assert nivel_cor(60) == 'amarelo'

    def test_fronteira_amarelo_vermelho(self):
        assert nivel_cor(26) == 'amarelo'
        assert nivel_cor(25) == 'vermelho'

    def test_pior_se_alto_inverte_logica(self):
        # 80% de água = ruim
        assert nivel_cor(80, pior_se_alto=True) == 'vermelho'
        # 10% de água = bom
        assert nivel_cor(10, pior_se_alto=True) == 'verde'


class TestSetaAscii:
    def test_norte(self):
        assert seta_ascii_para_heading(0) == '^'

    def test_sul(self):
        assert seta_ascii_para_heading(180) == 'v'

    def test_leste(self):
        assert seta_ascii_para_heading(90) == '>'

    def test_oeste(self):
        assert seta_ascii_para_heading(270) == '<'

    def test_360_equivale_a_norte(self):
        assert seta_ascii_para_heading(360) == seta_ascii_para_heading(0)
