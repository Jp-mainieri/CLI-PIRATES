"""saves.py – Sistema de save/load de capitães do mundo aberto."""

from __future__ import annotations

import json
import logging
import random
import re
import shutil
import unicodedata
from datetime import datetime, timezone
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .core.state import Estado
    from .world.state import EstadoMundo

VERSAO_SAVE = 1
_logger = logging.getLogger(__name__)


# ── Pastas ────────────────────────────────────────────────────────────────────

def _raiz() -> Path:
    return Path(__file__).parent.parent


def pasta_saves() -> Path:
    p = _raiz() / "saves"
    p.mkdir(exist_ok=True)
    return p


def pasta_historico() -> Path:
    p = _raiz() / "historico"
    p.mkdir(exist_ok=True)
    return p


# ── Slug ──────────────────────────────────────────────────────────────────────

def gerar_slug(nome: str) -> str:
    """'João Barba Negra' → 'joao_barba_negra'."""
    sem_acento = "".join(
        c for c in unicodedata.normalize("NFD", nome)
        if unicodedata.category(c) != "Mn"
    )
    slug = re.sub(r"\s+", "_", sem_acento.lower())
    slug = re.sub(r"[^a-z0-9_]", "", slug).strip("_")
    return slug or "capitao"


def gerar_slug_unico(nome: str) -> str:
    base = gerar_slug(nome)
    existentes = {
        p.stem
        for pasta in (pasta_saves(), pasta_historico())
        for p in pasta.glob("*.json")
    }
    if base not in existentes:
        return base
    n = 2
    while f"{base}_{n}" in existentes:
        n += 1
    return f"{base}_{n}"


# ── Serialização ──────────────────────────────────────────────────────────────

def estado_para_dict(
    estado: "Estado",
    estado_mundo: "EstadoMundo",
    *,
    slug: str,
    nome_capitao: str,
    criado_em: str,
) -> dict:
    navio = estado.jogador
    return {
        "versao_save": VERSAO_SAVE,
        "slug": slug,
        "nome_capitao": nome_capitao,
        "seed_mundo": estado_mundo.seed_mundo,
        "criado_em": criado_em,
        "atualizado_em": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S"),
        "preferencias": {
            "cores_ativo": estado.cores_ativo,
            "hotkeys_ativo": estado.hotkeys_ativo,
            "graficos_unicode": estado.graficos_unicode,
            "textura_mar": estado.textura_mar,
            "rastro_ativo": estado.rastro_ativo,
        },
        "capitao": {
            "tipo_navio": estado_mundo.tipo_navio,
            "x": estado_mundo.jogador_x,
            "y": estado_mundo.jogador_y,
            "heading": estado_mundo.jogador_heading,
            "notoriedade": getattr(estado_mundo, "notoriedade", 0),
            "horas_na_faixa8": getattr(estado_mundo, "horas_na_faixa8", 0.0),
            "portos_visitados": list(getattr(estado_mundo, "portos_visitados", [])),
        },
        "navio": {
            "nome": navio.nome,
            "partes": dict(navio.partes),
            "agua": navio.agua,
            "moral_atual": navio.moral_atual,
            "nivel_vela": navio.nivel_vela,
            "alcance_canhao": navio.alcance_canhao,
            "upgrades": dict(navio.upgrades),
            "upgrade_niveis": dict(navio.upgrade_niveis),
            "itens_topo": dict(navio.itens_topo),
            "porao": [
                {"tipo": b.tipo, "quantidade": b.quantidade}
                for b in navio.porao.barris
            ],
        },
        "estatisticas_finais": {
            "causa_morte": None,
            "notoriedade_maxima": getattr(estado_mundo, "notoriedade", 0),
            "navios_afundados": 0,
            "ouro_total_acumulado": 0,
            "duracao_segundos": int(getattr(estado, "tempo", 0)),
            "inimigo_fatal": None,
        },
    }


def restaurar_estado(data: dict, config: dict) -> tuple["Estado", "EstadoMundo"]:
    """Reconstrói Estado e EstadoMundo a partir de um save carregado."""
    from .core.state import Estado
    from .world.state import EstadoMundo
    from .core.porao import Barril

    tipo_navio = data["capitao"]["tipo_navio"]
    seed = data["seed_mundo"]
    prefs = data.get("preferencias", {})

    estado = Estado(
        tipo_navio=tipo_navio,
        hotkeys=prefs.get("hotkeys_ativo", config.get("hotkeys", True)),
        cores=prefs.get("cores_ativo", config.get("cores", True)),
        graficos_unicode=prefs.get("graficos_unicode", config.get("unicode", True)),
        textura_mar=prefs.get("textura_mar", config.get("textura_mar", True)),
        rastro_ativo=prefs.get("rastro_ativo", config.get("rastro", True)),
    )

    navio_data = data["navio"]
    estado.jogador.nome = navio_data["nome"]
    estado.jogador.partes.update(navio_data["partes"])
    estado.jogador.agua = navio_data["agua"]
    estado.jogador.moral_atual = navio_data["moral_atual"]
    estado.jogador.nivel_vela = navio_data["nivel_vela"]
    estado.jogador.alcance_canhao = navio_data["alcance_canhao"]
    estado.jogador.upgrades = dict(navio_data["upgrades"])
    estado.jogador.upgrade_niveis = dict(navio_data["upgrade_niveis"])
    estado.jogador.itens_topo = dict(navio_data.get("itens_topo", {}))
    estado.jogador.porao.barris = [
        Barril(tipo=b["tipo"], quantidade=b["quantidade"])
        for b in navio_data["porao"]
    ]

    heading = data["capitao"]["heading"]
    estado.jogador.heading = heading
    estado.jogador.heading_alvo = heading

    estado_mundo = EstadoMundo(tipo_navio, seed=seed)
    cap = data["capitao"]
    estado_mundo.jogador_x = cap["x"]
    estado_mundo.jogador_y = cap["y"]
    estado_mundo.jogador_heading = cap["heading"]
    estado_mundo.jogador_heading_alvo = cap["heading"]
    estado_mundo.notoriedade = cap.get("notoriedade", 0)
    estado_mundo.horas_na_faixa8 = cap.get("horas_na_faixa8", 0.0)
    estado_mundo.portos_visitados = list(cap.get("portos_visitados", []))

    return estado, estado_mundo


# ── I/O ───────────────────────────────────────────────────────────────────────

def _escrever_atomico(path: Path, data: dict) -> None:
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    tmp.replace(path)


def criar_novo_save(nome: str, tipo_navio: str) -> tuple[str, int]:
    """Cria save inicial e retorna (slug, seed_mundo)."""
    slug = gerar_slug_unico(nome)
    seed = random.randint(0, 2**31 - 1)
    agora = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S")
    data = {
        "versao_save": VERSAO_SAVE,
        "slug": slug,
        "nome_capitao": nome,
        "seed_mundo": seed,
        "criado_em": agora,
        "atualizado_em": agora,
        "preferencias": {
            "cores_ativo": True,
            "hotkeys_ativo": True,
            "graficos_unicode": True,
            "textura_mar": True,
            "rastro_ativo": True,
        },
        "capitao": {
            "tipo_navio": tipo_navio,
            "x": 4000.0,
            "y": 4000.0,
            "heading": 0.0,
            "notoriedade": 0,
            "horas_na_faixa8": 0.0,
            "portos_visitados": [],
        },
        "navio": {
            "nome": "Seu Navio",
            "partes": {"casco": 100.0, "mastro": 100.0, "vela": 100.0, "roda": 100.0},
            "agua": 0.0,
            "moral_atual": 100.0,
            "nivel_vela": 1,
            "alcance_canhao": 550.0,
            "upgrades": {},
            "upgrade_niveis": {},
            "itens_topo": {},
            "porao": [],
        },
        "estatisticas_finais": {
            "causa_morte": None,
            "notoriedade_maxima": 0,
            "navios_afundados": 0,
            "ouro_total_acumulado": 0,
            "duracao_segundos": 0,
            "inimigo_fatal": None,
        },
    }
    _escrever_atomico(pasta_saves() / f"{slug}.json", data)
    return slug, seed


def salvar(estado: "Estado", estado_mundo: "EstadoMundo", slug: str) -> None:
    path = pasta_saves() / f"{slug}.json"
    try:
        existing = json.loads(path.read_text(encoding="utf-8"))
        nome_capitao = existing.get("nome_capitao", slug)
        criado_em = existing.get("criado_em", datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S"))
    except (FileNotFoundError, json.JSONDecodeError):
        nome_capitao = slug
        criado_em = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S")

    data = estado_para_dict(
        estado, estado_mundo,
        slug=slug,
        nome_capitao=nome_capitao,
        criado_em=criado_em,
    )
    _escrever_atomico(path, data)


def carregar(slug: str) -> dict:
    path = pasta_saves() / f"{slug}.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    v = data.get("versao_save", 0)
    if v != VERSAO_SAVE:
        _logger.warning("Save '%s' tem versao_save=%s (esperado %s).", slug, v, VERSAO_SAVE)
    return data


def listar_saves_ativos() -> list[dict]:
    saves = []
    for p in sorted(pasta_saves().glob("*.json"), key=lambda f: f.stat().st_mtime, reverse=True):
        try:
            d = json.loads(p.read_text(encoding="utf-8"))
            saves.append({
                "slug": d.get("slug", p.stem),
                "nome_capitao": d.get("nome_capitao", p.stem),
                "tipo_navio": d.get("capitao", {}).get("tipo_navio", "?"),
                "atualizado_em": d.get("atualizado_em", ""),
            })
        except (json.JSONDecodeError, KeyError):
            continue
    return saves


def listar_historico() -> list[dict]:
    hist = []
    for p in sorted(pasta_historico().glob("*.json"), key=lambda f: f.stat().st_mtime, reverse=True):
        try:
            d = json.loads(p.read_text(encoding="utf-8"))
            ef = d.get("estatisticas_finais", {})
            hist.append({
                "slug": d.get("slug", p.stem),
                "nome_capitao": d.get("nome_capitao", p.stem),
                "causa_morte": ef.get("causa_morte"),
                "notoriedade_maxima": ef.get("notoriedade_maxima", 0),
                "duracao_segundos": ef.get("duracao_segundos", 0),
                "atualizado_em": d.get("atualizado_em", ""),
            })
        except (json.JSONDecodeError, KeyError):
            continue
    return hist


def mover_para_historico(slug: str, estatisticas: dict) -> None:
    path = pasta_saves() / f"{slug}.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    data["estatisticas_finais"].update(estatisticas)
    data["atualizado_em"] = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S")
    dest = pasta_historico() / f"{slug}.json"
    _escrever_atomico(path, data)
    shutil.move(str(path), str(dest))
