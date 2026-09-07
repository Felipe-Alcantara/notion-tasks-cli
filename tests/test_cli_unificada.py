"""Testes da entrada distribuída, sem rede, token ou instalação real."""

from __future__ import annotations

import json
import socket

import pytest

from cli import unificada


def test_version_mostra_a_distribuicao_unica(capsys):
    """A entrada pública revela uma versão antes de exigir autenticação."""

    with pytest.raises(SystemExit) as exc_info:
        unificada.main(["--version"])

    assert exc_info.value.code == 0
    assert capsys.readouterr().out.strip() == "notion-automacoes 0.3.0"


def test_tasks_delega_sem_reescrever_os_subcomandos(monkeypatch):
    """A fachada preserva a sintaxe e a implementação madura de notion-tasks."""

    chamadas = []

    class Legacy:
        @staticmethod
        def main(argumentos):
            chamadas.append(argumentos)
            return 7

    monkeypatch.setattr(unificada, "importlib", unificada.importlib)
    monkeypatch.setattr("cli.notion_tasks.main", Legacy.main)

    codigo = unificada.main(["--perfil", "pessoal", "--json", "tasks", "listar"])

    assert codigo == 7
    assert chamadas == [["--json", "--perfil", "pessoal", "listar"]]


def test_tasks_help_chega_ao_guia_legado(monkeypatch):
    """A forma documentada ``tasks --help`` mantém o guia completo da CLI."""

    chamadas = []
    monkeypatch.setattr(
        "cli.notion_tasks.main",
        lambda argumentos: chamadas.append(argumentos) or 0,
    )

    assert unificada.main(["tasks", "--help"]) == 0
    assert chamadas == [["--help"]]


def test_auth_delega_para_perfis_com_flags_globais(monkeypatch):
    """O atalho auth continua usando o store persistente já existente."""

    chamadas = []
    monkeypatch.setattr(
        "cli.notion_tasks.main",
        lambda argumentos: chamadas.append(argumentos) or 0,
    )

    assert unificada.main(["--json", "auth", "listar"]) == 0
    assert chamadas == [["--json", "perfis", "listar"]]


def test_doctor_funciona_sem_token_e_nao_exibe_credencial(monkeypatch, tmp_path, capsys):
    """Doctor deve ser útil no primeiro comando, antes de qualquer token."""

    # ``pasta_configuracao`` usa XDG no POSIX e APPDATA no Windows. Cobrir os
    # dois evita que o perfil real da máquina entre no diagnóstico durante a
    # suíte, independentemente do sistema operacional.
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
    monkeypatch.setenv("APPDATA", str(tmp_path))
    monkeypatch.delenv("NOTION_TOKEN", raising=False)
    monkeypatch.setattr(
        socket,
        "create_connection",
        lambda *args, **kwargs: socket.socket(socket.AF_INET, socket.SOCK_STREAM),
    )

    codigo = unificada.main(["--json", "doctor"])
    saida = json.loads(capsys.readouterr().out)

    assert codigo == 0
    assert saida["ok"] is True
    assert saida["perfis"]["caminho"] == str(
        tmp_path / "notion-tasks" / ".notion-workspaces.json"
    )
    assert saida["perfis"]["quantidade"] == 0
    assert saida["perfis"]["ativo"] == ""
    assert any(
        item["nome"] == "Credencial" and item["estado"] == "aviso"
        for item in saida["checks"]
    )
    assert "NOTION_TOKEN" not in json.dumps(saida)


def test_update_apenas_imprime_comando_e_nao_executa(monkeypatch, capsys):
    """O update não pode alterar o ambiente sem uma confirmação externa."""

    monkeypatch.setattr(
        unificada,
        "_gerenciador_atualizacao",
        lambda: ("pipx", ["pipx", "upgrade", "notion-automacoes"], "teste"),
    )

    codigo = unificada.main(["update"])
    saida = capsys.readouterr().out

    assert codigo == 0
    assert "pipx upgrade notion-automacoes" in saida
    assert "Nenhum comando foi executado." in saida


def test_app_sem_extra_dá_instrução_de_instalação(monkeypatch, capsys):
    """Sem o extra opcional, app start falha com uma ação reparável."""

    real_import = unificada.importlib.import_module

    def importar(nome):
        if nome == "start_app":
            raise ModuleNotFoundError("start_app")
        return real_import(nome)

    monkeypatch.setattr(unificada.importlib, "import_module", importar)

    codigo = unificada.main(["app", "start"])

    assert codigo == 2
    assert "notion-automacoes[app]" in capsys.readouterr().out


def test_mcp_isola_o_servidor_em_processo_separado(monkeypatch):
    """O pacote app não pode reutilizar o ``core`` já carregado pela CLI."""

    chamadas = []
    monkeypatch.setattr(unificada, "_importavel", lambda nome: nome == "server.mcp_server")
    monkeypatch.setattr(
        unificada.subprocess,
        "call",
        lambda comando: chamadas.append(comando) or 0,
    )

    assert unificada.main(["mcp", "start", "--transport", "streamable-http"]) == 0
    assert chamadas == [
        [
            unificada.sys.executable,
            "-m",
            "server.mcp_server",
            "--transport",
            "streamable-http",
        ]
    ]
