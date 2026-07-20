"""Testes de pirates.world.simulation — física toroidal e transformações."""

import math

import pytest

from pirates.constants import MUNDO_TAMANHO, MUNDO_ALCANCE_VISAO_FUGA
from pirates.world.entities import NavioMundo
from pirates.world.state import EstadoMundo
from pirates.world.simulation import (
    delta_toroidal,
    atualizar_ia_mundo,
    mundo_para_arena,
    arena_para_mundo,
)
from pirates.core.movimento import calcular_tick_fisica
from pirates.core.velas import gerar_slots_fabrica


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


class TestCalcularTickFisica:
    def _chamar(self, **overrides):
        base = dict(
            heading=0.0, heading_alvo=0.0, velocidade=0.0, velocidade_lateral=0.0,
            giro_graus_seg_base=10.0, velocidade_max_base=10.0,
            slots_vela=gerar_slots_fabrica("brigantim"),
            peso_casco=500.0, area_casco=16.0, num_velas=3, ancorado=False,
            fator_dano=1.0, dt=1.0,
            angulo_relativo_vento_atual=67.5, intensidade_vento_atual=10.0,
            vento_direcao_atual=0.0,
        )
        base.update(overrides)
        return calcular_tick_fisica(**base)

    def test_giro_aplica_limite(self):
        # Taxa de giro 10°/s (sem bonus_curva na chalupa/brigantim padrão), dt=1
        heading, *_ = self._chamar(
            heading=0.0, heading_alvo=90.0, giro_graus_seg_base=10.0,
            slots_vela=[],
        )
        assert heading == pytest.approx(10.0)

    def test_giro_snap_ao_alvo(self):
        heading, *_ = self._chamar(
            heading=0.0, heading_alvo=5.0, giro_graus_seg_base=10.0,
            slots_vela=[],
        )
        assert heading == pytest.approx(5.0)

    def test_freia_sem_velas_abertas(self):
        # Regressão: com slots vazios (eficiencia_bruta=0), vmax=0, mas o
        # navio tem que desacelerar (arrasto do casco), nao ficar travado
        # na velocidade antiga.
        _, velocidade, *_ = self._chamar(
            velocidade=10.0, slots_vela=[], dt=1.0,
        )
        assert velocidade < 10.0

    def test_freia_ate_zero_com_dt_grande(self):
        _, velocidade, *_ = self._chamar(
            velocidade=10.0, slots_vela=[], dt=1000.0,
        )
        assert velocidade == pytest.approx(0.0)

    def test_intensidade_aumenta_velocidade_final(self):
        _, v_calmaria, *_ = self._chamar(
            velocidade=0.0, dt=100.0, intensidade_vento_atual=0.0,
        )
        _, v_rajada, *_ = self._chamar(
            velocidade=0.0, dt=100.0, intensidade_vento_atual=20.0,
        )
        assert v_rajada > v_calmaria

    def test_ancorado_zera_velocidade_mas_ainda_gira(self):
        heading, velocidade, *_ = self._chamar(
            heading=0.0, heading_alvo=90.0, giro_graus_seg_base=10.0,
            velocidade=10.0, ancorado=True, dt=1000.0,
        )
        assert velocidade == pytest.approx(0.0)
        assert heading == pytest.approx(90.0)


class TestAtualizarIaMundo:
    def test_patrulha_nao_muda_pra_fugindo_fora_do_alcance(self):
        em = EstadoMundo("brigantim")
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
        em = EstadoMundo("brigantim")
        em.ilhas = []  # evita flakiness: ilha sorteada sem seed podia cair perto e disparar evasao
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

    def test_vento_reduz_velocidade_na_zona_morta(self, monkeypatch):
        # Trava o inimigo em patrulha sem re-sortear heading_alvo (5% de chance/tick).
        monkeypatch.setattr("pirates.world.simulation.random.random", lambda: 1.0)

        em = EstadoMundo("brigantim")
        for n in em.inimigos:
            n.status = "patrulha"
            n.heading = 0.0
            n.heading_alvo = 0.0
            n.velocidade = 0.0
            # Tipo/slots fixos pra teste determinístico (spawn sorteia o
            # tipo aleatoriamente, mesmo em EstadoMundo("brigantim")).
            n.tipo_navio = "brigantim"
            n.slots_vela = gerar_slots_fabrica("brigantim")

        # Sem vento: velocidade sobe livremente até o teto de patrulha.
        atualizar_ia_mundo(em, dt=5.0, vento_direcao=None)
        v_sem_vento = em.inimigos[0].velocidade

        em2 = EstadoMundo("brigantim")
        for n in em2.inimigos:
            n.status = "patrulha"
            n.heading = 0.0
            n.heading_alvo = 0.0
            n.velocidade = 0.0
            n.tipo_navio = "brigantim"
            n.slots_vela = gerar_slots_fabrica("brigantim")

        # Vento vindo direto da proa (heading=0) → zona morta, eficiência reduzida.
        atualizar_ia_mundo(em2, dt=5.0, vento_direcao=0.0)
        v_com_vento = em2.inimigos[0].velocidade

        assert v_com_vento < v_sem_vento


class TestMundoParaArena:
    def test_offset_zero_quando_inimigo_no_mesmo_lugar(self):
        em = EstadoMundo("brigantim")
        em.jogador_x = 1000.0
        em.jogador_y = 2000.0
        navio = NavioMundo(x=1000.0, y=2000.0)
        dx, dy, ox, oy = mundo_para_arena(em, navio)
        assert dx == pytest.approx(0.0)
        assert dy == pytest.approx(0.0)

    def test_offset_simples(self):
        em = EstadoMundo("brigantim")
        em.jogador_x = 1000.0
        em.jogador_y = 1000.0
        navio = NavioMundo(x=1300.0, y=1400.0)
        dx, dy, ox, oy = mundo_para_arena(em, navio)
        assert dx == pytest.approx(300.0)
        assert dy == pytest.approx(400.0)


class TestArenaParaMundo:
    def test_round_trip(self):
        em = EstadoMundo("brigantim")
        em.jogador_x = 1500.0
        em.jogador_y = 2500.0
        navio = NavioMundo(x=1800.0, y=2900.0)
        dx, dy, ox, oy = mundo_para_arena(em, navio)
        wx, wy = arena_para_mundo(ox, oy, dx, dy)
        assert wx == pytest.approx(navio.x)
        assert wy == pytest.approx(navio.y)

    def test_round_trip_wrap(self):
        em = EstadoMundo("brigantim")
        em.jogador_x = 100.0
        em.jogador_y = 100.0
        # Inimigo na borda oposta — menor caminho vai pelo wrap
        navio = NavioMundo(x=7990.0, y=7990.0)
        dx, dy, ox, oy = mundo_para_arena(em, navio)
        wx, wy = arena_para_mundo(ox, oy, dx, dy)
        assert wx == pytest.approx(navio.x)
        assert wy == pytest.approx(navio.y)
