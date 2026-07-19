"""Testes de pirates.core.frota — Frota, NavioPossuido, comprar_navio."""

import pytest

from pirates.core.ship import Navio
from pirates.core.frota import Frota, NavioPossuido, comprar_navio, renomear_navio
from pirates.core.state import Estado, sincronizar_crew_com_navio_ativo


def _navio_simples() -> Navio:
    return Navio("Teste", x=0, y=0, heading=0)


class TestFrota:
    def test_ativo_none_quando_vazia(self):
        f = Frota()
        assert f.ativo() is None

    def test_adicionar_e_ativo(self):
        f = Frota()
        n = _navio_simples()
        f.adicionar("Meu Navio", n, "chalupa", porto_id=0)
        f.indice_ativo = 0
        assert f.ativo() is not None
        assert f.ativo().nome == "Meu Navio"

    def test_navios_no_porto(self):
        f = Frota()
        f.adicionar("A", _navio_simples(), "chalupa", porto_id=0)
        f.adicionar("B", _navio_simples(), "brigantim", porto_id=1)
        f.adicionar("C", _navio_simples(), "chalupa", porto_id=0)
        assert len(f.navios_no_porto(0)) == 2
        assert len(f.navios_no_porto(1)) == 1

    def test_trocar_ativo_no_mesmo_porto(self):
        f = Frota()
        f.adicionar("Ativo", _navio_simples(), "chalupa", porto_id=0)
        f.adicionar("Outro", _navio_simples(), "brigantim", porto_id=0)
        f.indice_ativo = 0
        f.navios[0].porto_ancorado = None  # simula "em navegação"
        ok = f.trocar_ativo(1, porto_atual_id=0)
        assert ok is True
        assert f.ativo().nome == "Outro"
        assert f.navios[0].porto_ancorado == 0  # antigo ativo ficou ancorado

    def test_trocar_ativo_falha_porto_errado(self):
        f = Frota()
        f.adicionar("Ativo", _navio_simples(), "chalupa", porto_id=None)
        f.adicionar("Outro", _navio_simples(), "brigantim", porto_id=1)
        f.indice_ativo = 0
        ok = f.trocar_ativo(1, porto_atual_id=0)
        assert ok is False

    def test_trocar_ativo_falha_indice_invalido(self):
        f = Frota()
        f.adicionar("Unico", _navio_simples(), "chalupa", porto_id=0)
        f.indice_ativo = 0
        ok = f.trocar_ativo(99, porto_atual_id=0)
        assert ok is False


class TestComprarNavio:
    def test_comprar_cria_navio_na_frota(self):
        f = Frota()
        ok = comprar_navio(f, "chalupa", "Minha Chalupa", porto_id=0, preco=50.0)
        assert ok is True
        assert len(f.navios) == 1
        assert f.navios[0].nome == "Minha Chalupa"

    def test_comprar_tipo_invalido(self):
        f = Frota()
        ok = comprar_navio(f, "navio_fantasma", "X", porto_id=0, preco=0.0)
        assert ok is False

    def test_navio_comprado_tem_porcao_inicial(self):
        f = Frota()
        comprar_navio(f, "brigantim", "Brigantim", porto_id=0, preco=100.0)
        porao = f.navios[0].navio.porao
        assert porao.total("polvora") > 0
        assert porao.total("bolas") > 0


class TestSincronizarCrewResincronizaTipoNavio:
    def test_tipo_navio_acompanha_navio_ativo_ao_trocar(self):
        """Regressao: estado.tipo_navio ficava preso no tipo ORIGINAL do
        capitao mesmo depois de trocar pra um navio de outro tipo (afetava
        cor do HUD e teto de upgrades da loja, que leem estado.tipo_navio)."""
        estado = Estado(tipo_navio="chalupa")
        assert estado.tipo_navio == "chalupa"

        comprar_navio(estado.frota, "galeao", "Meu Galeao", porto_id=0, preco=200.0)
        novo = estado.frota.navios[-1]
        estado.jogador = novo.navio
        sincronizar_crew_com_navio_ativo(estado, novo.tipo)

        assert estado.tipo_navio == "galeao"


class TestRenomear:
    def test_renomear_valido(self):
        f = Frota()
        f.adicionar("Original", _navio_simples(), "chalupa", porto_id=0)
        ok = renomear_navio(f, 0, "Novo Nome")
        assert ok is True
        assert f.navios[0].nome == "Novo Nome"

    def test_renomear_indice_invalido(self):
        f = Frota()
        ok = renomear_navio(f, 5, "X")
        assert ok is False
