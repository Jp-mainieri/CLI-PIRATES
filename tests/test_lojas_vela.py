"""Testes para pirates/port/lojas.py: trocar_vela e instalar_vela_auxiliar."""

import pytest

from pirates.core.ship import Navio
from pirates.core.porao import Barril
from pirates.core.velas import gerar_slots_fabrica
from pirates.port.lojas import trocar_vela, instalar_vela_auxiliar
from pirates.constants import PRECO_TROCA_VELA, PRECO_INSTALAR_AUX


def _navio(tipo="brigantim", ouro=0.0):
    n = Navio(
        "TestShip", x=0, y=0, heading=0, porao_capacidade=6,
        slots_vela=gerar_slots_fabrica(tipo),
    )
    if ouro > 0:
        n.porao.barris.append(Barril("ouro", ouro))
    return n


class TestTrocarVela:
    def test_troca_slot_principal(self):
        n = _navio("brigantim", ouro=999.0)
        idx = next(i for i, s in enumerate(n.slots_vela) if s["local"] == "principal")
        ok, msg = trocar_vela(n, "brigantim", idx, "latina")
        assert ok is True
        assert n.slots_vela[idx]["tipo"] == "latina"
        assert n.slots_vela[idx]["nivel"] == 2

    def test_rejeita_slot_auxiliar(self):
        n = _navio("brigantim", ouro=999.0)
        idx = next(i for i, s in enumerate(n.slots_vela) if s["local"].startswith("aux"))
        ok, msg = trocar_vela(n, "brigantim", idx, "latina")
        assert ok is False

    def test_rejeita_tipo_auxiliar_num_slot_normal(self):
        n = _navio("brigantim", ouro=999.0)
        idx = next(i for i, s in enumerate(n.slots_vela) if s["local"] == "principal")
        ok, msg = trocar_vela(n, "brigantim", idx, "topo_quadrada")
        assert ok is False

    def test_debita_ouro(self):
        n = _navio("brigantim", ouro=999.0)
        idx = next(i for i, s in enumerate(n.slots_vela) if s["local"] == "principal")
        antes = n.porao.total("ouro")
        trocar_vela(n, "brigantim", idx, "latina")
        assert n.porao.total("ouro") == pytest.approx(antes - PRECO_TROCA_VELA["brigantim"])

    def test_falha_sem_ouro_suficiente(self):
        n = _navio("brigantim", ouro=1.0)
        idx = next(i for i, s in enumerate(n.slots_vela) if s["local"] == "principal")
        tipo_antes = n.slots_vela[idx]["tipo"]
        ok, msg = trocar_vela(n, "brigantim", idx, "latina")
        assert ok is False
        assert n.slots_vela[idx]["tipo"] == tipo_antes


class TestInstalarVelaAuxiliar:
    def test_instala_em_slot_vazio(self):
        n = _navio("brigantim", ouro=999.0)
        idx = next(i for i, s in enumerate(n.slots_vela) if s["local"].startswith("aux"))
        ok, msg = instalar_vela_auxiliar(n, idx, "topo_quadrada")
        assert ok is True
        assert n.slots_vela[idx]["tipo"] == "topo_quadrada"
        assert n.slots_vela[idx]["nivel"] == 2

    def test_rejeita_slot_nao_auxiliar(self):
        n = _navio("brigantim", ouro=999.0)
        idx = next(i for i, s in enumerate(n.slots_vela) if s["local"] == "principal")
        ok, msg = instalar_vela_auxiliar(n, idx, "topo_quadrada")
        assert ok is False

    def test_rejeita_tipo_nao_auxiliar(self):
        n = _navio("brigantim", ouro=999.0)
        idx = next(i for i, s in enumerate(n.slots_vela) if s["local"].startswith("aux"))
        ok, msg = instalar_vela_auxiliar(n, idx, "latina")
        assert ok is False

    def test_debita_ouro(self):
        n = _navio("galeao", ouro=999.0)
        idx = next(i for i, s in enumerate(n.slots_vela) if s["local"].startswith("aux"))
        antes = n.porao.total("ouro")
        instalar_vela_auxiliar(n, idx, "vela_de_asa")
        assert n.porao.total("ouro") == pytest.approx(antes - PRECO_INSTALAR_AUX["vela_de_asa"])

    def test_falha_sem_ouro_suficiente(self):
        n = _navio("brigantim", ouro=1.0)
        idx = next(i for i, s in enumerate(n.slots_vela) if s["local"].startswith("aux"))
        ok, msg = instalar_vela_auxiliar(n, idx, "topo_quadrada")
        assert ok is False
        assert n.slots_vela[idx]["tipo"] is None
