"""Testes de economia: preços, munição em combate e integração porão."""

import pytest

from pirates.constants import (
    PRECO_BARRIL_NOVO, PRECO_REABASTECER_POR_UNIDADE, PRECO_VENDA_BARRIL_CHEIO,
    PRECO_REPARO_POR_PONTO_DANO, NAVIO_TIPOS,
)
from pirates.core.porao import (
    Barril, Porao, CAPACIDADE_BARRIL,
    estoque_inicial_jogador, gerar_porao_inimigo,
)
from pirates.core.ship import Navio, Canhao
from pirates.core.state import Estado


# ---------------------------------------------------------------------------
# Funções de preço
# ---------------------------------------------------------------------------

def preco_reabastecer(unidades: float) -> float:
    return unidades * PRECO_REABASTECER_POR_UNIDADE


def preco_venda(barril: Barril) -> float:
    return (barril.quantidade / CAPACIDADE_BARRIL) * PRECO_VENDA_BARRIL_CHEIO


def preco_reparo(navio: Navio) -> float:
    dano_total = sum(100 - navio.partes[p] for p in navio.partes)
    return dano_total * PRECO_REPARO_POR_PONTO_DANO


class TestPrecos:
    def test_ponto_de_virada_exato(self):
        """Reabastecer exatamente metade de um barril (12.5u) custa igual a 1 barril novo."""
        custo = preco_reabastecer(CAPACIDADE_BARRIL / 2)
        assert custo == pytest.approx(PRECO_BARRIL_NOVO)

    def test_menos_que_metade_mais_barato_que_barril_novo(self):
        custo = preco_reabastecer(CAPACIDADE_BARRIL / 2 - 1)
        assert custo < PRECO_BARRIL_NOVO

    def test_mais_que_metade_mais_caro_que_barril_novo(self):
        custo = preco_reabastecer(CAPACIDADE_BARRIL / 2 + 1)
        assert custo > PRECO_BARRIL_NOVO

    def test_venda_barril_cheio(self):
        b = Barril("ouro", CAPACIDADE_BARRIL)
        assert preco_venda(b) == pytest.approx(PRECO_VENDA_BARRIL_CHEIO)

    def test_venda_proporcional_ao_conteudo(self):
        b = Barril("polvora", CAPACIDADE_BARRIL / 2)
        assert preco_venda(b) == pytest.approx(PRECO_VENDA_BARRIL_CHEIO / 2)

    def test_reparo_navio_intacto_zero(self):
        n = Navio("X", 0, 0, 0)
        assert preco_reparo(n) == pytest.approx(0.0)

    def test_reparo_dano_parcial(self):
        n = Navio("X", 0, 0, 0)
        n.partes['casco'] = 50.0  # 50% de dano
        custo = preco_reparo(n)
        assert custo == pytest.approx(50.0 * PRECO_REPARO_POR_PONTO_DANO)


class TestMunicaoCombate:
    def _estado_com_porcao(self, polvora=5.0, bolas=5.0):
        """Cria um Estado com porão controlado e inimigo no arco de estibordo."""
        e = Estado(tipo_navio="facil")
        e.jogador.porao.barris.clear()
        if polvora > 0:
            e.jogador.porao.barris.append(Barril("polvora", polvora))
        if bolas > 0:
            e.jogador.porao.barris.append(Barril("bolas", bolas))
        # heading=0 (norte) → estibordo cobre 20°–160° → inimigo a leste (90°)
        e.jogador.heading = 0.0
        e.jogador.heading_alvo = 0.0
        e.inimigo.x = 200.0  # leste, arco de estibordo, dentro do alcance
        e.inimigo.y = 0.0
        c = e.jogador.canhoes['estibordo'][0]
        c.tripulantes = 1
        c.dist_alvo = 200.0
        return e, c

    def test_sem_municao_canhao_para(self):
        from pirates.core.combat import disparar_canhao_unico
        from collections import deque
        e, c = self._estado_com_porcao(polvora=0.0, bolas=5.0)
        log = deque()
        resultado = disparar_canhao_unico(e.jogador, e.inimigo, c, log)
        assert resultado is False

    def test_sem_municao_loga_uma_vez(self):
        from pirates.core.combat import disparar_canhao_unico
        from collections import deque
        e, c = self._estado_com_porcao(polvora=0.0, bolas=0.0)
        log = deque()
        disparar_canhao_unico(e.jogador, e.inimigo, c, log)
        disparar_canhao_unico(e.jogador, e.inimigo, c, log)
        disparar_canhao_unico(e.jogador, e.inimigo, c, log)
        mensagens_municao = [m for m in log if "municao" in m.lower()]
        assert len(mensagens_municao) == 1

    def test_com_municao_consome_ao_atirar(self):
        """Com munição suficiente, cada disparo bem-sucedido consume 1 pólvora + 1 bola."""
        import random
        from pirates.core.combat import disparar_canhao_unico
        from collections import deque
        random.seed(1)  # seed para garantir acerto/erro determinístico
        e, c = self._estado_com_porcao(polvora=CAPACIDADE_BARRIL, bolas=CAPACIDADE_BARRIL)
        polvora_antes = e.jogador.porao.total("polvora")
        bolas_antes = e.jogador.porao.total("bolas")
        log = deque()
        resultado = disparar_canhao_unico(e.jogador, e.inimigo, c, log)
        assert resultado in ("acerto", "erro")
        assert e.jogador.porao.total("polvora") == pytest.approx(polvora_antes - 1)
        assert e.jogador.porao.total("bolas") == pytest.approx(bolas_antes - 1)


class TestPoraoCombate:
    def test_galeao_tem_mais_capacidade_que_chalupa(self):
        cap_chalupa = NAVIO_TIPOS["facil"]["porao_capacidade"]
        cap_galeao = NAVIO_TIPOS["dificil"]["porao_capacidade"]
        assert cap_galeao > cap_chalupa

    def test_estado_jogador_tem_estoque_inicial(self):
        e = Estado(tipo_navio="normal")
        assert e.jogador.porao.total("polvora") > 0
        assert e.jogador.porao.total("bolas") > 0

    def test_inimigo_tem_porao_gerado(self):
        e = Estado(tipo_navio="normal")
        assert e.inimigo.porao.total("ouro") > 0
