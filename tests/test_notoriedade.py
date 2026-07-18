"""Testes de pirates.core.notoriedade — faixas, elite e pontuação."""

import pytest

from pirates.core.notoriedade import (
    NOTORIEDADE_FAIXAS,
    DISTRIBUICAO_TIPO_POR_FAIXA,
    FAIXA8_ELITE_TETO,
    FRACAO_PERDA_FUGA_JOGADOR,
    DESBLOQUEIO_MUNDO_FAIXA,
    DESBLOQUEIO_ARENA_VITORIAS,
    faixa_index,
    titulo,
    icone,
    chance_elite,
    sortear_tipo_navio,
    sortear_bonus_elite,
    pontos_por_afundamento,
    pontos_perdidos_por_fuga,
    bloqueios_mundo,
    bloqueios_arena,
)


class TestFaixaIndex:
    def test_zero_pontos_e_faixa_0(self):
        assert faixa_index(0) == 0

    def test_limite_exato_de_cada_faixa(self):
        for i, faixa in enumerate(NOTORIEDADE_FAIXAS):
            assert faixa_index(faixa["minimo"]) == i

    def test_um_ponto_abaixo_do_limite_fica_na_faixa_anterior(self):
        for i, faixa in enumerate(NOTORIEDADE_FAIXAS):
            if i == 0:
                continue
            assert faixa_index(faixa["minimo"] - 1) == i - 1

    def test_pontos_acima_da_ultima_faixa_ficam_na_ultima(self):
        assert faixa_index(999999) == len(NOTORIEDADE_FAIXAS) - 1

    def test_99_vs_100_pontos(self):
        assert faixa_index(99) == 0
        assert faixa_index(100) == 1


class TestTituloIcone:
    def test_titulo_bate_com_a_faixa(self):
        assert titulo(0) == "Desconhecido"
        assert titulo(12000) == "Lenda Viva"

    def test_icone_ascii_vs_unicode(self):
        assert icone(0, unicode=False) == "."
        assert icone(0, unicode=True) == "·"


class TestChanceElite:
    def test_zero_nas_faixas_0_e_1(self):
        assert chance_elite(0) == 0.0
        assert chance_elite(100) == 0.0

    def test_positiva_a_partir_da_faixa_2(self):
        assert chance_elite(300) == pytest.approx(0.06)

    def test_faixa8_sem_horas_usa_base(self):
        assert chance_elite(12000, horas_na_faixa8=0.0) == pytest.approx(0.35)

    def test_faixa8_cresce_com_horas_mas_nunca_excede_teto(self):
        anterior = chance_elite(12000, horas_na_faixa8=0.0)
        for horas in (1, 5, 20, 100, 1000, 100000):
            atual = chance_elite(12000, horas_na_faixa8=horas)
            assert atual >= anterior
            assert atual <= FAIXA8_ELITE_TETO
            anterior = atual

    def test_faixa8_assintota_perto_do_teto_com_muitas_horas(self):
        assert chance_elite(12000, horas_na_faixa8=100000) == pytest.approx(
            FAIXA8_ELITE_TETO, abs=1e-6
        )


class TestSortearTipoNavio:
    def test_distribuicao_soma_1_em_todas_as_faixas(self):
        for pesos in DISTRIBUICAO_TIPO_POR_FAIXA:
            assert sum(pesos) == pytest.approx(1.0)

    def test_retorna_chave_valida(self):
        for _ in range(50):
            assert sortear_tipo_navio(0) in ("chalupa", "brigantim", "galeao")
            assert sortear_tipo_navio(12000) in ("chalupa", "brigantim", "galeao")


class TestBloqueiosMundo:
    def test_chalupa_nunca_bloqueada(self):
        assert bloqueios_mundo(0)["chalupa"] is None
        assert bloqueios_mundo(7)["chalupa"] is None

    def test_brigantim_bloqueada_abaixo_do_requisito(self):
        exigido = DESBLOQUEIO_MUNDO_FAIXA["brigantim"]
        assert bloqueios_mundo(exigido - 1)["brigantim"] is not None
        assert bloqueios_mundo(exigido)["brigantim"] is None

    def test_galeao_bloqueada_abaixo_do_requisito(self):
        exigido = DESBLOQUEIO_MUNDO_FAIXA["galeao"]
        assert bloqueios_mundo(exigido - 1)["galeao"] is not None
        assert bloqueios_mundo(exigido)["galeao"] is None

    def test_faixa_alta_libera_tudo(self):
        bloqueios = bloqueios_mundo(7)
        assert all(motivo is None for motivo in bloqueios.values())


class TestBloqueiosArena:
    def test_chalupa_nunca_bloqueada(self):
        assert bloqueios_arena(0)["chalupa"] is None

    def test_brigantim_bloqueada_abaixo_do_requisito(self):
        exigido = DESBLOQUEIO_ARENA_VITORIAS["brigantim"]
        assert bloqueios_arena(exigido - 1)["brigantim"] is not None
        assert bloqueios_arena(exigido)["brigantim"] is None

    def test_galeao_bloqueada_abaixo_do_requisito(self):
        exigido = DESBLOQUEIO_ARENA_VITORIAS["galeao"]
        assert bloqueios_arena(exigido - 1)["galeao"] is not None
        assert bloqueios_arena(exigido)["galeao"] is None

    def test_muitas_vitorias_libera_tudo(self):
        bloqueios = bloqueios_arena(999)
        assert all(motivo is None for motivo in bloqueios.values())


class TestSortearBonusElite:
    def test_faixas_sem_elite_retornam_zero(self):
        for _ in range(20):
            bonus = sortear_bonus_elite(0)
            assert bonus == {"casco": 0.0, "tripulacao": 0.0, "cooldown": 0.0}

    def test_bonus_dentro_do_range_da_faixa(self):
        for _ in range(50):
            bonus = sortear_bonus_elite(300)  # faixa 2: (0.10, 0.20)
            assert 0.10 <= bonus["casco"] <= 0.20
            assert bonus["casco"] == bonus["tripulacao"] == bonus["cooldown"]


class TestPontosPorAfundamento:
    def test_pontos_normais_por_tipo(self):
        assert pontos_por_afundamento("chalupa", elite=False) == 10.0
        assert pontos_por_afundamento("brigantim", elite=False) == 25.0
        assert pontos_por_afundamento("galeao", elite=False) == 50.0

    def test_chalupa_elite(self):
        assert pontos_por_afundamento("chalupa", elite=True) == pytest.approx(55.0)

    def test_formula_elite_generica(self):
        assert pontos_por_afundamento("galeao", elite=True) == pytest.approx(
            50 * 2.5 + 30.0
        )


class TestPontosPerdidosPorFuga:
    def test_e_uma_fracao_dos_pontos_de_afundamento(self):
        for tipo in ("chalupa", "brigantim", "galeao"):
            for elite in (False, True):
                assert pontos_perdidos_por_fuga(tipo, elite) == pytest.approx(
                    pontos_por_afundamento(tipo, elite) * FRACAO_PERDA_FUGA_JOGADOR
                )
