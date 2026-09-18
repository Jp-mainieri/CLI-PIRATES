"""Testes do zoom manual do mapa de navegação (hotkeys +/-)."""

from types import SimpleNamespace

import pytest

from pirates.constants import (
    ZOOM_NIVEIS, MUNDO_ZOOM_NAV_PADRAO, MUNDO_VISAO_INIMIGOS, MUNDO_VISAO_PORTOS,
)
from pirates.core.state import Estado
from pirates.input.hotkeys import _ajustar_zoom_nav, processar_hotkey
from pirates.ui.hud import build_mapa_navegacao_linhas
from pirates.world.state import EstadoMundo


MAIS = ord('+')
MENOS = ord('-')

# Cada direção tem duas teclas: a mesma tecla física com e sem SHIFT.
TECLAS_APROXIMA = [ord('+'), ord('=')]
TECLAS_AFASTA = [ord('-'), ord('_')]


def _estado():
    return Estado(tipo_navio="brigantim", hotkeys=True)


def _mundo(em_combate=False):
    em = EstadoMundo("brigantim", seed=1)
    em.em_combate = em_combate
    return em


class TestAjustarZoomNav:
    def test_padrao_inicial_e_um_nivel_valido(self):
        e = _estado()
        assert e.zoom_nav == MUNDO_ZOOM_NAV_PADRAO
        assert e.zoom_nav in ZOOM_NIVEIS

    def test_aproximar_desce_um_nivel(self):
        e = _estado()
        idx = ZOOM_NIVEIS.index(e.zoom_nav)
        assert _ajustar_zoom_nav(e, -1) is True
        assert e.zoom_nav == ZOOM_NIVEIS[idx - 1]

    def test_afastar_sobe_um_nivel(self):
        e = _estado()
        idx = ZOOM_NIVEIS.index(e.zoom_nav)
        assert _ajustar_zoom_nav(e, +1) is True
        assert e.zoom_nav == ZOOM_NIVEIS[idx + 1]

    def test_nao_passa_do_nivel_minimo(self):
        e = _estado()
        e.zoom_nav = ZOOM_NIVEIS[0]
        assert _ajustar_zoom_nav(e, -1) is False
        assert e.zoom_nav == ZOOM_NIVEIS[0]

    def test_nao_passa_do_nivel_maximo(self):
        e = _estado()
        e.zoom_nav = ZOOM_NIVEIS[-1]
        assert _ajustar_zoom_nav(e, +1) is False
        assert e.zoom_nav == ZOOM_NIVEIS[-1]

    def test_percorre_a_lista_inteira_nos_dois_sentidos(self):
        e = _estado()
        e.zoom_nav = ZOOM_NIVEIS[0]
        for esperado in ZOOM_NIVEIS[1:]:
            assert _ajustar_zoom_nav(e, +1) is True
            assert e.zoom_nav == esperado
        for esperado in reversed(ZOOM_NIVEIS[:-1]):
            assert _ajustar_zoom_nav(e, -1) is True
            assert e.zoom_nav == esperado

    def test_valor_fora_da_lista_cai_no_nivel_mais_proximo(self):
        e = _estado()
        e.zoom_nav = 850  # save antigo / valor manual invalido
        _ajustar_zoom_nav(e, +1)
        assert e.zoom_nav == ZOOM_NIVEIS[ZOOM_NIVEIS.index(800) + 1]

    def test_registra_timestamp_da_mudanca(self):
        e = _estado()
        e.tempo = 42.0
        _ajustar_zoom_nav(e, +1)
        assert e.zoom_nav_mudou_em == 42.0

    def test_limite_nao_mexe_no_timestamp(self):
        e = _estado()
        e.zoom_nav = ZOOM_NIVEIS[-1]
        e.tempo = 42.0
        _ajustar_zoom_nav(e, +1)
        assert e.zoom_nav_mudou_em == -999.0


class TestHotkeys:
    def test_mais_aproxima_e_menos_afasta(self):
        e, em = _estado(), _mundo()
        assert processar_hotkey(MAIS, e, em) is True
        assert e.zoom_nav == 400
        assert processar_hotkey(MENOS, e, em) is True
        assert e.zoom_nav == 800

    def test_inerte_em_combate(self):
        e, em = _estado(), _mundo(em_combate=True)
        assert processar_hotkey(MAIS, e, em) is False
        assert e.zoom_nav == MUNDO_ZOOM_NAV_PADRAO

    def test_inerte_sem_estado_mundo(self):
        """Combate de arena avulso não tem mapa de navegação na tela."""
        e = _estado()
        assert processar_hotkey(MAIS, e, None) is False
        assert e.zoom_nav == MUNDO_ZOOM_NAV_PADRAO

    @pytest.mark.parametrize("tecla", TECLAS_APROXIMA)
    def test_todas_as_teclas_de_aproximar_funcionam(self, tecla):
        """'+' e '=' sao a mesma tecla fisica; ambas precisam valer."""
        e, em = _estado(), _mundo()
        assert processar_hotkey(tecla, e, em) is True
        assert e.zoom_nav == 400

    @pytest.mark.parametrize("tecla", TECLAS_AFASTA)
    def test_todas_as_teclas_de_afastar_funcionam(self, tecla):
        """'-' e '_' sao a mesma tecla fisica; ambas precisam valer."""
        e, em = _estado(), _mundo()
        assert processar_hotkey(tecla, e, em) is True
        assert e.zoom_nav == 1600

    def test_nenhuma_tecla_de_zoom_aparece_nas_duas_direcoes(self):
        """Uma tecla listada nos dois grupos mudaria de sentido silenciosamente."""
        from pirates.input.hotkeys import ZOOM_APROXIMA, ZOOM_AFASTA
        assert not set(ZOOM_APROXIMA) & set(ZOOM_AFASTA)
        assert len(set(ZOOM_APROXIMA)) == len(ZOOM_APROXIMA)
        assert len(set(ZOOM_AFASTA)) == len(ZOOM_AFASTA)

    def test_nao_rouba_teclas_de_outras_hotkeys(self):
        e, em = _estado(), _mundo()
        heading_antes = e.jogador.heading_alvo
        processar_hotkey(ord('d'), e, em)
        assert e.jogador.heading_alvo != heading_antes
        assert e.zoom_nav == MUNDO_ZOOM_NAV_PADRAO


class TestMapaUsaOZoom:
    def _linha_zoom(self, e, em):
        return build_mapa_navegacao_linhas(em, e)[-1][0]

    def test_rodape_reflete_o_nivel_atual(self):
        e, em = _estado(), _mundo()
        assert self._linha_zoom(e, em) == f"ZOOM: ~{MUNDO_ZOOM_NAV_PADRAO}m"
        _ajustar_zoom_nav(e, +1)
        assert self._linha_zoom(e, em) == "ZOOM: ~1600m"

    def test_grade_mantem_as_dimensoes_em_qualquer_zoom(self):
        e, em = _estado(), _mundo()
        base = build_mapa_navegacao_linhas(em, e)
        for nivel in ZOOM_NIVEIS:
            e.zoom_nav = nivel
            linhas = build_mapa_navegacao_linhas(em, e)
            assert len(linhas) == len(base)
            assert [len(l[0]) for l in linhas[:-1]] == [len(l[0]) for l in base[:-1]]

    def test_zoom_maximo_nao_ultrapassa_a_visao_do_capitao(self):
        """O mapa de navegação filtra entidades só por half_range, sem o gate de
        visão que o mapa-mundo aplica. Enquanto o maior zoom couber dentro do
        alcance de visão isso é inofensivo; um nível novo maior que MUNDO_VISAO_*
        passaria a revelar inimigos/portos que o capitão não deveria enxergar."""
        assert ZOOM_NIVEIS[-1] <= MUNDO_VISAO_INIMIGOS
        assert ZOOM_NIVEIS[-1] <= MUNDO_VISAO_PORTOS

    def test_estado_sem_zoom_nav_usa_o_padrao(self):
        """build_* aceita SimpleNamespace nos testes de HUD — não pode quebrar."""
        em = _mundo()
        e = SimpleNamespace(cores_ativo=False, graficos_unicode=False,
                            textura_mar=False, rastro_ativo=False, tempo=0.0)
        assert build_mapa_navegacao_linhas(em, e)[-1][0] == f"ZOOM: ~{MUNDO_ZOOM_NAV_PADRAO}m"
