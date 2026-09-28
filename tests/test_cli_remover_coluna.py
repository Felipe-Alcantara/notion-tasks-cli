"""``remover-coluna`` exige ``--sim``; ``linhas --completo`` lê ``Criado em``.

``remover_coluna`` e os leitores dos carimbos do Notion entraram no
``notion-starter`` depois do último release publicado; os testes que dependem
deles pulam com o starter do PyPI (a CI).
"""

from __future__ import annotations

from typing import Any

import pytest
from notion_starter import readers
from notion_starter.services import schema as schema_starter

from cli import notion_tasks as cli

DB = "30296e2d-cd39-4cf3-8bbd-3fb2f53c0195"

precisa_remover = pytest.mark.skipif(
    not hasattr(schema_starter, "remover_coluna"),
    reason="notion-starter instalado ainda sem services.schema.remover_coluna",
)
precisa_leitores = pytest.mark.skipif(
    not hasattr(readers, "ler_created_time"),
    reason="notion-starter instalado ainda sem os leitores de created_time",
)


class ClienteSchema:
    def __init__(self) -> None:
        self.propriedades = {"Nome": {"type": "title"}, "Tema/Pilar": {"type": "multi_select"}}
        self.remocoes: list[dict[str, Any]] = []

    def listar_data_sources(self, database_id: str):
        return [{"id": "ds1", "name": "Principal"}]

    def get_data_source(self, data_source_id: str):
        return {"properties": self.propriedades}

    def atualizar_data_source(self, data_source_id: str, *, propriedades):
        self.remocoes.append(propriedades)
        return {}

    def consultar_data_source(self, data_source_id: str, buscar_todos: bool = False, **_: Any):
        return [{
            "id": "l1",
            "url": "https://notion.so/l1",
            "properties": {
                "Nome": {"type": "title", "title": [{"plain_text": "Ideia"}]},
                "Criado em": {"type": "created_time",
                              "created_time": "2026-09-01T10:00:00.000Z"},
            },
        }]


def _executar(args: list[str], cliente: Any) -> tuple[int, Any]:
    return cli.executar(args, tasklist_factory=lambda: None, client_factory=lambda: cliente)


def test_sem_sim_recusa_sem_tocar_no_schema():
    cliente = ClienteSchema()

    codigo, saida = _executar(["--json", "remover-coluna", DB, "Tema/Pilar"], cliente)

    assert codigo == 2
    assert saida["erro"]["codigo"] == "validacao"
    assert saida["erro"]["proximo_passo"].endswith("--sim")
    assert cliente.remocoes == []


@precisa_remover
def test_com_sim_remove_e_devolve_o_tipo():
    cliente = ClienteSchema()

    codigo, saida = _executar(["--json", "remover-coluna", DB, "Tema/Pilar", "--sim"], cliente)

    assert codigo == 0, saida
    assert saida["dados"] == {"database_id": DB, "coluna": "Tema/Pilar", "tipo": "multi_select"}
    assert cliente.remocoes == [{"Tema/Pilar": None}]


@precisa_remover
def test_coluna_de_titulo_e_recusada():
    cliente = ClienteSchema()

    codigo, saida = _executar(["--json", "remover-coluna", DB, "Nome", "--sim"], cliente)

    assert (codigo, saida["erro"]["codigo"]) == (2, "validacao")
    assert cliente.remocoes == []


def test_starter_sem_remover_coluna_recusa_com_configuracao(monkeypatch):
    monkeypatch.delattr(schema_starter, "remover_coluna", raising=False)

    codigo, saida = _executar(
        ["--json", "remover-coluna", DB, "Tema/Pilar", "--sim"], ClienteSchema()
    )

    assert (codigo, saida["erro"]["codigo"]) == (2, "configuracao")


@precisa_leitores
def test_linhas_completo_mostra_a_data_de_criacao():
    codigo, saida = _executar(["--json", "linhas", DB, "--completo"], ClienteSchema())

    assert codigo == 0, saida
    assert saida["dados"]["linhas"][0]["propriedades"]["Criado em"] == "2026-09-01T10:00:00.000Z"
