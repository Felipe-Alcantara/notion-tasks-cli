"""Configuração central do servidor — lida inteiramente do ambiente.

Nenhum segredo mora no repositório: o token do Notion, a ``SECRET_KEY`` do Django
e as demais opções vêm de variáveis de ambiente (ou de um ``.env`` local, ignorado
pelo git). Esta camada não conhece HTTP nem o Django — é só leitura de configuração,
para que ``config/settings.py`` e ``integrations/`` consumam um objeto estável.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

#: Raiz do repositório (``server/core/config.py`` → sobe três níveis).
REPO_RAIZ = Path(__file__).resolve().parents[2]

#: ``.env`` local opcional, no mesmo padrão usado por ``start_app.py``.
ENV_FILE = REPO_RAIZ / ".env"

# Nomes das variáveis de ambiente que o servidor lê.
ENV_SECRET_KEY = "DJANGO_SECRET_KEY"
ENV_DEBUG = "DJANGO_DEBUG"
ENV_ALLOWED_HOSTS = "DJANGO_ALLOWED_HOSTS"
ENV_NOTION_TOKEN = "NOTION_TOKEN"
ENV_NOTION_DATABASE_ID = "NOTION_DATABASE_ID"
ENV_DB_PATH = "OPERATIONAL_DB_PATH"

#: SECRET_KEY de desenvolvimento — só usada quando ``DEBUG`` e nenhuma foi definida.
#: Nunca deve ser usada em produção; ``settings.py`` exige a real quando ``DEBUG`` é off.
SECRET_KEY_DEV = "dev-inseguro-troque-em-producao"  # noqa: S105 - placeholder, não é segredo real


def carregar_env_file(caminho: Path = ENV_FILE) -> None:
    """Carrega pares ``CHAVE=valor`` de um ``.env`` para ``os.environ``.

    Não sobrescreve variáveis já definidas no ambiente (o ambiente real vence o
    arquivo) e ignora linhas vazias e comentários. Sem dependência externa, no mesmo
    espírito do leitor de ``.env`` de ``start_app.py``.
    """

    if not caminho.exists():
        return
    for linha in caminho.read_text(encoding="utf-8").splitlines():
        linha = linha.strip()
        if not linha or linha.startswith("#") or "=" not in linha:
            continue
        chave, valor = linha.split("=", 1)
        chave, valor = chave.strip(), valor.strip()
        if chave and chave not in os.environ:
            os.environ[chave] = valor


def _bool_env(nome: str, padrao: bool = False) -> bool:
    """Lê uma variável de ambiente como booleano (1/true/yes/on)."""

    valor = os.environ.get(nome)
    if valor is None:
        return padrao
    return valor.strip().lower() in ("1", "true", "yes", "on", "sim")


def _lista_env(nome: str) -> list[str]:
    """Lê uma variável separada por vírgulas como lista (sem itens vazios)."""

    valor = os.environ.get(nome, "")
    return [item.strip() for item in valor.split(",") if item.strip()]


@dataclass(frozen=True)
class Config:
    """Configuração resolvida do servidor, sem expor segredos em ``repr``."""

    secret_key: str
    debug: bool
    allowed_hosts: list[str]
    notion_token: str | None
    notion_database_id: str | None
    database_path: Path

    def __repr__(self) -> str:  # nunca vazar o token/secret em log
        token = "definido" if self.notion_token else "ausente"
        return (
            f"Config(debug={self.debug}, allowed_hosts={self.allowed_hosts}, "
            f"notion_token={token}, notion_database_id="
            f"{'definido' if self.notion_database_id else 'ausente'}, "
            f"database_path={self.database_path})"
        )


def carregar_config(carregar_dotenv: bool = True) -> Config:
    """Resolve a configuração a partir do ambiente (e do ``.env`` local, se houver).

    Args:
        carregar_dotenv: Quando ``True`` (padrão), popula o ``os.environ`` a partir
            do ``.env`` antes de ler — sem sobrescrever o que já está no ambiente.

    Returns:
        Um :class:`Config` imutável.
    """

    if carregar_dotenv:
        carregar_env_file()

    debug = _bool_env(ENV_DEBUG, padrao=False)
    secret_key = os.environ.get(ENV_SECRET_KEY, "").strip()
    if not secret_key:
        # Em dev seguimos com uma chave previsível; em produção, settings exige a real.
        secret_key = SECRET_KEY_DEV

    allowed_hosts = _lista_env(ENV_ALLOWED_HOSTS) or (
        ["*"] if debug else ["localhost", "127.0.0.1"]
    )

    db_path = os.environ.get(ENV_DB_PATH, "").strip()
    database_path = Path(db_path) if db_path else (REPO_RAIZ / "operacional.sqlite3")

    notion_token = os.environ.get(ENV_NOTION_TOKEN, "").strip() or None
    notion_database_id = os.environ.get(ENV_NOTION_DATABASE_ID, "").strip() or None

    return Config(
        secret_key=secret_key,
        debug=debug,
        allowed_hosts=allowed_hosts,
        notion_token=notion_token,
        notion_database_id=notion_database_id,
        database_path=database_path,
    )
