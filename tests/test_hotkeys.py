"""Testes para pirates/input/hotkeys.py (ajuste de mira e ciclagem de foco)."""

from pirates.core.state import Estado
from pirates.input.hotkeys import _ajustar_mira, _ciclar_canhao


def _estado(tipo="brigantim"):
    return Estado(tipo_navio=tipo)


def _todos_canhoes(e):
    return [c for lado in e.jogador.canhoes.values() for c in lado]


class TestAjustarMira:
    def test_ajusta_todos_os_canhoes_sem_foco(self):
        e = _estado()
        antes = [c.mira_atual for c in _todos_canhoes(e)]
        _ajustar_mira(e, 25.0)
        depois = [c.mira_atual for c in _todos_canhoes(e)]
        assert depois == [m + 25.0 for m in antes]

    def test_ajusta_todos_os_canhoes_mesmo_com_foco_em_um(self):
        e = _estado()
        _ciclar_canhao(e, "estibordo")  # foca no primeiro canhao de estibordo
        antes = [c.mira_atual for c in _todos_canhoes(e)]
        _ajustar_mira(e, -25.0)
        depois = [c.mira_atual for c in _todos_canhoes(e)]
        assert depois == [m - 25.0 for m in antes]

    def test_ciclar_muda_o_foco_para_o_proximo_canhao_do_lado(self):
        e = _estado("galeao")  # varios canhoes por lado
        _ciclar_canhao(e, "estibordo")
        primeiro = e.foco
        _ciclar_canhao(e, "estibordo")
        segundo = e.foco
        assert primeiro != segundo
        assert segundo[2] == primeiro[2] + 1

    def test_ajusta_dist_alvo_dos_canhoes_armados(self):
        e = _estado()
        armado = _todos_canhoes(e)[0]
        armado.dist_alvo = 300.0
        _ajustar_mira(e, 25.0)
        assert armado.dist_alvo == 325.0

    def test_respeita_limites_de_clamp(self):
        e = _estado()
        for c in _todos_canhoes(e):
            c.mira_atual = 895.0
        _ajustar_mira(e, 25.0)
        assert all(c.mira_atual == 900.0 for c in _todos_canhoes(e))
