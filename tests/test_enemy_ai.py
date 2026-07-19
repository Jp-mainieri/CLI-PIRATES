"""Testes para pirates/ai/enemy.py (IA do inimigo e modo fuga)."""

import pytest
from pirates.core.state import Estado
from pirates.ai.enemy import atualizar_estado_fuga, atualizar_ia_tripulacao


def _estado(tipo="brigantim"):
    return Estado(tipo_navio=tipo)


class TestAtualizarEstadoFuga:
    def test_entra_em_fuga_quando_moral_baixa(self):
        e = _estado()
        e.inimigo.moral_atual = 0.0
        e.ia_limiar_fuga_entrada = 20.0
        e.ia_limiar_fuga_saida = 40.0
        atualizar_estado_fuga(e)
        assert e.inimigo_em_fuga is True

    def test_nao_entra_em_fuga_com_moral_alta(self):
        e = _estado()
        e.inimigo.moral_atual = 80.0
        e.ia_limiar_fuga_entrada = 20.0
        atualizar_estado_fuga(e)
        assert e.inimigo_em_fuga is False

    def test_sai_da_fuga_quando_moral_recupera(self):
        e = _estado()
        e.inimigo_em_fuga = True
        e.inimigo.moral_atual = 60.0
        e.ia_limiar_fuga_saida = 50.0
        e.tempo_fuga_longe = 5.0
        atualizar_estado_fuga(e)
        assert e.inimigo_em_fuga is False
        assert e.tempo_fuga_longe == 0.0

    def test_permanece_em_fuga_entre_limiares(self):
        e = _estado()
        e.inimigo_em_fuga = True
        e.inimigo.moral_atual = 30.0
        e.ia_limiar_fuga_entrada = 15.0
        e.ia_limiar_fuga_saida = 45.0
        atualizar_estado_fuga(e)
        assert e.inimigo_em_fuga is True

    def test_log_registra_entrada_em_fuga(self):
        e = _estado()
        e.inimigo.moral_atual = 0.0
        e.ia_limiar_fuga_entrada = 20.0
        atualizar_estado_fuga(e)
        assert any("fugir" in msg.lower() for msg in e.log)

    def test_log_registra_saida_da_fuga(self):
        e = _estado()
        e.inimigo_em_fuga = True
        e.inimigo.moral_atual = 90.0
        e.ia_limiar_fuga_saida = 50.0
        atualizar_estado_fuga(e)
        assert any("volta" in msg.lower() for msg in e.log)


class TestAtualizarIaTripulacaoModoFuga:
    def test_fuga_desarma_todos_canhoes(self):
        e = _estado("brigantim")
        e.inimigo_em_fuga = True
        for lado in ('estibordo', 'bombordo'):
            for c in e.inimigo.canhoes[lado]:
                c.tripulantes = 2
                c.dist_alvo = 300.0
        atualizar_ia_tripulacao(e)
        for lado in ('estibordo', 'bombordo'):
            for c in e.inimigo.canhoes[lado]:
                assert c.tripulantes == 0
                assert c.dist_alvo is None

    def test_normal_pode_armar_canhoes(self):
        e = _estado("brigantim")
        e.inimigo_em_fuga = False
        atualizar_ia_tripulacao(e)
        total_armados = sum(
            1 for lado in ('estibordo', 'bombordo')
            for c in e.inimigo.canhoes[lado]
            if c.tripulantes > 0
        )
        assert total_armados >= 1
