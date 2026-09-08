"""Testes do preflight de projeto sem rede nem token real."""

from __future__ import annotations

import pytest

from services import preflight as svc

DATABASE_TAREFAS = "db-tarefas"
DATABASE_GITHUB = "db-github"


def _schema_tarefas() -> dict:
    return {
        "properties": {
            "Tarefa": {"type": "title", "title": {}},
            "URL de referência": {"type": "url", "url": {}},
            "Projeto": {
                "type": "relation",
                "relation": {"database_id": DATABASE_GITHUB},
            },
        }
    }


def _pagina_projeto(page_id: str, url: str, titulo: str) -> dict:
    return {
        "id": page_id,
        "properties": {
            "Nome": {"type": "title", "title": [{"plain_text": titulo}]},
            "URL": {"type": "url", "url": url},
        },
    }


class ClienteFalso:
    def __init__(self, projetos: list[dict] | None = None) -> None:
        self.projetos = projetos or []
        self.consultas: list[str] = []

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
        self.consultas.append(database_id)
        return self.projetos


def test_parser_aceita_git_subpath_query_e_fragmento():
    repositorio = svc.parsear_url_github(
        "https://github.com/Felipe-Alcantara/notion-tasks-cli.git/tree/main?tab=readme#top"
    )

    assert repositorio is not None
    assert repositorio.identificador == "Felipe-Alcantara/notion-tasks-cli"
    assert repositorio.url_canonica == "https://github.com/Felipe-Alcantara/notion-tasks-cli"


@pytest.mark.parametrize(
    "url",
    [
        "https://github.com/Felipe-Alcantara",
        "https://gitlab.com/Felipe-Alcantara/projeto",
        "https://github.com/",
        "não é uma URL",
    ],
)
def test_parser_devolve_nao_resolvido_para_url_que_nao_identifica_repositorio(url):
    assert svc.parsear_url_github(url) is None


def test_resolver_encontra_uma_unica_linha_por_url_canonica():
    cliente = ClienteFalso(
        [
            _pagina_projeto(
                "projeto-1",
                "https://github.com/Felipe-Alcantara/notion-tasks-cli",
                "Felipe-Alcantara/notion-tasks-cli",
            )
        ]
    )

    resultado = svc.resolver_projeto_por_url(
        "https://github.com/Felipe-Alcantara/notion-tasks-cli.git/issues/1?x=1",
        cliente=cliente,
        database_id=DATABASE_TAREFAS,
    )

    assert resultado is not None
    assert resultado.id == "projeto-1"
    assert resultado.repositorio.identificador == "Felipe-Alcantara/notion-tasks-cli"


def test_resolver_recusa_duplicidade():
    cliente = ClienteFalso(
        [
            _pagina_projeto("projeto-1", "https://github.com/felipe/repo", "felipe/repo"),
            _pagina_projeto("projeto-2", "https://github.com/Felipe/repo.git", "Felipe/repo"),
        ]
    )

    with pytest.raises(ValueError, match="mais de uma"):
        svc.resolver_projeto_por_url(
            "https://github.com/FELIPE/repo/tree/main",
            cliente=cliente,
            database_id=DATABASE_TAREFAS,
        )


def test_preflight_strict_aceita_alias_humano_com_acento():
    cliente = ClienteFalso(
        [
            _pagina_projeto(
                "projeto-automacoes",
                "https://github.com/Felipe-Alcantara/Automa-es-do-Notion",
                "Felipe-Alcantara/Automa-es-do-Notion",
            )
        ]
    )

    resultado = svc.preflight_criar(
        "Automações/Tasks — corrigir relation",
        {"URL de referência": "https://github.com/Felipe-Alcantara/Automa-es-do-Notion"},
        cliente=cliente,
        database_id=DATABASE_TAREFAS,
        estrito=True,
    )

    assert resultado.resolvido is True
    assert resultado.titulo_valido is True
    assert resultado.projeto is not None
    assert resultado.projeto.id == "projeto-automacoes"
    assert "Projeto" not in resultado.valores


def test_url_desconhecida_nao_inventa_relation_e_strict_bloqueia():
    cliente = ClienteFalso()
    valores = {"URL de referência": "https://github.com/Felipe/nao-catalogado"}

    resultado = svc.preflight_criar(
        "nao-catalogado/Tasks — investigar",
        valores,
        cliente=cliente,
        database_id=DATABASE_TAREFAS,
    )
    assert resultado.projeto is None
    assert resultado.resolvido is False
    assert resultado.valores == valores
    assert resultado.avisos

    with pytest.raises(ValueError, match="não foi encontrada"):
        svc.preflight_criar(
            "nao-catalogado/Tasks — investigar",
            valores,
            cliente=cliente,
            database_id=DATABASE_TAREFAS,
            estrito=True,
        )


def test_url_desconhecida_em_projeto_nao_vaza_para_payload_de_relation():
    cliente = ClienteFalso()
    resultado = svc.preflight_criar(
        "nao-catalogado/Tasks — investigar",
        {"Projeto": "https://github.com/Felipe/nao-catalogado"},
        cliente=cliente,
        database_id=DATABASE_TAREFAS,
    )

    assert resultado.projeto is None
    assert resultado.resolvido is False
    assert "Projeto" not in resultado.valores
    assert resultado.avisos


def test_strict_bloqueia_titulo_fora_do_projeto_canonico():
    cliente = ClienteFalso(
        [
            _pagina_projeto("projeto-1", "https://github.com/felipe/repo", "felipe/repo")
        ]
    )

    with pytest.raises(ValueError, match="título precisa seguir"):
        svc.preflight_criar(
            "outro-projeto/Tasks — escrever",
            {"URL de referência": "https://github.com/felipe/repo"},
            cliente=cliente,
            database_id=DATABASE_TAREFAS,
            estrito=True,
        )


def test_tarefa_pessoal_continua_permitida_em_strict():
    cliente = ClienteFalso()

    resultado = svc.preflight_criar(
        "Comprar presente",
        {},
        cliente=cliente,
        database_id=DATABASE_TAREFAS,
        estrito=True,
    )

    assert resultado.projeto is None
    assert resultado.motivo and "exceção pessoal" in resultado.motivo
    assert cliente.consultas == []
