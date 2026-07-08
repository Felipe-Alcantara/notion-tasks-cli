"""Testes dos perfis locais de workspaces do Notion."""

from __future__ import annotations

import json

import pytest

from core import workspaces

TOKEN_1 = "ntn_" + "a" * 20
TOKEN_2 = "ntn_" + "b" * 20


def test_adicionar_perfil_salva_token_mas_retorna_publico_mascarado(tmp_path):
    arquivo = tmp_path / "perfis.json"

    perfil = workspaces.adicionar_perfil(
        alias="Trabalho",
        token=TOKEN_1,
        database_id="db1",
        nome="Workspace Trabalho",
        ativar=True,
        caminho=arquivo,
    )

    assert perfil.alias == "trabalho"
    assert perfil.publico(ativo=True) == {
        "alias": "trabalho",
        "nome": "Workspace Trabalho",
        "descricao": "",
        "database_id": "db1",
        "token": "ntn_aa...aaaa",
        "ativo": True,
    }
    bruto = json.loads(arquivo.read_text(encoding="utf-8"))
    assert bruto["perfis"]["trabalho"]["token"] == TOKEN_1


def test_permite_varios_perfis_e_aplica_o_escolhido(tmp_path, monkeypatch):
    arquivo = tmp_path / "perfis.json"
    workspaces.adicionar_perfil(alias="pessoal", token=TOKEN_1, database_id="db1", caminho=arquivo)
    workspaces.adicionar_perfil(alias="cliente", token=TOKEN_2, database_id="db2", caminho=arquivo)
    monkeypatch.setenv("NOTION_TOKEN", "ntn_original")
    monkeypatch.setenv("NOTION_DATABASE_ID", "db-original")
    monkeypatch.setenv("NOTION_PROFILE", "pessoal")

    perfil = workspaces.aplicar_perfil("cliente", caminho=arquivo)

    assert perfil is not None
    assert perfil.alias == "cliente"
    assert workspaces.os.environ["NOTION_TOKEN"] == TOKEN_2
    assert workspaces.os.environ["NOTION_DATABASE_ID"] == "db2"
    assert workspaces.os.environ["NOTION_PROFILE"] == "cliente"


def test_env_notion_profile_resolve_perfil_sem_alias(tmp_path, monkeypatch):
    arquivo = tmp_path / "perfis.json"
    workspaces.adicionar_perfil(alias="pessoal", token=TOKEN_1, database_id="db1", caminho=arquivo)
    workspaces.adicionar_perfil(alias="cliente", token=TOKEN_2, database_id="db2", caminho=arquivo)
    monkeypatch.setenv("NOTION_PROFILE", "cliente")

    perfil = workspaces.resolver_perfil(caminho=arquivo)

    assert perfil is not None
    assert perfil.alias == "cliente"


def test_remover_perfil_exige_confirmacao(tmp_path):
    arquivo = tmp_path / "perfis.json"
    workspaces.adicionar_perfil(alias="pessoal", token=TOKEN_1, caminho=arquivo)

    with pytest.raises(workspaces.WorkspaceConfigError, match="--sim"):
        workspaces.remover_perfil("pessoal", confirmar=False, caminho=arquivo)


def test_recusa_alias_e_token_invalidos(tmp_path):
    arquivo = tmp_path / "perfis.json"

    with pytest.raises(workspaces.WorkspaceConfigError, match="Alias"):
        workspaces.adicionar_perfil(alias="Meu Workspace", token=TOKEN_1, caminho=arquivo)
    with pytest.raises(workspaces.WorkspaceConfigError, match="Token"):
        workspaces.adicionar_perfil(alias="ok", token="secret_x", caminho=arquivo)
