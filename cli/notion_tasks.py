"""CLI para IA operar tarefas do Notion via ``server/services``.

Esta borda valida entradas, escolhe formato de saída e delega a regra para os
services compartilhados com API/MCP. Não monta payload cru do Notion.
"""

from __future__ import annotations

import argparse
import os
import sys
from collections.abc import Callable, Iterable, Sequence
from pathlib import Path
from typing import Any

RAIZ = Path(__file__).resolve().parents[1]
SERVER_DIR = RAIZ / "server"
if str(SERVER_DIR) not in sys.path:
    sys.path.insert(0, str(SERVER_DIR))

from core.config import carregar_env_file  # noqa: E402
from integrations.github import GitHubClient  # noqa: E402
from services import clonagem as svc_clonagem  # noqa: E402
from services import conteudo as svc_conteudo  # noqa: E402
from services import inventario_github as svc_inventario  # noqa: E402
from services import normalizacao as svc_normalizacao  # noqa: E402
from services import propriedades as svc_propriedades  # noqa: E402
from services import tarefas as svc  # noqa: E402

from notion_starter import (  # noqa: E402
    NotionAPIError,
    NotionClient,
    NotionConfigurationError,
    NotionHTTPError,
    TaskList,
    construir_inventario,
)

carregar_env_file()

TaskListFactory = Callable[[], TaskList]
ClientFactory = Callable[[], NotionClient]


class CLIError(RuntimeError):
    """Erro esperado de uso/configuração, seguro para exibir ao consumidor."""


def _criar_client() -> NotionClient:
    token = os.environ.get("NOTION_TOKEN", "").strip()
    if not token:
        raise CLIError("NOTION_TOKEN não configurado.")
    return NotionClient(token=token)


def _criar_tasklist() -> TaskList:
    database_id = os.environ.get("NOTION_DATABASE_ID", "").strip()
    if not database_id:
        raise CLIError("NOTION_DATABASE_ID não configurado.")
    return TaskList(_criar_client(), database_id)


def _normalizar_texto(valor: str | None) -> str | None:
    if valor is None:
        return None
    return valor.strip() or None


def _texto_obrigatorio(valor: str | None, campo: str) -> str:
    normalizado = _normalizar_texto(valor)
    if not normalizado:
        raise CLIError(f"O campo '{campo}' é obrigatório.")
    return normalizado


def _lista_csv(valores: Sequence[str] | None) -> list[str] | None:
    if not valores:
        return None
    itens: list[str] = []
    for valor in valores:
        itens.extend(item.strip() for item in valor.split(",") if item.strip())
    return itens


def _tarefa_dict(tarefa: Any) -> dict[str, Any]:
    return {
        "id": tarefa.id,
        "nome": tarefa.nome,
        "status": tarefa.status,
        "prazo": tarefa.prazo,
        "duracao": tarefa.duracao,
        "areas": tarefa.areas,
        "areas_nomes": tarefa.areas_nomes,
        "url": tarefa.url,
    }


def _database_titulo(item: dict[str, Any]) -> str:
    partes = item.get("title", [])
    titulo = "".join(parte.get("plain_text", "") for parte in partes).strip()
    return titulo or "(sem título)"


def _database_dict(item: dict[str, Any]) -> dict[str, Any]:
    return {"id": item.get("id", ""), "titulo": _database_titulo(item), "url": item.get("url")}


def _nomes_data_sources(fontes: list[dict[str, Any]]) -> list[str]:
    nomes = []
    for fonte in fontes:
        nome = str(fonte.get("name") or "").strip()
        if nome:
            nomes.append(nome)
    return nomes


def _envelope(sucesso: bool, dados: Any = None, erro: str | None = None) -> dict[str, Any]:
    if sucesso:
        return {"ok": True, "dados": dados}
    return {"ok": False, "erro": {"mensagem": erro or "Erro desconhecido."}}


def _json(dados: Any) -> str:
    # Usar safe_json_dumps para prevenir erros de surrogate inválidos
    from notion_starter.utils import safe_json_dumps
    return safe_json_dumps(dados, ensure_ascii=False, indent=2, sort_keys=True)


def _linhas_tabela(registros: Iterable[dict[str, Any]], colunas: Sequence[str]) -> list[str]:
    linhas = list(registros)
    if not linhas:
        return ["Nenhum item encontrado."]
    larguras = {
        coluna: max(len(coluna), *(len(str(item.get(coluna) or "")) for item in linhas))
        for coluna in colunas
    }
    cabecalho = "  ".join(coluna.ljust(larguras[coluna]) for coluna in colunas)
    separador = "  ".join("-" * larguras[coluna] for coluna in colunas)
    corpo = [
        "  ".join(str(item.get(coluna) or "").ljust(larguras[coluna]) for coluna in colunas)
        for item in linhas
    ]
    return [cabecalho, separador, *corpo]


def _formatar_guia(dados: dict[str, Any]) -> str:
    """Renderiza o guia de comandos em texto legível."""

    linhas = [dados["ferramenta"], dados["dica"], ""]
    for passo in dados.get("fluxo_recomendado", []):
        linhas.append(f">> {passo}")
    linhas.append("")
    for item in dados["comandos"]:
        linhas.append(f"{item['comando']:18} {item['descricao']}")
        for exemplo in item["exemplos"]:
            linhas.append(f"    {exemplo}")
    return "\n".join(linhas)


def _formatar_humano(comando: str, dados: Any) -> str:
    if comando == "guia":
        return _formatar_guia(dados)
    if comando in {"listar", "ler", "criar", "editar", "mover", "concluir"}:
        tarefas = dados if isinstance(dados, list) else [dados]
        return "\n".join(
            _linhas_tabela(
                tarefas,
                ("id", "nome", "status", "duracao", "areas_nomes", "prazo", "url"),
            )
        )
    if comando == "opcoes":
        return _json(dados)
    if comando == "databases":
        return "\n".join(_linhas_tabela(dados, ("id", "titulo", "url")))
    if comando == "buscar":
        return "\n".join(_linhas_tabela(dados, ("id", "tipo", "titulo", "url")))
    if comando == "conteudo":
        if dados.get("tipo") == "database":
            cabecalho = dados["aviso"]
            tabela = "\n".join(_linhas_tabela(dados["linhas"], ("id", "titulo", "url")))
            return f"{cabecalho}\n\n{tabela}"
        return dados["markdown"] or "(página sem conteúdo)"
    if comando == "linhas":
        return "\n".join(_linhas_tabela(dados["linhas"], ("id", "titulo", "url")))
    if comando == "clonar-database":
        return (
            f"Clone criado: {dados['titulo']} ({dados['id']})\n"
            f"Propriedades: {len(dados['propriedades'])} | "
            f"linhas copiadas: {dados['linhas_copiadas']}"
        )
    if comando == "database-atual":
        if not dados["database_id"]:
            return "Database atual: (não configurado)"
        fontes = ", ".join(dados.get("data_sources") or []) or "(sem data source acessível)"
        return (
            f"Database atual: {dados['titulo']} ({dados['database_id']})\n"
            f"Data source: {fontes}\n"
            f"URL: {dados['url'] or '(sem URL)'}"
        )
    if comando == "normalizar-nomes":
        return _json(dados)
    if comando == "mapear":
        return (
            f"Itens: {dados['total_itens']} | páginas: {dados['total_paginas']} | "
            f"databases: {dados['total_databases']} | raízes: {dados['total_raizes']} | "
            f"duplicatas: {dados['total_duplicatas']} | órfãos: {dados['total_orfaos']}"
        )
    if comando == "atualizar-github":
        return (
            f"Repos: {dados['repos_encontrados']} | criados: {dados['paginas_criadas']} | "
            f"atualizados: {dados['paginas_atualizadas']} | "
            f"READMEs novos: {dados['readmes_escritos']} | "
            f"READMEs atualizados: {dados['readmes_atualizados']} | "
            f"erros: {len(dados['erros'])}"
        )
    return _json(dados)


def _salvar_database_env(database_id: str, env_file: Path = RAIZ / ".env") -> None:
    linhas: list[str] = []
    if env_file.exists():
        linhas = env_file.read_text(encoding="utf-8").splitlines()
    chave = "NOTION_DATABASE_ID"
    nova_linha = f"{chave}={database_id}"
    atualizado = False
    for indice, linha in enumerate(linhas):
        if linha.startswith(f"{chave}="):
            linhas[indice] = nova_linha
            atualizado = True
            break
    if not atualizado:
        linhas.append(nova_linha)
    env_file.write_text("\n".join(linhas).rstrip() + "\n", encoding="utf-8")
    os.environ[chave] = database_id


def cmd_listar(args: argparse.Namespace, *, tasklist_factory: TaskListFactory) -> Any:
    tarefas = svc.listar_tarefas(
        status=_normalizar_texto(args.status),
        duracao=_normalizar_texto(args.duracao),
        areas=_lista_csv(args.area),
        tasklist=tasklist_factory(),
    )
    return [_tarefa_dict(tarefa) for tarefa in tarefas]


def cmd_ler(args: argparse.Namespace, *, tasklist_factory: TaskListFactory) -> Any:
    task_id = _texto_obrigatorio(args.task_id, "task_id")
    tarefas = svc.listar_tarefas(tasklist=tasklist_factory())
    for tarefa in tarefas:
        if tarefa.id == task_id:
            return _tarefa_dict(tarefa)
    raise CLIError("Tarefa não encontrada.")


def cmd_criar(args: argparse.Namespace, *, tasklist_factory: TaskListFactory) -> Any:
    """Cria uma tarefa nova.

    IMPORTANTE: Valida status contra opções disponíveis no database para evitar
    erro "Invalid status option" da API do Notion.

    Problema conhecido: CLI falhava com status inválido que não existe no schema.
    Solução: Validar status contra opções do database antes de enviar.
    """
    # Validar status contra opções disponíveis (se fornecido)
    status = _normalizar_texto(args.status)
    if status:
        opcoes = svc.listar_opcoes(tasklist=tasklist_factory())
        status_validos = opcoes.get("status", [])
        if status not in status_validos:
            raise CLIError(
                f"Status '{status}' inválido. Opções disponíveis: {', '.join(status_validos)}"
            )

    tarefa = svc.criar_tarefa(
        _texto_obrigatorio(args.nome, "nome"),
        status=status,
        prazo=_normalizar_texto(args.prazo),
        duracao=_normalizar_texto(args.duracao),
        areas=_lista_csv(args.area),
        tasklist=tasklist_factory(),
    )
    return _tarefa_dict(tarefa)


def cmd_editar(args: argparse.Namespace, *, tasklist_factory: TaskListFactory) -> Any:
    """Edita uma tarefa existente.

    IMPORTANTE: Valida status contra opções disponíveis no database para evitar
    erro "Invalid status option" da API do Notion.

    Problema conhecido: CLI falhava com status inválido que não existe no schema.
    Solução: Validar status contra opções do database antes de enviar.
    """
    campos = {
        "nome": _normalizar_texto(args.nome),
        "status": _normalizar_texto(args.status),
        "prazo": _normalizar_texto(args.prazo),
        "duracao": _normalizar_texto(args.duracao),
        "areas": _lista_csv(args.area),
    }

    if all(valor is None for valor in campos.values()):
        raise CLIError("Informe ao menos um campo para editar.")

    # Validar status contra opções disponíveis (se fornecido)
    status = campos["status"]
    if status:
        opcoes = svc.listar_opcoes(tasklist=tasklist_factory())
        status_validos = opcoes.get("status", [])
        if status not in status_validos:
            raise CLIError(
                f"Status '{status}' inválido. Opções disponíveis: {', '.join(status_validos)}"
            )

    tarefa = svc.editar_tarefa(
        _texto_obrigatorio(args.task_id, "task_id"),
        **campos,
        tasklist=tasklist_factory(),
    )
    return _tarefa_dict(tarefa)


def cmd_mover(args: argparse.Namespace, *, tasklist_factory: TaskListFactory) -> Any:
    """Move tarefa para outro status.

    IMPORTANTE: Valida status contra opções disponíveis no database para evitar
    erro "Invalid status option" da API do Notion.

    Problema conhecido: CLI falhava com status inválido que não existe no schema.
    Solução: Validar status contra opções do database antes de enviar.
    """
    status = _texto_obrigatorio(args.status, "status")

    # Validar status contra opções disponíveis
    opcoes = svc.listar_opcoes(tasklist=tasklist_factory())
    status_validos = opcoes.get("status", [])
    if status not in status_validos:
        raise CLIError(
            f"Status '{status}' inválido. Opções disponíveis: {', '.join(status_validos)}"
        )

    tarefa = svc.mover_status(
        _texto_obrigatorio(args.task_id, "task_id"),
        status,
        tasklist=tasklist_factory(),
    )
    return _tarefa_dict(tarefa)


def cmd_concluir(args: argparse.Namespace, *, tasklist_factory: TaskListFactory) -> Any:
    """Conclui tarefa com o status informado.

    IMPORTANTE: Valida status contra opções disponíveis no database para evitar
    erro "Invalid status option" da API do Notion.

    Problema conhecido: CLI falhava com status inválido que não existe no schema.
    Solução: Validar status contra opções do database antes de enviar.
    """
    status = _texto_obrigatorio(args.status, "status")

    # Validar status contra opções disponíveis
    opcoes = svc.listar_opcoes(tasklist=tasklist_factory())
    status_validos = opcoes.get("status", [])
    if status not in status_validos:
        raise CLIError(
            f"Status '{status}' inválido. Opções disponíveis: {', '.join(status_validos)}"
        )

    tarefa = svc.concluir_tarefa(
        _texto_obrigatorio(args.task_id, "task_id"),
        status,
        tasklist=tasklist_factory(),
    )
    return _tarefa_dict(tarefa)


def cmd_opcoes(args: argparse.Namespace, *, tasklist_factory: TaskListFactory) -> Any:
    return svc.listar_opcoes(tasklist=tasklist_factory())


def cmd_databases(args: argparse.Namespace, *, client_factory: ClientFactory) -> Any:
    itens = client_factory().buscar(
        query=_normalizar_texto(args.query),
        buscar_todos=True,
        filtro={"property": "object", "value": "database"},
    )
    return [_database_dict(item) for item in itens]


def cmd_database_atual(args: argparse.Namespace, *, client_factory: ClientFactory) -> Any:
    database_id = os.environ.get("NOTION_DATABASE_ID", "").strip()
    if not database_id:
        return {"database_id": "", "titulo": "", "url": "", "data_sources": []}
    cliente = client_factory()
    database = cliente.get_database(database_id)
    fontes = cliente.listar_data_sources(database_id)
    return {
        "database_id": database_id,
        "titulo": _database_titulo(database),
        "url": database.get("url"),
        "data_sources": _nomes_data_sources(fontes),
    }


def cmd_escolher_database(args: argparse.Namespace) -> Any:
    database_id = _texto_obrigatorio(args.database_id, "database_id")
    _salvar_database_env(database_id)
    return {"database_id": database_id, "salvo_em": str(RAIZ / ".env")}


def cmd_normalizar_nomes(args: argparse.Namespace, *, client_factory: ClientFactory) -> Any:
    database_id = os.environ.get("NOTION_DATABASE_ID", "").strip()
    if not database_id:
        raise CLIError("NOTION_DATABASE_ID não configurado.")
    return svc_normalizacao.normalizar_nomes(
        database_id,
        aplicar=not args.dry_run,
        cliente=client_factory(),
    )


def cmd_mapear(args: argparse.Namespace, *, client_factory: ClientFactory) -> Any:
    itens = client_factory().buscar(
        query=_normalizar_texto(args.query),
        page_size=args.page_size,
        buscar_todos=True,
    )
    inventario = construir_inventario(itens)
    duplicatas = [
        {"titulo": titulo, "ids": [item.id for item in grupo]}
        for titulo, grupo in inventario.duplicatas.items()
    ]
    return {
        "total_itens": len(inventario.itens),
        "total_paginas": inventario.total_paginas,
        "total_databases": inventario.total_databases,
        "total_raizes": len(inventario.raizes),
        "total_duplicatas": len(inventario.duplicatas),
        "total_orfaos": len(inventario.orfaos),
        "duplicatas": duplicatas[: args.limite_duplicatas],
    }


def cmd_conteudo(args: argparse.Namespace, *, client_factory: ClientFactory) -> Any:
    page_id = _texto_obrigatorio(args.page_id, "page_id")
    resultado = svc_conteudo.ler_pagina_ou_database(page_id, cliente=client_factory())
    if resultado["tipo"] == "database":
        # Borda acrescenta o aviso voltado ao usuário da CLI.
        resultado["aviso"] = (
            "Isto é um database: o conteúdo são as linhas, não blocos. "
            "Use 'linhas' para listá-las (já incluídas em 'linhas' abaixo)."
        )
    return resultado


def cmd_linhas(args: argparse.Namespace, *, client_factory: ClientFactory) -> Any:
    database_id = _texto_obrigatorio(args.database_id, "database_id")
    linhas = svc_conteudo.listar_linhas(database_id, cliente=client_factory())
    return {"id": database_id, "linhas": linhas}


def _pares_chave_valor(itens: Sequence[str] | None, flag: str) -> dict[str, str]:
    """Converte ``["Nome=valor", ...]`` num mapa ``{Nome: valor}``.

    Divide no primeiro ``=`` para o valor poder conter ``=``. O nome não pode
    ficar vazio. ``flag`` é citada na mensagem de erro (ex.: ``--set``).
    """

    pares: dict[str, str] = {}
    for item in itens or []:
        nome, sep, valor = item.partition("=")
        nome = nome.strip()
        if not sep or not nome:
            raise CLIError(f'Use o formato "Nome=valor" em {flag} (recebido: {item!r}).')
        pares[nome] = valor
    return pares


def cmd_editar_linha(args: argparse.Namespace, *, client_factory: ClientFactory) -> Any:
    page_id = _texto_obrigatorio(args.page_id, "page_id")
    valores = _pares_chave_valor(args.set, "--set")
    acrescentos = _pares_chave_valor(args.append, "--append")
    return svc_propriedades.editar_linha(
        page_id, valores, acrescentos, cliente=client_factory()
    )


def cmd_escrever(args: argparse.Namespace, *, client_factory: ClientFactory) -> Any:
    page_id = _texto_obrigatorio(args.page_id, "page_id")
    conteudo = _texto_obrigatorio(args.conteudo, "conteudo")
    total = svc_conteudo.escrever_conteudo(page_id, conteudo, cliente=client_factory())
    return {"id": page_id, "blocos_anexados": total}


def cmd_editar_bloco(args: argparse.Namespace, *, client_factory: ClientFactory) -> Any:
    block_id = _texto_obrigatorio(args.block_id, "block_id")
    conteudo = _texto_obrigatorio(args.conteudo, "conteudo")
    svc_conteudo.editar_bloco(block_id, conteudo, cliente=client_factory())
    return {"id": block_id, "editado": True}


def cmd_apagar_bloco(args: argparse.Namespace, *, client_factory: ClientFactory) -> Any:
    block_id = _texto_obrigatorio(args.block_id, "block_id")
    # Operação destrutiva: exige confirmação explícita, nunca apaga "no susto".
    if not args.sim:
        raise CLIError(
            "Apagar é destrutivo. Repita com --sim para confirmar a exclusão do bloco."
        )
    svc_conteudo.excluir_bloco(block_id, cliente=client_factory())
    return {"id": block_id, "apagado": True}


def cmd_buscar(args: argparse.Namespace, *, client_factory: ClientFactory) -> Any:
    return svc_conteudo.buscar(_normalizar_texto(args.query), cliente=client_factory())


def cmd_clonar_database(args: argparse.Namespace, *, client_factory: ClientFactory) -> Any:
    database_id = _texto_obrigatorio(args.database_id, "database_id")
    return svc_clonagem.clonar_database(
        database_id,
        titulo=_normalizar_texto(args.titulo) or None,
        pagina_destino=_normalizar_texto(args.pagina) or None,
        com_linhas=args.com_linhas,
        relacoes=args.relacoes,
        cliente=client_factory(),
    )


def _resumo_inventario_dict(resumo: Any) -> dict[str, Any]:
    return {
        "repos_encontrados": resumo.repos_encontrados,
        "paginas_criadas": resumo.paginas_criadas,
        "paginas_atualizadas": resumo.paginas_atualizadas,
        "readmes_escritos": resumo.readmes_escritos,
        "readmes_atualizados": resumo.readmes_atualizados,
        "erros": resumo.erros,
    }


def cmd_atualizar_github(args: argparse.Namespace, *, client_factory: ClientFactory) -> Any:
    """Re-sincroniza o database GITHUB: repos novos, propriedades e README mudado."""

    contas = _lista_csv(args.contas) or _lista_csv([os.environ.get("GITHUB_CONTAS", "")])
    if not contas:
        raise CLIError(
            "Informe as contas com --contas (CSV) ou defina GITHUB_CONTAS no ambiente."
        )
    database_id = _normalizar_texto(args.database) or os.environ.get(
        "NOTION_DATABASE_ID", ""
    ).strip()
    if not database_id:
        raise CLIError("Informe o database com --database ou defina NOTION_DATABASE_ID.")

    resumo = svc_inventario.atualizar_repos(
        contas,
        database_id,
        github_client=GitHubClient(),
        notion_client=client_factory(),
        sincronizar_readme=not args.sem_readme,
    )
    return _resumo_inventario_dict(resumo)


#: Exemplos de uso por comando, mostrados pelo ``guia``. Texto curto e copiável.
EXEMPLOS_GUIA: dict[str, list[str]] = {
    "listar": ['python -m cli --json listar --status "Entrada"'],
    "ler": ["python -m cli --json ler <task_id>"],
    "criar": ['python -m cli --json criar "Nova tarefa" --status "Entrada" --duracao "Dias"'],
    "editar": ['python -m cli --json editar <task_id> --status "Concluída"'],
    "mover": ['python -m cli --json mover <task_id> "Concluída"'],
    "concluir": ['python -m cli --json concluir <task_id> "Concluída"'],
    "opcoes": ["python -m cli --json opcoes"],
    "databases": ["python -m cli --json databases"],
    "database-atual": ["python -m cli --json database-atual"],
    "escolher-database": ["python -m cli --json escolher-database <database_id>"],
    "normalizar-nomes": ["python -m cli --json normalizar-nomes --dry-run"],
    "mapear": ["python -m cli --json mapear"],
    "buscar": ['python -m cli --json buscar "nota de reunião"'],
    "conteudo": ["python -m cli --json conteudo <page_id>"],
    "linhas": ["python -m cli --json linhas <database_id>"],
    "editar-linha": [
        'python -m cli --json editar-linha <page_id> --set "Status=Feito"',
        'python -m cli --json editar-linha <page_id> --set "Prazo=2026-07-10" --set "Tags=urgente,casa"',
        'python -m cli --json editar-linha <page_id> --append "Resumo=\\n\\nNova observação ao final"',
    ],
    "escrever": ["python -m cli --json escrever <page_id> $'# Título\\n\\nTexto'"],
    "editar-bloco": ['python -m cli --json editar-bloco <block_id> "## Novo título"'],
    "apagar-bloco": ["python -m cli --json apagar-bloco <block_id> --sim"],
    "clonar-database": [
        "python -m cli --json clonar-database <database_id>",
        'python -m cli --json clonar-database <database_id> --titulo "Cópia" --com-linhas',
    ],
    "atualizar-github": [
        "python -m cli --json atualizar-github --contas conta-um,conta-dois",
        "python -m cli --json atualizar-github --database <database_id> --sem-readme",
    ],
    "guia": ["python -m cli --json guia"],
}


def cmd_guia(args: argparse.Namespace) -> Any:
    """Auto-documenta a CLI: todos os comandos, o que fazem e um exemplo.

    Pensado para uma IA descobrir como operar a ferramenta sem tatear: é a
    primeira chamada a fazer. Reflete o próprio parser, então nunca desatualiza.
    """

    parser = construir_parser()
    subparsers = next(
        acao for acao in parser._subparsers._group_actions if hasattr(acao, "choices")
    )
    # O texto de ajuda de cada subcomando fica em ``_choices_actions`` (o ``help``
    # passado em ``add_parser``); lê de lá para o guia refletir o parser.
    ajudas = {acao.dest: (acao.help or "") for acao in subparsers._choices_actions}
    comandos = []
    for nome in subparsers.choices:
        comandos.append(
            {
                "comando": nome,
                "descricao": ajudas.get(nome, ""),
                "exemplos": EXEMPLOS_GUIA.get(nome, [f"python -m cli {nome} --help"]),
            }
        )
    return {
        "ferramenta": "cli notion (mesmos services da API e do MCP)",
        "dica": (
            "Use estes comandos em vez de chamar a API do Notion na mão. "
            "Acrescente --json para saída estável {ok, dados}. Sufixo '--help' "
            "em qualquer comando mostra os argumentos."
        ),
        "fluxo_recomendado": [
            "REGRA: ao trabalhar numa página que é linha de um database, edite "
            "PRIMEIRO as propriedades (as colunas) e SÓ DEPOIS o conteúdo (o corpo).",
            "1. Propriedades (colunas: status, datas, seleções, relações…) → "
            "'editar-linha <page_id> --set \"Nome=valor\"'.",
            "2. Conteúdo (o corpo da nota, em blocos) → 'escrever <page_id> <markdown>'.",
            "Não pare no conteúdo esquecendo as propriedades: uma linha de database "
            "só fica completa quando as colunas também são preenchidas.",
        ],
        "comandos": comandos,
    }


def construir_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m cli",
        description="CLI para IA operar tarefas do Notion via services.",
    )
    parser.add_argument("--json", action="store_true", help="emite envelope JSON estável")
    sub = parser.add_subparsers(dest="comando", required=True)

    listar = sub.add_parser("listar", help="lista tarefas")
    listar.add_argument("--status")
    listar.add_argument("--duracao")
    listar.add_argument("--area", action="append", help="ID de área; aceita CSV e repetição")

    ler = sub.add_parser("ler", help="lê uma tarefa pelo ID")
    ler.add_argument("task_id")

    criar = sub.add_parser("criar", help="cria uma tarefa")
    criar.add_argument("nome")
    criar.add_argument("--status")
    criar.add_argument("--prazo")
    criar.add_argument("--duracao")
    criar.add_argument("--area", action="append", help="ID de área; aceita CSV e repetição")

    editar = sub.add_parser("editar", help="edita uma tarefa")
    editar.add_argument("task_id")
    editar.add_argument("--nome")
    editar.add_argument("--status")
    editar.add_argument("--prazo")
    editar.add_argument("--duracao")
    editar.add_argument("--area", action="append", help="ID de área; aceita CSV e repetição")

    mover = sub.add_parser("mover", help="move tarefa para outro status")
    mover.add_argument("task_id")
    mover.add_argument("status")

    concluir = sub.add_parser("concluir", help="conclui tarefa com o status informado")
    concluir.add_argument("task_id")
    concluir.add_argument("status")

    sub.add_parser("opcoes", help="lista opções de status, duração e áreas")

    databases = sub.add_parser("databases", help="lista databases visíveis")
    databases.add_argument("--query")

    database_atual = sub.add_parser("database-atual", help="mostra o database configurado")
    database_atual.set_defaults(alias_comando="database-atual")

    escolher = sub.add_parser("escolher-database", help="grava NOTION_DATABASE_ID no .env")
    escolher.add_argument("database_id")

    normalizar_nomes = sub.add_parser(
        "normalizar-nomes",
        help="renomeia propriedades e opções no Notion para nomes intuitivos",
    )
    normalizar_nomes.add_argument(
        "--dry-run",
        action="store_true",
        help="mostra o plano sem escrever no Notion",
    )

    mapear = sub.add_parser("mapear", help="resume o inventário do workspace")
    mapear.add_argument("--query")
    mapear.add_argument("--page-size", type=int, default=100)
    mapear.add_argument("--limite-duplicatas", type=int, default=10)

    conteudo = sub.add_parser("conteudo", help="lê o conteúdo de uma página como Markdown")
    conteudo.add_argument("page_id")

    linhas = sub.add_parser("linhas", help="lista as linhas de um database (resolve data sources)")
    linhas.add_argument("database_id")

    editar_linha = sub.add_parser(
        "editar-linha",
        help="edita propriedades (colunas) de uma linha de database — faça ISTO "
        "antes de escrever o conteúdo",
    )
    editar_linha.add_argument("page_id")
    editar_linha.add_argument(
        "--set",
        action="append",
        metavar="NOME=VALOR",
        help='substitui o valor de uma coluna; repita para várias. Ex.: --set '
        '"Status=Feito" --set "Prazo=2026-07-10". Listas (multi_select/relation) '
        "aceitam CSV; texto vazio limpa a coluna.",
    )
    editar_linha.add_argument(
        "--append",
        action="append",
        metavar="NOME=TEXTO",
        help='acrescenta texto ao FINAL de uma coluna de texto (title/rich_text), '
        'preservando o conteúdo atual. Ex.: --append "Resumo=\\n\\nMais uma nota". '
        "Texto longo é fatiado automaticamente no limite de 2000.",
    )

    escrever = sub.add_parser(
        "escrever",
        help="anexa conteúdo (Markdown) a uma página — se for linha de database, "
        "defina antes as propriedades com 'editar-linha'",
    )
    escrever.add_argument("page_id")
    escrever.add_argument("conteudo", help="texto em Markdown a anexar")

    editar_bloco = sub.add_parser("editar-bloco", help="substitui o texto de um bloco")
    editar_bloco.add_argument("block_id")
    editar_bloco.add_argument("conteudo", help="nova linha em Markdown")

    apagar_bloco = sub.add_parser("apagar-bloco", help="apaga (arquiva) um bloco — destrutivo")
    apagar_bloco.add_argument("block_id")
    apagar_bloco.add_argument("--sim", action="store_true", help="confirma a exclusão")

    buscar = sub.add_parser("buscar", help="pesquisa páginas e databases visíveis")
    buscar.add_argument("query", nargs="?", help="texto do título; vazio lista tudo")

    clonar = sub.add_parser(
        "clonar-database",
        help="clona um database com todas as propriedades, sem vínculo com a origem",
    )
    clonar.add_argument("database_id")
    clonar.add_argument("--titulo", help="título do clone (padrão: '<origem> (cópia)')")
    clonar.add_argument("--pagina", help="página onde criar o clone (padrão: a pai da origem)")
    clonar.add_argument(
        "--com-linhas",
        action="store_true",
        help="copia também as linhas da origem",
    )
    clonar.add_argument(
        "--relacoes",
        choices=("auto-novo", "texto"),
        default="auto-novo",
        help="auto-novo: auto-relações apontam pro clone, externas preservam; "
        "texto: relações viram texto sem vínculo",
    )

    atualizar_github = sub.add_parser(
        "atualizar-github",
        help="re-sincroniza o database GITHUB (repos novos, propriedades, README mudado)",
    )
    atualizar_github.add_argument(
        "--contas",
        action="append",
        help="contas do GitHub (CSV); padrão: variável de ambiente GITHUB_CONTAS",
    )
    atualizar_github.add_argument(
        "--database",
        help="database de destino (padrão: NOTION_DATABASE_ID)",
    )
    atualizar_github.add_argument(
        "--sem-readme",
        action="store_true",
        help="atualiza só as propriedades, sem mexer na subpágina README",
    )

    sub.add_parser("guia", help="lista todos os comandos com o que fazem e exemplos")
    return parser


def executar(
    argv: Sequence[str] | None = None,
    *,
    tasklist_factory: TaskListFactory = _criar_tasklist,
    client_factory: ClientFactory = _criar_client,
) -> tuple[int, dict[str, Any] | str]:
    parser = construir_parser()
    args = parser.parse_args(argv)
    try:
        comando = args.comando
        if comando == "guia":
            dados = cmd_guia(args)
        elif comando == "listar":
            dados = cmd_listar(args, tasklist_factory=tasklist_factory)
        elif comando == "ler":
            dados = cmd_ler(args, tasklist_factory=tasklist_factory)
        elif comando == "criar":
            dados = cmd_criar(args, tasklist_factory=tasklist_factory)
        elif comando == "editar":
            dados = cmd_editar(args, tasklist_factory=tasklist_factory)
        elif comando == "mover":
            dados = cmd_mover(args, tasklist_factory=tasklist_factory)
        elif comando == "concluir":
            dados = cmd_concluir(args, tasklist_factory=tasklist_factory)
        elif comando == "opcoes":
            dados = cmd_opcoes(args, tasklist_factory=tasklist_factory)
        elif comando == "databases":
            dados = cmd_databases(args, client_factory=client_factory)
        elif comando == "database-atual":
            dados = cmd_database_atual(args, client_factory=client_factory)
        elif comando == "escolher-database":
            dados = cmd_escolher_database(args)
        elif comando == "normalizar-nomes":
            dados = cmd_normalizar_nomes(args, client_factory=client_factory)
        elif comando == "mapear":
            dados = cmd_mapear(args, client_factory=client_factory)
        elif comando == "conteudo":
            dados = cmd_conteudo(args, client_factory=client_factory)
        elif comando == "linhas":
            dados = cmd_linhas(args, client_factory=client_factory)
        elif comando == "editar-linha":
            dados = cmd_editar_linha(args, client_factory=client_factory)
        elif comando == "escrever":
            dados = cmd_escrever(args, client_factory=client_factory)
        elif comando == "editar-bloco":
            dados = cmd_editar_bloco(args, client_factory=client_factory)
        elif comando == "apagar-bloco":
            dados = cmd_apagar_bloco(args, client_factory=client_factory)
        elif comando == "buscar":
            dados = cmd_buscar(args, client_factory=client_factory)
        elif comando == "clonar-database":
            dados = cmd_clonar_database(args, client_factory=client_factory)
        elif comando == "atualizar-github":
            dados = cmd_atualizar_github(args, client_factory=client_factory)
        else:
            raise CLIError(f"Comando desconhecido: {comando}")
        return 0, _envelope(True, dados=dados) if args.json else _formatar_humano(comando, dados)
    except (CLIError, ValueError) as exc:
        return 2, _envelope(False, erro=str(exc)) if args.json else f"Erro: {exc}"
    except (NotionHTTPError, NotionAPIError) as exc:
        if isinstance(exc, NotionHTTPError) and exc.status_code == 404:
            mensagem = "Recurso não encontrado."
        else:
            mensagem = "Falha ao falar com o Notion."
        return 1, _envelope(False, erro=mensagem) if args.json else f"Erro: {mensagem}"
    except NotionConfigurationError:
        mensagem = "Configuração do Notion inválida."
        return 2, _envelope(False, erro=mensagem) if args.json else f"Erro: {mensagem}"


def _garantir_saida_utf8() -> None:
    """Evita ``UnicodeEncodeError`` em consoles Windows (cp1252).

    Páginas do Notion trazem setas, emojis e travessões que o cp1252 não
    representa; reconfigura stdout/stderr para UTF-8 com substituição, para a
    saída nunca derrubar o comando por causa de um caractere.
    """

    for fluxo in (sys.stdout, sys.stderr):
        reconfigure = getattr(fluxo, "reconfigure", None)
        if reconfigure is not None:
            reconfigure(encoding="utf-8", errors="replace")


def main(argv: Sequence[str] | None = None) -> int:
    _garantir_saida_utf8()
    codigo, saida = executar(argv)
    if isinstance(saida, dict):
        print(_json(saida))
    else:
        print(saida)
    return codigo
