"""Testes de pirates/core/tripulacao.py — trânsito individual de tripulantes."""

import pytest

from pirates.constants import (
    TRANSITO_CANHAO_MESMO_BORDO, TRANSITO_CANHAO_BORDO_OPOSTO,
    TRANSITO_TAREFA_DIFERENTE, TRANSITO_REPARO_ENTRE_PARTES,
)
from pirates.core.tripulacao import (
    POSTO_BOMBA, Tripulacao, Tripulante, custo_transito, descrever_frente,
    descrever_posto, mesma_tarefa, posto_canhao, posto_reparo, reconciliar,
)

E1 = ('canhao', 'estibordo', 1)
E2 = ('canhao', 'estibordo', 2)
B1 = ('canhao', 'bombordo', 1)
REPARO_CASCO = ('reparo', 'casco')
REPARO_VELA = ('reparo', 'vela')


def _roster(n=4, prefixo="T"):
    return Tripulacao([f"{prefixo}{i+1}" for i in range(n)])


class TestCustoTransito:
    def test_mesmo_bordo(self):
        assert custo_transito(E1, E2) == TRANSITO_CANHAO_MESMO_BORDO

    def test_bordo_oposto(self):
        assert custo_transito(E1, B1) == TRANSITO_CANHAO_BORDO_OPOSTO

    def test_canhao_para_bomba(self):
        assert custo_transito(E1, POSTO_BOMBA) == TRANSITO_TAREFA_DIFERENTE

    def test_bomba_para_canhao(self):
        assert custo_transito(POSTO_BOMBA, E1) == TRANSITO_TAREFA_DIFERENTE

    def test_reparo_para_bomba(self):
        assert custo_transito(REPARO_CASCO, POSTO_BOMBA) == TRANSITO_TAREFA_DIFERENTE

    def test_reparo_entre_partes(self):
        assert custo_transito(REPARO_CASCO, REPARO_VELA) == TRANSITO_REPARO_ENTRE_PARTES

    def test_mesmo_posto_gratis(self):
        assert custo_transito(E1, E1) == 0.0

    def test_ficar_ocioso_gratis(self):
        assert custo_transito(E1, None) == 0.0

    def test_recem_contratado_gratis(self):
        """Quem nunca trabalhou assume o primeiro posto na hora."""
        assert custo_transito(None, B1) == 0.0


# Um posto de cada forma que custo_transito distingue: dois canhoes do mesmo
# bordo, um do bordo oposto, duas partes de reparo e a bomba.
_POSTOS = {
    'canhao E1': E1,
    'canhao E2': E2,
    'canhao B1': B1,
    'reparo casco': REPARO_CASCO,
    'reparo vela': REPARO_VELA,
    'bomba': POSTO_BOMBA,
}


class TestDesigualdadeTriangular:
    """O custo de trânsito precisa se comportar como distância.

    Se um desvio for mais barato que o caminho direto, o jogador troca de bordo
    passando pelo reparo e ganha tempo parando no meio do caminho. Foi o que
    acontecia com TRANSITO_TAREFA_DIFERENTE em 3.0: ir de um canhão ao canhão do
    bordo oposto custava 8.0s direto e 6.0s via qualquer posto de outra tarefa.
    """

    def test_nenhum_desvio_e_mais_barato_que_o_caminho_direto(self):
        for nome_a, a in _POSTOS.items():
            for nome_c, c in _POSTOS.items():
                if a == c:
                    continue
                direto = custo_transito(a, c)
                for nome_b, b in _POSTOS.items():
                    if b == a or b == c:
                        continue
                    via = custo_transito(a, b) + custo_transito(b, c)
                    assert via >= direto, (
                        f"desvio mais barato que o caminho direto: "
                        f"{nome_a} -> {nome_c} custa {direto}s direto, mas só "
                        f"{via}s passando por {nome_b}. Ajuste as constantes de "
                        f"TRANSITO_* para que nenhum atalho compense."
                    )

    def test_trocar_de_bordo_nao_fica_barato_passando_por_outra_tarefa(self):
        """O caso concreto: a ponte que o jogador encontrou."""
        direto = custo_transito(E1, B1)
        for ponte in (REPARO_CASCO, REPARO_VELA, POSTO_BOMBA):
            via = custo_transito(E1, ponte) + custo_transito(ponte, B1)
            assert via >= direto

    def test_constantes_respeitam_o_limite_que_torna_o_desvio_inutil(self):
        """Forma fechada do invariante, para falhar já na calibração."""
        teto = 2 * TRANSITO_TAREFA_DIFERENTE
        assert TRANSITO_CANHAO_MESMO_BORDO <= teto
        assert TRANSITO_CANHAO_BORDO_OPOSTO <= teto


class TestMesmaTarefa:
    """Frente de trabalho: o que a realocacao automatica protege."""

    def test_canhoes_do_mesmo_bordo(self):
        assert mesma_tarefa(E1, E2) is True

    def test_canhoes_de_bordos_diferentes(self):
        assert mesma_tarefa(E1, B1) is False

    def test_o_proprio_canhao(self):
        assert mesma_tarefa(E1, E1) is True

    def test_reparo_da_mesma_parte(self):
        assert mesma_tarefa(REPARO_CASCO, REPARO_CASCO) is True

    def test_reparo_de_partes_diferentes(self):
        assert mesma_tarefa(REPARO_CASCO, REPARO_VELA) is False

    def test_bomba_consigo_mesma(self):
        assert mesma_tarefa(POSTO_BOMBA, POSTO_BOMBA) is True

    def test_tarefas_cruzadas(self):
        assert mesma_tarefa(E1, POSTO_BOMBA) is False
        assert mesma_tarefa(E1, REPARO_CASCO) is False
        assert mesma_tarefa(REPARO_CASCO, POSTO_BOMBA) is False

    def test_ocioso_nunca_e_mesma_tarefa(self):
        """Quem esta no conves e sempre elegivel como doador."""
        assert mesma_tarefa(None, E1) is False
        assert mesma_tarefa(E1, None) is False
        assert mesma_tarefa(None, None) is False

    def test_e_simetrica(self):
        for a in (E1, E2, B1, REPARO_CASCO, REPARO_VELA, POSTO_BOMBA, None):
            for b in (E1, E2, B1, REPARO_CASCO, REPARO_VELA, POSTO_BOMBA, None):
                assert mesma_tarefa(a, b) == mesma_tarefa(b, a)


class TestDescreverFrente:
    def test_canhao_nomeia_o_bordo_nao_o_canhao(self):
        assert descrever_frente(E2) == "canhoes de estibordo"
        assert descrever_frente(B1) == "canhoes de bombordo"

    def test_reparo_nomeia_a_parte(self):
        assert descrever_frente(REPARO_CASCO) == "reparo de casco"

    def test_bomba_e_conves(self):
        assert descrever_frente(POSTO_BOMBA) == "bomba"
        assert descrever_frente(None) == "conves"


class TestDescreverPosto:
    def test_ocioso(self):
        assert descrever_posto(None) == "conves"

    def test_canhao(self):
        assert descrever_posto(E2) == "canhao E2"
        assert descrever_posto(B1) == "canhao B1"

    def test_reparo_e_bomba(self):
        assert descrever_posto(REPARO_CASCO) == "reparo casco"
        assert descrever_posto(POSTO_BOMBA) == "bomba"


class TestAlocarELiberar:
    def test_primeira_alocacao_e_imediata(self):
        tr = _roster(1)
        t = tr.membros[0]
        tr.alocar(t, E1)
        assert t.efetivo()
        assert t.ultimo_posto == E1

    def test_alocar_cobra_transito(self):
        tr = _roster(1)
        t = tr.membros[0]
        tr.alocar(t, E1)
        tr.alocar(t, B1)
        assert t.transito_restante == TRANSITO_CANHAO_BORDO_OPOSTO
        assert t.em_transito()
        assert not t.efetivo()

    def test_ultimo_posto_so_muda_ao_vencer_o_transito(self):
        tr = _roster(1)
        t = tr.membros[0]
        tr.alocar(t, E1)
        tr.alocar(t, B1)
        assert t.ultimo_posto == E1
        tr.atualizar(TRANSITO_CANHAO_BORDO_OPOSTO)
        assert t.ultimo_posto == B1
        assert t.efetivo()

    def test_liberar_preserva_ultimo_posto(self):
        tr = _roster(1)
        t = tr.membros[0]
        tr.alocar(t, E1)
        tr.liberar(t)
        assert t.posto is None
        assert t.ultimo_posto == E1


class TestLavagemPorOcio:
    """O custo vem do último posto TRABALHADO, nunca do estado 'ocioso'."""

    def test_passar_pelo_conves_nao_barateia_a_troca_de_bordo(self):
        tr = _roster(1)
        t = tr.membros[0]
        tr.alocar(t, E1)
        tr.liberar(t)
        tr.alocar(t, B1)
        assert t.transito_restante == TRANSITO_CANHAO_BORDO_OPOSTO

    def test_ocio_prolongado_nao_decai_o_custo(self):
        tr = _roster(1)
        t = tr.membros[0]
        tr.alocar(t, E1)
        tr.liberar(t)
        for _ in range(120):
            tr.atualizar(0.5)  # 60s no convés
        tr.alocar(t, B1)
        assert t.transito_restante == TRANSITO_CANHAO_BORDO_OPOSTO

    def test_transito_interrompido_nao_credita_o_destino(self):
        """Sair no meio do caminho não conta como ter trabalhado lá."""
        tr = _roster(1)
        t = tr.membros[0]
        tr.alocar(t, E1)
        tr.alocar(t, B1)
        tr.atualizar(1.0)
        tr.liberar(t)
        assert t.ultimo_posto == E1
        tr.alocar(t, B1)
        assert t.transito_restante == TRANSITO_CANHAO_BORDO_OPOSTO


class TestAtualizar:
    def test_decrementa_ate_zero_sem_passar(self):
        tr = _roster(1)
        t = tr.membros[0]
        tr.alocar(t, E1)
        tr.alocar(t, POSTO_BOMBA)
        for _ in range(100):
            tr.atualizar(0.5)
        assert t.transito_restante == 0.0

    def test_quem_ja_trabalha_nao_e_afetado(self):
        tr = _roster(1)
        t = tr.membros[0]
        tr.alocar(t, E1)
        tr.atualizar(5.0)
        assert t.efetivo()
        assert t.transito_restante == 0.0


class TestReconciliar:
    def test_converge_para_o_desejado(self):
        tr = _roster(5)
        reconciliar(tr, {E1: 2, POSTO_BOMBA: 1, REPARO_CASCO: 1})
        assert tr.alocados_por_posto() == {E1: 2, POSTO_BOMBA: 1, REPARO_CASCO: 1}
        assert sum(1 for t in tr.membros if t.posto is None) == 1

    def test_idempotente_nao_reinicia_transito(self):
        tr = _roster(2)
        reconciliar(tr, {E1: 1})
        reconciliar(tr, {B1: 1})
        alvo = next(t for t in tr.membros if t.posto == B1)
        tr.atualizar(2.0)
        restante = alvo.transito_restante
        for _ in range(100):
            reconciliar(tr, {B1: 1})
        assert alvo.transito_restante == restante

    def test_transito_progride_sob_reconciliacao_repetida(self):
        tr = _roster(1)
        reconciliar(tr, {E1: 1})
        reconciliar(tr, {B1: 1})
        anterior = tr.membros[0].transito_restante
        for _ in range(30):
            tr.atualizar(0.5)
            reconciliar(tr, {B1: 1})
            assert tr.membros[0].transito_restante <= anterior
            anterior = tr.membros[0].transito_restante
        assert tr.membros[0].efetivo()

    def test_quem_ja_esta_no_posto_certo_nao_e_tocado(self):
        tr = _roster(3)
        reconciliar(tr, {E1: 1})
        veterano = next(t for t in tr.membros if t.posto == E1)
        reconciliar(tr, {E1: 1, POSTO_BOMBA: 2})
        assert veterano.posto == E1
        assert veterano.efetivo()

    def test_excedente_removido_prefere_quem_esta_em_transito(self):
        tr = _roster(2)
        # T1 trabalha no reparo; T2 chega depois vindo de um canhão (em trânsito).
        reconciliar(tr, {REPARO_CASCO: 1})
        tr.atualizar(1.0)
        trabalhando = next(t for t in tr.membros if t.posto == REPARO_CASCO)
        outro = next(t for t in tr.membros if t.posto is None)
        tr.alocar(outro, E1)
        tr.atualizar(TRANSITO_CANHAO_MESMO_BORDO + 1)
        reconciliar(tr, {REPARO_CASCO: 2})
        assert outro.em_transito()
        reconciliar(tr, {REPARO_CASCO: 1})
        assert trabalhando.posto == REPARO_CASCO
        assert outro.posto is None

    def test_escolhe_o_candidato_mais_barato(self):
        tr = _roster(2)
        perto, longe = tr.membros
        tr.alocar(perto, E2)          # mesmo bordo do destino
        tr.alocar(longe, B1)          # bordo oposto
        tr.atualizar(50.0)
        tr.liberar(perto)
        tr.liberar(longe)
        reconciliar(tr, {E1: 1})
        assert perto.posto == E1
        assert perto.transito_restante == TRANSITO_CANHAO_MESMO_BORDO

    def test_determinismo_no_empate(self):
        escolhidos = set()
        for _ in range(10):
            tr = _roster(4)
            reconciliar(tr, {E1: 1})
            escolhidos.add(next(t.id for t in tr.membros if t.posto == E1))
        assert len(escolhidos) == 1

    def test_desejado_maior_que_o_roster_nao_estoura(self):
        tr = _roster(2)
        reconciliar(tr, {E1: 5})
        assert tr.alocados_por_posto() == {E1: 2}

    def test_desejado_vazio_libera_todos(self):
        tr = _roster(3)
        reconciliar(tr, {E1: 2})
        reconciliar(tr, {})
        assert all(t.posto is None for t in tr.membros)


class TestRedimensionar:
    def test_preserva_quem_fica(self):
        tr = _roster(3)
        reconciliar(tr, {E1: 1})
        veterano = next(t for t in tr.membros if t.posto == E1)
        tr.redimensionar([f"T{i+1}" for i in range(5)])
        assert len(tr.membros) == 5
        assert veterano in tr.membros
        assert veterano.posto == E1

    def test_encolher_remove_do_fim(self):
        tr = _roster(4)
        tr.redimensionar(["T1", "T2"])
        assert [t.id for t in tr.membros] == ["T1", "T2"]

    def test_contratado_agora_nao_paga_o_primeiro_posto(self):
        tr = _roster(1)
        tr.redimensionar(["T1", "T2"])
        novo = tr.membros[1]
        tr.alocar(novo, B1)
        assert novo.efetivo()


class TestConsultas:
    def test_efetivos_ignora_quem_esta_a_caminho(self):
        tr = _roster(2)
        a, b = tr.membros
        tr.alocar(a, E1)
        tr.alocar(b, E1)
        tr.alocar(b, B1)
        assert tr.efetivos_por_posto() == {E1: 1}
        assert tr.alocados_por_posto() == {E1: 1, B1: 1}

    def test_transito_restante_do_posto(self):
        tr = _roster(1)
        t = tr.membros[0]
        tr.alocar(t, E1)
        tr.alocar(t, B1)
        tr.atualizar(2.0)
        assert tr.transito_restante_do_posto(B1) == pytest.approx(
            TRANSITO_CANHAO_BORDO_OPOSTO - 2.0
        )
        assert tr.transito_restante_do_posto(E1) == 0.0

    def test_transito_restante_sem_ninguem_a_caminho(self):
        tr = _roster(1)
        assert tr.transito_restante_do_posto(E1) == 0.0


class TestHelpersDePosto:
    def test_posto_canhao_usa_lado_e_indice(self):
        class _C:
            lado, indice = 'bombordo', 3
        assert posto_canhao(_C()) == ('canhao', 'bombordo', 3)

    def test_posto_reparo(self):
        assert posto_reparo('vela') == ('reparo', 'vela')
