"""Testes de lógica pura das lojas do porto (Tier 3b)."""

import pytest

from pirates.core.ship import Navio
from pirates.core.porao import Barril, Porao, CAPACIDADE_BARRIL
from pirates.core.frota import Frota
from pirates.core.porao import preco_reabastecer, preco_venda, preco_reparo
from pirates.port.lojas import (
    preco_upgrade_nivel,
    comprar_barril, reabastecer_barril, vender_barril, reparo_instantaneo,
    comprar_navio_loja, renomear_navio_loja, aplicar_upgrade,
    nivel_atual_upgrade, nivel_max_upgrade,
)
from pirates.constants import PRECO_BARRIL_NOVO, PRECO_VENDA_BARRIL_CHEIO, PARTES


def _navio(cap: int = 6) -> Navio:
    n = Navio("TestShip", x=0, y=0, heading=0, porao_capacidade=cap)
    n.tipo_nome = "Chalupa"
    return n


def _navio_com_ouro(qtd: float = 100.0, cap: int = 6) -> Navio:
    n = _navio(cap)
    n.porao.barris.append(Barril("ouro", qtd))
    return n


# ---------------------------------------------------------------------------
# Funções de preço
# ---------------------------------------------------------------------------

class TestPrecoLoja:
    def test_reabastecer_metade_igual_novo(self):
        assert preco_reabastecer(CAPACIDADE_BARRIL / 2) == pytest.approx(PRECO_BARRIL_NOVO)

    def test_venda_barril_cheio(self):
        b = Barril("polvora", CAPACIDADE_BARRIL)
        assert preco_venda(b) == pytest.approx(PRECO_VENDA_BARRIL_CHEIO)

    def test_venda_proporcional(self):
        b = Barril("polvora", CAPACIDADE_BARRIL / 2)
        assert preco_venda(b) == pytest.approx(PRECO_VENDA_BARRIL_CHEIO / 2)

    def test_reparo_navio_intacto_zero(self):
        n = _navio()
        assert preco_reparo(n) == pytest.approx(0.0)

    def test_reparo_dano_parcial(self):
        from pirates.constants import PRECO_REPARO_POR_PONTO_DANO
        n = _navio()
        n.partes['casco'] = 50.0
        assert preco_reparo(n) == pytest.approx(50.0 * PRECO_REPARO_POR_PONTO_DANO)

    def test_upgrade_nivel_cresce_com_1_5(self):
        base = preco_upgrade_nivel("velocidade_giro", 0)
        nivel1 = preco_upgrade_nivel("velocidade_giro", 1)
        assert nivel1 == pytest.approx(base * 1.5)


# ---------------------------------------------------------------------------
# Comprar barril
# ---------------------------------------------------------------------------

class TestComprarBarril:
    def test_compra_debita_ouro_e_adiciona_barril(self):
        n = _navio_com_ouro(50.0)
        ok, _ = comprar_barril(n, "polvora")
        assert ok is True
        assert n.porao.total("polvora") == pytest.approx(CAPACIDADE_BARRIL)
        assert n.porao.total("ouro") == pytest.approx(50.0 - PRECO_BARRIL_NOVO)

    def test_compra_falha_sem_ouro(self):
        n = _navio()
        ok, msg = comprar_barril(n, "bolas")
        assert ok is False
        assert "insuficiente" in msg.lower()

    def test_compra_falha_porcao_lotado(self):
        n = _navio_com_ouro(100.0, cap=1)
        n.porao.barris.append(Barril("polvora", CAPACIDADE_BARRIL))
        ok, msg = comprar_barril(n, "bolas")
        assert ok is False
        assert "slots" in msg.lower() or "lotado" in msg.lower()


# ---------------------------------------------------------------------------
# Reabastecer barril
# ---------------------------------------------------------------------------

class TestReabastecerBarril:
    def test_reabastece_debita_ouro_correto(self):
        n = _navio_com_ouro(50.0)
        n.porao.barris.append(Barril("polvora", 10.0))
        idx = len(n.porao.barris) - 1
        falta = CAPACIDADE_BARRIL - 10.0
        ok, _ = reabastecer_barril(n, idx, "polvora")
        assert ok is True
        assert n.porao.barris[idx].quantidade == pytest.approx(CAPACIDADE_BARRIL)
        assert n.porao.total("ouro") == pytest.approx(50.0 - preco_reabastecer(falta))

    def test_reabastece_falha_ouro_insuficiente(self):
        n = _navio()
        n.porao.barris.append(Barril("polvora", 0.0))
        ok, msg = reabastecer_barril(n, 0, "polvora")
        assert ok is False
        # nenhuma alteração
        assert n.porao.total("ouro") == pytest.approx(0.0)

    def test_reabastece_falha_tipo_errado(self):
        n = _navio_com_ouro(50.0)
        n.porao.barris.append(Barril("bolas", 10.0))
        ok, _ = reabastecer_barril(n, len(n.porao.barris) - 1, "polvora")
        assert ok is False


# ---------------------------------------------------------------------------
# Vender barril
# ---------------------------------------------------------------------------

class TestVenderBarril:
    def test_venda_credita_ouro_e_remove_barril(self):
        n = _navio()
        n.porao.barris.append(Barril("polvora", CAPACIDADE_BARRIL))
        ok, _ = vender_barril(n, 0)
        assert ok is True
        assert n.porao.total("polvora") == pytest.approx(0.0)
        assert n.porao.total("ouro") == pytest.approx(PRECO_VENDA_BARRIL_CHEIO)

    def test_venda_indice_invalido(self):
        n = _navio()
        ok, _ = vender_barril(n, 99)
        assert ok is False


# ---------------------------------------------------------------------------
# Reparo instantâneo
# ---------------------------------------------------------------------------

class TestReparoInstantaneo:
    def test_reparo_zera_dano_com_ouro_suficiente(self):
        from pirates.constants import PRECO_REPARO_POR_PONTO_DANO
        n = _navio()
        n.partes['casco'] = 50.0
        n.partes['mastro'] = 70.0
        dano = sum(100.0 - n.partes[p] for p in PARTES)
        custo = dano * PRECO_REPARO_POR_PONTO_DANO
        n.porao.barris.append(Barril("ouro", custo + 10.0))
        ok, _ = reparo_instantaneo(n)
        assert ok is True
        for p in PARTES:
            assert n.partes[p] == pytest.approx(100.0)

    def test_reparo_falha_ouro_insuficiente(self):
        n = _navio()
        n.partes['casco'] = 0.0
        n.porao.barris.append(Barril("ouro", 0.01))
        antes = dict(n.partes)
        ok, msg = reparo_instantaneo(n)
        assert ok is False
        assert "insuficiente" in msg.lower()
        # partes não mudaram
        for p in PARTES:
            assert n.partes[p] == pytest.approx(antes[p])

    def test_reparo_navio_intacto_retorna_false(self):
        n = _navio_com_ouro(999.0)
        ok, _ = reparo_instantaneo(n)
        assert ok is False


# ---------------------------------------------------------------------------
# Comprar navio
# ---------------------------------------------------------------------------

class TestComprarNavioLoja:
    def test_compra_cria_navio_na_frota(self):
        frota = Frota()
        n_ativo = _navio_com_ouro(200.0)
        ok, _ = comprar_navio_loja(frota, "facil", "Minha Chalupa", 0, n_ativo)
        assert ok is True
        assert len(frota.navios) == 1
        assert frota.navios[0].nome == "Minha Chalupa"

    def test_compra_falha_ouro_insuficiente(self):
        frota = Frota()
        n_ativo = _navio()
        ok, msg = comprar_navio_loja(frota, "normal", "Bergantim", 0, n_ativo)
        assert ok is False
        assert len(frota.navios) == 0


# ---------------------------------------------------------------------------
# Upgrades
# ---------------------------------------------------------------------------

class TestUpgrades:
    def test_velocidade_giro_aumenta_com_upgrade(self):
        n = _navio_com_ouro(999.0)
        v_antes = n.velocidade_maxima()
        ok, _ = aplicar_upgrade(n, "facil", "velocidade_giro")
        assert ok is True
        assert n.velocidade_maxima() > v_antes

    def test_alcance_canhao_aumenta_com_upgrade(self):
        n = _navio_com_ouro(999.0)
        a_antes = n.alcance_canhao_efetivo()
        ok, _ = aplicar_upgrade(n, "facil", "alcance_canhao")
        assert ok is True
        assert n.alcance_canhao_efetivo() > a_antes

    def test_porao_slot_aumenta_capacidade(self):
        n = _navio_com_ouro(999.0)
        cap_antes = n.porao.capacidade
        ok, _ = aplicar_upgrade(n, "facil", "porao_slot")
        assert ok is True
        assert n.porao.capacidade == cap_antes + 1

    def test_upgrade_max_bloqueado(self):
        n = _navio_com_ouro(9999.0)
        # facil: max "velocidade_giro" = 1
        aplicar_upgrade(n, "facil", "velocidade_giro")
        ok, msg = aplicar_upgrade(n, "facil", "velocidade_giro")
        assert ok is False
        assert "maximo" in msg.lower()

    def test_upgrade_falha_sem_ouro(self):
        n = _navio()
        ok, msg = aplicar_upgrade(n, "normal", "cooldown")
        assert ok is False
        assert "insuficiente" in msg.lower()

    def test_nivel_atual_inicia_zero(self):
        n = _navio()
        assert nivel_atual_upgrade(n, "cooldown") == 0

    def test_nivel_max_por_tipo(self):
        assert nivel_max_upgrade("facil", "porao_slot") == 1
        assert nivel_max_upgrade("dificil", "porao_slot") == 3


def test_capitao_perto_de():
    from pirates.port.scene import capitao_perto_de
    assert capitao_perto_de(9, 3, 9, 3) is True
    assert capitao_perto_de(9, 2, 9, 3) is True
    assert capitao_perto_de(7, 3, 9, 3) is False
