"""``inventario`` → ``baixar-corpos`` → ``buscar-conteudo``, de ponta a ponta.

Os serviços (``inventario_workspace``, ``corpos``, ``busca_conteudo``) são
testados no ``notion-starter``; aqui a borda: argumentos, arquivos gerados,
progresso no stderr com stdout em JSON, e a recusa amigável quando o starter
instalado ainda não tem os serviços.
"""

from __future__ import annotations

import importlib
import importlib.util
import json
from typing import Any

import pytest

from cli import notion_tasks as cli

DB = "30296e2d-cd39-4cf3-8bbd-3fb2f53c0195"

precisa_do_servico = pytest.mark.skipif(
    importlib.util.find_spec("notion_starter.services.busca_conteudo") is None,
    reason="notion-starter instalado ainda sem os serviços do acervo",
)


def _pagina(pid: str, titulo: str, parent: dict[str, Any], criado: str) -> dict[str, Any]:
    return {
        "object": "page",
        "id": pid,
        "url": f"https://notion.so/{pid}",
        "created_time": criado,
        "last_edited_time": criado,
        "parent": parent,
        "properties": {"Nome": {"type": "title", "title": [{"plain_text": titulo}]}},
    }


class ClienteAcervo:
    corpos = {
        "p1": "Pensei numa publicação sobre agentes.",
        "p2": "Lista de compras.",
        "l1": "Rascunho: artigo sobre Notion e IA.",
    }

    def buscar(self, query=None, page_size=100, buscar_todos=False, filtro=None):
        return [
            _pagina("p1", "Diário", {"type": "workspace", "workspace": True},
                    "2026-02-01T00:00:00.000Z"),
            _pagina("p2", "Mercado", {"type": "page_id", "page_id": "p1"},
                    "2026-01-01T00:00:00.000Z"),
            {"object": "database", "id": DB, "title": [{"plain_text": "Ideias"}],
             "created_time": "2026-01-01T00:00:00.000Z", "last_edited_time": None,
             "parent": {"type": "page_id", "page_id": "p1"}},
            _pagina("l1", "Linha", {"type": "database_id", "database_id": DB},
                    "2026-03-01T00:00:00.000Z"),
        ]

    def ler_blocos(self, block_id: str, buscar_todos: bool = False, recursivo: bool = False):
        texto = self.corpos[block_id]
        return [{"type": "paragraph", "has_children": False,
                 "paragraph": {"rich_text": [{"type": "text", "plain_text": texto,
                                              "text": {"content": texto}}]}}]


def _executar(args: list[str]) -> tuple[int, Any]:
    cliente = ClienteAcervo()
    return cli.executar(args, tasklist_factory=lambda: None, client_factory=lambda: cliente)


@precisa_do_servico
def test_fluxo_inventario_corpos_busca(tmp_path, capsys):
    inventario = tmp_path / "inventario.json"
    corpos = tmp_path / "corpos"

    codigo, saida = _executar(["--json", "inventario", "--saida", str(inventario)])
    assert codigo == 0, saida
    assert (saida["dados"]["total"], saida["dados"]["paginas"]) == (4, 3)
    itens = json.loads(inventario.read_text(encoding="utf-8"))["itens"]
    linha = next(i for i in itens if i["id"] == "l1")
    assert linha["caminho"] == ["Diário", "Ideias"]
    assert linha["criado_em"] == "2026-03-01T00:00:00.000Z"

    codigo, saida = _executar([
        "--json", "baixar-corpos", str(inventario), "--destino", str(corpos),
        "--ignorar-caminho", "Diário / Mercado", "--progresso-a-cada", "1",
    ])
    assert codigo == 0, saida
    assert (saida["dados"]["baixados"], saida["dados"]["selecionadas"]) == (2, 2)
    assert "[baixar-corpos] 2/2" in capsys.readouterr().err
    assert sorted(a.name for a in corpos.glob("*.md")) == ["l1.md", "p1.md"]

    codigo, saida = _executar(["--json", "buscar-conteudo", str(corpos), "publicacao|artigo"])
    assert codigo == 0, saida
    ocorrencias = saida["dados"]["ocorrencias"]
    assert [o["id"] for o in ocorrencias] == ["p1", "l1"]
    assert ocorrencias[0]["trechos"] == ["Pensei numa publicação sobre agentes."]
    assert ocorrencias[1]["caminho"] == "Diário / Ideias"


@precisa_do_servico
def test_baixar_de_novo_pula_o_que_ja_existe(tmp_path):
    inventario = tmp_path / "inventario.json"
    _executar(["--json", "inventario", "--saida", str(inventario)])
    destino = str(tmp_path / "corpos")
    _executar(["--json", "baixar-corpos", str(inventario), "--destino", destino, "--limite", "1"])

    codigo, saida = _executar([
        "--json", "baixar-corpos", str(inventario), "--destino", destino,
        "--somente-database", DB,
    ])

    assert codigo == 0
    assert saida["dados"]["selecionadas"] == 1


@precisa_do_servico
def test_saida_humana_da_busca(tmp_path):
    inventario = tmp_path / "inventario.json"
    corpos = str(tmp_path / "corpos")
    _executar(["--json", "inventario", "--saida", str(inventario)])
    _executar(["--json", "baixar-corpos", str(inventario), "--destino", corpos])

    codigo, saida = _executar(["buscar-conteudo", corpos, "artigo"])

    assert codigo == 0
    assert saida.startswith("1 página(s) com 'artigo'")
    assert "Diário / Ideias / Linha" in saida


@precisa_do_servico
def test_erros_viram_validacao(tmp_path):
    ruim = tmp_path / "ruim.json"
    ruim.write_text("{}", encoding="utf-8")

    codigo, saida = _executar(["--json", "baixar-corpos", str(ruim), "--destino", str(tmp_path)])
    assert (codigo, saida["erro"]["codigo"]) == (2, "validacao")

    codigo, saida = _executar(["--json", "buscar-conteudo", str(tmp_path), "(aberto"])
    assert (codigo, saida["erro"]["codigo"]) == (2, "validacao")

    inventario = tmp_path / "inventario.json"
    _executar(["--json", "inventario", "--saida", str(inventario)])
    codigo, saida = _executar([
        "--json", "baixar-corpos", str(inventario), "--destino", str(tmp_path / "c"),
        "--priorizar", "(",
    ])
    assert (codigo, saida["erro"]["codigo"]) == (2, "validacao")


@pytest.mark.parametrize("comando", ["inventario", "baixar-corpos", "buscar-conteudo"])
def test_starter_sem_os_servicos_recusa_com_configuracao(monkeypatch, tmp_path, comando):
    original = importlib.import_module

    def sem_servicos(nome: str, *args: Any, **kwargs: Any):
        if nome.split(".")[-1] in {"inventario_workspace", "corpos", "busca_conteudo"}:
            raise ImportError(nome)
        return original(nome, *args, **kwargs)

    monkeypatch.setattr(cli.importlib, "import_module", sem_servicos)
    argumentos = {
        "inventario": ["--saida", str(tmp_path / "i.json")],
        "baixar-corpos": [str(tmp_path / "i.json"), "--destino", str(tmp_path)],
        "buscar-conteudo": [str(tmp_path), "x"],
    }[comando]

    codigo, saida = _executar(["--json", comando, *argumentos])

    assert (codigo, saida["erro"]["codigo"]) == (2, "configuracao")
