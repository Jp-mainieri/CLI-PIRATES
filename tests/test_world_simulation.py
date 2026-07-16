"""Testes de pirates.world.simulation — física toroidal e transformações."""

import math

import pytest

from pirates.constants import MUNDO_TAMANHO, MUNDO_ALCANCE_VISAO_FUGA
from pirates.world.entities import NavioMundo
from pirates.world.state import EstadoMundo
from pirates.world.simulation import (
    delta_toroidal,
    atualizar_posicao_toroidal,
    atualizar_ia_mundo,
    mundo_para_arena,
    arena_para_mundo,
)


class TestDeltaToroidal:
    def test_sem_wrap(self):
        dx, dy = delta_toroidal(100, 100, 200, 300)
        assert dx == pytest.approx(100.0)
        assert dy == pytest.approx(200.0)

    def test_wrap_x(self):
        # De 10 → 7990 pelo wrap: dx = -20
        dx, dy = delta_toroidal(10, 0, 7990, 0)
        assert dx == pytest.approx(-20.0)

    def test_wrap_y(self):
        dy_wrap = delta_toroidal(0, 10, 0, 7990)[1]
        assert dy_wrap == pytest.approx(-20.0)

    def test_sem_wrap_diagonal(self):
        dx, dy = delta_toroidal(0, 0, 3, 4)
        assert (dx ** 2 + dy ** 2) ** 0.5 == pytest.approx(5.0)

    def test_wrap_simetria(self):
        dx1, dy1 = delta_toroidal(100, 0, 200, 0)
        dx2, dy2 = delta_toroidal(200, 0, 100, 0)
        assert dx1 == pytest.approx(-dx2)


class TestAtualizarPosicaoToroidal:
    def test_avanca_norte(self):
        x, y, h, v = atualizar_posicao_toroidal(
            4000, 4000, 0.0, 0.0, 10.0, 10.0, 5.0, 1.0
        )
        # heading=0 → sin(0)=0, cos(0)=1 → só y cresce
        assert x == pytest.approx(4000.0)
        assert y == pytest.approx(4010.0)

    def test_wrap_borda_superior(self):
        # Começa perto da borda y=MUNDO_TAMANHO e avança norte
        x, y, h, v = atualizar_posicao_toroidal(
            4000, MUNDO_TAMANHO - 5, 0.0, 0.0, 20.0, 20.0, 5.0, 1.0
        )
        assert y == pytest.approx(15.0)

    def test_giro_aplica_limite(self):
        # Taxa de giro 10°/s, dt=1 → máx 10° de variação
        _, _, h, _ = atualizar_posicao_toroidal(
            0, 0, 0.0, 90.0, 0.0, 0.0, 10.0, 1.0
        )
        assert h == pytest.approx(10.0)

    def test_giro_snap_ao_alvo(self):
        # Diferença menor que giro_max → heading fica exatamente no alvo
        _, _, h, _ = atualizar_posicao_toroidal(
            0, 0, 0.0, 5.0, 0.0, 0.0, 10.0, 1.0
        )
        assert h == pytest.approx(5.0)


class TestAtualizarIaMundo:
    def test_patrulha_nao_muda_pra_fugindo_fora_do_alcance(self):
        em = EstadoMundo("normal")
        em.jogador_x = 0.0
        em.jogador_y = 0.0
        # Coloca inimigo bem longe
        for n in em.inimigos:
            n.x = MUNDO_TAMANHO / 2
            n.y = MUNDO_TAMANHO / 2
            n.status = "patrulha"
        atualizar_ia_mundo(em, 0.5)
        # Status deve continuar patrulha
        for n in em.inimigos:
            assert n.status == "patrulha"

    def test_fugindo_dentro_do_alcance_muda_heading(self):
        em = EstadoMundo("normal")
        em.jogador_x = 4000.0
        em.jogador_y = 4000.0
        navio = em.inimigos[0]
        navio.x = 4100.0  # ~100m do jogador, dentro de MUNDO_ALCANCE_VISAO_FUGA=900
        navio.y = 4000.0
        navio.status = "fugindo"
        heading_antes = navio.heading_alvo
        atualizar_ia_mundo(em, 0.5)
        # Navio está a leste do jogador (4100 vs 4000); fuga aponta para leste = 90°
        assert navio.heading_alvo == pytest.approx(90.0, abs=1.0)


class TestMundoParaArena:
    def test_offset_zero_quando_inimigo_no_mesmo_lugar(self):
        em = EstadoMundo("normal")
        em.jogador_x = 1000.0
        em.jogador_y = 2000.0
        navio = NavioMundo(x=1000.0, y=2000.0)
        dx, dy, ox, oy = mundo_para_arena(em, navio)
        assert dx == pytest.approx(0.0)
        assert dy == pytest.approx(0.0)

    def test_offset_simples(self):
        em = EstadoMundo("normal")
        em.jogador_x = 1000.0
        em.jogador_y = 1000.0
        navio = NavioMundo(x=1300.0, y=1400.0)
        dx, dy, ox, oy = mundo_para_arena(em, navio)
        assert dx == pytest.approx(300.0)
        assert dy == pytest.approx(400.0)


class TestArenaParaMundo:
    def test_round_trip(self):
        em = EstadoMundo("normal")
        em.jogador_x = 1500.0
        em.jogador_y = 2500.0
        navio = NavioMundo(x=1800.0, y=2900.0)
        dx, dy, ox, oy = mundo_para_arena(em, navio)
        wx, wy = arena_para_mundo(ox, oy, dx, dy)
        assert wx == pytest.approx(navio.x)
        assert wy == pytest.approx(navio.y)

    def test_round_trip_wrap(self):
        em = EstadoMundo("normal")
        em.jogador_x = 100.0
        em.jogador_y = 100.0
        # Inimigo na borda oposta — menor caminho vai pelo wrap
        navio = NavioMundo(x=7990.0, y=7990.0)
        dx, dy, ox, oy = mundo_para_arena(em, navio)
        wx, wy = arena_para_mundo(ox, oy, dx, dy)
        assert wx == pytest.approx(navio.x)
        assert wy == pytest.approx(navio.y)
