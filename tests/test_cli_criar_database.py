"""``criar --database <id>`` grava em qualquer database, não só no padrão do perfil.

Antes, ``criar`` só conhecia o ``NOTION_DATABASE_ID``/perfil ativo: criar uma
linha noutro database exigia script com chamada direta à API. A flag troca o
destino **só desta chamada** e mantém ``--set``, ``--conteudo``, ``--arquivo`` e
``--dry-run``.
"""

from __future__ import annotations

import json
from typing import Any

from cli import notion_tasks as cli

OUTRO = "38e91f95-497e-818b-ab08-ff19918d6c7c"


class ClienteDeOutroDatabase:
    """Um database genérico ("Ideias") com título, select e texto."""

    def __init__(self) -> None:
        self.criadas: list[tuple[str, dict[str, Any]]] = []
        self.patches: list[tuple[str, dict[str, Any]]] = []
        self.anexos: list[str] = []
        self.paginas: dict[str, dict[str, Any]] = {}

    def get_database(self, database_id: str) -> dict[str, Any]:
        return {
            "id": database_id,
            "properties": {
                "Ideia": {"type": "title", "title": {}},
                "Etapa": {"type": "select", "select": {"options": [{"name": "Ideia"}]}},
                "Notas": {"type": "rich_text", "rich_text": {}},
            },
        }

    def criar_pagina(self, database_id: str, propriedades: dict[str, Any]) -> dict[str, Any]:
        page_id = f"linha-{len(self.criadas) + 1}"
        self.criadas.append((database_id, propriedades))
        titulo = propriedades["Ideia"]["title"][0]["text"]["content"]
        pagina = {
            "id": page_id,
            "url": f"https://notion.so/{page_id}",
            "parent": {"type": "database_id", "database_id": database_id},
            "properties": {
                "Ideia": {"type": "title", "title": [{"plain_text": titulo}]},
                "Etapa": {"type": "select", "select": None},
                "Notas": {"type": "rich_text", "rich_text": []},
            },
        }
        self.paginas[page_id] = pagina
        return pagina

    def obter_pagina(self, page_id: str) -> dict[str, Any]:
        return self.paginas[page_id]

    def atualizar_pagina(self, page_id: str, propriedades: dict[str, Any]) -> dict[str, Any]:
        self.patches.append((page_id, propriedades))
        return {"id": page_id}

    def ler_blocos(self, block_id: str, **_: Any) -> list[dict[str, Any]]:
        return []

    def anexar_blocos(self, block_id: str, blocos: list[dict[str, Any]], **_: Any):
        self.anexos.append(block_id)
        return {"results": [{"id": f"{block_id}-b{i}", **b} for i, b in enumerate(blocos)]}


def _executar(args: list[str], cliente: ClienteDeOutroDatabase) -> tuple[int, Any]:
    def tasklist_padrao():
        raise AssertionError("--database não pode cair no database padrão do perfil")

    return cli.executar(args, tasklist_factory=tasklist_padrao, client_factory=lambda: cliente)


def test_cria_linha_completa_no_database_informado():
    cliente = ClienteDeOutroDatabase()

    codigo, saida = _executar(
        [
            "--json", "criar", "Ideia de artigo", "--database", OUTRO,
            "--set", "Etapa=Ideia", "--conteudo", "## Rascunho",
        ],
        cliente,
    )

    assert codigo == 0, saida
    assert [db for db, _ in cliente.criadas] == [OUTRO]
    assert cliente.patches == [("linha-1", {"Etapa": {"select": {"name": "Ideia"}}})]
    assert cliente.anexos == ["linha-1"]
    assert saida["dados"]["database_id"] == OUTRO
    assert saida["dados"]["id"] == "linha-1"


def test_aceita_link_do_database():
    cliente = ClienteDeOutroDatabase()
    link = f"https://www.notion.so/workspace/{OUTRO.replace('-', '')}?v=abc"

    codigo, saida = _executar(["--json", "criar", "Oi", "--database", link], cliente)

    assert codigo == 0, saida
    assert cliente.criadas[0][0] == OUTRO


def test_dry_run_diz_o_destino_e_nao_cria():
    cliente = ClienteDeOutroDatabase()

    codigo, saida = _executar(
        ["--json", "criar", "Oi", "--database", OUTRO, "--set", "Etapa=Ideia", "--dry-run"],
        cliente,
    )

    assert codigo == 0, saida
    assert saida["dados"]["database_id"] == OUTRO
    assert saida["dados"]["dry_run"] is True
    assert cliente.criadas == []


def test_lote_vai_todo_para_o_database_informado(tmp_path):
    lote = tmp_path / "linhas.json"
    lote.write_text(
        json.dumps([
            {"nome": "Primeira", "propriedades": {"Etapa": "Ideia"}},
            {"nome": "Segunda"},
        ]),
        encoding="utf-8",
    )
    cliente = ClienteDeOutroDatabase()

    codigo, saida = _executar(
        ["--json", "criar", "--arquivo", str(lote), "--database", OUTRO], cliente
    )

    assert codigo == 0, saida
    assert [db for db, _ in cliente.criadas] == [OUTRO, OUTRO]
    assert saida["dados"]["sucessos"] == 2
