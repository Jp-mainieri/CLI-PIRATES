"""Testes de pirates.ui.hud.build_mapa_mundo_linhas — quadrante + visão do capitão."""

from types import SimpleNamespace

import pytest

from pirates.constants import (
    MUNDO_QUADRANTE_TAMANHO, MUNDO_VISAO_PORTOS, MUNDO_VISAO_INIMIGOS, MUNDO_TAMANHO,
)
from pirates.ui.hud import build_mapa_mundo_linhas
from pirates.world.entities import Porto, NavioMundo
from pirates.world.state import EstadoMundo


def _estado():
    return SimpleNamespace(cores_ativo=False, graficos_unicode=False)


def _grid_texto(linhas: list[tuple]) -> str:
    """Concatena só as linhas de grade em si (pula título, N, S, legenda final e os
    rótulos fixos W/E nas bordas da linha central, que não são entidades do mundo)."""
    return "\n".join(l[0][1:-1] for l in linhas[2:-2])


class TestQuadrante:
    def test_entidade_fora_do_quadrante_nao_aparece(self):
        em = EstadoMundo("brigantim", seed=1)
        em.jogador_x, em.jogador_y = 100.0, 100.0
        em.portos = [Porto(x=em.jogador_x + MUNDO_QUADRANTE_TAMANHO + 500, y=em.jogador_y, nome="Longe")]
        em.ilhas = []
        em.inimigos = []
        linhas = build_mapa_mundo_linhas(em, _estado())
        assert "P" not in _grid_texto(linhas)

    def test_entidade_dentro_do_quadrante_aparece(self):
        em = EstadoMundo("brigantim", seed=1)
        em.jogador_x, em.jogador_y = 100.0, 100.0
        em.portos = [Porto(x=em.jogador_x + 500, y=em.jogador_y, nome="Perto")]
        em.ilhas = []
        em.inimigos = []
        linhas = build_mapa_mundo_linhas(em, _estado())
        assert "P" in _grid_texto(linhas)

    def test_quadrante_perto_da_borda_do_mundo_nao_quebra(self):
        em = EstadoMundo("brigantim", seed=1)
        em.jogador_x, em.jogador_y = MUNDO_TAMANHO - 1.0, MUNDO_TAMANHO - 1.0
        em.portos = []
        em.ilhas = []
        em.inimigos = []
        linhas = build_mapa_mundo_linhas(em, _estado())
        assert "Quadrante (3,3)" in linhas[0][0]


class TestVisaoCapitao:
    def test_porto_alem_do_alcance_nao_aparece(self):
        em = EstadoMundo("brigantim", seed=1)
        em.jogador_x, em.jogador_y = 100.0, 100.0
        em.portos = [Porto(x=em.jogador_x + MUNDO_VISAO_PORTOS + 100, y=em.jogador_y, nome="Longe")]
        em.ilhas = []
        em.inimigos = []
        linhas = build_mapa_mundo_linhas(em, _estado())
        assert "P" not in _grid_texto(linhas)

    def test_porto_dentro_do_alcance_aparece(self):
        em = EstadoMundo("brigantim", seed=1)
        em.jogador_x, em.jogador_y = 100.0, 100.0
        em.portos = [Porto(x=em.jogador_x + MUNDO_VISAO_PORTOS - 100, y=em.jogador_y, nome="Perto")]
        em.ilhas = []
        em.inimigos = []
        linhas = build_mapa_mundo_linhas(em, _estado())
        assert "P" in _grid_texto(linhas)

    def test_inimigo_alem_do_alcance_nao_aparece(self):
        em = EstadoMundo("brigantim", seed=1)
        em.jogador_x, em.jogador_y = 100.0, 100.0
        em.portos = []
        em.ilhas = []
        # offset em y (nao x) pra nao cair na coluna 0/39 usada pelos rotulos W/E
        em.inimigos = [NavioMundo(x=em.jogador_x, y=em.jogador_y + MUNDO_VISAO_INIMIGOS + 100,
                                   heading=0.0, status="patrulha")]
        linhas = build_mapa_mundo_linhas(em, _estado())
        assert "E" not in _grid_texto(linhas)

    def test_inimigo_dentro_do_alcance_aparece(self):
        em = EstadoMundo("brigantim", seed=1)
        em.jogador_x, em.jogador_y = 100.0, 100.0
        em.portos = []
        em.ilhas = []
        em.inimigos = [NavioMundo(x=em.jogador_x + MUNDO_VISAO_INIMIGOS - 100, y=em.jogador_y,
                                   heading=0.0, status="patrulha")]
        linhas = build_mapa_mundo_linhas(em, _estado())
        assert "E" in _grid_texto(linhas)

    def test_ilha_sempre_visivel_no_quadrante_sem_gate_de_distancia(self):
        em = EstadoMundo("brigantim", seed=1)
        em.jogador_x, em.jogador_y = 100.0, 100.0
        em.portos = []
        em.inimigos = []
        # Ilha bem além de MUNDO_VISAO_PORTOS/INIMIGOS mas dentro do quadrante de 8km.
        from pirates.world.entities import Ilha
        em.ilhas = [Ilha(
            x=em.jogador_x + MUNDO_QUADRANTE_TAMANHO - 500, y=em.jogador_y,
            raio_base=100.0, a1=0.2, a2=0.2, a3=0.2, k1=3, k2=4, k3=5, f1=0.0, f2=0.0, f3=0.0,
        )]
        linhas = build_mapa_mundo_linhas(em, _estado())
        assert "#" in _grid_texto(linhas)
