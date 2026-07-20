"""Testes para pirates/ui/hud.py: build_velas_linhas."""

from pirates.core.state import Estado
from pirates.ui.hud import build_velas_linhas


def _estado(tipo="brigantim"):
    return Estado(tipo_navio=tipo)


class TestBuildVelasLinhas:
    def test_uma_linha_por_slot_mais_cabecalho_e_deriva(self):
        e = _estado("brigantim")
        linhas = build_velas_linhas(e)
        n_slots = len(e.jogador.slots_vela)
        # cabecalho "VELAS" + N slots + linha em branco + linha DERIVA
        assert len(linhas) == 1 + n_slots + 2

    def test_marca_slot_selecionado(self):
        e = _estado("brigantim")
        e.jogador.slot_vela_selecionado = 1
        linhas = build_velas_linhas(e)
        texto_slot1 = linhas[1 + 1][0]  # cabecalho + slot 0 -> slot 1
        assert texto_slot1.startswith(">")

    def test_slot_nao_selecionado_sem_marca(self):
        e = _estado("brigantim")
        e.jogador.slot_vela_selecionado = 1
        linhas = build_velas_linhas(e)
        texto_slot0 = linhas[1][0]
        assert texto_slot0.startswith(" ")

    def test_slot_vazio_mostra_vazio(self):
        e = _estado("brigantim")
        idx = next(i for i, s in enumerate(e.jogador.slots_vela) if s["local"].startswith("aux"))
        linhas = build_velas_linhas(e)
        assert "vazio" in linhas[1 + idx][0]

    def test_ultima_linha_e_deriva(self):
        e = _estado("brigantim")
        linhas = build_velas_linhas(e)
        assert linhas[-1][0].startswith("DERIVA")

    def test_linha_em_branco_antes_da_deriva(self):
        e = _estado("brigantim")
        linhas = build_velas_linhas(e)
        assert linhas[-2][0] == ""
