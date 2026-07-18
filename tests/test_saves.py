"""test_saves.py – Testes unitários do sistema de save/load."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

import pirates.saves as saves_mod
from pirates.saves import (
    gerar_slug,
    gerar_slug_unico,
    criar_novo_save,
    salvar,
    carregar,
    listar_saves_ativos,
    listar_historico,
    mover_para_historico,
    salvar_resultado_arena,
    listar_arena_historico,
    VERSAO_SAVE,
)


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture(autouse=True)
def pastas_tmp(monkeypatch, tmp_path):
    """Redireciona pasta_saves()/pasta_historico()/pasta_arena_historico() para tmp_path."""
    saves_dir = tmp_path / "saves"
    hist_dir = tmp_path / "historico"
    arena_hist_dir = tmp_path / "arena_historico"
    saves_dir.mkdir()
    hist_dir.mkdir()
    arena_hist_dir.mkdir()
    monkeypatch.setattr(saves_mod, "pasta_saves", lambda: saves_dir)
    monkeypatch.setattr(saves_mod, "pasta_historico", lambda: hist_dir)
    monkeypatch.setattr(saves_mod, "pasta_arena_historico", lambda: arena_hist_dir)
    return tmp_path


def _estado_mundo_fake(tipo_navio: str = "normal", seed: int = 42):
    """Cria um EstadoMundo mínimo para testes (sem curses)."""
    from pirates.world.state import EstadoMundo
    return EstadoMundo(tipo_navio, seed=seed)


def _estado_fake(tipo_navio: str = "normal"):
    """Cria um Estado mínimo para testes."""
    from pirates.core.state import Estado
    return Estado(tipo_navio=tipo_navio)


# ── Slug ──────────────────────────────────────────────────────────────────────

def test_slug_normalizacao():
    assert gerar_slug("João Barba Negra") == "joao_barba_negra"


def test_slug_espacos_multiplos():
    assert gerar_slug("  Anne   Bonny  ") == "anne_bonny"


def test_slug_caracteres_especiais():
    slug = gerar_slug("Çapitão O'Malley!")
    assert all(c in "abcdefghijklmnopqrstuvwxyz0123456789_" for c in slug)


def test_slug_vazio_retorna_fallback():
    assert gerar_slug("!!!") == "capitao"


# ── Slug único ────────────────────────────────────────────────────────────────

def test_slug_unico_sem_colisao():
    slug = gerar_slug_unico("Calico Jack")
    assert slug == "calico_jack"


def test_slug_unico_com_colisao(pastas_tmp):
    saves_dir = saves_mod.pasta_saves()
    (saves_dir / "calico_jack.json").write_text("{}")
    slug = gerar_slug_unico("Calico Jack")
    assert slug == "calico_jack_2"


def test_slug_unico_colisao_multipla(pastas_tmp):
    saves_dir = saves_mod.pasta_saves()
    (saves_dir / "joao.json").write_text("{}")
    (saves_dir / "joao_2.json").write_text("{}")
    slug = gerar_slug_unico("João")
    assert slug == "joao_3"


def test_slug_unico_evita_historico(pastas_tmp):
    hist_dir = saves_mod.pasta_historico()
    (hist_dir / "anne.json").write_text("{}")
    slug = gerar_slug_unico("Anne")
    assert slug == "anne_2"


# ── criar_novo_save ───────────────────────────────────────────────────────────

def test_criar_novo_save_cria_arquivo():
    slug, seed = criar_novo_save("Barbanegra", "normal")
    path = saves_mod.pasta_saves() / f"{slug}.json"
    assert path.exists()


def test_criar_novo_save_versao_presente():
    slug, _ = criar_novo_save("Barbanegra", "normal")
    data = json.loads((saves_mod.pasta_saves() / f"{slug}.json").read_text())
    assert data["versao_save"] == VERSAO_SAVE


def test_criar_novo_save_retorna_seed():
    slug, seed = criar_novo_save("Barbanegra", "normal")
    data = json.loads((saves_mod.pasta_saves() / f"{slug}.json").read_text())
    assert data["seed_mundo"] == seed
    assert isinstance(seed, int)


def test_criar_dois_capitaes_mesmo_nome():
    slug1, _ = criar_novo_save("Barbanegra", "normal")
    slug2, _ = criar_novo_save("Barbanegra", "normal")
    assert slug1 != slug2
    assert slug2.endswith("_2")


# ── salvar / carregar roundtrip ───────────────────────────────────────────────

def test_roundtrip_posicao():
    slug, seed = criar_novo_save("Anne", "normal")
    estado = _estado_fake("normal")
    estado_mundo = _estado_mundo_fake("normal", seed)
    estado_mundo.jogador_x = 1234.5
    estado_mundo.jogador_y = 6789.0
    estado_mundo.jogador_heading = 90.0

    salvar(estado, estado_mundo, slug)
    data = carregar(slug)

    assert data["capitao"]["x"] == pytest.approx(1234.5)
    assert data["capitao"]["y"] == pytest.approx(6789.0)
    assert data["capitao"]["heading"] == pytest.approx(90.0)


def test_roundtrip_porao():
    from pirates.core.porao import Barril
    slug, seed = criar_novo_save("Anne", "facil")
    estado = _estado_fake("facil")
    estado_mundo = _estado_mundo_fake("facil", seed)
    estado.jogador.porao.barris = [Barril("polvora", 10.0), Barril("ouro", 50.0)]

    salvar(estado, estado_mundo, slug)
    data = carregar(slug)

    porao = data["navio"]["porao"]
    assert len(porao) == 2
    assert porao[0] == {"tipo": "polvora", "quantidade": 10.0}
    assert porao[1] == {"tipo": "ouro", "quantidade": 50.0}


def test_roundtrip_partes_navio():
    slug, seed = criar_novo_save("Jack", "dificil")
    estado = _estado_fake("dificil")
    estado_mundo = _estado_mundo_fake("dificil", seed)
    estado.jogador.partes["casco"] = 42.0
    estado.jogador.partes["mastro"] = 77.5

    salvar(estado, estado_mundo, slug)
    data = carregar(slug)

    assert data["navio"]["partes"]["casco"] == pytest.approx(42.0)
    assert data["navio"]["partes"]["mastro"] == pytest.approx(77.5)


def test_roundtrip_nome_capitao_preservado():
    slug, seed = criar_novo_save("Calico Jack", "normal")
    estado = _estado_fake("normal")
    estado_mundo = _estado_mundo_fake("normal", seed)

    salvar(estado, estado_mundo, slug)
    data = carregar(slug)

    assert data["nome_capitao"] == "Calico Jack"


def test_roundtrip_criado_em_preservado():
    slug, seed = criar_novo_save("Rackham", "normal")
    data_inicial = json.loads((saves_mod.pasta_saves() / f"{slug}.json").read_text())
    criado_em = data_inicial["criado_em"]

    estado = _estado_fake("normal")
    estado_mundo = _estado_mundo_fake("normal", seed)
    salvar(estado, estado_mundo, slug)

    data = carregar(slug)
    assert data["criado_em"] == criado_em


# ── restaurar_estado ──────────────────────────────────────────────────────────

def test_restaurar_posicao():
    from pirates.saves import restaurar_estado
    slug, seed = criar_novo_save("Anne", "normal")
    estado = _estado_fake("normal")
    estado_mundo = _estado_mundo_fake("normal", seed)
    estado_mundo.jogador_x = 999.0
    estado_mundo.jogador_y = 888.0
    salvar(estado, estado_mundo, slug)

    data = carregar(slug)
    config = {"hotkeys": True, "cores": True, "unicode": True, "textura_mar": True, "rastro": True}
    _e, em = restaurar_estado(data, config)

    assert em.jogador_x == pytest.approx(999.0)
    assert em.jogador_y == pytest.approx(888.0)


def test_restaurar_seed_deterministica():
    from pirates.saves import restaurar_estado
    slug, seed = criar_novo_save("Porto", "normal")
    estado = _estado_fake("normal")
    em1 = _estado_mundo_fake("normal", seed)
    salvar(estado, em1, slug)

    data = carregar(slug)
    config = {"hotkeys": True, "cores": True, "unicode": True, "textura_mar": True, "rastro": True}
    _, em2 = restaurar_estado(data, config)

    # Mesma seed → mesmos portos
    assert len(em1.portos) == len(em2.portos)
    for p1, p2 in zip(em1.portos, em2.portos):
        assert p1.x == pytest.approx(p2.x)
        assert p1.y == pytest.approx(p2.y)


# ── mover_para_historico ──────────────────────────────────────────────────────

def test_mover_para_historico_arquivo_migra():
    slug, _ = criar_novo_save("Morto", "facil")
    assert (saves_mod.pasta_saves() / f"{slug}.json").exists()

    mover_para_historico(slug, {"causa_morte": "afundado"})

    assert not (saves_mod.pasta_saves() / f"{slug}.json").exists()
    assert (saves_mod.pasta_historico() / f"{slug}.json").exists()


def test_mover_para_historico_estatisticas_preenchidas():
    slug, _ = criar_novo_save("Morto", "facil")
    mover_para_historico(slug, {"causa_morte": "abordagem", "navios_afundados": 3})

    data = json.loads((saves_mod.pasta_historico() / f"{slug}.json").read_text())
    assert data["estatisticas_finais"]["causa_morte"] == "abordagem"
    assert data["estatisticas_finais"]["navios_afundados"] == 3


# ── versão desconhecida ───────────────────────────────────────────────────────

def test_versao_desconhecida_nao_quebra(caplog):
    import logging
    slug, _ = criar_novo_save("Velho", "normal")
    path = saves_mod.pasta_saves() / f"{slug}.json"
    data = json.loads(path.read_text())
    data["versao_save"] = 99
    path.write_text(json.dumps(data))

    with caplog.at_level(logging.WARNING, logger="pirates.saves"):
        resultado = carregar(slug)

    assert resultado["versao_save"] == 99  # não lança; só avisa
    assert any("99" in r.message for r in caplog.records)


# ── listar saves / histórico ──────────────────────────────────────────────────

def test_listar_saves_ativos():
    criar_novo_save("Alpha", "normal")
    criar_novo_save("Beta", "facil")
    saves = listar_saves_ativos()
    nomes = {s["nome_capitao"] for s in saves}
    assert "Alpha" in nomes
    assert "Beta" in nomes


def test_listar_historico():
    slug, _ = criar_novo_save("Finado", "dificil")
    mover_para_historico(slug, {"causa_morte": "tempestade"})
    hist = listar_historico()
    assert any(h["nome_capitao"] == "Finado" for h in hist)


# ── histórico de Arena ──────────────────────────────────────────────────────

def test_arena_historico_vazio_por_padrao():
    assert listar_arena_historico() == []


def test_salvar_resultado_arena_cria_arquivo():
    salvar_resultado_arena("Barbanegra", "normal", 3, "derrota", 842)
    arquivos = list(saves_mod.pasta_arena_historico().glob("*.json"))
    assert len(arquivos) == 1


def test_salvar_resultado_arena_campos_preenchidos():
    salvar_resultado_arena("Barbanegra", "dificil", 5, "fuga_jogador", 1200)
    hist = listar_arena_historico()
    assert len(hist) == 1
    entrada = hist[0]
    assert entrada["nome_capitao"] == "Barbanegra"
    assert entrada["tipo_navio"] == "dificil"
    assert entrada["rodadas_vencidas"] == 5
    assert entrada["causa_fim"] == "fuga_jogador"
    assert entrada["duracao_segundos"] == 1200


def test_salvar_multiplas_campanhas_mesmo_nome_nao_colidem():
    salvar_resultado_arena("Anne", "facil", 1, "derrota", 100)
    salvar_resultado_arena("Anne", "facil", 2, "derrota", 200)
    hist = listar_arena_historico()
    assert len(hist) == 2


def test_gerar_slug_unico_evita_arena_historico():
    salvar_resultado_arena("Rackham", "normal", 0, "derrota", 10)
    slug = gerar_slug_unico("Rackham")
    assert slug == "rackham_2"
