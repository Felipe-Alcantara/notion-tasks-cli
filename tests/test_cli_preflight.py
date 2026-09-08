"""Testes de integração da proteção URL GitHub -> Projeto na CLI."""

from __future__ import annotations

import json
from copy import deepcopy
from unittest import mock

from notion_starter import Tarefa

from cli import notion_tasks as cli

DATABASE_TAREFAS = "db-tarefas"
DATABASE_GITHUB = "db-github"
PROJETO_ID = "projeto-canonico"
URL_REPO = "https://github.com/Felipe/repo"


def _schema_tarefas() -> dict:
    return {
        "id": DATABASE_TAREFAS,
        "properties": {
            "Tarefa": {"type": "title", "title": {}},
            "URL de referência": {"type": "url", "url": {}},
            "Projeto": {
                "type": "relation",
                "relation": {"database_id": DATABASE_GITHUB, "type": "single_property"},
            },
        },
    }


def _pagina_tarefa(
    page_id: str,
    *,
    titulo: str = "repo/Tasks — investigar",
    url: str | None = URL_REPO,
    projeto: list[str] | None = None,
) -> dict:
    return {
        "id": page_id,
        "parent": {"type": "database_id", "database_id": DATABASE_TAREFAS},
        "properties": {
            "Tarefa": {
                "type": "title",
                "title": [{"plain_text": titulo}],
            },
            "URL de referência": {"type": "url", "url": url},
            "Projeto": {
                "type": "relation",
                "relation": [{"id": item} for item in (projeto or [])],
            },
        },
    }


class ClientePreflight:
    def __init__(self, *, projetos: list[dict] | None = None) -> None:
        self.projetos = projetos or [
            {
                "id": PROJETO_ID,
                "properties": {
                    "Nome": {
                        "type": "title",
                        "title": [{"plain_text": "Felipe/repo"}],
                    },
                    "URL": {"type": "url", "url": URL_REPO},
                },
            }
        ]
        self.paginas: dict[str, dict] = {}
        self.patches: list[tuple[str, dict]] = []

    def get_database(self, database_id: str) -> dict:
        if database_id == DATABASE_TAREFAS:
            return _schema_tarefas()
        return {
            "id": DATABASE_GITHUB,
            "properties": {
                "Nome": {"type": "title", "title": {}},
                "URL": {"type": "url", "url": {}},
            },
        }

    def listar_data_sources(self, database_id: str) -> list[dict]:
        return []

    def consultar_database(self, database_id: str, *, buscar_todos: bool = False) -> list[dict]:
        return self.projetos if database_id == DATABASE_GITHUB else []

    def obter_pagina(self, page_id: str) -> dict:
        if page_id not in self.paginas:
            self.paginas[page_id] = _pagina_tarefa(page_id)
        return deepcopy(self.paginas[page_id])

    def atualizar_pagina(self, page_id: str, propriedades: dict) -> dict:
        pagina = self.obter_pagina(page_id)
        self.patches.append((page_id, deepcopy(propriedades)))
        for nome, valor in propriedades.items():
            tipo = pagina["properties"].get(nome, {}).get("type")
            if tipo is None:
                tipo = next(iter(valor))
            pagina["properties"][nome] = {"type": tipo, tipo: deepcopy(valor.get(tipo))}
        self.paginas[page_id] = pagina
        return deepcopy(pagina)


class TaskListPreflight:
    def __init__(self, cliente: ClientePreflight) -> None:
        self._client = cliente
        self._database_id = DATABASE_TAREFAS


def _executar(argv: list[str], cliente: ClientePreflight) -> tuple[int, dict]:
    tasklist = TaskListPreflight(cliente)
    return cli.executar(
        argv,
        tasklist_factory=lambda: tasklist,
        client_factory=lambda: cliente,
    )


def _tarefa_nova() -> Tarefa:
    return Tarefa(
        id="nova-tarefa",
        nome="repo/Tasks — investigar",
        status="Entrada",
        areas=[],
        areas_nomes=[],
        url="https://notion.so/nova-tarefa",
    )


def test_criar_strict_bloqueia_titulo_antes_de_criar():
    cliente = ClientePreflight()
    with mock.patch.object(cli.svc, "criar_tarefa", return_value=_tarefa_nova()) as criar:
        codigo, saida = _executar(
            [
                "--json",
                "criar",
                "outro/Tasks — investigar",
                "--set",
                f"URL de referência={URL_REPO}",
                "--strict",
            ],
            cliente,
        )

    assert codigo == 2
    assert criar.call_count == 0
    assert not cliente.patches
    assert "título precisa seguir" in saida["erro"]["mensagem"]


def test_criar_resolve_projeto_aplica_relation_e_rele():
    cliente = ClientePreflight()
    with mock.patch.object(cli.svc, "criar_tarefa", return_value=_tarefa_nova()):
        codigo, saida = _executar(
            [
                "--json",
                "criar",
                "repo/Tasks — investigar",
                "--set",
                f"URL de referência={URL_REPO}.git/tree/main?tab=files#fim",
            ],
            cliente,
        )

    assert codigo == 0
    dados = saida["dados"]
    assert dados["preflight"]["projeto"]["id"] == PROJETO_ID
    assert dados["relacao_projeto"]["acao"] == "ligada"
    assert any(
        patch.get("Projeto", {}).get("relation") == [{"id": PROJETO_ID}]
        for page_id, patch in cliente.patches
        if page_id == "nova-tarefa"
    )
    assert cliente.paginas["nova-tarefa"]["properties"]["Projeto"]["relation"] == [
        {"id": PROJETO_ID}
    ]


def test_url_desconhecida_cria_somente_url_sem_relation():
    cliente = ClientePreflight(projetos=[])
    url = "https://github.com/Felipe/repo-inexistente"
    with mock.patch.object(cli.svc, "criar_tarefa", return_value=_tarefa_nova()):
        codigo, saida = _executar(
            [
                "--json",
                "criar",
                "repo-inexistente/Tasks — investigar",
                "--set",
                f"URL de referência={url}",
            ],
            cliente,
        )

    assert codigo == 0
    assert saida["dados"]["preflight"]["resolvido"] is False
    assert not any(patch.get("relation") for _, patch in cliente.patches)


def test_dry_run_nao_cria_nem_faz_patch():
    cliente = ClientePreflight()
    with mock.patch.object(cli.svc, "criar_tarefa", return_value=_tarefa_nova()) as criar:
        codigo, saida = _executar(
            [
                "--json",
                "criar",
                "repo/Tasks — investigar",
                "--set",
                f"URL de referência={URL_REPO}",
                "--strict",
                "--dry-run",
            ],
            cliente,
        )

    assert codigo == 0
    assert criar.call_count == 0
    assert cliente.patches == []
    assert saida["dados"]["dry_run"] is True
    assert saida["dados"]["escrever"] is False


def test_editar_strict_bloqueia_projeto_informado_incorreto_antes_do_patch():
    cliente = ClientePreflight()
    cliente.paginas["tarefa"] = _pagina_tarefa("tarefa", projeto=[PROJETO_ID])

    codigo, saida = _executar(
        [
            "--json",
            "editar-linha",
            "tarefa",
            "--set",
            "Projeto=projeto-errado",
            "--strict",
        ],
        cliente,
    )

    assert codigo == 2
    assert cliente.patches == []
    assert "canônico" in saida["erro"]["mensagem"]


def test_editar_por_url_cria_relation_quando_estava_ausente():
    cliente = ClientePreflight()
    cliente.paginas["tarefa"] = _pagina_tarefa("tarefa", projeto=[])

    codigo, saida = _executar(
        [
            "--json",
            "editar-linha",
            "tarefa",
            "--set",
            f"URL de referência={URL_REPO}.git/issues/1?tab=x",
        ],
        cliente,
    )

    assert codigo == 0
    assert saida["dados"]["relacao_projeto"]["acao"] == "ligada"
    assert cliente.paginas["tarefa"]["properties"]["Projeto"]["relation"] == [
        {"id": PROJETO_ID}
    ]


def test_criar_lote_strict_faz_preflight_completo_antes_de_qualquer_criacao(tmp_path):
    arquivo = tmp_path / "novas.json"
    arquivo.write_text(
        json.dumps(
            [
                {
                    "nome": "repo/Tasks — válida",
                    "propriedades": {"URL de referência": URL_REPO},
                },
                {
                    "nome": "título incompatível",
                    "propriedades": {"URL de referência": URL_REPO},
                },
            ]
        ),
        encoding="utf-8",
    )
    cliente = ClientePreflight()
    with mock.patch.object(cli.svc, "criar_tarefa", return_value=_tarefa_nova()) as criar:
        codigo, saida = _executar(
            ["--json", "criar", "--arquivo", str(arquivo), "--strict"], cliente
        )

    assert codigo == 0
    assert criar.call_count == 0
    assert cliente.patches == []
    assert saida["dados"]["erros"] == 1
    assert saida["dados"]["bloqueados"] == 1
