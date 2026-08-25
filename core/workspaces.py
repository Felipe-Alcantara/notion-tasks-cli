"""Perfis locais para operar varios workspaces do Notion.

O ``.env`` continua sendo suportado para compatibilidade, mas perfis permitem
guardar varias credenciais locais e escolher qual workspace usar por comando.
Tokens nunca aparecem em ``repr`` nem nas respostas publicas.
"""

from __future__ import annotations

import json
import os
import shutil
import sys
import sysconfig
from collections.abc import Mapping
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Any

from notion_starter.constants import NOTION_TOKEN_PREFIX

APP_NOME = "notion-tasks"
ARQUIVO_NOME = ".notion-workspaces.json"

#: Onde o store morava ate 24/08/2026: ao lado do pacote instalado. Continua
#: sendo lido para migrar quem ja tinha perfis salvos.
ARQUIVO_LEGADO = Path(__file__).resolve().parents[1] / ARQUIVO_NOME


def _enderecos_legados() -> tuple[Path, ...]:
    """Todos os "ao lado do pacote" que ja valeram, sem repetir endereco.

    Nao era um lugar so: no modo editavel o pacote roda da raiz do repositorio
    (``ARQUIVO_LEGADO``), no nao-editavel roda de um ``site-packages``. Trocar o
    modo de instalacao trocava o endereco, e olhar so um deles fazia a CLI
    responder "Nenhum perfil configurado" com o arquivo intacto no outro.

    O ``site-packages`` vem de ``sysconfig``, e nao de um ``parents[n]`` do
    fonte: no modo editavel o fonte mora no repositorio, entao subir diretorios
    a partir dele aponta para dentro do proprio repositorio — nunca para a pasta
    de instalacao onde o store realmente ficou.
    """

    candidatos = [ARQUIVO_LEGADO]
    for chave in ("purelib", "platlib"):
        pasta = sysconfig.get_paths().get(chave)
        if pasta:
            candidatos.append(Path(pasta) / ARQUIVO_NOME)
    unicos: list[Path] = []
    for caminho in candidatos:
        if caminho not in unicos:
            unicos.append(caminho)
    return tuple(unicos)


ARQUIVOS_LEGADOS = _enderecos_legados()

ENV_PERFIL = "NOTION_PROFILE"
ENV_TOKEN = "NOTION_TOKEN"
ENV_DATABASE = "NOTION_DATABASE_ID"


def decidir_pasta_configuracao(*, windows: bool, ambiente: Mapping[str, str], home: Path) -> Path:
    """Decide a pasta de configuracao a partir do sistema, ambiente e home.

    Funcao pura de proposito: o sistema entra por parametro em vez de ser lido
    de ``os.name``. Testar a variante do Windows trocando ``os.name`` no
    processo faria o proprio ``pathlib`` passar a construir ``WindowsPath`` e
    quebrar em maquina POSIX — o teste derrubaria o interpretador, nao o
    comportamento.
    """

    if windows:
        base = ambiente.get("APPDATA")
        raiz = Path(base) if base else home / "AppData" / "Roaming"
    else:
        base = ambiente.get("XDG_CONFIG_HOME")
        raiz = Path(base) if base else home / ".config"
    return raiz / APP_NOME


def pasta_configuracao() -> Path:
    """Pasta de configuracao do usuario, conforme a convencao do sistema.

    ``%APPDATA%/notion-tasks`` no Windows, ``$XDG_CONFIG_HOME/notion-tasks``
    (com ``~/.config`` de padrao) no restante.
    """

    return decidir_pasta_configuracao(
        windows=os.name == "nt", ambiente=os.environ, home=Path.home()
    )


def caminho_padrao() -> Path:
    """Endereco canonico do store de perfis."""

    return pasta_configuracao() / ARQUIVO_NOME


#: Resolvido no import para que a suite consiga trocar por ``tmp_path``.
ARQUIVO_PADRAO = caminho_padrao()


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
    _garantir_pasta(caminho.parent)
    caminho.write_text(
        json.dumps(dados, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    _restringir(caminho, 0o600)


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


def definir_database(
    database_id: str,
    alias: str | None = None,
    caminho: Path | None = None,
) -> WorkspaceProfile:
    """Grava o database padrao no perfil resolvido (o ativo, por padrao).

    Existe porque ``escolher-database`` gravava so num ``.env`` ao lado do
    pacote instalado: o perfil ativo continuava sem ``database_id``, vencia o
    ``.env`` em silencio e o comando seguinte falhava com "NOTION_DATABASE_ID
    nao configurado". Escolher database e escolher perfil precisam gravar no
    mesmo lugar.

    Args:
        database_id: Database que passa a ser o padrao do perfil.
        alias: Perfil a atualizar; ``None`` usa o resolvido/ativo.
        caminho: Store alternativo (a suite passa ``tmp_path``).

    Returns:
        O perfil ja atualizado.

    Raises:
        WorkspaceConfigError: Se nao houver perfil para atualizar.
    """

    perfil = resolver_perfil(alias, caminho)
    if perfil is None:
        raise WorkspaceConfigError(
            "Nenhum perfil ativo para guardar o database. "
            "Crie um com 'perfis adicionar <alias> --token ... --ativar'."
        )
    limpo = _texto_opcional(database_id)
    if limpo is None:
        raise WorkspaceConfigError("database_id nao pode ficar vazio.")
    store = carregar_store(caminho)
    perfis = dict(store.perfis)
    atualizado = replace(perfil, database_id=limpo)
    perfis[perfil.alias] = atualizado
    salvar_store(WorkspaceStore(ativo=store.ativo, perfis=perfis), caminho)
    os.environ[ENV_DATABASE] = limpo
    return atualizado


def caminho_em_uso(caminho: Path | None = None) -> Path:
    """Arquivo de perfis efetivamente em uso, ja considerada a migracao."""

    return _caminho(caminho)


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
    """Resolve o arquivo de perfis, migrando o endereco antigo na primeira vez.

    Um caminho explicito (a suite, ou quem quiser outro store) manda e nao
    dispara migracao nenhuma.
    """

    if caminho is not None:
        return caminho
    return _migrar_legado(ARQUIVO_PADRAO)


def _migrar_legado(destino: Path) -> Path:
    """Move o store do endereco antigo para o canonico, uma unica vez.

    Ate 24/08/2026 o arquivo morava ao lado do pacote instalado, entao trocar o
    modo de instalacao (editavel <-> nao editavel) trocava o endereco e a CLI
    respondia "Nenhum perfil configurado" — parecia perda de dado, e cada modo
    deixava mais uma copia de tokens espalhada pelo disco. Por isso a busca
    percorre ``ARQUIVOS_LEGADOS``, e nao um endereco unico: o store escrito no
    modo nao-editavel fica no ``site-packages``, invisivel para quem so olha a
    raiz do repositorio.

    Se a migracao nao for possivel (disco somente leitura, permissao), o antigo
    continua sendo usado: e melhor manter o usuario funcionando no lugar errado
    do que fingir que ele nao tem perfil nenhum.
    """

    if destino.exists():
        return destino
    origem = next((caminho for caminho in ARQUIVOS_LEGADOS if caminho.exists()), None)
    if origem is None:
        return destino
    try:
        _garantir_pasta(destino.parent)
        shutil.move(str(origem), str(destino))
        _restringir(destino, 0o600)
    except OSError:
        return origem
    print(f"Perfis migrados para {destino}", file=sys.stderr)
    return destino


def _garantir_pasta(pasta: Path) -> None:
    """Cria a pasta do store, restringindo a permissao **apenas se a criou**.

    A restricao vale para a pasta que este codigo passa a existir; nao para uma
    que ja estava la. Sem essa distincao, um caminho de store apontado para
    dentro da HOME faria a CLI fechar a HOME inteira em 0700.
    """

    if pasta.exists():
        return
    pasta.mkdir(parents=True, exist_ok=True)
    _restringir(pasta, 0o700)


def _restringir(alvo: Path, modo: int) -> None:
    """Restringe a permissao, ignorando sistemas que nao suportam chmod."""

    try:
        os.chmod(alvo, modo)
    except OSError:
        pass


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
