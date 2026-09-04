"""Borda da CLI distribuída do ecossistema Automações do Notion.

Este módulo só interpreta o comando de alto nível e delega as regras existentes
para a CLI de tarefas, o launcher do app e o servidor MCP. O comportamento de
domínio continua nos módulos consumidores e no ``notion-starter``.
"""

from __future__ import annotations

import argparse
import importlib
import importlib.metadata
import importlib.util
import json
import os
import shutil
import socket
import subprocess
import sys
from collections.abc import Sequence
from pathlib import Path
from typing import Any

DISTRIBUICAO = "notion-automacoes"
VERSAO_FONTE = "0.3.0"
PORTAS_APP = (8000, 5173)


def versao_distribuicao() -> str:
    """Retorna a versão instalada, com fallback útil durante o desenvolvimento."""

    try:
        return importlib.metadata.version(DISTRIBUICAO)
    except importlib.metadata.PackageNotFoundError:
        return VERSAO_FONTE


def construir_parser() -> argparse.ArgumentParser:
    """Monta o parser enxuto da entrada distribuída."""

    parser = argparse.ArgumentParser(
        prog="notion-automacoes",
        description=(
            "CLI única para tarefas, perfis, app local e servidor MCP do Notion. "
            "Use 'tasks --help' para os comandos completos de operação."
        ),
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"%(prog)s {versao_distribuicao()}",
        help="mostra a versão instalada",
    )
    parser.add_argument("--json", action="store_true", help="emite JSON quando aplicável")
    parser.add_argument(
        "--perfil",
        help="alias do workspace salvo; vale para tasks, app e mcp",
    )
    sub = parser.add_subparsers(dest="comando", required=True)

    tasks = sub.add_parser(
        "tasks",
        aliases=("tarefas",),
        add_help=False,
        help="opera tarefas, páginas e databases (preserva o comando notion-tasks)",
        description="Delegação para todos os subcomandos existentes de notion-tasks.",
    )
    tasks.add_argument(
        "--help",
        action="store_true",
        dest="ajuda",
        help="mostra o guia completo de notion-tasks",
    )
    tasks.add_argument("argumentos", nargs=argparse.REMAINDER)

    auth = sub.add_parser(
        "auth",
        aliases=("perfis",),
        add_help=False,
        help="gerencia perfis persistentes de workspace",
        description="Atalho para 'notion-tasks perfis'.",
    )
    auth.add_argument(
        "--help",
        action="store_true",
        dest="ajuda",
        help="mostra a ajuda de notion-tasks perfis",
    )
    auth.add_argument("argumentos", nargs=argparse.REMAINDER)

    app = sub.add_parser("app", help="controla o app local com SPA e API")
    app_sub = app.add_subparsers(dest="acao_app", required=True)
    app_sub.add_parser("start", help="inicia API e SPA empacotada")

    mcp = sub.add_parser("mcp", help="controla o servidor MCP")
    mcp_sub = mcp.add_subparsers(dest="acao_mcp", required=True)
    mcp_start = mcp_sub.add_parser("start", help="inicia o servidor MCP")
    mcp_start.add_argument(
        "--transport",
        choices=("stdio", "streamable-http"),
        default="stdio",
        help="transporte MCP (padrão: stdio)",
    )

    sub.add_parser(
        "doctor",
        help="verifica Python, dependências, perfis, rede e componentes opcionais",
    )
    sub.add_parser(
        "update",
        aliases=("atualizar",),
        help="mostra o comando seguro para atualizar a instalação",
    )
    return parser


def _aplicar_perfil(alias: str | None) -> None:
    """Aplica o perfil escolhido sem duplicar a regra existente de autenticação."""

    if not alias:
        return
    from core.workspaces import aplicar_perfil

    aplicar_perfil(alias)


def _argumentos_legacy(
    args: argparse.Namespace,
    comando: Sequence[str] = (),
) -> list[str]:
    """Prepara argumentos para ``notion-tasks``, mantendo sua ordem pública."""

    prefixo: list[str] = []
    if args.json:
        prefixo.append("--json")
    if args.perfil:
        prefixo.extend(("--perfil", args.perfil))
    argumentos = [*comando, *args.argumentos]
    if getattr(args, "ajuda", False):
        argumentos.append("--help")
    if not argumentos:
        argumentos = ["--help"]
    return [*prefixo, *argumentos]


def _delegar_tasks(args: argparse.Namespace) -> int:
    """Executa o parser legado e devolve seu código de saída."""

    from . import notion_tasks

    return int(notion_tasks.main(_argumentos_legacy(args)))


def _delegar_auth(args: argparse.Namespace) -> int:
    """Executa o gerenciamento de perfis através da implementação existente."""

    from . import notion_tasks

    return int(notion_tasks.main(_argumentos_legacy(args, ("perfis",))))


def _importavel(nome: str) -> bool:
    """Testa a presença de um módulo sem importá-lo nem executar efeitos colaterais."""

    try:
        return importlib.util.find_spec(nome) is not None
    except (ImportError, ModuleNotFoundError, ValueError):
        return False


def _status(nome: str, estado: str, detalhe: str, *, opcional: bool = False) -> dict[str, Any]:
    """Cria uma checagem serializável do diagnóstico."""

    return {"nome": nome, "estado": estado, "detalhe": detalhe, "opcional": opcional}


def _porta_disponivel(porta: int) -> bool:
    """Indica se não há processo aceitando conexões TCP na porta local."""

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.settimeout(0.2)
        return sock.connect_ex(("127.0.0.1", porta)) != 0


def _checar_perfis() -> dict[str, Any]:
    """Lê o store do usuário sem expor ou carregar tokens para a saída."""

    from core import workspaces

    caminho = workspaces.pasta_configuracao() / workspaces.ARQUIVO_NOME
    try:
        store = workspaces.carregar_store(caminho)
    except workspaces.WorkspaceConfigError as exc:
        return {
            "check": _status("Perfis", "erro", str(exc)),
            "caminho": str(caminho),
            "quantidade": 0,
            "ativo": "",
        }
    detalhe = f"{len(store.perfis)} perfil(is)"
    if store.ativo:
        detalhe += f" · ativo: {store.ativo}"
    else:
        detalhe += " · nenhum ativo"
    return {
        "check": _status("Perfis", "ok", detalhe),
        "caminho": str(caminho),
        "quantidade": len(store.perfis),
        "ativo": store.ativo or "",
    }


def diagnosticar() -> dict[str, Any]:
    """Executa diagnóstico seguro, sem exigir token e sem chamar a API do Notion."""

    checks: list[dict[str, Any]] = []
    py = f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
    python_ok = sys.version_info >= (3, 10)
    checks.append(
        _status(
            "Python",
            "ok" if python_ok else "erro",
            f"{py}{'' if python_ok else ' · requer 3.10+'}",
        )
    )

    starter_ok = _importavel("notion_starter")
    checks.append(
        _status(
            "notion-starter",
            "ok" if starter_ok else "erro",
            "importável" if starter_ok else "não instalado; reinstale a distribuição",
        )
    )

    perfis = _checar_perfis()
    checks.append(perfis["check"])
    token = bool(os.environ.get("NOTION_TOKEN", "").strip())
    checks.append(
        _status(
            "Credencial",
            "ok" if token or perfis["quantidade"] else "aviso",
            "token disponível no ambiente"
            if token
            else "nenhum token carregado (pode configurar depois)",
        )
    )

    try:
        with socket.create_connection(("api.notion.com", 443), timeout=2):
            rede_estado, rede_detalhe = "ok", "api.notion.com:443 acessível"
    except OSError as exc:
        rede_estado, rede_detalhe = "aviso", f"API não acessível agora ({type(exc).__name__})"
    checks.append(_status("Rede do Notion", rede_estado, rede_detalhe))

    app_ok = _importavel("start_app") and _importavel("server.mcp_server")
    checks.append(
        _status(
            "App local",
            "ok" if app_ok else "aviso",
            "launcher e servidor MCP importáveis"
            if app_ok
            else "extra app ausente; instale notion-automacoes[app]",
            opcional=True,
        )
    )
    django_ok = _importavel("django")
    mcp_ok = _importavel("mcp")
    checks.append(
        _status(
            "Django",
            "ok" if django_ok else "aviso",
            "instalado" if django_ok else "extra app não instalado",
            opcional=True,
        )
    )
    checks.append(
        _status(
            "SDK MCP",
            "ok" if mcp_ok else "aviso",
            "instalado" if mcp_ok else "extra app não instalado",
            opcional=True,
        )
    )

    for porta in PORTAS_APP:
        livre = _porta_disponivel(porta)
        checks.append(
            _status(
                f"Porta {porta}",
                "ok" if livre else "aviso",
                "livre" if livre else "ocupada por outro processo",
                opcional=True,
            )
        )

    return {
        "ok": not any(item["estado"] == "erro" for item in checks),
        "versao": versao_distribuicao(),
        "checks": checks,
        "perfis": {key: value for key, value in perfis.items() if key != "check"},
    }


def _gerenciador_atualizacao() -> tuple[str, list[str], str]:
    """Resolve o gerenciador provável e apenas monta o comando de atualização."""

    caminho_python = str(Path(sys.executable).resolve()).lower()
    prefixo = str(Path(sys.prefix).resolve()).lower()
    if os.environ.get("VIRTUAL_ENV") or sys.prefix != getattr(sys, "base_prefix", sys.prefix):
        return (
            "venv",
            [sys.executable, "-m", "pip", "install", "--upgrade", DISTRIBUICAO],
            "ambiente virtual ativo",
        )
    if "pipx" in caminho_python or "pipx" in prefixo:
        return "pipx", ["pipx", "upgrade", DISTRIBUICAO], "instalação gerenciada pelo pipx"
    if "uv" in caminho_python or "uv" in prefixo:
        return "uv", ["uv", "tool", "upgrade", DISTRIBUICAO], "instalação gerenciada pelo uv"
    if shutil.which("pipx"):
        return "pipx", ["pipx", "upgrade", DISTRIBUICAO], "pipx disponível no PATH"
    if shutil.which("uv"):
        return "uv", ["uv", "tool", "upgrade", DISTRIBUICAO], "uv disponível no PATH"
    return (
        "pip",
        [sys.executable, "-m", "pip", "install", "--upgrade", DISTRIBUICAO],
        "fallback do Python atual",
    )


def preparar_atualizacao() -> dict[str, Any]:
    """Informa como atualizar sem executar instalação ou alterar o ambiente."""

    gerenciador, comando, motivo = _gerenciador_atualizacao()
    return {
        "distribuicao": DISTRIBUICAO,
        "versao_atual": versao_distribuicao(),
        "gerenciador": gerenciador,
        "comando": comando,
        "motivo": motivo,
        "executado": False,
    }


def _iniciar_app(args: argparse.Namespace) -> int:
    """Inicia o launcher empacotado, que detecta a SPA sem Node/npm."""

    _aplicar_perfil(args.perfil)
    try:
        modulo = importlib.import_module("start_app")
    except ModuleNotFoundError as exc:
        raise RuntimeError(
            "O app local não está instalado. Use: pipx install 'notion-automacoes[app]'"
        ) from exc
    resultado = modulo.main(["--action", "tudo"])
    return int(resultado) if isinstance(resultado, int) else 0


def _iniciar_mcp(args: argparse.Namespace) -> int:
    """Inicia o servidor MCP empacotado sem passar pelo menu interativo."""

    _aplicar_perfil(args.perfil)
    if not _importavel("server.mcp_server"):
        raise RuntimeError(
            "O servidor MCP não está instalado. Use: pipx install 'notion-automacoes[app]'"
        )
    # O app tem pacotes legados chamados ``core`` e ``services``. Um processo
    # separado evita que o ``core`` da CLI já importado para aplicar o perfil
    # seja confundido com o ``core`` do servidor MCP.
    return int(
        subprocess.call(
            [sys.executable, "-m", "server.mcp_server", "--transport", args.transport]
        )
    )


def _imprimir(dados: Any, *, json_saida: bool) -> None:
    """Imprime um resultado humano ou JSON determinístico."""

    if json_saida:
        print(json.dumps(dados, ensure_ascii=False, indent=2, sort_keys=True))
        return
    if isinstance(dados, dict) and "checks" in dados:
        print(f"notion-automacoes {dados['versao']}")
        for item in dados["checks"]:
            simbolo = {"ok": "✓", "aviso": "⚠", "erro": "✗"}.get(item["estado"], "•")
            print(f"{simbolo} {item['nome']}: {item['detalhe']}")
        return
    if isinstance(dados, dict) and "comando" in dados:
        print(f"Versão atual: {dados['versao_atual']}")
        print(f"Atualização ({dados['motivo']}):")
        print(" ".join(dados["comando"]))
        print("Nenhum comando foi executado.")
        return
    if dados is not None:
        print(json.dumps(dados, ensure_ascii=False, indent=2, sort_keys=True))


def main(argv: Sequence[str] | None = None) -> int:
    """Ponto de entrada público da distribuição única."""

    parser = construir_parser()
    args = parser.parse_args(argv)
    try:
        if args.comando in {"tasks", "tarefas"}:
            return _delegar_tasks(args)
        if args.comando in {"auth", "perfis"}:
            return _delegar_auth(args)
        if args.comando == "doctor":
            dados = diagnosticar()
            _imprimir(dados, json_saida=args.json)
            return 0 if dados["ok"] else 1
        if args.comando in {"update", "atualizar"}:
            _imprimir(preparar_atualizacao(), json_saida=args.json)
            return 0
        if args.comando == "app" and args.acao_app == "start":
            return _iniciar_app(args)
        if args.comando == "mcp" and args.acao_mcp == "start":
            return _iniciar_mcp(args)
        parser.error("Comando incompleto.")
    except Exception as exc:  # noqa: BLE001 - fronteira pública com erro legível
        dados = {"ok": False, "erro": {"mensagem": str(exc)}}
        _imprimir(dados, json_saida=getattr(args, "json", False))
        return 2
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
