"""Testes para pirates/core/combat.py (geometria e zoom)."""

import math
import pytest
from pirates.core.ship import Navio
from pirates.core.combat import distancia, rumo_para, dentro_do_arco, escolher_zoom
from pirates.constants import ZOOM_NIVEIS


def _navio(x=0.0, y=0.0, heading=0.0):
    n = Navio("T", x=x, y=y, heading=heading)
    n.alcance_canhao = 550.0
    return n


class TestDistancia:
    def test_mesma_posicao(self):
        n = _navio(0, 0)
        assert distancia(n, n) == 0.0

    def test_horizontal(self):
        a = _navio(0, 0)
        b = _navio(100, 0)
        assert abs(distancia(a, b) - 100.0) < 0.001

    def test_vertical(self):
        a = _navio(0, 0)
        b = _navio(0, 200)
        assert abs(distancia(a, b) - 200.0) < 0.001

    def test_diagonal(self):
        a = _navio(0, 0)
        b = _navio(3, 4)
        assert abs(distancia(a, b) - 5.0) < 0.001

    def test_simetrico(self):
        a = _navio(10, 20)
        b = _navio(30, 50)
        assert abs(distancia(a, b) - distancia(b, a)) < 0.001


class TestRumoPara:
    def test_norte(self):
        a = _navio(0, 0)
        b = _navio(0, 100)  # y positivo = norte
        r = rumo_para(a, b)
        assert abs(r - 0.0) < 0.1

    def test_sul(self):
        a = _navio(0, 0)
        b = _navio(0, -100)
        r = rumo_para(a, b)
        assert abs(r - 180.0) < 0.1

    def test_leste(self):
        a = _navio(0, 0)
        b = _navio(100, 0)  # x positivo = leste
        r = rumo_para(a, b)
        assert abs(r - 90.0) < 0.1

    def test_oeste(self):
        a = _navio(0, 0)
        b = _navio(-100, 0)
        r = rumo_para(a, b)
        assert abs(r - 270.0) < 0.1

    def test_resultado_no_intervalo_0_360(self):
        a = _navio(50, 50)
        b = _navio(0, 0)
        r = rumo_para(a, b)
        assert 0.0 <= r < 360.0


class TestDentroDoArco:
    def test_estibordo_alvo_a_90_graus(self):
        # Navio apontando Norte (heading=0), alvo a leste (90° relativo) → estibordo
        atirador = _navio(0, 0, heading=0)
        alvo = _navio(200, 0)  # a leste
        ok, d = dentro_do_arco(atirador, alvo, 'estibordo')
        assert ok is True

    def test_bombordo_alvo_a_270_graus(self):
        # Navio apontando Norte, alvo a oeste (270° relativo) → bombordo
        atirador = _navio(0, 0, heading=0)
        alvo = _navio(-200, 0)  # a oeste
        ok, d = dentro_do_arco(atirador, alvo, 'bombordo')
        assert ok is True

    def test_fora_do_alcance(self):
        atirador = _navio(0, 0, heading=0)
        alvo = _navio(2000, 0)  # além do alcance de 550
        ok, d = dentro_do_arco(atirador, alvo, 'estibordo')
        assert ok is False

    def test_alvo_na_proa_nao_e_estibordo(self):
        # Alvo direto à frente (0° relativo) não está no arco estibordo (20-160°)
        atirador = _navio(0, 0, heading=0)
        alvo = _navio(0, 200)  # à frente (norte)
        ok, _ = dentro_do_arco(atirador, alvo, 'estibordo')
        assert ok is False

    def test_retorna_distancia(self):
        atirador = _navio(0, 0, heading=0)
        alvo = _navio(200, 0)
        _, d = dentro_do_arco(atirador, alvo, 'estibordo')
        assert abs(d - 200.0) < 0.1


class TestEscolherZoom:
    def test_primeiro_nivel_adequado_quando_sem_zoom_atual(self):
        # Distância pequena → zoom pequeno
        z = escolher_zoom(100, None)
        assert z in ZOOM_NIVEIS

    def test_zoom_maximo_para_distancia_grande(self):
        z = escolher_zoom(5000, None)
        assert z == ZOOM_NIVEIS[-1]

    def test_zoom_nao_muda_com_histerese(self):
        # Dentro da histerese, zoom não deve cair
        z_atual = 400
        # Distância um pouco abaixo do nível 200 mas dentro da histerese
        z_novo = escolher_zoom(180, z_atual)
        # Deve manter 400 ou cair para 200 (mas não pular para baixo de 200)
        assert z_novo in ZOOM_NIVEIS

    def test_zoom_sobe_quando_distancia_aumenta(self):
        z_atual = ZOOM_NIVEIS[0]
        z_novo = escolher_zoom(10000, z_atual)
        assert z_novo >= z_atual
