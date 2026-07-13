"""Testes da CLI para IA.

A CLI é testada por injeção de doubles de ``TaskList``/``NotionClient``: sem
token, sem rede e sem tocar no Notion real.
"""

from __future__ import annotations

import json
from pathlib import Path
from unittest import mock

from notion_starter import Tarefa

from cli import notion_tasks as cli


class FakeTaskList:
    def __init__(self) -> None:
        self.chamadas: list[tuple[str, object]] = []

    def listar(self, status=None, duracao=None, areas=None):
        self.chamadas.append(("listar", (status, duracao, areas)))
        return [
            Tarefa(
                id="t1",
                nome="Estudar",
                status=status or "Entrada",
                prazo="2026-07-01",
                duracao=duracao or "Dias",
                areas=areas or ["a1"],
                areas_nomes=["Estudos"],
                url="https://notion.so/t1",
            )
        ]

    def criar(self, nome, status=None, prazo=None, duracao=None, areas=None):
        self.chamadas.append(("criar", (nome, status, prazo, duracao, areas)))
        return Tarefa(
            id="novo",
            nome=nome,
            status=status,
            prazo=prazo,
            duracao=duracao,
            areas=areas or [],
            url="https://notion.so/novo",
        )

    def editar(self, task_id, *, nome=None, status=None, prazo=None, duracao=None, areas=None):
        self.chamadas.append(("editar", (task_id, nome, status, prazo, duracao, areas)))
        return Tarefa(
            id=task_id,
            nome=nome or "Editada",
            status=status,
            prazo=prazo,
            duracao=duracao,
            areas=areas or [],
            url=f"https://notion.so/{task_id}",
        )

    def atualizar_status(self, task_id, status):
        self.chamadas.append(("atualizar_status", (task_id, status)))
        return Tarefa(id=task_id, nome="Movida", status=status, url=f"https://notion.so/{task_id}")

    def concluir(self, task_id, status_concluido):
        self.chamadas.append(("concluir", (task_id, status_concluido)))
        return Tarefa(
            id=task_id,
            nome="Concluída",
            status=status_concluido,
            url=f"https://notion.so/{task_id}",
        )

    def opcoes(self):
        self.chamadas.append(("opcoes", None))
        return {
            "status": ["Entrada", "Assim que possível", "Concluída"],
            "duracao": ["Dias"],
            "areas": [{"id": "a1", "nome": "Estudos"}],
        }


class FakeClient:
    def __init__(self) -> None:
        self.chamadas: list[tuple[str, object]] = []
        self.database = {
            "id": "db1",
            "url": "https://notion.so/db1",
            "title": [{"plain_text": "Tarefas"}],
            "properties": {
                "Nome": {"type": "title", "title": {}},
                "Status": {
                    "type": "status",
                    "status": {
                        "options": [
                            {"id": "old-status", "name": "00. Inbox", "color": "default"},
                            {"id": "done-status", "name": "06. Feito", "color": "green"},
                        ],
                        "groups": [
                            {
                                "name": "In progress",
                                "option_ids": ["old-status"],
                            },
                            {
                                "name": "Complete",
                                "option_ids": ["done-status"],
                            },
                        ],
                    },
                },
                "Duração": {
                    "type": "status",
                    "status": {
                        "options": [
                            {"id": "fast", "name": "Mais rápido possível", "color": "red"},
                            {"id": "days", "name": "Dias", "color": "yellow"},
                        ],
                        "groups": [{"name": "To-do", "option_ids": ["fast", "days"]}],
                    },
                },
                "Áreas-da-Vida": {
                    "type": "relation",
                    "relation": {"database_id": "areas-db"},
                },
            },
        }
        self.areas_database = {
            "id": "areas-db",
            "title": [{"plain_text": "Áreas-da-Vida"}],
            "properties": {"Name": {"type": "title", "title": {}}},
        }
        self.paginas = [
            {
                "id": "t1",
                "properties": {
                    "Status": {"type": "status", "status": {"name": "00. Inbox"}},
                    "Duração": {
                        "type": "status",
                        "status": {"name": "Mais rápido possível"},
                    },
                },
            }
        ]
        self.areas = [
            {
                "id": "a1",
                "properties": {"Name": {"type": "title", "title": [{"plain_text": "Money"}]}},
            }
        ]

    def buscar(self, query=None, page_size=100, buscar_todos=False, filtro=None):
        if filtro == {"property": "object", "value": "database"}:
            return [
                {
                    "id": "db1",
                    "object": "database",
                    "title": [{"plain_text": "Tarefas"}],
                    "url": "https://notion.so/db1",
                }
            ]
        return [
            {
                "id": "p1",
                "object": "page",
                "parent": {"type": "workspace", "workspace": True},
                "properties": {"Nome": {"type": "title", "title": [{"plain_text": "Home"}]}},
            },
            {
                "id": "db1",
                "object": "database",
                "parent": {"type": "page_id", "page_id": "p1"},
                "title": [{"plain_text": "Tarefas"}],
            },
        ]

    def get_database(self, database_id):
        if database_id == "areas-db":
            return self.areas_database
        return self.database

    def listar_data_sources(self, database_id):
        self.chamadas.append(("listar_data_sources", database_id))
        return [{"id": "ds1", "name": "Tarefas"}]

    def consultar_database(self, database_id, buscar_todos=False):
        return self.areas if database_id == "areas-db" else self.paginas

    def atualizar_database(self, database_id, *, titulo=None, propriedades=None):
        self.chamadas.append(("atualizar_database", (database_id, titulo, propriedades)))
        if database_id == "areas-db":
            alvo = self.areas_database
        else:
            alvo = self.database
        if titulo:
            alvo["title"] = [{"plain_text": titulo}]
        for nome, mudanca in (propriedades or {}).items():
            if "name" in mudanca and nome in alvo["properties"]:
                alvo["properties"][mudanca["name"]] = alvo["properties"].pop(nome)
            elif nome in alvo["properties"] and "status" in mudanca:
                atuais = {op["name"]: op for op in alvo["properties"][nome]["status"]["options"]}
                novas = []
                for op in mudanca["status"]["options"]:
                    if "id" in op:
                        novas.extend(item for item in atuais.values() if item.get("id") == op["id"])
                    else:
                        novas.append(
                            {
                                "id": op["name"].casefold().replace(" ", "-"),
                                "name": op["name"],
                                "color": op.get("color", "default"),
                            }
                        )
                alvo["properties"][nome]["status"]["options"] = novas
        return alvo

    def obter_pagina(self, page_id):
        self.chamadas.append(("obter_pagina", page_id))
        return {
            "id": page_id,
            "properties": {
                "Nome": {"type": "title", "title": []},
                "Status": {"type": "status", "status": {"name": "Inbox"}},
                "Prazo": {"type": "date", "date": None},
                "Tags": {"type": "multi_select", "multi_select": []},
                "Peso": {"type": "number", "number": None},
                "Fórmula": {"type": "formula", "formula": {}},
            },
        }

    def atualizar_pagina(self, page_id, propriedades):
        self.chamadas.append(("atualizar_pagina", (page_id, propriedades)))
        return {"id": page_id, "properties": propriedades}

    def ler_blocos(self, block_id, page_size=100, buscar_todos=False, recursivo=False):
        self.chamadas.append(("ler_blocos", block_id))
        return [{"type": "paragraph", "paragraph": {"rich_text": [{"plain_text": "oi"}]}}]

    def anexar_blocos(self, block_id, blocos):
        self.chamadas.append(("anexar_blocos", (block_id, blocos)))
        return {"results": blocos}

    def atualizar_bloco(self, block_id, conteudo):
        self.chamadas.append(("atualizar_bloco", (block_id, conteudo)))
        return {"id": block_id}

    def excluir_bloco(self, block_id):
        self.chamadas.append(("excluir_bloco", block_id))
        return {"id": block_id, "archived": True}

    def consultar_data_source(self, data_source_id, page_size=100, buscar_todos=False, filtro=None):
        self.chamadas.append(("consultar_data_source", data_source_id))
        return []


class FakeCloneClient(FakeClient):
    """Cliente que sustenta o fluxo de ``clonar-database`` ponta a ponta."""

    def listar_data_sources(self, database_id):
        nome = "Origem" if database_id == "db1" else "Origem (cópia)"
        fonte = "f_origem" if database_id == "db1" else "f_clone"
        return [{"id": fonte, "name": nome}]

    def get_data_source(self, data_source_id):
        if data_source_id == "f_origem":
            return {
                "properties": {
                    "Tarefa": {"type": "title", "title": {}},
                    "Esforço": {"type": "status", "status": {"options": [{"name": "Dias"}]}},
                },
                "parent": {"type": "page_id", "page_id": "pagina_pai"},
            }
        return {"properties": {}}

    def criar_database(self, pagina_id, titulo, propriedades):
        self.chamadas.append(("criar_database", (pagina_id, titulo)))
        return {"id": "db_clone"}

    def atualizar_data_source(self, data_source_id, *, propriedades):
        self.chamadas.append(("atualizar_data_source", data_source_id))
        return {"properties": propriedades}

    def criar_pagina_em_fonte(self, data_source_id, propriedades):
        self.chamadas.append(("criar_pagina_em_fonte", data_source_id))
        return {"id": "nova"}


class FakeDatabaseClient(FakeClient):
    """Cliente onde o ID consultado é um database (blocos vazios, com linhas)."""

    def obter_pagina(self, page_id):
        # Como na API real: GET /pages/<database_id> responde 404.
        from notion_starter import NotionHTTPError

        raise NotionHTTPError(404, "não é uma página")

    def ler_blocos(self, block_id, page_size=100, buscar_todos=False, recursivo=False):
        return []

    def listar_data_sources(self, database_id):
        return [{"id": "ds1", "name": "Principal"}]

    def consultar_data_source(self, data_source_id, page_size=100, buscar_todos=False, filtro=None):
        return [
            {
                "id": "r1",
                "url": "https://notion.so/r1",
                "properties": {"Name": {"type": "title", "title": [{"plain_text": "Linha 1"}]}},
            }
        ]


def _executar(args, fake: FakeTaskList | None = None, client=None):
    tasklist = fake or FakeTaskList()
    notion_client = client or FakeClient()
    return cli.executar(
        args,
        tasklist_factory=lambda: tasklist,
        client_factory=lambda: notion_client,
    )


def test_listar_json_emite_envelope_estavel():
    codigo, saida = _executar(
        ["--json", "listar", "--status", "Entrada", "--duracao", "Dias", "--area", "a1"]
    )
    assert codigo == 0
    assert saida["ok"] is True
    assert saida["dados"][0]["id"] == "t1"
    assert "bruto" not in saida["dados"][0]


def test_listar_delega_filtros_para_services():
    fake = FakeTaskList()
    codigo, _ = _executar(
        ["--json", "listar", "--status", "Entrada", "--duracao", "Dias", "--area", "a1,a2"],
        fake,
    )

    assert codigo == 0
    assert fake.chamadas == [("listar", ("Entrada", "Dias", ["a1", "a2"]))]


def test_criar_delega_campos_amplos_para_services():
    fake = FakeTaskList()
    codigo, saida = _executar(
        [
            "--json",
            "criar",
            "Nova tarefa",
            "--status",
            "Entrada",
            "--duracao",
            "Dias",
            "--area",
            "a1,a2",
        ],
        fake,
    )
    assert codigo == 0
    # Agora valida status antes de criar, então espera chamada a listar_opcoes também
    assert fake.chamadas[0] == ("opcoes", None)
    assert fake.chamadas[1] == ("criar", ("Nova tarefa", "Entrada", None, "Dias", ["a1", "a2"]))
    assert saida["dados"]["areas"] == ["a1", "a2"]


def test_editar_exige_ao_menos_um_campo():
    codigo, saida = _executar(["--json", "editar", "t1"])
    assert codigo == 2
    assert saida == {
        "ok": False,
        "erro": {"mensagem": "Informe ao menos um campo para editar."},
    }


def test_mover_e_concluir_delegam_para_tasklist():
    fake = FakeTaskList()
    codigo_mover, _ = _executar(["mover", "t1", "Assim que possível"], fake)
    codigo_concluir, _ = _executar(["concluir", "t1", "Concluída"], fake)
    assert codigo_mover == 0
    assert codigo_concluir == 0
    # Agora valida status antes de mover/concluir
    assert fake.chamadas[0] == ("opcoes", None)
    assert fake.chamadas[1] == ("atualizar_status", ("t1", "Assim que possível"))
    assert fake.chamadas[2] == ("opcoes", None)
    assert fake.chamadas[3] == ("concluir", ("t1", "Concluída"))


def test_ler_busca_tarefa_por_id():
    codigo, saida = _executar(["--json", "ler", "t1"])
    assert codigo == 0
    assert saida["dados"]["nome"] == "Estudar"


def test_ler_retorna_erro_quando_nao_encontra():
    codigo, saida = _executar(["--json", "ler", "inexistente"])
    assert codigo == 2
    assert saida["erro"]["mensagem"] == "Tarefa não encontrada."


def test_opcoes_retorna_json_dos_seletores():
    codigo, saida = _executar(["--json", "opcoes"])
    assert codigo == 0
    assert saida["dados"]["status"] == ["Entrada", "Assim que possível", "Concluída"]


def test_databases_lista_databases_visiveis():
    codigo, saida = _executar(["--json", "databases"])
    assert codigo == 0
    assert saida["dados"] == [{"id": "db1", "titulo": "Tarefas", "url": "https://notion.so/db1"}]


def test_mapear_resume_workspace():
    codigo, saida = _executar(["--json", "mapear"])
    assert codigo == 0
    assert saida["dados"]["total_itens"] == 2
    assert saida["dados"]["total_paginas"] == 1
    assert saida["dados"]["total_databases"] == 1


def test_escolher_database_grava_env_file(tmp_path: Path):
    env_file = tmp_path / ".env"
    salvar_database_env = cli._salvar_database_env
    with (
        mock.patch.object(cli, "RAIZ", tmp_path),
        mock.patch.object(
            cli,
            "_salvar_database_env",
            wraps=lambda db_id: salvar_database_env(db_id, env_file),
        ),
    ):
        codigo, saida = _executar(["--json", "escolher-database", "db_novo"])
    assert codigo == 0
    assert env_file.read_text(encoding="utf-8") == "NOTION_DATABASE_ID=db_novo\n"
    assert saida["dados"]["database_id"] == "db_novo"


def test_perfil_global_aplica_workspace_antes_do_comando():
    with mock.patch.object(cli.perfis_workspace, "aplicar_perfil") as aplicar:
        codigo, saida = _executar(["--json", "--perfil", "cliente", "databases"])

    assert codigo == 0
    assert saida["dados"][0]["id"] == "db1"
    aplicar.assert_called_once_with("cliente")


def test_perfis_adicionar_retorna_token_mascarado(tmp_path: Path):
    arquivo = tmp_path / "perfis.json"
    token = "ntn_" + "a" * 20
    with mock.patch.object(cli.perfis_workspace, "ARQUIVO_PADRAO", arquivo):
        codigo, saida = _executar(
            [
                "--json",
                "perfis",
                "adicionar",
                "cliente",
                "--token",
                token,
                "--database",
                "db-cliente",
                "--nome",
                "Cliente",
                "--ativar",
            ]
        )

    assert codigo == 0
    assert saida["dados"]["perfil"]["alias"] == "cliente"
    assert saida["dados"]["perfil"]["token"] == "ntn_aa...aaaa"
    assert token not in json.dumps(saida, ensure_ascii=False)


def test_perfis_remover_exige_confirmacao(tmp_path: Path):
    arquivo = tmp_path / "perfis.json"
    cli.perfis_workspace.adicionar_perfil(
        alias="cliente",
        token="ntn_" + "a" * 20,
        caminho=arquivo,
    )
    with mock.patch.object(cli.perfis_workspace, "ARQUIVO_PADRAO", arquivo):
        codigo, saida = _executar(["--json", "perfis", "remover", "cliente"])

    assert codigo == 2
    assert "--sim" in saida["erro"]["mensagem"]


def test_normalizar_nomes_dry_run_nao_escreve_no_notion(monkeypatch):
    monkeypatch.setenv("NOTION_DATABASE_ID", "db1")
    client = FakeClient()

    codigo, saida = _executar(["--json", "normalizar-nomes", "--dry-run"], client=client)

    assert codigo == 0
    assert saida["dados"]["aplicado"] is False
    assert saida["dados"]["paginas_alteradas"] == 1
    assert saida["dados"]["opcoes_adicionadas"]["status"] == [
        {"de": "00. Inbox", "para": "Entrada"},
        {"de": "06. Feito", "para": "Concluída"},
    ]
    assert client.chamadas == []


def test_normalizar_nomes_aplica_migracao_na_fonte(monkeypatch):
    monkeypatch.setenv("NOTION_DATABASE_ID", "db1")
    client = FakeClient()

    codigo, saida = _executar(["--json", "normalizar-nomes"], client=client)

    assert codigo == 0
    assert saida["dados"]["aplicado"] is True
    assert ("atualizar_pagina", ("t1", mock.ANY)) in client.chamadas
    assert any(chamada[0] == "atualizar_database" for chamada in client.chamadas)
    assert "Etapa" in client.database["properties"]
    assert "Tarefa" in client.database["properties"]
    assert "Área" in client.areas_database["properties"]


def test_main_imprime_json(capsys):
    with mock.patch.object(cli, "executar", return_value=(0, {"ok": True, "dados": []})):
        codigo = cli.main(["--json", "listar"])
    assert codigo == 0
    assert json.loads(capsys.readouterr().out) == {"ok": True, "dados": []}


# -- Conteúdo (blocos) -----------------------------------------------------


def test_conteudo_le_pagina_como_markdown():
    client = FakeClient()
    codigo, saida = _executar(["--json", "conteudo", "page1"], client=client)
    assert codigo == 0
    assert saida["dados"]["markdown"] == "oi"
    assert ("ler_blocos", "page1") in client.chamadas


def test_escrever_anexa_blocos():
    client = FakeClient()
    codigo, saida = _executar(
        ["--json", "escrever", "page1", "linha um\nlinha dois"], client=client
    )
    assert codigo == 0
    assert saida["dados"]["blocos_anexados"] == 2
    assert any(c[0] == "anexar_blocos" for c in client.chamadas)


def test_editar_linha_atualiza_propriedades_por_tipo():
    client = FakeClient()
    codigo, saida = _executar(
        [
            "--json",
            "editar-linha",
            "page1",
            "--set",
            "Status=Feito",
            "--set",
            "Tags=urgente,casa",
            "--set",
            "Peso=3",
        ],
        client=client,
    )
    assert codigo == 0
    assert saida["dados"]["atualizadas"] == {
        "Status": "status",
        "Tags": "multi_select",
        "Peso": "number",
    }
    enviados = [c[1][1] for c in client.chamadas if c[0] == "atualizar_pagina"][0]
    assert enviados["Status"] == {"status": {"name": "Feito"}}
    assert enviados["Tags"] == {"multi_select": [{"name": "urgente"}, {"name": "casa"}]}
    assert enviados["Peso"] == {"number": 3}


def test_editar_linha_propriedade_inexistente_erra():
    client = FakeClient()
    codigo, saida = _executar(
        ["--json", "editar-linha", "page1", "--set", "Inexistente=x"], client=client
    )
    assert codigo == 2
    assert not saida["ok"]
    assert "Inexistente" in saida["erro"]["mensagem"]
    assert not any(c[0] == "atualizar_pagina" for c in client.chamadas)


def test_editar_linha_tipo_somente_leitura_erra():
    client = FakeClient()
    codigo, saida = _executar(
        ["--json", "editar-linha", "page1", "--set", "Fórmula=x"], client=client
    )
    assert codigo == 2
    assert "formula" in saida["erro"]["mensagem"]


def test_editar_linha_sem_set_erra():
    client = FakeClient()
    codigo, saida = _executar(["--json", "editar-linha", "page1"], client=client)
    assert codigo == 2
    assert not saida["ok"]


def test_editar_bloco_atualiza():
    client = FakeClient()
    codigo, saida = _executar(["--json", "editar-bloco", "b1", "## Novo"], client=client)
    assert codigo == 0
    assert saida["dados"]["editado"] is True
    assert any(c[0] == "atualizar_bloco" for c in client.chamadas)


def test_apagar_bloco_sem_sim_nao_apaga():
    client = FakeClient()
    codigo, saida = _executar(["--json", "apagar-bloco", "b1"], client=client)
    assert codigo == 2
    assert saida["ok"] is False
    assert not any(c[0] == "excluir_bloco" for c in client.chamadas)


def test_apagar_bloco_com_sim_apaga():
    client = FakeClient()
    codigo, saida = _executar(["--json", "apagar-bloco", "b1", "--sim"], client=client)
    assert codigo == 0
    assert saida["dados"]["apagado"] is True
    assert ("excluir_bloco", "b1") in client.chamadas


def test_blocos_lista_ids_para_editar_ou_apagar():
    client = FakeClient()
    client.ler_blocos = lambda *a, **k: [
        {"id": "b1", "type": "heading_1", "heading_1": {"rich_text": [{"plain_text": "T"}]}},
        {"id": "b2", "type": "paragraph", "paragraph": {"rich_text": [{"plain_text": "corpo"}]}},
    ]
    codigo, saida = _executar(["--json", "blocos", "page1"], client=client)
    assert codigo == 0
    ids = [b["id"] for b in saida["dados"]["blocos"]]
    assert ids == ["b1", "b2"]
    assert saida["dados"]["blocos"][0]["preview"] == "# T"


def test_escrever_substituir_limpa_antes():
    client = FakeClient()
    client.ler_blocos = lambda *a, **k: [
        {"id": "velho", "type": "paragraph", "paragraph": {"rich_text": [{"plain_text": "lixo"}]}}
    ]
    codigo, saida = _executar(
        ["--json", "escrever", "page1", "novo", "--substituir"], client=client
    )
    assert codigo == 0
    assert saida["dados"]["substituiu"] is True
    assert ("excluir_bloco", "velho") in client.chamadas
    assert any(c[0] == "anexar_blocos" for c in client.chamadas)


def test_limpar_sem_sim_nao_apaga():
    client = FakeClient()
    codigo, saida = _executar(["--json", "limpar", "page1"], client=client)
    assert codigo == 2
    assert saida["ok"] is False
    assert not any(c[0] == "excluir_bloco" for c in client.chamadas)


def test_limpar_com_sim_apaga_o_corpo():
    client = FakeClient()
    client.ler_blocos = lambda *a, **k: [
        {"id": "b1", "type": "paragraph", "paragraph": {"rich_text": []}},
        {"id": "b2", "type": "paragraph", "paragraph": {"rich_text": []}},
    ]
    codigo, saida = _executar(["--json", "limpar", "page1", "--sim"], client=client)
    assert codigo == 0
    assert saida["dados"]["blocos_apagados"] == 2
    assert ("excluir_bloco", "b1") in client.chamadas
    assert ("excluir_bloco", "b2") in client.chamadas


def test_buscar_normaliza_itens():
    client = FakeClient()
    codigo, saida = _executar(["--json", "buscar", "x"], client=client)
    assert codigo == 0
    ids = {item["id"] for item in saida["dados"]}
    assert ids == {"p1", "db1"}


def test_database_atual_traz_titulo_real():
    client = FakeClient()
    with mock.patch.dict(cli.os.environ, {"NOTION_DATABASE_ID": "db1"}, clear=False):
        codigo, saida = _executar(["--json", "database-atual"], client=client)

    assert codigo == 0
    assert saida["dados"] == {
        "database_id": "db1",
        "titulo": "Tarefas",
        "url": "https://notion.so/db1",
        "data_sources": ["Tarefas"],
    }


def test_conteudo_de_database_avisa_e_traz_linhas():
    codigo, saida = _executar(
        ["--json", "conteudo", "db1"], client=FakeDatabaseClient()
    )
    assert codigo == 0
    dados = saida["dados"]
    assert dados["tipo"] == "database"
    assert "database" in dados["aviso"].lower()
    assert dados["linhas"][0]["titulo"] == "Linha 1"


def test_conteudo_de_pagina_sem_corpo_nao_inventa_linhas():
    client = FakeClient()
    # ler_blocos do FakeClient devolve um parágrafo; força vazio aqui.
    client.ler_blocos = lambda *a, **k: []
    codigo, saida = _executar(["--json", "conteudo", "page1"], client=client)
    assert codigo == 0
    # Página = propriedades + corpo: mesmo sem corpo, as propriedades
    # preenchidas vêm no resultado (e vêm primeiro).
    assert saida["dados"] == {
        "id": "page1",
        "tipo": "pagina",
        "propriedades": {"Status": "Inbox"},
        "markdown": "",
    }


def test_conteudo_traz_propriedades_antes_do_corpo():
    codigo, saida = _executar(["conteudo", "page1"])
    assert codigo == 0
    assert saida.index("Propriedades") < saida.index("Corpo")
    assert "Status: Inbox" in saida


def test_linhas_lista_linhas_do_database():
    codigo, saida = _executar(["--json", "linhas", "db1"], client=FakeDatabaseClient())
    assert codigo == 0
    assert saida["dados"]["linhas"][0]["id"] == "r1"


def test_guia_lista_todos_os_comandos():
    codigo, saida = _executar(["--json", "guia"])
    assert codigo == 0
    comandos = {c["comando"] for c in saida["dados"]["comandos"]}
    # Cobre tarefas, conteúdo e o próprio guia — reflete o parser.
    assert {"listar", "conteudo", "linhas", "apagar-bloco", "guia"} <= comandos
    # Cada comando traz ao menos um exemplo.
    assert all(c["exemplos"] for c in saida["dados"]["comandos"])


def test_guia_recomenda_propriedades_antes_do_conteudo():
    codigo, saida = _executar(["--json", "guia"])
    assert codigo == 0
    fluxo = " ".join(saida["dados"]["fluxo_recomendado"]).lower()
    assert "editar-linha" in fluxo and "escrever" in fluxo
    # A ordem recomendada: propriedades (editar-linha) antes do conteúdo (escrever).
    assert fluxo.index("editar-linha") < fluxo.index("escrever")
    comandos = {c["comando"] for c in saida["dados"]["comandos"]}
    assert "editar-linha" in comandos


def test_guia_humano_mostra_fluxo_recomendado():
    codigo, saida = _executar(["guia"])
    assert codigo == 0
    assert "editar-linha" in saida and "propriedades" in saida.lower()


def test_guia_humano_tem_dica_de_uso():
    codigo, saida = _executar(["guia"])
    assert codigo == 0
    assert "--json" in saida


def test_guia_inclui_clonar_database():
    codigo, saida = _executar(["--json", "guia"])
    comandos = {c["comando"] for c in saida["dados"]["comandos"]}
    assert "clonar-database" in comandos


def test_clonar_database_cria_clone_e_aplica_schema():
    codigo, saida = _executar(["--json", "clonar-database", "db1"], client=FakeCloneClient())
    assert codigo == 0
    dados = saida["dados"]
    assert dados["id"] == "db_clone"
    assert dados["titulo"] == "Origem (cópia)"
    assert dados["linhas_copiadas"] == 0


def test_clonar_database_com_titulo_e_com_linhas():
    cli_fake = FakeCloneClient()
    codigo, saida = _executar(
        ["--json", "clonar-database", "db1", "--titulo", "Clone X", "--com-linhas"],
        client=cli_fake,
    )
    assert codigo == 0
    assert saida["dados"]["titulo"] == "Clone X"
    assert ("criar_database", ("pagina_pai", "Clone X")) in cli_fake.chamadas


def test_clonar_database_humano_resume():
    codigo, saida = _executar(["clonar-database", "db1"], client=FakeCloneClient())
    assert codigo == 0
    assert "Clone criado" in saida


# -- atualizar-github ------------------------------------------------------


class _ResumoFake:
    repos_encontrados = 3
    paginas_criadas = 1
    paginas_atualizadas = 2
    paginas_puladas = 0
    readmes_escritos = 1
    readmes_atualizados = 1
    erros: list[str] = []


def test_atualizar_github_passa_contas_e_database(monkeypatch):
    capturado = {}

    def fake_atualizar(contas, database_id, **kwargs):
        capturado["contas"] = contas
        capturado["database_id"] = database_id
        capturado["sincronizar_readme"] = kwargs["sincronizar_readme"]
        return _ResumoFake()

    monkeypatch.setattr(cli.svc_inventario, "atualizar_repos", fake_atualizar)
    monkeypatch.setattr(cli, "GitHubClient", lambda *a, **k: object())

    codigo, saida = _executar(
        ["--json", "atualizar-github", "--contas", "conta-a,conta-b", "--database", "db1"]
    )
    assert codigo == 0
    assert capturado["contas"] == ["conta-a", "conta-b"]
    assert capturado["database_id"] == "db1"
    assert capturado["sincronizar_readme"] is True
    assert saida["dados"]["paginas_atualizadas"] == 2


def test_atualizar_github_sem_readme(monkeypatch):
    capturado = {}
    monkeypatch.setattr(
        cli.svc_inventario,
        "atualizar_repos",
        lambda c, d, **k: capturado.update(k) or _ResumoFake(),
    )
    monkeypatch.setattr(cli, "GitHubClient", lambda *a, **k: object())
    codigo, _ = _executar(
        ["--json", "atualizar-github", "--contas", "x", "--database", "db1", "--sem-readme"]
    )
    assert codigo == 0
    assert capturado["sincronizar_readme"] is False
    # Sem a flag, arquivados entram normalmente.
    assert capturado["ignorar_arquivados"] is False


def test_atualizar_github_sem_arquivados(monkeypatch):
    capturado = {}
    monkeypatch.setattr(
        cli.svc_inventario,
        "atualizar_repos",
        lambda c, d, **k: capturado.update(k) or _ResumoFake(),
    )
    monkeypatch.setattr(cli, "GitHubClient", lambda *a, **k: object())
    codigo, _ = _executar(
        ["--json", "atualizar-github", "--contas", "x", "--database", "db1", "--sem-arquivados"]
    )
    assert codigo == 0
    assert capturado["ignorar_arquivados"] is True


def test_atualizar_github_apenas_mudancas(monkeypatch):
    capturado = {}
    monkeypatch.setattr(
        cli.svc_inventario,
        "atualizar_repos",
        lambda c, d, **k: capturado.update(k) or _ResumoFake(),
    )
    monkeypatch.setattr(cli, "GitHubClient", lambda *a, **k: object())
    codigo, _ = _executar(
        ["--json", "atualizar-github", "--contas", "x", "--database", "db1", "--apenas-mudancas"]
    )
    assert codigo == 0
    assert capturado["apenas_mudancas"] is True


def test_atualizar_github_exige_contas(monkeypatch):
    monkeypatch.delenv("GITHUB_CONTAS", raising=False)
    codigo, saida = _executar(["--json", "atualizar-github", "--database", "db1"])
    assert codigo == 2
    assert saida["ok"] is False


def test_atualizar_github_humano_resume(monkeypatch):
    monkeypatch.setattr(cli.svc_inventario, "atualizar_repos", lambda c, d, **k: _ResumoFake())
    monkeypatch.setattr(cli, "GitHubClient", lambda *a, **k: object())
    codigo, saida = _executar(["atualizar-github", "--contas", "x", "--database", "db1"])
    assert codigo == 0
    assert "Repos: 3" in saida


# -- exportar-docx ---------------------------------------------------------


def test_exportar_docx_passa_periodo_database_e_saida(monkeypatch, tmp_path: Path):
    capturado = {}

    def fake_exportar(**kwargs):
        capturado.update(kwargs)
        return {
            "database_id": kwargs["database_id"],
            "periodo": {"de": kwargs["data_inicio"], "ate": kwargs["data_fim"]},
            "campo_data": kwargs["campo_data"],
            "saida": str(kwargs["saida"]),
            "total": 1,
            "arquivos": [],
        }

    monkeypatch.setattr(cli.svc_relatorios_docx, "exportar_relatorios_docx", fake_exportar)

    codigo, saida = _executar(
        [
            "--json",
            "exportar-docx",
            "--database",
            "db-relatorios",
            "--de",
            "2026-07-01",
            "--ate",
            "2026-07-06",
            "--saida",
            str(tmp_path),
        ]
    )

    assert codigo == 0
    assert saida["dados"]["total"] == 1
    assert capturado["database_id"] == "db-relatorios"
    assert capturado["data_inicio"] == "2026-07-01"
    assert capturado["data_fim"] == "2026-07-06"
    assert capturado["campo_data"] == "Data"


def test_exportar_docx_usa_env_especifico_antes_do_database_padrao(monkeypatch, tmp_path: Path):
    capturado = {}
    monkeypatch.setenv("NOTION_REPORTS_DATABASE_ID", "db-relatorios")
    monkeypatch.setenv("NOTION_DATABASE_ID", "db-tarefas")
    monkeypatch.setattr(
        cli.svc_relatorios_docx,
        "exportar_relatorios_docx",
        lambda **kwargs: capturado.update(kwargs)
        or {
            "database_id": kwargs["database_id"],
            "periodo": {"de": kwargs["data_inicio"], "ate": kwargs["data_fim"]},
            "saida": str(kwargs["saida"]),
            "total": 0,
            "arquivos": [],
        },
    )

    codigo, _ = _executar(
        [
            "--json",
            "exportar-docx",
            "--de",
            "2026-07-01",
            "--ate",
            "2026-07-06",
            "--saida",
            str(tmp_path),
        ]
    )

    assert codigo == 0
    assert capturado["database_id"] == "db-relatorios"


def test_exportar_docx_humano_resume(monkeypatch, tmp_path: Path):
    monkeypatch.setattr(
        cli.svc_relatorios_docx,
        "exportar_relatorios_docx",
        lambda **kwargs: {
            "database_id": "db1",
            "periodo": {"de": "2026-07-01", "ate": "2026-07-06"},
            "saida": str(tmp_path),
            "total": 2,
            "arquivos": [],
        },
    )

    codigo, saida = _executar(
        [
            "exportar-docx",
            "--database",
            "db1",
            "--de",
            "2026-07-01",
            "--ate",
            "2026-07-06",
            "--saida",
            str(tmp_path),
        ]
    )

    assert codigo == 0
    assert "DOCX exportados: 2" in saida


# -- criar-database / importar-planilha / anexar-arquivo / mover ------------


class FakeNovosClient:
    def __init__(self):
        self.chamadas: list[tuple[str, object]] = []
        self.pagina = {"properties": {}}

    def criar_database(self, pagina_id, titulo, propriedades, **kwargs):
        self.chamadas.append(("criar_database", (pagina_id, titulo, propriedades, kwargs)))
        return {"id": "db_novo", "url": "https://notion.so/db_novo"}

    def mover_pagina(self, page_id, novo_pai_id, *, tipo_pai="page_id"):
        self.chamadas.append(("mover_pagina", (page_id, novo_pai_id, tipo_pai)))
        return {"id": page_id}

    def mover_database(self, database_id, novo_pai_id):
        self.chamadas.append(("mover_database", (database_id, novo_pai_id)))
        return {"id": database_id}

    def enviar_arquivo(self, conteudo, nome, content_type):
        self.chamadas.append(("enviar_arquivo", (nome, content_type)))
        return "upload-1"

    def obter_pagina(self, page_id):
        return self.pagina

    def atualizar_pagina(self, page_id, props):
        self.chamadas.append(("atualizar_pagina", (page_id, props)))
        return {"id": page_id}

    def consultar_database(self, database_id, page_size=1, filtro=None):
        return []

    def criar_pagina(self, database_id, props):
        self.chamadas.append(("criar_pagina", (database_id, props)))
        return {"id": "linha-nova"}


def test_criar_database_monta_schema_e_atalhos():
    fake = FakeNovosClient()
    codigo, saida = _executar(
        [
            "--json",
            "criar-database",
            "pag1",
            "Cadastro",
            "--prop",
            "Seguidores=numero",
            "--prop",
            "Plataforma=select",
            "--prefixo-id",
            "DVIP",
            "--inline",
        ],
        client=fake,
    )
    assert codigo == 0
    assert saida["dados"]["id"] == "db_novo"
    nome, (pagina, titulo, props, kwargs) = fake.chamadas[0]
    assert props["Seguidores"] == {"number": {}}
    assert props["Nome"] == {"title": {}}  # título automático
    assert kwargs["prefixo_id"] == "DVIP"
    assert kwargs["is_inline"] is True


def test_criar_database_tipo_invalido_da_erro_de_uso():
    codigo, saida = _executar(
        ["--json", "criar-database", "pag1", "X", "--prop", "Valor=moeda"],
        client=FakeNovosClient(),
    )
    assert codigo == 2
    assert "Tipos aceitos" in str(saida["erro"])


def test_importar_planilha_csv_upsert(tmp_path):
    planilha = tmp_path / "contas.csv"
    planilha.write_text("Nome,Seguidores\nConta A,1.614\n", encoding="utf-8")
    fake = FakeNovosClient()
    codigo, saida = _executar(
        ["--json", "importar-planilha", "db1", str(planilha), "--tipo", "Seguidores=numero"],
        client=fake,
    )
    assert codigo == 0
    assert saida["dados"]["criados"] == 1
    props = [c for c in fake.chamadas if c[0] == "criar_pagina"][0][1][1]
    assert props["Seguidores"] == {"number": 1614}


def test_anexar_arquivo_sobe_e_grava_propriedade(tmp_path):
    arquivo = tmp_path / "rel.docx"
    arquivo.write_bytes(b"x")
    fake = FakeNovosClient()
    codigo, saida = _executar(
        ["--json", "anexar-arquivo", "pag1", str(arquivo)], client=fake
    )
    assert codigo == 0
    assert saida["dados"]["upload_id"] == "upload-1"
    atualizacao = [c for c in fake.chamadas if c[0] == "atualizar_pagina"][0]
    assert "Arquivos e mídia" in atualizacao[1][1]


def test_mover_pagina_avisa_sobre_databases():
    fake = FakeNovosClient()
    codigo, saida = _executar(
        ["--json", "mover-pagina", "pag1", "pai2", "--tipo-pai", "database_id"],
        client=fake,
    )
    assert codigo == 0
    assert ("mover_pagina", ("pag1", "pai2", "database_id")) in fake.chamadas
    assert "mover-database" in saida["dados"]["aviso"]


def test_mover_database_reparenteia():
    fake = FakeNovosClient()
    codigo, saida = _executar(["--json", "mover-database", "db1", "pai2"], client=fake)
    assert codigo == 0
    assert ("mover_database", ("db1", "pai2")) in fake.chamadas


def test_guia_inclui_comandos_novos():
    codigo, saida = _executar(["--json", "guia"])
    comandos = {c["comando"] for c in saida["dados"]["comandos"]}
    assert {
        "criar-database",
        "importar-planilha",
        "anexar-arquivo",
        "mover-pagina",
        "mover-database",
    } <= comandos
