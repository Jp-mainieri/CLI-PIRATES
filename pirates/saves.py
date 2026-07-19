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

VERSAO_SAVE = 2
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


def pasta_arena_historico() -> Path:
    p = _raiz() / "arena_historico"
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
        for pasta in (pasta_saves(), pasta_historico(), pasta_arena_historico())
        for p in pasta.glob("*.json")
    }
    if base not in existentes:
        return base
    n = 2
    while f"{base}_{n}" in existentes:
        n += 1
    return f"{base}_{n}"


# ── Serialização ──────────────────────────────────────────────────────────────

def _navio_para_dict(navio) -> dict:
    """Serializa os campos persistentes de um Navio (dano, upgrades, porão)."""
    return {
        "nome": navio.nome,
        "partes": dict(navio.partes),
        "agua": navio.agua,
        "moral_atual": navio.moral_atual,
        "nivel_vela": navio.nivel_vela,
        "alcance_canhao": navio.alcance_canhao,
        "upgrades": dict(navio.upgrades),
        "upgrade_niveis": dict(navio.upgrade_niveis),
        "itens_topo": dict(navio.itens_topo),
        "porao_capacidade": navio.porao.capacidade,
        "porao": [
            {"tipo": b.tipo, "quantidade": b.quantidade}
            for b in navio.porao.barris
        ],
    }


def _aplicar_navio_dict(navio, data: dict) -> None:
    """Aplica de volta a um Navio já construído os campos de _navio_para_dict."""
    from .core.porao import Barril, capacidade_barril_ouro_efetiva
    navio.nome = data["nome"]
    navio.partes.update(data["partes"])
    navio.agua = data["agua"]
    navio.afundado = navio.agua >= 100
    navio.moral_atual = data["moral_atual"]
    navio.nivel_vela = data["nivel_vela"]
    navio.alcance_canhao = data["alcance_canhao"]
    navio.upgrades = dict(data["upgrades"])
    navio.upgrade_niveis = dict(data["upgrade_niveis"])
    navio.itens_topo = dict(data.get("itens_topo", {}))
    navio.porao.capacidade = data.get("porao_capacidade", navio.porao.capacidade)
    # navio.upgrades ja esta setado acima: barris de ouro reconstroem com a
    # capacidade efetiva do upgrade capacidade_barril_ouro, senao ela some no reload.
    navio.porao.barris = [
        Barril(
            tipo=b["tipo"], quantidade=b["quantidade"],
            capacidade=capacidade_barril_ouro_efetiva(navio) if b["tipo"] == "ouro" else 0.0,
        )
        for b in data["porao"]
    ]


def estado_para_dict(
    estado: "Estado",
    estado_mundo: "EstadoMundo",
    *,
    slug: str,
    nome_capitao: str,
    criado_em: str,
) -> dict:
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
            "x": estado_mundo.jogador_x,
            "y": estado_mundo.jogador_y,
            "heading": estado_mundo.jogador_heading,
            "notoriedade": getattr(estado_mundo, "notoriedade", 0),
            "notoriedade_maxima": getattr(estado_mundo, "notoriedade_maximo", 0.0),
            "horas_na_faixa8": getattr(estado_mundo, "horas_na_faixa8", 0.0),
            "portos_visitados": list(getattr(estado_mundo, "portos_visitados", [])),
        },
        "frota": [
            {
                "nome": np_.nome,
                "tipo": np_.tipo,
                "porto_ancorado": np_.porto_ancorado,
                "navio": _navio_para_dict(np_.navio),
            }
            for np_ in estado.frota.navios
        ],
        "frota_indice_ativo": estado.frota.indice_ativo,
        "estatisticas_finais": {
            "causa_morte": None,
            "notoriedade_maxima": getattr(estado_mundo, "notoriedade_maximo", 0.0),
            "navios_afundados": 0,
            "ouro_total_acumulado": 0,
            "duracao_segundos": int(getattr(estado, "tempo", 0)),
            "inimigo_fatal": None,
        },
    }


def restaurar_estado(data: dict, config: dict) -> tuple["Estado", "EstadoMundo"]:
    """Reconstrói Estado e EstadoMundo a partir de um save carregado."""
    from .core.state import Estado, sincronizar_crew_com_navio_ativo
    from .world.state import EstadoMundo
    from .core.frota import Frota, NavioPossuido
    from .core.ship import Navio, criar_canhoes
    from .constants import NAVIO_TIPOS

    tipo_navio_ativo = data["frota"][data["frota_indice_ativo"]]["tipo"]
    seed = data["seed_mundo"]
    prefs = data.get("preferencias", {})

    estado = Estado(
        tipo_navio=tipo_navio_ativo,
        hotkeys=prefs.get("hotkeys_ativo", config.get("hotkeys", True)),
        cores=prefs.get("cores_ativo", config.get("cores", True)),
        graficos_unicode=prefs.get("graficos_unicode", config.get("unicode", True)),
        textura_mar=prefs.get("textura_mar", config.get("textura_mar", True)),
        rastro_ativo=prefs.get("rastro_ativo", config.get("rastro", True)),
    )

    heading = data["capitao"]["heading"]

    frota = Frota()
    for entry in data["frota"]:
        tipo_n = entry.get("tipo", tipo_navio_ativo)
        p = NAVIO_TIPOS.get(tipo_n, NAVIO_TIPOS[tipo_navio_ativo])
        navio_n = Navio(
            entry["navio"]["nome"], x=0.0, y=0.0, heading=heading,
            velocidade_max_base=p["velocidade_max_base"],
            giro_graus_seg=p["giro_graus_seg"],
            reparo_mult=p["reparo_mult"],
            porao_capacidade=p["porao_capacidade"],
        )
        navio_n.tipo_nome = p["navio"]
        navio_n.num_velas = p["num_velas"]
        navio_n.canhoes = criar_canhoes(p["canhoes_lado"])
        _aplicar_navio_dict(navio_n, entry["navio"])
        frota.navios.append(NavioPossuido(
            nome=entry["nome"], navio=navio_n, tipo=tipo_n,
            porto_ancorado=entry.get("porto_ancorado"),
        ))
    frota.indice_ativo = data["frota_indice_ativo"]
    estado.frota = frota
    ativo = frota.ativo()
    estado.jogador = ativo.navio
    estado.jogador.heading = heading
    estado.jogador.heading_alvo = heading

    sincronizar_crew_com_navio_ativo(estado, ativo.tipo)

    estado_mundo = EstadoMundo(tipo_navio_ativo, seed=seed)
    cap = data["capitao"]
    estado_mundo.jogador_x = cap["x"]
    estado_mundo.jogador_y = cap["y"]
    estado_mundo.jogador_heading = cap["heading"]
    estado_mundo.jogador_heading_alvo = cap["heading"]
    estado_mundo.notoriedade = cap.get("notoriedade", 0)
    estado_mundo.notoriedade_maximo = cap.get("notoriedade_maxima", estado_mundo.notoriedade)
    estado_mundo.horas_na_faixa8 = cap.get("horas_na_faixa8", 0.0)
    estado_mundo.portos_visitados = list(cap.get("portos_visitados", []))

    # O lote de inimigos sorteado no __init__ do EstadoMundo respeitou o
    # espaçamento mínimo em relação à posição padrão de spawn (centro do
    # mapa), não a posição real salva do capitão (só definida acima) — sem
    # re-sortear aqui, inimigos podem aparecer bem mais perto do jogador
    # do que MUNDO_ESPACAMENTO_MIN permite, disparando combate imediato.
    estado_mundo.sortear_novo_lote()

    return estado, estado_mundo


# ── I/O ───────────────────────────────────────────────────────────────────────

def _escrever_atomico(path: Path, data: dict) -> None:
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    tmp.replace(path)


def criar_novo_save(nome: str, tipo_navio: str) -> tuple[str, int]:
    """Cria save inicial e retorna (slug, seed_mundo)."""
    from .constants import NAVIO_TIPOS
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
            "x": 4000.0,
            "y": 4000.0,
            "heading": 0.0,
            "notoriedade": 0,
            "notoriedade_maxima": 0.0,
            "horas_na_faixa8": 0.0,
            "portos_visitados": [],
        },
        "frota": [
            {
                "nome": "Seu Navio",
                "tipo": tipo_navio,
                "porto_ancorado": None,
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
                    "porao_capacidade": NAVIO_TIPOS[tipo_navio]["porao_capacidade"],
                    "porao": [],
                },
            },
        ],
        "frota_indice_ativo": 0,
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


def _tipo_navio_ativo(d: dict) -> str:
    """Tipo do navio ATIVO da frota (não o tipo original do capitão, que
    não existe mais como campo solto — ver frota[frota_indice_ativo])."""
    frota = d.get("frota", [])
    idx = d.get("frota_indice_ativo", 0)
    if 0 <= idx < len(frota):
        return frota[idx].get("tipo", "?")
    return "?"


def listar_saves_ativos() -> list[dict]:
    saves = []
    for p in sorted(pasta_saves().glob("*.json"), key=lambda f: f.stat().st_mtime, reverse=True):
        try:
            d = json.loads(p.read_text(encoding="utf-8"))
            saves.append({
                "slug": d.get("slug", p.stem),
                "nome_capitao": d.get("nome_capitao", p.stem),
                "tipo_navio": _tipo_navio_ativo(d),
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


def melhor_faixa_notoriedade_alcancada() -> int:
    """Maior faixa (0-7) de notoriedade já alcançada em QUALQUER capitão,
    ativo (saves/) ou falecido (historico/) — usada pro desbloqueio de
    navios na criação de um mundo aberto novo."""
    from .core.notoriedade import faixa_index

    melhor = 0.0
    for pasta in (pasta_saves(), pasta_historico()):
        for p in pasta.glob("*.json"):
            try:
                d = json.loads(p.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError):
                continue
            melhor = max(melhor, d.get("capitao", {}).get("notoriedade_maxima", 0.0))
    return faixa_index(melhor)


def melhor_vitorias_arena() -> int:
    """Maior número de rodadas vencidas numa única campanha de Arena já
    finalizada — usada pro desbloqueio de navios ao iniciar uma campanha
    de Arena nova."""
    melhor = 0
    for p in pasta_arena_historico().glob("*.json"):
        try:
            d = json.loads(p.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            continue
        melhor = max(melhor, d.get("rodadas_vencidas", 0))
    return melhor


def mover_para_historico(slug: str, estatisticas: dict) -> None:
    path = pasta_saves() / f"{slug}.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    data["estatisticas_finais"].update(estatisticas)
    data["atualizado_em"] = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S")
    dest = pasta_historico() / f"{slug}.json"
    _escrever_atomico(path, data)
    shutil.move(str(path), str(dest))


# ── Histórico de campanhas de Arena ─────────────────────────────────────────

def salvar_resultado_arena(
    nome_capitao: str,
    tipo_navio: str,
    rodadas_vencidas: int,
    causa_fim: str | None,
    duracao_segundos: int,
) -> None:
    """Grava o resultado de uma campanha de Arena finalizada.

    Diferente dos saves de capitão do mundo aberto, a Arena não tem fase de
    "save ativo"/"continuar" — cada campanha só é gravada quando termina.
    """
    slug = gerar_slug_unico(nome_capitao)
    agora = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S")
    data = {
        "nome_capitao": nome_capitao,
        "tipo_navio": tipo_navio,
        "rodadas_vencidas": rodadas_vencidas,
        "causa_fim": causa_fim,
        "duracao_segundos": duracao_segundos,
        "finalizado_em": agora,
    }
    _escrever_atomico(pasta_arena_historico() / f"{slug}.json", data)


def listar_arena_historico() -> list[dict]:
    hist = []
    for p in sorted(pasta_arena_historico().glob("*.json"), key=lambda f: f.stat().st_mtime, reverse=True):
        try:
            d = json.loads(p.read_text(encoding="utf-8"))
            hist.append({
                "nome_capitao": d.get("nome_capitao", p.stem),
                "tipo_navio": d.get("tipo_navio", "?"),
                "rodadas_vencidas": d.get("rodadas_vencidas", 0),
                "causa_fim": d.get("causa_fim"),
                "duracao_segundos": d.get("duracao_segundos", 0),
                "finalizado_em": d.get("finalizado_em", ""),
            })
        except (json.JSONDecodeError, KeyError):
            continue
    return hist
