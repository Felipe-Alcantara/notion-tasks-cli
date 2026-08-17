"""Comandos que evitam os erros mais caros de operar o Notion às cegas.

- ``schema``: descobrir colunas, opções válidas e relações **antes** de escrever,
  em vez de chamar a API do Notion na mão (ou adivinhar e gravar errado).
- ``relacionar``: ligar duas linhas conferindo a outra ponta.
- ``escrever``: recusar bloco solto em página que contém database.
- ``criar --set/--conteudo``: criar a linha completa numa chamada só.

Testado por injeção de doubles: sem token, sem rede, sem tocar no Notion real.
"""

from __future__ import annotations

import json
from typing import Any
from unittest import mock

from cli import notion_tasks as cli

DATABASE = "30296e2d-cd39-4cf3-8bbd-3fb2f53c0195"


class ClienteFalso:
    """Cliente mínimo com um database de tarefas e páginas de mentira."""

    def __init__(self, blocos: list[dict[str, Any]] | None = None) -> None:
        self.blocos = blocos if blocos is not None else []
        self.patches: list[tuple[str, dict[str, Any]]] = []
        self.anexados: list[dict[str, Any]] = []

    def get_database(self, database_id: str) -> dict[str, Any]:
        return {
            "id": DATABASE,
            "title": [{"plain_text": "Tarefas"}],
            "properties": {
                "Tarefa": {"type": "title"},
                "Prioridade": {
                    "type": "select",
                    "select": {"options": [{"name": "Alta"}, {"name": "Baixa"}]},
                },
                "Criado em": {"type": "created_time"},
                "Relacionadas": {
                    "type": "relation",
                    "relation": {"database_id": DATABASE, "type": "single_property"},
                },
            },
        }

    def obter_pagina(self, page_id: str) -> dict[str, Any]:
        return {
            "id": page_id,
            "parent": {"type": "database_id", "database_id": DATABASE},
            "properties": {
                "Relacionadas": {"type": "relation", "relation": []},
                "Prioridade": {"type": "select", "select": None},
            },
        }

    def atualizar_pagina(self, page_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        self.patches.append((page_id, payload))
        return {"id": page_id}

    def ler_blocos(self, page_id: str, **kwargs: Any) -> list[dict[str, Any]]:
        return self.blocos

    def excluir_bloco(self, block_id: str) -> dict[str, Any]:
        return {"id": block_id}

    def anexar_blocos(self, page_id: str, lote: list[dict[str, Any]]) -> dict[str, Any]:
        self.anexados.extend(lote)
        return {"results": lote}


def _executar(argv: list[str], cliente: ClienteFalso) -> tuple[int, Any]:
    return cli.executar(argv, client_factory=lambda: cliente)


# --------------------------------------------------------------------- schema


def test_schema_devolve_colunas_opcoes_e_avisos():
    codigo, saida = _executar(["--json", "schema", DATABASE], ClienteFalso())

    assert codigo == 0
    dados = saida["dados"]
    por_nome = {coluna["nome"]: coluna for coluna in dados["colunas"]}
    assert dados["titulo"] == "Tarefas"
    assert por_nome["Prioridade"]["opcoes"] == ["Alta", "Baixa"]
    assert por_nome["Criado em"]["editavel"] is False
    assert len(dados["avisos"]) == 1


def test_schema_editaveis_esconde_o_que_o_notion_calcula():
    codigo, saida = _executar(
        ["--json", "schema", DATABASE, "--editaveis"], ClienteFalso()
    )

    nomes = {coluna["nome"] for coluna in saida["dados"]["colunas"]}
    assert codigo == 0
    assert "Criado em" not in nomes
    assert "Tarefa" in nomes


# ----------------------------------------------------------------- relacionar


def test_relacionar_grava_e_devolve_o_que_foi_escrito():
    cliente = ClienteFalso()

    codigo, saida = _executar(
        ["--json", "relacionar", "pg-a", "pg-b", "--coluna", "Relacionadas"], cliente
    )

    assert codigo == 0
    assert saida["dados"]["acao"] == "ligada"
    assert [page_id for page_id, _ in cliente.patches] == ["pg-a", "pg-b"]


def test_relacionar_recusa_a_mesma_pagina_dos_dois_lados():
    codigo, saida = _executar(
        ["--json", "relacionar", "pg-a", "pg-a", "--coluna", "Relacionadas"],
        ClienteFalso(),
    )

    assert codigo == 2
    assert "mesma página" in saida["erro"]["mensagem"]


def test_relacionar_ignora_hifen_ao_comparar_a_mesma_pagina():
    codigo, _ = _executar(
        [
            "--json",
            "relacionar",
            "3bf91f95-497e-81cc-93b7-f0d5cd5d58ad",
            "3bf91f95497e81cc93b7f0d5cd5d58ad",
            "--coluna",
            "Relacionadas",
        ],
        ClienteFalso(),
    )

    assert codigo == 2


# ------------------------------------------------------- guarda da database


def _cliente_com_database() -> ClienteFalso:
    return ClienteFalso(
        [
            {"id": "txt", "type": "paragraph"},
            {
                "id": DATABASE,
                "type": "child_database",
                "child_database": {"title": "Tarefas — HOME"},
            },
        ]
    )


def test_escrever_em_pagina_com_database_e_recusado_com_caminho_pronto():
    cliente = _cliente_com_database()

    codigo, saida = _executar(["--json", "escrever", "pg", "# Nota"], cliente)

    assert codigo == 2
    assert cliente.anexados == []
    assert "linhas" in saida["erro"]["mensagem"]
    assert saida["databases_dentro"][0]["titulo"] == "Tarefas — HOME"


def test_escrever_com_permissao_explicita_passa():
    cliente = _cliente_com_database()

    codigo, saida = _executar(
        ["--json", "escrever", "pg", "# Nota", "--mesmo-com-database"], cliente
    )

    assert codigo == 0
    assert saida["dados"]["blocos_anexados"] == 1


def test_conteudo_avisa_que_a_pagina_contem_database():
    cliente = _cliente_com_database()

    codigo, saida = _executar(["--json", "conteudo", "pg"], cliente)

    assert codigo == 0
    assert saida["dados"]["databases_dentro"][0]["id"] == DATABASE
    assert "LINHAS" in saida["dados"]["aviso"]


def test_substituir_preserva_a_database_e_avisa():
    cliente = _cliente_com_database()

    codigo, saida = _executar(
        ["--json", "escrever", "pg", "# Nota", "--substituir", "--mesmo-com-database"],
        cliente,
    )

    assert codigo == 0
    preservados = saida["dados"]["blocos_preservados"]
    assert [bloco["tipo"] for bloco in preservados] == ["child_database"]
    assert "--apagar-tudo" in saida["dados"]["aviso"]


def test_apagar_tudo_sozinho_e_recusado():
    """Sem --substituir a flag não teria efeito; falhar é melhor que ignorar."""

    codigo, saida = _executar(
        ["--json", "escrever", "pg", "# Nota", "--apagar-tudo"], ClienteFalso()
    )

    assert codigo == 2
    assert "--substituir" in saida["erro"]["mensagem"]


# ----------------------------------------------------------------- criar


class TaskListFalsa:
    def criar(self, nome, status=None, prazo=None, duracao=None, areas=None):
        from notion_starter import Tarefa

        return Tarefa(
            id="linha-nova",
            nome=nome,
            status=status or "Entrada",
            prazo=prazo,
            duracao=duracao,
            areas=areas or [],
            areas_nomes=[],
            url="https://notion.so/linha-nova",
        )


def _criar(argv: list[str], cliente: ClienteFalso) -> tuple[int, Any]:
    with mock.patch.object(cli.svc, "listar_opcoes", return_value={"status": ["Entrada"]}):
        return cli.executar(
            argv, tasklist_factory=TaskListFalsa, client_factory=lambda: cliente
        )


def test_criar_preenche_propriedades_e_corpo_numa_chamada():
    cliente = ClienteFalso()

    codigo, saida = _criar(
        [
            "--json",
            "criar",
            "Tarefa nova",
            "--status",
            "Entrada",
            "--set",
            "Prioridade=Alta",
            "--conteudo",
            "## Contexto",
        ],
        cliente,
    )

    assert codigo == 0
    assert saida["dados"]["propriedades"] == {"Prioridade": "select"}
    assert saida["dados"]["blocos_anexados"] == 1
    assert cliente.anexados


def test_criar_sem_extras_nao_faz_chamada_a_mais():
    cliente = ClienteFalso()

    codigo, saida = _criar(["--json", "criar", "Só o título"], cliente)

    assert codigo == 0
    assert cliente.patches == []
    assert "propriedades" not in saida["dados"]


def test_falha_ao_completar_reporta_o_id_da_linha_ja_criada():
    """A linha já existe: sem o id na mensagem, um script cria outra e duplica."""

    cliente = ClienteFalso()
    with mock.patch.object(
        cli.svc_propriedades, "editar_linha", side_effect=RuntimeError("timeout")
    ):
        codigo, saida = _criar(
            ["--json", "criar", "Tarefa", "--set", "Prioridade=Alta"], cliente
        )

    assert codigo == 2
    assert "linha-nova" in saida["erro"]["mensagem"]
    assert "não crie de novo" in saida["erro"]["mensagem"]


def test_saida_json_continua_serializavel():
    """Dataclass nova no retorno não pode quebrar a saída --json."""

    cliente = _cliente_com_database()

    _, saida = _executar(
        ["--json", "escrever", "pg", "# Nota", "--substituir", "--mesmo-com-database"],
        cliente,
    )

    assert json.loads(json.dumps(saida))


# ------------------------------------------------- relatorios-do-git (dedup)


def test_descoberta_nao_duplica_repositorio_ja_nomeado(tmp_path, monkeypatch):
    """`--repo` existe para dar nome de produto; dedup por nome deixa passar.

    O mesmo repositório entrava duas vezes — uma com o nome de produto e outra
    com o nome da pasta — e o relatório do dia saía com a mesma lista de
    commits repetida sob dois títulos.
    """

    repo = tmp_path / "Felixoverse-Official-Bot"
    repo.mkdir()
    (repo / ".git").mkdir()

    capturados: list[str] = []

    def _consolidar(repositorios, **_):
        capturados.extend(r.nome for r in repositorios)
        return []

    monkeypatch.setattr(cli.svc_historico, "consolidar_dias", _consolidar)

    codigo, _ = cli.executar(
        [
            "--json",
            "relatorios-do-git",
            "--database",
            "db",
            "--descobrir",
            str(tmp_path),
            "--repo",
            f"Felixoverse Official Bot={repo}",
            "--dry-run",
        ],
        client_factory=lambda: ClienteFalso(),
    )

    assert codigo == 0
    assert capturados == ["Felixoverse Official Bot"]


def test_sem_repositorio_nenhum_o_erro_ensina_as_duas_saidas():
    codigo, saida = _executar(
        ["--json", "relatorios-do-git", "--database", "db", "--dry-run"],
        ClienteFalso(),
    )

    assert codigo == 2
    assert "--repo" in saida["erro"]["mensagem"]
    assert "--descobrir" in saida["erro"]["mensagem"]
