"""Perfis locais para operar varios workspaces do Notion.

O ``.env`` continua sendo suportado para compatibilidade, mas perfis permitem
guardar varias credenciais locais e escolher qual workspace usar por comando.
Tokens nunca aparecem em ``repr`` nem nas respostas publicas.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from notion_starter.constants import NOTION_TOKEN_PREFIX

ARQUIVO_PADRAO = Path(__file__).resolve().parents[1] / ".notion-workspaces.json"
ENV_PERFIL = "NOTION_PROFILE"
ENV_TOKEN = "NOTION_TOKEN"
ENV_DATABASE = "NOTION_DATABASE_ID"


class WorkspaceConfigError(ValueError):
    """Erro previsivel de configuracao dos perfis locais."""


@dataclass(frozen=True)
class WorkspaceProfile:
    """Credenciais e defaults de um workspace salvo localmente."""

    alias: str
    token: str
    database_id: str | None = None
    nome: str | None = None
    descricao: str | None = None

    def __repr__(self) -> str:
        return (
            "WorkspaceProfile("
            f"alias={self.alias!r}, token=definido, "
            f"database_id={'definido' if self.database_id else 'ausente'}, "
            f"nome={self.nome!r})"
        )

    def publico(self, *, ativo: bool = False) -> dict[str, Any]:
        """Representacao segura para CLI/JSON, sem vazar token."""

        return {
            "alias": self.alias,
            "nome": self.nome or "",
            "descricao": self.descricao or "",
            "database_id": self.database_id or "",
            "token": _mascarar_token(self.token),
            "ativo": ativo,
        }


@dataclass(frozen=True)
class WorkspaceStore:
    """Arquivo local com todos os perfis conhecidos."""

    ativo: str | None
    perfis: dict[str, WorkspaceProfile]

    def publico(self) -> dict[str, Any]:
        return {
            "ativo": self.ativo or "",
            "perfis": [
                perfil.publico(ativo=alias == self.ativo)
                for alias, perfil in sorted(self.perfis.items())
            ],
        }


def carregar_store(caminho: Path | None = None) -> WorkspaceStore:
    """Carrega o arquivo de perfis; arquivo ausente equivale a lista vazia."""

    caminho = _caminho(caminho)
    if not caminho.exists():
        return WorkspaceStore(ativo=None, perfis={})
    try:
        dados = json.loads(caminho.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise WorkspaceConfigError(f"Arquivo de perfis invalido: {caminho}") from exc
    if not isinstance(dados, dict):
        raise WorkspaceConfigError("Arquivo de perfis precisa conter um objeto JSON.")

    bruto_perfis = dados.get("perfis", {})
    if not isinstance(bruto_perfis, dict):
        raise WorkspaceConfigError("Campo 'perfis' precisa ser um objeto.")

    perfis: dict[str, WorkspaceProfile] = {}
    for alias, bruto in bruto_perfis.items():
        if not isinstance(bruto, dict):
            raise WorkspaceConfigError(f"Perfil '{alias}' precisa ser um objeto.")
        perfil = WorkspaceProfile(
            alias=_normalizar_alias(str(alias)),
            token=_validar_token(str(bruto.get("token", ""))),
            database_id=_texto_opcional(bruto.get("database_id")),
            nome=_texto_opcional(bruto.get("nome")),
            descricao=_texto_opcional(bruto.get("descricao")),
        )
        perfis[perfil.alias] = perfil

    ativo = _texto_opcional(dados.get("ativo"))
    if ativo and ativo not in perfis:
        ativo = None
    return WorkspaceStore(ativo=ativo, perfis=perfis)


def salvar_store(store: WorkspaceStore, caminho: Path | None = None) -> None:
    """Persiste os perfis em JSON estavel e restrito ao arquivo local."""

    caminho = _caminho(caminho)
    dados = {
        "ativo": store.ativo,
        "perfis": {
            alias: {
                "token": perfil.token,
                "database_id": perfil.database_id,
                "nome": perfil.nome,
                "descricao": perfil.descricao,
            }
            for alias, perfil in sorted(store.perfis.items())
        },
    }
    caminho.write_text(
        json.dumps(dados, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    try:
        os.chmod(caminho, 0o600)
    except OSError:
        pass


def adicionar_perfil(
    *,
    alias: str,
    token: str,
    database_id: str | None = None,
    nome: str | None = None,
    descricao: str | None = None,
    ativar: bool = False,
    sobrescrever: bool = False,
    caminho: Path | None = None,
) -> WorkspaceProfile:
    """Cria ou atualiza um perfil local de workspace."""

    alias_normalizado = _normalizar_alias(alias)
    store = carregar_store(caminho)
    if alias_normalizado in store.perfis and not sobrescrever:
        raise WorkspaceConfigError(
            f"Perfil '{alias_normalizado}' ja existe. Use --sobrescrever para atualizar."
        )
    perfil = WorkspaceProfile(
        alias=alias_normalizado,
        token=_validar_token(token),
        database_id=_texto_opcional(database_id),
        nome=_texto_opcional(nome),
        descricao=_texto_opcional(descricao),
    )
    perfis = dict(store.perfis)
    perfis[alias_normalizado] = perfil
    ativo = alias_normalizado if ativar or not store.ativo else store.ativo
    salvar_store(WorkspaceStore(ativo=ativo, perfis=perfis), caminho)
    return perfil


def selecionar_perfil(alias: str, caminho: Path | None = None) -> WorkspaceProfile:
    """Marca um perfil como ativo e devolve suas credenciais."""

    alias_normalizado = _normalizar_alias(alias)
    store = carregar_store(caminho)
    perfil = store.perfis.get(alias_normalizado)
    if perfil is None:
        raise WorkspaceConfigError(f"Perfil '{alias_normalizado}' nao encontrado.")
    salvar_store(WorkspaceStore(ativo=alias_normalizado, perfis=store.perfis), caminho)
    return perfil


def remover_perfil(
    alias: str,
    *,
    confirmar: bool,
    caminho: Path | None = None,
) -> WorkspaceProfile:
    """Remove um perfil salvo; exige confirmacao explicita."""

    if not confirmar:
        raise WorkspaceConfigError("Remover perfil apaga credenciais locais. Repita com --sim.")
    alias_normalizado = _normalizar_alias(alias)
    store = carregar_store(caminho)
    perfil = store.perfis.get(alias_normalizado)
    if perfil is None:
        raise WorkspaceConfigError(f"Perfil '{alias_normalizado}' nao encontrado.")
    perfis = dict(store.perfis)
    del perfis[alias_normalizado]
    ativo = None if store.ativo == alias_normalizado else store.ativo
    salvar_store(WorkspaceStore(ativo=ativo, perfis=perfis), caminho)
    return perfil


def resolver_perfil(
    alias: str | None = None,
    caminho: Path | None = None,
) -> WorkspaceProfile | None:
    """Resolve o perfil pedido, o env ``NOTION_PROFILE`` ou o perfil ativo."""

    store = carregar_store(caminho)
    escolhido = _texto_opcional(alias) or _texto_opcional(os.environ.get(ENV_PERFIL)) or store.ativo
    if not escolhido:
        return None
    alias_normalizado = _normalizar_alias(escolhido)
    perfil = store.perfis.get(alias_normalizado)
    if perfil is None:
        raise WorkspaceConfigError(f"Perfil '{alias_normalizado}' nao encontrado.")
    return perfil


def aplicar_perfil(
    alias: str | None = None,
    caminho: Path | None = None,
) -> WorkspaceProfile | None:
    """Aplica o perfil resolvido ao processo atual.

    A borda existente continua lendo ``NOTION_TOKEN`` e ``NOTION_DATABASE_ID``.
    Esta funcao faz a ponte sem espalhar conhecimento de perfis pelos comandos.
    """

    perfil = resolver_perfil(alias, caminho)
    if perfil is None:
        return None
    os.environ[ENV_TOKEN] = perfil.token
    if perfil.database_id:
        os.environ[ENV_DATABASE] = perfil.database_id
    else:
        os.environ.pop(ENV_DATABASE, None)
    os.environ[ENV_PERFIL] = perfil.alias
    return perfil


def _caminho(caminho: Path | None) -> Path:
    return caminho or ARQUIVO_PADRAO


def _normalizar_alias(alias: str) -> str:
    limpo = alias.strip().lower()
    if not limpo:
        raise WorkspaceConfigError("Alias do perfil nao pode ficar vazio.")
    permitidos = set("abcdefghijklmnopqrstuvwxyz0123456789-_")
    if any(caractere not in permitidos for caractere in limpo):
        raise WorkspaceConfigError("Alias deve usar apenas letras, numeros, '-' ou '_'.")
    return limpo


def _validar_token(token: str) -> str:
    limpo = token.strip()
    if not limpo:
        raise WorkspaceConfigError("Token do Notion nao pode ficar vazio.")
    if not limpo.startswith(NOTION_TOKEN_PREFIX):
        raise WorkspaceConfigError(f"Token do Notion deve comecar com '{NOTION_TOKEN_PREFIX}'.")
    return limpo


def _texto_opcional(valor: object) -> str | None:
    if valor is None:
        return None
    texto = str(valor).strip()
    return texto or None


def _mascarar_token(token: str) -> str:
    if len(token) <= 12:
        return "***"
    return f"{token[:6]}...{token[-4:]}"
