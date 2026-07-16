"""Testes de pirates.world.state — EstadoMundo e sortear_novo_lote."""

import math

import pytest

from pirates.constants import MUNDO_NUM_INIMIGOS, MUNDO_ESPACAMENTO_MIN, MUNDO_TAMANHO
from pirates.world.state import EstadoMundo


class TestEstadoMundoInit:
    def test_cria_com_tres_inimigos(self):
        em = EstadoMundo("normal")
        ativos = [n for n in em.inimigos if n.status != "afundado"]
        assert len(ativos) == MUNDO_NUM_INIMIGOS

    def test_jogador_inicia_no_centro(self):
        em = EstadoMundo("normal")
        assert em.jogador_x == pytest.approx(MUNDO_TAMANHO / 2)
        assert em.jogador_y == pytest.approx(MUNDO_TAMANHO / 2)

    def test_mapa_mundo_oculto_por_padrao(self):
        em = EstadoMundo("normal")
        assert em.mapa_mundo_visivel is False


class TestSortearNovoLote:
    def test_sempre_produz_num_inimigos_nao_afundados(self):
        em = EstadoMundo("normal")
        em.sortear_novo_lote()
        ativos = [n for n in em.inimigos if n.status != "afundado"]
        assert len(ativos) == MUNDO_NUM_INIMIGOS

    def test_preserva_afundados(self):
        em = EstadoMundo("normal")
        em.inimigos[0].status = "afundado"
        em.sortear_novo_lote()
        afundados = [n for n in em.inimigos if n.status == "afundado"]
        assert len(afundados) >= 1

    def test_preserva_fugindo(self):
        em = EstadoMundo("normal")
        em.inimigos[0].status = "fugindo"
        em.sortear_novo_lote()
        fugindo = [n for n in em.inimigos if n.status == "fugindo"]
        assert len(fugindo) >= 1

    def test_espacamento_minimo_entre_novos(self):
        em = EstadoMundo("normal")
        ativos = [n for n in em.inimigos if n.status != "afundado"]
        for i, a in enumerate(ativos):
            for b in ativos[i + 1:]:
                d = em._distancia_toroidal(a.x, a.y, b.x, b.y)
                assert d >= MUNDO_ESPACAMENTO_MIN, (
                    f"Inimigos muito proximos: {d:.0f}m < {MUNDO_ESPACAMENTO_MIN}m"
                )

    def test_espacamento_minimo_do_jogador(self):
        em = EstadoMundo("normal")
        for n in em.inimigos:
            if n.status == "afundado":
                continue
            d = em._distancia_toroidal(n.x, n.y, em.jogador_x, em.jogador_y)
            assert d >= MUNDO_ESPACAMENTO_MIN, (
                f"Inimigo muito proximo do jogador: {d:.0f}m"
            )


class TestDistanciaToroidal:
    def test_mesmo_ponto(self):
        em = EstadoMundo("normal")
        assert em._distancia_toroidal(100, 200, 100, 200) == pytest.approx(0.0)

    def test_vizinhos_proximos_sem_wrap(self):
        em = EstadoMundo("normal")
        assert em._distancia_toroidal(0, 0, 3, 4) == pytest.approx(5.0)

    def test_borda_x_wrap(self):
        # x1=10, x2=7990 → caminho mais curto = 20 (pelo wrap)
        em = EstadoMundo("normal")
        d = em._distancia_toroidal(10, 4000, 7990, 4000)
        assert d == pytest.approx(20.0)

    def test_borda_y_wrap(self):
        em = EstadoMundo("normal")
        d = em._distancia_toroidal(4000, 10, 4000, 7990)
        assert d == pytest.approx(20.0)

    def test_diagonal_wrap(self):
        em = EstadoMundo("normal")
        d = em._distancia_toroidal(10, 10, 7990, 7990)
        assert d == pytest.approx(math.sqrt(20 ** 2 + 20 ** 2))
