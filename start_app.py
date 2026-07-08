#!/usr/bin/env python3
"""Menu de entrada do notion-tasks-cli — a porta de entrada única.

Rode ``python start_app.py`` para abrir um menu interativo onde você instala a
CLI, configura o token do Notion no ``.env``, confere o estado do ambiente e
executa os primeiros comandos sem decorar nada.

Segue o contrato de menu de entrada do Felixo System Design: interativo,
colorido e descritivo, com Iniciar/Rodar, Instalar/Setup, Configurar e
Status/Sair. Cross-platform; nenhum segredo vive neste script — o token fica no
``.env``, ignorado pelo git.
"""

from __future__ import annotations

import importlib.util
import subprocess
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent
ENV_FILE = RAIZ / ".env"

# Variáveis que o menu ajuda a preencher no .env.
VARS_ENV = {
    "NOTION_TOKEN": "Credencial da integração do Notion (começa com ntn_).",
    "NOTION_DATABASE_ID": "ID do database padrão de tarefas (opcional).",
}

# As deps de TUI são do próprio menu; o passo de Instalar/Setup garante que
# existem. Antes disso, caímos num fallback de instalação guiada.
_DEPS_TUI = ("questionary", "rich")


# --------------------------------------------------------------------------- #
# Infraestrutura: TUI, subprocessos e .env                                     #
# --------------------------------------------------------------------------- #
def _tui_disponivel() -> bool:
    """Indica se as bibliotecas do menu interativo estão instaladas."""

    return all(importlib.util.find_spec(dep) is not None for dep in _DEPS_TUI)


def _instalar_deps_tui() -> bool:
    """Instala as dependências de TUI do menu. Retorna sucesso."""

    print(f"Instalando dependências do menu ({', '.join(_DEPS_TUI)})...")
    codigo = subprocess.call([sys.executable, "-m", "pip", "install", *_DEPS_TUI])
    if codigo != 0:
        print(
            "Não consegui instalar as dependências do menu. Instale manualmente:\n"
            f"  {sys.executable} -m pip install {' '.join(_DEPS_TUI)}"
        )
        return False
    return True


def _rodar(comando: list[str]) -> int:
    """Executa um comando mostrando-o antes; retorna o código de saída."""

    print(f"$ {' '.join(comando)}")
    try:
        return subprocess.call(comando)
    except OSError as exc:
        print(f"Não consegui executar o comando: {exc}")
        return 1


def _ler_env() -> dict[str, str]:
    """Lê o .env local (formato simples CHAVE=valor), sem dependências."""

    valores: dict[str, str] = {}
    if not ENV_FILE.exists():
        return valores
    for linha in ENV_FILE.read_text(encoding="utf-8").splitlines():
        linha = linha.strip()
        if not linha or linha.startswith("#") or "=" not in linha:
            continue
        chave, _, valor = linha.partition("=")
        valores[chave.strip()] = valor.strip()
    return valores


def _gravar_env(chave: str, valor: str) -> None:
    """Grava/atualiza uma variável no .env preservando as demais linhas."""

    linhas: list[str] = []
    encontrada = False
    if ENV_FILE.exists():
        for linha in ENV_FILE.read_text(encoding="utf-8").splitlines():
            if linha.split("=", 1)[0].strip() == chave and "=" in linha:
                linhas.append(f"{chave}={valor}")
                encontrada = True
            else:
                linhas.append(linha)
    if not encontrada:
        linhas.append(f"{chave}={valor}")
    ENV_FILE.write_text("\n".join(linhas) + "\n", encoding="utf-8")


def _cli_instalada() -> bool:
    """Indica se o pacote da CLI está importável neste Python."""

    return importlib.util.find_spec("cli") is not None


# --------------------------------------------------------------------------- #
# Ações do menu                                                                #
# --------------------------------------------------------------------------- #
def acao_instalar(console) -> None:
    """Instalar/Setup: instala a CLI em modo editável com deps de dev."""

    console.rule("[bold]Instalar / Setup")
    _rodar([sys.executable, "-m", "pip", "install", "-e", f"{RAIZ}[dev]"])
    console.print("[green]✓[/green] Instalação concluída. Use 'Status' para conferir.")


def acao_configurar(console) -> None:
    """Configurar: preenche NOTION_TOKEN e NOTION_DATABASE_ID no .env."""

    import questionary

    console.rule("[bold]Configurar .env")
    console.print(
        "O token vem de uma integração do Notion (https://www.notion.so/my-integrations).\n"
        "Lembre de compartilhar as páginas/databases com a integração (••• → Conexões)."
    )
    atuais = _ler_env()
    for chave, descricao in VARS_ENV.items():
        atual = atuais.get(chave, "")
        sufixo = " [definida]" if atual else ""
        novo = questionary.text(f"{chave}{sufixo} — {descricao} (Enter mantém):").ask()
        if novo:
            _gravar_env(chave, novo.strip())
            console.print(f"[green]✓[/green] {chave} gravada no .env")


def acao_rodar(console) -> None:
    """Iniciar/Rodar: mostra o guia da CLI e lista as tarefas."""

    console.rule("[bold]Usar a CLI")
    if not _cli_instalada():
        console.print("[yellow]![/yellow] A CLI não está instalada. Rode 'Instalar / Setup'.")
        return
    console.print("Guia completo (escrito para pessoas e IAs): [bold]notion-tasks --help[/bold]\n")
    _rodar([sys.executable, "-m", "cli.notion_tasks", "--help"])


def acao_status(console) -> None:
    """Status: mostra Python, instalação da CLI e variáveis do .env."""

    console.rule("[bold]Status")
    console.print(f"Python: {sys.version.split()[0]} ({sys.executable})")
    instalada = _cli_instalada()
    cor = "green" if instalada else "red"
    console.print(f"CLI instalada: [{cor}]{'sim' if instalada else 'não'}[/{cor}]")
    valores = _ler_env()
    for chave in VARS_ENV:
        definida = bool(valores.get(chave))
        cor = "green" if definida else "yellow"
        console.print(f"{chave}: [{cor}]{'definida' if definida else 'ausente'}[/{cor}]")
    if not ENV_FILE.exists():
        console.print("[dim].env ainda não existe — use 'Configurar'.[/dim]")


# --------------------------------------------------------------------------- #
# Menu principal                                                               #
# --------------------------------------------------------------------------- #
def main() -> None:
    """Abre o menu interativo da CLI."""

    if not _tui_disponivel():
        print(
            "O menu interativo precisa de 'questionary' e 'rich'.\n"
            "Posso instalá-los agora neste ambiente Python."
        )
        resposta = input("Instalar agora? [S/n] ").strip().lower()
        if resposta not in ("", "s", "sim", "y", "yes") or not _instalar_deps_tui():
            raise SystemExit(1)
        if not _tui_disponivel():
            raise SystemExit(1)

    import questionary
    from rich.console import Console

    console = Console()
    acoes = {
        "▶ Usar a CLI (guia e exemplos)": acao_rodar,
        "⬇ Instalar / Setup": acao_instalar,
        "⚙ Configurar (.env: token e database)": acao_configurar,
        "ℹ Status do ambiente": acao_status,
    }
    console.print("[bold cyan]notion-tasks-cli[/bold cyan] — CLI do Notion para pessoas e IAs\n")
    while True:
        escolha = questionary.select(
            "O que você quer fazer?",
            choices=[*acoes, "✕ Sair"],
        ).ask()
        if escolha is None or escolha == "✕ Sair":
            console.print("[dim]Até logo![/dim]")
            return
        acoes[escolha](console)
        console.print()


if __name__ == "__main__":
    main()
