"""Testes da fuga do jogador: limiar alcançável + painel de progresso no HUD."""

import pytest

from pirates.constants import ALCANCE_FUGA_ESCAPE, TEMPO_FUGA_ESCAPE_SEG, MUNDO_GATILHO_COMBATE
from pirates.core.simulation import atualizar_simulacao
from pirates.core.state import Estado
from pirates.ui.hud import build_fuga_linhas


def _estado(distancia_inimigo: float):
    """Estado de combate com o inimigo a *distancia_inimigo* do jogador."""
    e = Estado(tipo_navio="brigantim")
    e.jogador.x, e.jogador.y = 0.0, 0.0
    e.inimigo.x, e.inimigo.y = 0.0, distancia_inimigo
    e.inimigo.afundado = False
    e.inimigo_em_fuga = False
    e.ilhas_arena = []
    return e


def _texto(linhas):
    return linhas[0][0] if linhas else ""


class TestLimiar:
    def test_limiar_fica_acima_do_gatilho_de_combate(self):
        """Escapar tem que exigir mais que a distância em que o combate começa,
        senão a fuga seria automática ao entrar no combate."""
        assert ALCANCE_FUGA_ESCAPE > MUNDO_GATILHO_COMBATE

    def test_limiar_alcancavel_pelo_pico_do_ciclo_da_ia(self):
        """A IA oscila com pico de ~790-850m em confronto parelho; acima disso
        a fuga volta a ser impossível sem danificar as velas do perseguidor."""
        assert ALCANCE_FUGA_ESCAPE <= 800.0


class TestPainelVisibilidade:
    def test_vazio_quando_nao_esta_fugindo(self):
        e = _estado(600.0)
        assert build_fuga_linhas(e) == []

    def test_aparece_quando_esta_fugindo(self):
        e = _estado(600.0)
        e.jogador_tentando_fugir = True
        assert len(build_fuga_linhas(e)) == 1

    def test_vazio_quando_o_inimigo_afundou(self):
        e = _estado(600.0)
        e.jogador_tentando_fugir = True
        e.inimigo.afundado = True
        assert build_fuga_linhas(e) == []

    def test_vazio_quando_o_jogador_afundou(self):
        e = _estado(600.0)
        e.jogador_tentando_fugir = True
        e.jogador.afundado = True
        assert build_fuga_linhas(e) == []

    def test_avisa_que_esta_suspensa_se_o_inimigo_foge(self):
        """O timer do jogador nao corre enquanto o inimigo foge — o painel
        precisa dizer por que, senao parece travado."""
        e = _estado(600.0)
        e.jogador_tentando_fugir = True
        e.inimigo_em_fuga = True
        assert "suspensa" in _texto(build_fuga_linhas(e))


class TestPainelConteudo:
    def test_mostra_quanto_falta_abaixo_do_limiar(self):
        e = _estado(ALCANCE_FUGA_ESCAPE - 160.0)
        e.jogador_tentando_fugir = True
        assert "faltam 160m" in _texto(build_fuga_linhas(e))

    def test_manda_manter_acima_do_limiar(self):
        e = _estado(ALCANCE_FUGA_ESCAPE + 50.0)
        e.jogador_tentando_fugir = True
        assert "MANTENHA" in _texto(build_fuga_linhas(e))

    def test_barra_reflete_o_progresso_do_timer(self):
        e = _estado(ALCANCE_FUGA_ESCAPE + 50.0)
        e.jogador_tentando_fugir = True

        e.tempo_fuga_jogador = 0.0
        vazia = _texto(build_fuga_linhas(e))
        e.tempo_fuga_jogador = TEMPO_FUGA_ESCAPE_SEG / 2
        meio = _texto(build_fuga_linhas(e))
        e.tempo_fuga_jogador = TEMPO_FUGA_ESCAPE_SEG
        cheia = _texto(build_fuga_linhas(e))

        assert vazia.count("#") == 0
        assert meio.count("#") == 5
        assert cheia.count("#") == 10

    def test_mostra_o_limiar_vigente(self):
        e = _estado(600.0)
        e.jogador_tentando_fugir = True
        assert f"{ALCANCE_FUGA_ESCAPE:.0f}m" in _texto(build_fuga_linhas(e))


class TestTimer:
    def test_avanca_acima_do_limiar(self):
        e = _estado(ALCANCE_FUGA_ESCAPE + 50.0)
        e.jogador_tentando_fugir = True
        atualizar_simulacao(e, 1.0)
        assert e.tempo_fuga_jogador == pytest.approx(1.0)

    def test_nao_avanca_abaixo_do_limiar(self):
        e = _estado(ALCANCE_FUGA_ESCAPE - 50.0)
        e.jogador_tentando_fugir = True
        atualizar_simulacao(e, 1.0)
        assert e.tempo_fuga_jogador == 0.0

    def test_escapa_ao_completar_o_tempo(self):
        e = _estado(ALCANCE_FUGA_ESCAPE + 50.0)
        e.jogador_tentando_fugir = True
        e.tempo_fuga_jogador = TEMPO_FUGA_ESCAPE_SEG - 0.5
        atualizar_simulacao(e, 1.0)
        assert e.fim == "fuga_jogador"
        assert e.rodando is False

    def test_aviso_de_interrupcao_sai_uma_vez_so(self):
        """O reset roda a cada tick abaixo do limiar; logar sempre encheria o log."""
        e = _estado(ALCANCE_FUGA_ESCAPE - 50.0)
        e.jogador_tentando_fugir = True
        e.tempo_fuga_jogador = 5.0

        atualizar_simulacao(e, 1.0)
        for _ in range(5):
            atualizar_simulacao(e, 1.0)

        avisos = [m for m in e.log if "Fuga interrompida" in m]
        assert len(avisos) == 1

    def test_sem_aviso_se_o_timer_nunca_correu(self):
        e = _estado(ALCANCE_FUGA_ESCAPE - 50.0)
        e.jogador_tentando_fugir = True
        atualizar_simulacao(e, 1.0)
        assert not any("Fuga interrompida" in m for m in e.log)
