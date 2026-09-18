"""Marcação do tipo de navio inimigo nos mapas.

O símbolo de bordo esquerdo da célula dá o porte do inimigo sem precisar entrar
em combate: chalupa '*', brigantim ':', galeão '%'.
"""

import pytest

from pirates.core.state import Estado
from pirates.core.utils import (
    SIMBOLO_TIPO_NAVIO, SIMBOLO_TIPO_DESCONHECIDO, tipo_navio_mapa,
)
from pirates.constants import NAVIO_TIPOS
from pirates.ui.hud import (
    build_mapa_linhas, build_mapa_navegacao_linhas, build_mapa_mundo_linhas,
)
from pirates.world.state import EstadoMundo


def _estado():
    e = Estado(tipo_navio="brigantim")
    e.textura_mar = False
    e.rastro_ativo = False
    return e


def _grade(linhas):
    """Só as células do mapa.

    Descarta título, rodapé de zoom e legenda: o ':' do 'ZOOM: ~400m' colide
    com o símbolo do brigantim e faria uma asserção de ausência passar por
    engano.
    """
    return "\n".join(
        l[0] for l in linhas
        if set(l[0]) & set("~") and "ZOOM" not in l[0]
    )


class TestHelper:
    @pytest.mark.parametrize("tipo", list(NAVIO_TIPOS))
    def test_aceita_a_chave_canonica(self, tipo):
        assert tipo_navio_mapa(tipo) == SIMBOLO_TIPO_NAVIO[tipo]

    @pytest.mark.parametrize("tipo", list(NAVIO_TIPOS))
    def test_aceita_o_nome_de_exibicao(self, tipo):
        """Navio guarda 'Brigantim' em tipo_nome; NavioMundo guarda 'brigantim'
        em tipo_navio. Os dois chegam ao helper."""
        assert tipo_navio_mapa(NAVIO_TIPOS[tipo]["navio"]) == SIMBOLO_TIPO_NAVIO[tipo]

    def test_todo_tipo_de_navio_tem_simbolo(self):
        """Um tipo novo em NAVIO_TIPOS sem símbolo cairia no fallback e ficaria
        indistinguível de um tipo desconhecido."""
        assert set(NAVIO_TIPOS) == set(SIMBOLO_TIPO_NAVIO)

    def test_simbolos_sao_distintos(self):
        assert len(set(SIMBOLO_TIPO_NAVIO.values())) == len(SIMBOLO_TIPO_NAVIO)

    def test_fallback_nao_se_passa_por_tipo_real(self):
        assert SIMBOLO_TIPO_DESCONHECIDO not in SIMBOLO_TIPO_NAVIO.values()
        assert tipo_navio_mapa("fragata") == SIMBOLO_TIPO_DESCONHECIDO
        assert tipo_navio_mapa(None) == SIMBOLO_TIPO_DESCONHECIDO


class TestMapaDeCombate:
    """Em combate o marcador segue generico.

    O porte do inimigo serve pra decidir SE vale engajar; dentro do combate
    essa decisao ja foi tomada, e o tipo dele ja aparece no resto do HUD.
    """

    @pytest.mark.parametrize("tipo", list(NAVIO_TIPOS))
    def test_nao_marca_o_tipo(self, tipo):
        e = _estado()
        e.inimigo.afundado = False
        e.inimigo.x, e.inimigo.y = 300.0, 180.0
        e.inimigo.tipo_nome = NAVIO_TIPOS[tipo]["navio"]
        e.ilhas_arena = []
        grade = _grade(build_mapa_linhas(e))
        assert SIMBOLO_TIPO_DESCONHECIDO in grade
        assert SIMBOLO_TIPO_NAVIO[tipo] not in grade


class TestMapasDoMundo:
    """build_mapa_* do mundo recebem NavioMundo, cujo campo é tipo_navio.

    NavioMundo NAO tem tipo_nome — ler esse atributo ali levanta AttributeError
    e derruba o jogo assim que um inimigo entra no alcance do mapa.
    """

    def _mundo(self, tipo):
        em = EstadoMundo("brigantim", seed=3)
        em.em_combate = False
        em.jogador_x, em.jogador_y = 1000.0, 1000.0
        alvo = em.inimigos[0]
        alvo.tipo_navio = tipo
        alvo.status = "ativo"
        alvo.x, alvo.y = 1150.0, 1150.0
        alvo.heading = 0.0
        for outro in em.inimigos[1:]:
            outro.status = "afundado"
        return em

    @pytest.mark.parametrize("tipo", list(NAVIO_TIPOS))
    def test_navegacao_marca_o_tipo(self, tipo):
        assert SIMBOLO_TIPO_NAVIO[tipo] in _grade(
            build_mapa_navegacao_linhas(self._mundo(tipo), _estado())
        )

    @pytest.mark.parametrize("tipo", list(NAVIO_TIPOS))
    def test_mapa_mundo_marca_o_tipo(self, tipo):
        assert SIMBOLO_TIPO_NAVIO[tipo] in _grade(
            build_mapa_mundo_linhas(self._mundo(tipo), _estado())
        )

    def test_fugindo_continua_marcado_como_fuga(self):
        """Status de fuga tem prioridade sobre o tipo: saber que ele está
        fugindo vale mais que saber o porte dele."""
        em = self._mundo("galeao")
        em.inimigos[0].status = "fugindo"
        assert "(" in _grade(build_mapa_navegacao_linhas(em, _estado()))


class TestLegenda:
    def test_legenda_lista_todos_os_simbolos(self):
        em = EstadoMundo("brigantim", seed=3)
        em.em_combate = False
        legenda = build_mapa_mundo_linhas(em, _estado())[-2][0]
        for simbolo in SIMBOLO_TIPO_NAVIO.values():
            assert simbolo in legenda, f"legenda nao explica o simbolo {simbolo!r}"
