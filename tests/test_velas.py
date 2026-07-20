"""Testes para pirates/core/velas.py (doc10_customizacao_vela.md)."""

import pytest

from pirates.core.velas import (
    gerar_slots_fabrica, eficiencia_vento_bruta, bonus_fixo_vela_bruto,
    bonus_curva_vela_bruto, indice_slot_principal_inicial,
    trocar_tipo_slot, instalar_ou_trocar_aux,
)
from pirates.constants import TIPOS_VELA, LOADOUT_VELA_FABRICA


class TestGerarSlotsFabrica:
    def test_copia_independente(self):
        a = gerar_slots_fabrica("brigantim")
        b = gerar_slots_fabrica("brigantim")
        a[0]["nivel"] = 0
        assert b[0]["nivel"] != 0

    def test_bate_com_loadout_de_fabrica(self):
        slots = gerar_slots_fabrica("chalupa")
        assert slots == LOADOUT_VELA_FABRICA["chalupa"]


class TestEficienciaVentoBruta:
    def test_slot_vazio_nao_conta(self):
        slots = [{"local": "aux-1", "tipo": None, "nivel": 0}]
        assert eficiencia_vento_bruta(slots, 90.0) == pytest.approx(0.0)

    def test_estai_nao_conta_pra_velocidade(self):
        slots = [{"local": "proa", "tipo": "estai", "nivel": 2}]
        assert eficiencia_vento_bruta(slots, 90.0) == pytest.approx(0.0)

    def test_soma_proporcional_ao_nivel(self):
        slot_nivel1 = [{"local": "principal", "tipo": "quadrada", "nivel": 1}]
        slot_nivel2 = [{"local": "principal", "tipo": "quadrada", "nivel": 2}]
        e1 = eficiencia_vento_bruta(slot_nivel1, 157.5)  # popa
        e2 = eficiencia_vento_bruta(slot_nivel2, 157.5)
        assert e2 == pytest.approx(e1 * 2)

    def test_soma_dois_slots_iguais_dobra(self):
        um = [{"local": "principal-1", "tipo": "quadrada", "nivel": 2}]
        dois = [
            {"local": "principal-1", "tipo": "quadrada", "nivel": 2},
            {"local": "principal-2", "tipo": "quadrada", "nivel": 2},
        ]
        e_um = eficiencia_vento_bruta(um, 157.5)
        e_dois = eficiencia_vento_bruta(dois, 157.5)
        assert e_dois == pytest.approx(e_um * 2)


class TestBonusFixoVelaBruto:
    def test_slot_vazio_nao_conta(self):
        slots = [{"local": "aux-1", "tipo": None, "nivel": 0}]
        assert bonus_fixo_vela_bruto(slots) == pytest.approx(0.0)

    def test_estai_nao_conta(self):
        slots = [{"local": "proa", "tipo": "estai", "nivel": 2}]
        assert bonus_fixo_vela_bruto(slots) == pytest.approx(0.0)

    def test_soma_bonus_fixo_de_tipos_reais(self):
        slots = [
            {"local": "principal", "tipo": "quadrada", "nivel": 2},
            {"local": "popa", "tipo": "carangueja", "nivel": 2},
        ]
        esperado = TIPOS_VELA["quadrada"]["bonus_fixo"] + TIPOS_VELA["carangueja"]["bonus_fixo"]
        assert bonus_fixo_vela_bruto(slots) == pytest.approx(esperado)


class TestBonusCurvaVelaBruto:
    def test_estai_conta_pra_curva(self):
        slots = [{"local": "proa", "tipo": "estai", "nivel": 2}]
        assert bonus_curva_vela_bruto(slots) == pytest.approx(TIPOS_VELA["estai"]["bonus_curva"])

    def test_slot_vazio_nao_conta(self):
        slots = [{"local": "aux-1", "tipo": None, "nivel": 0}]
        assert bonus_curva_vela_bruto(slots) == pytest.approx(0.0)


class TestIndiceSlotPrincipalInicial:
    def test_acha_principal_simples(self):
        slots = gerar_slots_fabrica("brigantim")
        idx = indice_slot_principal_inicial(slots)
        assert slots[idx]["local"] == "principal"

    def test_acha_primeiro_principal_numerado(self):
        slots = gerar_slots_fabrica("galeao")
        idx = indice_slot_principal_inicial(slots)
        assert slots[idx]["local"] == "principal-1"


class TestTrocarTipoSlot:
    def test_sempre_resulta_em_nivel_2(self):
        slots = gerar_slots_fabrica("brigantim")
        slots[1]["nivel"] = 0
        trocar_tipo_slot(slots, 1, "latina")
        assert slots[1]["tipo"] == "latina"
        assert slots[1]["nivel"] == 2


class TestInstalarOuTrocarAux:
    def test_instala_em_slot_vazio_no_nivel_2(self):
        slots = gerar_slots_fabrica("brigantim")
        idx = next(i for i, s in enumerate(slots) if s["local"].startswith("aux"))
        assert slots[idx]["tipo"] is None
        instalar_ou_trocar_aux(slots, idx, "topo_quadrada")
        assert slots[idx]["tipo"] == "topo_quadrada"
        assert slots[idx]["nivel"] == 2

    def test_troca_slot_ja_ocupado(self):
        slots = gerar_slots_fabrica("galeao")
        idx = next(i for i, s in enumerate(slots) if s["tipo"] == "topo_quadrada")
        instalar_ou_trocar_aux(slots, idx, "vela_de_asa")
        assert slots[idx]["tipo"] == "vela_de_asa"
        assert slots[idx]["nivel"] == 2
