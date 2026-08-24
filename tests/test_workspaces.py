"""Testes dos perfis locais de workspaces do Notion."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

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


# --- Endereco do store: pasta de configuracao do usuario -------------------
#
# Ate 24/08/2026 o store morava ao lado do pacote instalado, entao trocar o modo
# de instalacao trocava o endereco e a CLI dizia "Nenhum perfil configurado".
# Estes testes prendem o endereco a convencao do sistema e cobrem a migracao.


def test_pasta_de_configuracao_respeita_o_xdg_no_posix(tmp_path):
    pasta = workspaces.decidir_pasta_configuracao(
        windows=False,
        ambiente={"XDG_CONFIG_HOME": str(tmp_path / "config")},
        home=tmp_path,
    )

    assert pasta == tmp_path / "config" / "notion-tasks"


def test_pasta_de_configuracao_cai_para_dot_config_sem_xdg(tmp_path):
    pasta = workspaces.decidir_pasta_configuracao(
        windows=False, ambiente={}, home=tmp_path
    )

    assert pasta == tmp_path / ".config" / "notion-tasks"


def test_pasta_de_configuracao_usa_appdata_no_windows(tmp_path):
    pasta = workspaces.decidir_pasta_configuracao(
        windows=True, ambiente={"APPDATA": str(tmp_path / "Roaming")}, home=tmp_path
    )

    assert pasta == tmp_path / "Roaming" / "notion-tasks"


def test_windows_sem_appdata_cai_para_o_roaming_da_home(tmp_path):
    pasta = workspaces.decidir_pasta_configuracao(
        windows=True, ambiente={}, home=tmp_path
    )

    assert pasta == tmp_path / "AppData" / "Roaming" / "notion-tasks"


def test_endereco_do_store_nao_depende_de_onde_o_pacote_esta_instalado():
    """O motivo de existir desta mudanca, preso num teste.

    Roda num processo separado de proposito. A fixture ``perfis_isolados``
    troca ``ARQUIVO_PADRAO`` por ``tmp_path`` em todo teste — necessario para
    o perfil real nao vazar para a suite, mas isso apaga justamente o valor que
    este teste precisa observar: o que o modulo resolve no import. Medido: com
    a assercao feita dentro do processo da suite, voltar o caminho a ser
    derivado de ``__file__`` passava despercebido.
    """

    codigo = (
        "from core import workspaces as w;"
        "print(w.ARQUIVO_PADRAO);"
        "print(w.caminho_padrao())"
    )
    saida = subprocess.run(
        [sys.executable, "-c", codigo],
        cwd=Path(__file__).resolve().parents[1],
        capture_output=True,
        text=True,
        check=True,
    ).stdout.split()
    resolvido_no_import, canonico = Path(saida[0]), Path(saida[1])

    assert resolvido_no_import == canonico
    pasta_do_pacote = Path(workspaces.__file__).resolve().parents[1]
    assert pasta_do_pacote not in resolvido_no_import.parents


def test_migra_o_store_antigo_na_primeira_leitura(monkeypatch, tmp_path, capsys):
    legado = tmp_path / "antigo" / ".notion-workspaces.json"
    legado.parent.mkdir()
    workspaces.adicionar_perfil(alias="pessoal", token=TOKEN_1, caminho=legado)
    novo = tmp_path / "config" / "notion-tasks" / ".notion-workspaces.json"
    monkeypatch.setattr(workspaces, "ARQUIVO_LEGADO", legado)
    monkeypatch.setattr(workspaces, "ARQUIVO_PADRAO", novo)

    store = workspaces.carregar_store()

    assert "pessoal" in store.perfis
    assert novo.exists()
    # O antigo tem que SAIR: cada copia esquecida e mais um token no disco.
    assert not legado.exists()
    assert "migrados" in capsys.readouterr().err


def test_store_migrado_continua_restrito_ao_dono(monkeypatch, tmp_path):
    if os.name == "nt":
        pytest.skip("Permissao POSIX nao se aplica ao Windows.")
    legado = tmp_path / "antigo" / ".notion-workspaces.json"
    legado.parent.mkdir()
    workspaces.adicionar_perfil(alias="pessoal", token=TOKEN_1, caminho=legado)
    novo = tmp_path / "config" / "notion-tasks" / ".notion-workspaces.json"
    monkeypatch.setattr(workspaces, "ARQUIVO_LEGADO", legado)
    monkeypatch.setattr(workspaces, "ARQUIVO_PADRAO", novo)

    workspaces.carregar_store()

    assert novo.stat().st_mode & 0o777 == 0o600
    assert novo.parent.stat().st_mode & 0o777 == 0o700


def test_nao_migra_quando_o_canonico_ja_existe(monkeypatch, tmp_path):
    legado = tmp_path / "antigo" / ".notion-workspaces.json"
    legado.parent.mkdir()
    workspaces.adicionar_perfil(alias="antigo", token=TOKEN_1, caminho=legado)
    novo = tmp_path / "config" / ".notion-workspaces.json"
    workspaces.adicionar_perfil(alias="atual", token=TOKEN_2, caminho=novo)
    monkeypatch.setattr(workspaces, "ARQUIVO_LEGADO", legado)
    monkeypatch.setattr(workspaces, "ARQUIVO_PADRAO", novo)

    store = workspaces.carregar_store()

    assert set(store.perfis) == {"atual"}
    assert legado.exists()


def test_sem_nenhum_dos_dois_a_lista_e_vazia(monkeypatch, tmp_path):
    monkeypatch.setattr(workspaces, "ARQUIVO_LEGADO", tmp_path / "nao-existe.json")
    monkeypatch.setattr(workspaces, "ARQUIVO_PADRAO", tmp_path / "config" / "novo.json")

    store = workspaces.carregar_store()

    assert store.perfis == {}
    # Nada de criar pasta para um store que nunca existiu.
    assert not (tmp_path / "config").exists()


def test_caminho_explicito_nunca_dispara_migracao(monkeypatch, tmp_path):
    legado = tmp_path / "antigo" / ".notion-workspaces.json"
    legado.parent.mkdir()
    workspaces.adicionar_perfil(alias="pessoal", token=TOKEN_1, caminho=legado)
    monkeypatch.setattr(workspaces, "ARQUIVO_LEGADO", legado)
    monkeypatch.setattr(workspaces, "ARQUIVO_PADRAO", tmp_path / "config" / "novo.json")

    store = workspaces.carregar_store(caminho=tmp_path / "outro.json")

    assert store.perfis == {}
    assert legado.exists()


def test_pasta_preexistente_nao_tem_a_permissao_alterada(monkeypatch, tmp_path):
    """Salvar num caminho dentro de uma pasta que ja existe nao mexe nela.

    Sem esta garantia, um store apontado para dentro da HOME faria a CLI
    fechar a HOME inteira em 0700.
    """

    if os.name == "nt":
        pytest.skip("Permissao POSIX nao se aplica ao Windows.")
    pasta = tmp_path / "compartilhada"
    pasta.mkdir(mode=0o755)
    antes = pasta.stat().st_mode & 0o777

    workspaces.adicionar_perfil(alias="pessoal", token=TOKEN_1, caminho=pasta / "s.json")

    assert pasta.stat().st_mode & 0o777 == antes
