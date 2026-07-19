"""Testes de pirates.core.porao — Barril, Porao, estoque e geração."""

import random

import pytest

from pirates.core.porao import (
    Barril, Porao, CAPACIDADE_BARRIL, CAPACIDADE_BARRIL_OURO,
    estoque_inicial_jogador, gerar_porao_inimigo, coletar_loot,
)


class TestBarril:
    def test_cheio_quando_na_capacidade(self):
        b = Barril("polvora", CAPACIDADE_BARRIL)
        assert b.cheio is True

    def test_nao_cheio_abaixo_da_capacidade(self):
        b = Barril("polvora", CAPACIDADE_BARRIL - 1)
        assert b.cheio is False

    def test_vazio_quando_zero(self):
        b = Barril("bolas", 0.0)
        assert b.vazio is True

    def test_nao_vazio_com_conteudo(self):
        b = Barril("bolas", 1.0)
        assert b.vazio is False

    def test_capacidade_default_por_tipo(self):
        assert Barril("polvora", 5.0).capacidade == pytest.approx(CAPACIDADE_BARRIL)
        assert Barril("ouro", 5.0).capacidade == pytest.approx(CAPACIDADE_BARRIL_OURO)

    def test_capacidade_explicita_sobrescreve_default(self):
        b = Barril("ouro", 5.0, capacidade=90.0)
        assert b.capacidade == pytest.approx(90.0)


class TestPorao:
    def test_slots_livres_inicial(self):
        p = Porao(5)
        assert p.slots_livres() == 5

    def test_total_por_tipo(self):
        p = Porao(3)
        p.barris.append(Barril("polvora", 10.0))
        p.barris.append(Barril("polvora", 5.0))
        p.barris.append(Barril("bolas", 20.0))
        assert p.total("polvora") == pytest.approx(15.0)
        assert p.total("bolas") == pytest.approx(20.0)
        assert p.total("ouro") == pytest.approx(0.0)

    def test_adicionar_preenche_barril_existente_mais_vazio_primeiro(self):
        p = Porao(3)
        p.barris.append(Barril("tabuas", 5.0))   # mais vazio
        p.barris.append(Barril("tabuas", 20.0))  # menos vazio
        p.adicionar("tabuas", 10.0)
        # O mais vazio (5) deve ter sido preenchido até 15, depois o restante vai pro segundo
        assert p.barris[0].quantidade == pytest.approx(15.0)
        assert p.barris[1].quantidade == pytest.approx(20.0)

    def test_adicionar_cria_barril_novo_quando_existentes_cheios(self):
        p = Porao(3)
        p.barris.append(Barril("polvora", CAPACIDADE_BARRIL))
        excedente = p.adicionar("polvora", 10.0)
        assert excedente == pytest.approx(0.0)
        assert len(p.barris) == 2
        assert p.barris[1].quantidade == pytest.approx(10.0)

    def test_adicionar_retorna_excedente_quando_sem_slots(self):
        p = Porao(1)
        p.barris.append(Barril("ouro", CAPACIDADE_BARRIL_OURO))  # slot cheio (cap=50)
        excedente = p.adicionar("ouro", 5.0)
        assert excedente == pytest.approx(5.0)

    def test_consumir_esvazia_sequencialmente(self):
        p = Porao(3)
        p.barris.append(Barril("bolas", 10.0))
        p.barris.append(Barril("bolas", 15.0))
        faltou = p.consumir("bolas", 12.0)
        assert faltou == pytest.approx(0.0)
        # Primeiro barril esvaziado; segundo com 13
        assert len(p.barris) == 1
        assert p.barris[0].quantidade == pytest.approx(13.0)

    def test_consumir_remove_barris_zerados(self):
        p = Porao(2)
        p.barris.append(Barril("polvora", 5.0))
        p.barris.append(Barril("polvora", 5.0))
        p.consumir("polvora", 10.0)
        assert len(p.barris) == 0

    def test_consumir_retorna_faltou_quando_insuficiente(self):
        p = Porao(2)
        p.barris.append(Barril("tabuas", 3.0))
        faltou = p.consumir("tabuas", 10.0)
        assert faltou == pytest.approx(7.0)
        assert len(p.barris) == 0

    def test_consumir_nao_afeta_outro_tipo(self):
        p = Porao(2)
        p.barris.append(Barril("polvora", 10.0))
        p.barris.append(Barril("bolas", 10.0))
        p.consumir("polvora", 10.0)
        assert p.total("bolas") == pytest.approx(10.0)


class TestEstoqueInicialJogador:
    def test_chalupa_capacidade_6(self):
        p = estoque_inicial_jogador(6)
        assert len(p.barris) == 3          # 3 usados, 3 vazios
        assert p.total("polvora") == pytest.approx(1 * CAPACIDADE_BARRIL)
        assert p.total("bolas") == pytest.approx(1 * CAPACIDADE_BARRIL)
        assert p.total("tabuas") == pytest.approx(1 * CAPACIDADE_BARRIL)
        assert p.total("ouro") == pytest.approx(0.0)

    def test_bergantim_capacidade_9(self):
        p = estoque_inicial_jogador(9)
        assert len(p.barris) == 6          # 6 usados, 3 vazios
        assert p.total("polvora") == pytest.approx(2 * CAPACIDADE_BARRIL)
        assert p.total("bolas") == pytest.approx(2 * CAPACIDADE_BARRIL)
        assert p.total("tabuas") == pytest.approx(2 * CAPACIDADE_BARRIL)
        assert p.total("ouro") == pytest.approx(0.0)

    def test_galeao_capacidade_14(self):
        p = estoque_inicial_jogador(14)
        assert len(p.barris) == 9          # 9 usados, 5 vazios
        assert p.total("polvora") == pytest.approx(3 * CAPACIDADE_BARRIL)
        assert p.total("bolas") == pytest.approx(3 * CAPACIDADE_BARRIL)
        assert p.total("tabuas") == pytest.approx(3 * CAPACIDADE_BARRIL)
        assert p.total("ouro") == pytest.approx(0.0)

    def test_deixa_slots_vazios(self):
        for cap in (6, 9, 14):
            p = estoque_inicial_jogador(cap)
            assert p.slots_livres() > 0, f"cap={cap} não deveria estar cheio"

    def test_nao_excede_capacidade(self):
        for cap in (6, 9, 14):
            p = estoque_inicial_jogador(cap)
            assert len(p.barris) <= cap


class TestGerarPorao:
    def test_sempre_tem_barril_de_ouro(self):
        for _ in range(20):
            p = gerar_porao_inimigo(6, "normal", 0.0, elite=False)
            assert p.total("ouro") > 0

    def test_sempre_tem_pelo_menos_1_polvora_bola_e_tabua(self):
        for _ in range(20):
            p = gerar_porao_inimigo(6, "normal", 0.0, elite=False)
            assert p.total("polvora") > 0
            assert p.total("bolas") > 0
            assert p.total("tabuas") > 0

    def test_barris_nao_excedem_capacidade(self):
        cap = 9
        for _ in range(20):
            p = gerar_porao_inimigo(cap, "normal", 0.0, elite=False)
            assert len(p.barris) <= cap

    def test_polvora_bolas_sao_inteiros(self):
        # Ouro nao entra mais aqui: MULT_OURO_POR_FAIXA e fracionario, entao
        # o total sorteado (randint * mult) pode ser fracionario por design.
        for _ in range(50):
            p = gerar_porao_inimigo(9, "normal", 0.0, elite=False)
            for b in p.barris:
                if b.tipo in ("polvora", "bolas"):
                    assert b.quantidade == int(b.quantidade), (b.tipo, b.quantidade)

    def test_tabuas_pode_ser_fracionaria(self):
        random.seed(7)
        valores = []
        for _ in range(200):
            p = gerar_porao_inimigo(9, "normal", 0.0, elite=False)
            valores.extend(b.quantidade for b in p.barris if b.tipo == "tabuas")
        assert any(v != int(v) for v in valores)

    def test_ouro_escala_com_faixa_de_notoriedade(self):
        from pirates.core.notoriedade import NOTORIEDADE_FAIXAS

        random.seed(123)
        faixa0 = [gerar_porao_inimigo(9, "normal", 0.0) for _ in range(200)]
        random.seed(123)
        pontos_faixa7 = NOTORIEDADE_FAIXAS[7]["minimo"]
        faixa7 = [gerar_porao_inimigo(9, "normal", pontos_faixa7) for _ in range(200)]

        media_faixa0 = sum(p.total("ouro") for p in faixa0) / len(faixa0)
        media_faixa7 = sum(p.total("ouro") for p in faixa7) / len(faixa7)
        assert media_faixa7 > media_faixa0 * 2

    def test_ouro_escala_com_tipo_de_navio(self):
        random.seed(99)
        facil = [gerar_porao_inimigo(6, "facil", 0.0) for _ in range(200)]
        random.seed(99)
        dificil = [gerar_porao_inimigo(14, "dificil", 0.0) for _ in range(200)]

        media_facil = sum(p.total("ouro") for p in facil) / len(facil)
        media_dificil = sum(p.total("ouro") for p in dificil) / len(dificil)
        assert media_dificil > media_facil

    def test_overflow_de_ouro_cria_multiplos_barris_sem_exceder_capacidade_cada(self):
        from pirates.core.notoriedade import NOTORIEDADE_FAIXAS

        pontos_faixa7 = NOTORIEDADE_FAIXAS[7]["minimo"]
        houve_overflow = False
        for _ in range(100):
            p = gerar_porao_inimigo(20, "dificil", pontos_faixa7)
            barris_ouro = [b for b in p.barris if b.tipo == "ouro"]
            for b in barris_ouro:
                assert b.quantidade <= CAPACIDADE_BARRIL_OURO + 1e-6
            if len(barris_ouro) > 1:
                houve_overflow = True
        assert houve_overflow, "esperava overflow em multiplos barris de ouro na faixa 7 dificil"


class TestGerarPoraoElite:
    def test_capacidade_30_por_cento_maior(self):
        p = gerar_porao_inimigo(10, "normal", 0.0, elite=True)
        assert p.capacidade == round(10 * 1.3)

    def test_nenhum_slot_vazio(self):
        for _ in range(20):
            p = gerar_porao_inimigo(9, "normal", 0.0, elite=True)
            assert len(p.barris) == p.capacidade

    def test_conteudo_medio_mais_cheio_que_normal(self):
        random.seed(42)
        normais = [gerar_porao_inimigo(9, "normal", 0.0, elite=False) for _ in range(200)]
        random.seed(42)
        elites = [gerar_porao_inimigo(9, "normal", 0.0, elite=True) for _ in range(200)]
        media_normal = sum(b.quantidade for p in normais for b in p.barris if b.tipo != "ouro") / sum(
            len(p.barris) - 1 for p in normais
        )
        media_elite = sum(b.quantidade for p in elites for b in p.barris if b.tipo != "ouro") / sum(
            len(p.barris) - 1 for p in elites
        )
        assert media_elite > media_normal


class TestColetarLoot:
    def test_coleta_completa_quando_ha_espaco(self):
        jogador = Porao(6)
        loot = Porao(3)
        loot.barris.append(Barril("ouro", 10.0))
        loot.barris.append(Barril("polvora", 5.0))
        resto = coletar_loot(jogador, loot)
        assert not resto.barris
        assert jogador.total("ouro") == pytest.approx(10.0)
        assert jogador.total("polvora") == pytest.approx(5.0)

    def test_retorna_resto_quando_porcao_cheio(self):
        jogador = Porao(1)
        jogador.barris.append(Barril("ouro", CAPACIDADE_BARRIL_OURO))  # slot cheio (cap=50)
        loot = Porao(2)
        loot.barris.append(Barril("ouro", 10.0))
        loot.barris.append(Barril("tabuas", 15.0))
        resto = coletar_loot(jogador, loot)
        # Slot ocupado por ouro cheio; ouro e tabuas nao couberam
        assert len(resto.barris) > 0
        total_resto = sum(b.quantidade for b in resto.barris)
        assert total_resto == pytest.approx(25.0)
