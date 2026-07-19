"""Testes de lógica pura das lojas do porto (Tier 3b)."""

import pytest

from pirates.core.ship import Navio
from pirates.core.porao import Barril, Porao, CAPACIDADE_BARRIL, CAPACIDADE_BARRIL_OURO
from pirates.core.frota import Frota
from pirates.core.porao import preco_reabastecer, preco_venda, preco_reparo
from pirates.port.lojas import (
    preco_upgrade_nivel,
    comprar_barril, reabastecer_barril, vender_barril, reparo_instantaneo,
    comprar_navio_loja, renomear_navio_loja, aplicar_upgrade,
    nivel_atual_upgrade, nivel_max_upgrade, comprar_item_topo,
    transferir_barril_frota,
)
from pirates.constants import (
    PRECO_BARRIL_NOVO, PRECO_VENDA_BARRIL_CHEIO, PARTES, PRECO_ITENS_TOPO,
    PRECO_TRANSFERENCIA_FROTA,
    PRECO_NAVIO_NOVO, PRECO_UPGRADE,
)


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
        ok, _ = comprar_navio_loja(frota, "chalupa", "Minha Chalupa", 0, n_ativo)
        assert ok is True
        assert len(frota.navios) == 1
        assert frota.navios[0].nome == "Minha Chalupa"

    def test_compra_falha_ouro_insuficiente(self):
        frota = Frota()
        n_ativo = _navio()
        ok, msg = comprar_navio_loja(frota, "brigantim", "Brigantim", 0, n_ativo)
        assert ok is False
        assert len(frota.navios) == 0

    def test_segunda_compra_do_mesmo_tipo_custa_1_4x_mais(self):
        frota = Frota()
        n_ativo = _navio_com_ouro(99999.0)
        ok1, msg1 = comprar_navio_loja(frota, "facil", "Chalupa 1", 0, n_ativo)
        ok2, msg2 = comprar_navio_loja(frota, "facil", "Chalupa 2", 0, n_ativo)
        assert ok1 is True and ok2 is True
        preco_base = PRECO_NAVIO_NOVO["facil"]
        assert f"{preco_base:.0f}" in msg1
        assert f"{preco_base * 1.4:.0f}" in msg2

    def test_comprar_tipos_diferentes_nao_afeta_preco_um_do_outro(self):
        frota = Frota()
        n_ativo = _navio_com_ouro(99999.0)
        comprar_navio_loja(frota, "facil", "Chalupa", 0, n_ativo)
        ok, msg = comprar_navio_loja(frota, "dificil", "Galeao", 0, n_ativo)
        assert ok is True
        assert f"{PRECO_NAVIO_NOVO['dificil']:.0f}" in msg


# ---------------------------------------------------------------------------
# Upgrades
# ---------------------------------------------------------------------------

class TestUpgrades:
    def test_velocidade_giro_aumenta_com_upgrade(self):
        n = _navio_com_ouro(999.0)
        v_antes = n.velocidade_maxima()
        ok, _ = aplicar_upgrade(n, "chalupa", "velocidade_giro")
        assert ok is True
        assert n.velocidade_maxima() > v_antes

    def test_alcance_canhao_aumenta_com_upgrade(self):
        n = _navio_com_ouro(999.0)
        a_antes = n.alcance_canhao_efetivo()
        ok, _ = aplicar_upgrade(n, "chalupa", "alcance_canhao")
        assert ok is True
        assert n.alcance_canhao_efetivo() > a_antes

    def test_porao_slot_aumenta_capacidade(self):
        n = _navio_com_ouro(999.0)
        cap_antes = n.porao.capacidade
        ok, _ = aplicar_upgrade(n, "chalupa", "porao_slot")
        assert ok is True
        assert n.porao.capacidade == cap_antes + 1

    def test_upgrade_max_bloqueado(self):
        n = _navio_com_ouro(9999.0)
        # facil: max "velocidade_giro" = 1
        aplicar_upgrade(n, "chalupa", "velocidade_giro")
        ok, msg = aplicar_upgrade(n, "chalupa", "velocidade_giro")
        assert ok is False
        assert "maximo" in msg.lower()

    def test_upgrade_falha_sem_ouro(self):
        n = _navio()
        ok, msg = aplicar_upgrade(n, "brigantim", "cooldown")
        assert ok is False
        assert "insuficiente" in msg.lower()

    def test_nivel_atual_inicia_zero(self):
        n = _navio()
        assert nivel_atual_upgrade(n, "cooldown") == 0

    def test_nivel_max_por_tipo(self):
        assert nivel_max_upgrade("chalupa", "porao_slot") == 1
        assert nivel_max_upgrade("galeao", "porao_slot") == 3

    def test_taxa_capacidade_barril_ouro_e_1_30_nao_1_5(self):
        preco_casco = preco_upgrade_nivel("casco_max", 1)
        preco_barril = preco_upgrade_nivel("capacidade_barril_ouro", 1)
        base_casco = PRECO_UPGRADE["casco_max"]
        base_barril = PRECO_UPGRADE["capacidade_barril_ouro"]
        assert preco_casco == pytest.approx(base_casco * 1.5)
        assert preco_barril == pytest.approx(base_barril * 1.30)

    def test_capacidade_barril_ouro_aumenta_upgrade_navio(self):
        n = _navio_com_ouro(999999.0)
        ok, _ = aplicar_upgrade(n, "facil", "capacidade_barril_ouro")
        assert ok is True
        assert n.upgrades["capacidade_barril_ouro"] == pytest.approx(10.0)

    def test_capacidade_barril_ouro_e_retroativa_em_barris_existentes(self):
        n = _navio_com_ouro(999999.0)
        barril_ouro = n.porao.barris[-1]
        assert barril_ouro.capacidade == pytest.approx(CAPACIDADE_BARRIL_OURO)
        aplicar_upgrade(n, "facil", "capacidade_barril_ouro")
        assert barril_ouro.capacidade == pytest.approx(CAPACIDADE_BARRIL_OURO + 10.0)

    @pytest.mark.parametrize("tipo,custo_esperado", [
        ("facil", 309.35),
        ("normal", 1192.9),
        ("dificil", 10923.5),
    ])
    def test_custo_total_ate_o_teto_de_capacidade_barril_ouro(self, tipo, custo_esperado):
        n = _navio_com_ouro(999999.0)
        custo_total = 0.0
        while nivel_atual_upgrade(n, "capacidade_barril_ouro") < nivel_max_upgrade(tipo, "capacidade_barril_ouro"):
            preco = preco_upgrade_nivel("capacidade_barril_ouro", nivel_atual_upgrade(n, "capacidade_barril_ouro"))
            ok, _ = aplicar_upgrade(n, tipo, "capacidade_barril_ouro")
            assert ok is True
            custo_total += preco
        assert custo_total == pytest.approx(custo_esperado, rel=1e-2)


def test_capitao_perto_de():
    from pirates.port.scene import capitao_perto_de
    assert capitao_perto_de(9, 3, 9, 3) is True
    assert capitao_perto_de(9, 2, 9, 3) is True
    assert capitao_perto_de(7, 3, 9, 3) is False


class TestComprarItemTopo:
    def test_compra_bem_sucedida_debita_ouro_e_aplica_efeito(self):
        n = _navio_com_ouro(1000.0)
        preco = PRECO_ITENS_TOPO["alcance_lendario"]
        ok, msg = comprar_item_topo(n, "alcance_lendario", faixa_notoriedade=6)
        assert ok is True
        assert n.itens_topo["alcance_lendario"] is True
        assert n.upgrades["alcance_canhao"] == pytest.approx(120.0)
        assert n.porao.total("ouro") == pytest.approx(1000.0 - preco)

    def test_casco_lendario_aplica_resistencia_casco(self):
        n = _navio_com_ouro(1000.0)
        ok, _ = comprar_item_topo(n, "casco_lendario", faixa_notoriedade=6)
        assert ok is True
        assert n.upgrades["resistencia_casco"] == pytest.approx(0.5)

    def test_porao_lendario_soma_3_slots(self):
        n = _navio_com_ouro(1000.0)
        cap_antes = n.porao.capacidade
        ok, _ = comprar_item_topo(n, "porao_lendario", faixa_notoriedade=7)
        assert ok is True
        assert n.porao.capacidade == cap_antes + 3

    def test_notoriedade_insuficiente(self):
        n = _navio_com_ouro(1000.0)
        ok, msg = comprar_item_topo(n, "casco_lendario", faixa_notoriedade=5)
        assert ok is False
        assert "notoriedade" in msg.lower()
        assert "casco_lendario" not in n.itens_topo

    def test_ouro_insuficiente(self):
        n = _navio_com_ouro(1.0)
        ok, msg = comprar_item_topo(n, "casco_lendario", faixa_notoriedade=6)
        assert ok is False
        assert "insuficiente" in msg.lower()

    def test_nao_pode_comprar_duas_vezes(self):
        n = _navio_com_ouro(2000.0)
        ok1, _ = comprar_item_topo(n, "alcance_lendario", faixa_notoriedade=6)
        ok2, msg2 = comprar_item_topo(n, "alcance_lendario", faixa_notoriedade=6)
        assert ok1 is True
        assert ok2 is False
        assert "ja comprado" in msg2.lower()
        # Efeito nao dobrou
        assert n.upgrades["alcance_canhao"] == pytest.approx(120.0)

    def test_item_inexistente(self):
        n = _navio_com_ouro(1000.0)
        ok, msg = comprar_item_topo(n, "item_fantasma", faixa_notoriedade=7)
        assert ok is False
        assert "nao existe" in msg.lower()


# ---------------------------------------------------------------------------
# Transferir carga entre navios da frota
# ---------------------------------------------------------------------------

class TestTransferirBarrilFrota:
    def test_transferir_recurso_comum_debita_origem(self):
        origem = _navio_com_ouro(qtd=100.0)
        origem.porao.barris.append(Barril("polvora", 25.0))
        destino = _navio()
        idx = len(origem.porao.barris) - 1  # barril de polvora
        ok, m = transferir_barril_frota(origem, destino, idx)
        assert ok is True
        assert destino.porao.total("polvora") == pytest.approx(25.0)
        assert origem.porao.total("ouro") == pytest.approx(100.0 - PRECO_TRANSFERENCIA_FROTA)

    def test_transferir_recurso_comum_cai_pro_destino_se_origem_sem_ouro(self):
        origem = _navio()  # sem ouro
        origem.porao.barris.append(Barril("polvora", 25.0))
        destino = _navio_com_ouro(qtd=100.0)
        idx = 0
        ok, m = transferir_barril_frota(origem, destino, idx)
        assert ok is True
        assert destino.porao.total("polvora") == pytest.approx(25.0)
        assert destino.porao.total("ouro") == pytest.approx(100.0 - PRECO_TRANSFERENCIA_FROTA)

    def test_transferir_recurso_comum_falha_sem_ouro_nos_dois_lados(self):
        origem = _navio()
        origem.porao.barris.append(Barril("polvora", 25.0))
        destino = _navio()
        ok, m = transferir_barril_frota(origem, destino, 0)
        assert ok is False
        assert len(origem.porao.barris) == 1  # nada mudou
        assert len(destino.porao.barris) == 0

    def test_transferir_ouro_taxa_sai_do_proprio_barril(self):
        origem = _navio_com_ouro(qtd=50.0)
        destino = _navio()
        ok, m = transferir_barril_frota(origem, destino, 0)
        assert ok is True
        assert destino.porao.total("ouro") == pytest.approx(50.0 - PRECO_TRANSFERENCIA_FROTA)
        assert origem.porao.total("ouro") == 0.0

    def test_transferir_ouro_falha_se_barril_nao_cobre_taxa(self):
        origem = _navio_com_ouro(qtd=2.0)  # menos que PRECO_TRANSFERENCIA_FROTA
        destino = _navio()
        ok, m = transferir_barril_frota(origem, destino, 0)
        assert ok is False
        assert origem.porao.total("ouro") == pytest.approx(2.0)  # nada mudou

    def test_transferir_ouro_exato_da_taxa_esvazia_sem_criar_barril_no_destino(self):
        origem = _navio_com_ouro(qtd=PRECO_TRANSFERENCIA_FROTA)
        destino = _navio()
        ok, m = transferir_barril_frota(origem, destino, 0)
        assert ok is True
        assert len(destino.porao.barris) == 0
        assert len(origem.porao.barris) == 0

    def test_transferir_falha_se_destino_sem_slot_livre(self):
        origem = _navio_com_ouro(qtd=50.0)
        destino = _navio(cap=0)  # zero slots
        ok, m = transferir_barril_frota(origem, destino, 0)
        assert ok is False
        assert len(origem.porao.barris) == 1  # nada mudou

    def test_transferir_indice_invalido(self):
        origem = _navio()
        destino = _navio()
        ok, m = transferir_barril_frota(origem, destino, 5)
        assert ok is False
