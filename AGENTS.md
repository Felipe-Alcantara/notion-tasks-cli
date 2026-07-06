# AGENTS.md — notion-tasks-cli

CLI do Notion **feito para IAs** ("MCP via CLI"), módulo do ecossistema [Automações do Notion](https://github.com/Felipe-Alcantara/Automa-es-do-Notion) — o hub tem o roteamento completo entre módulos.

## Arquitetura (fronteiras sagradas)

```
cli/notion_tasks.py   → borda: parse de argumentos, saída humana/JSON, --help para IAs
services/             → regra de negócio (tarefas, clonagem, conteúdo, inventário, sync GitHub)
integrations/         → adaptadores externos (Notion via notion-starter, GitHub, OpenRouter)
core/config.py        → configuração (.env, token) — imutável, nunca vaza segredo em repr
```

- A borda (`cli/`) **não monta payload cru do Notion** nem contém regra de negócio.
- `services` não conhece argparse nem HTTP de borda.
- A base Notion vem da lib [notion-starter](https://github.com/Felipe-Alcantara/notion-starter) (dependência via git).

## ⚠️ Camada duplicada

`core/`, `integrations/` e `services/` também existem em `notion-workspace-app/server/`. Bugfix nessa camada deve ser aplicado **nos dois repositórios**. (Roadmap: consolidar no `notion-starter`.)

## Convenções do CLI

- Toda saída de máquina é JSON estável; o `--help` é um guia escrito para modelos de IA — mantenha-o atualizado ao mexer nos subcomandos.
- Comando destrutivo exige confirmação explícita (`apagar-bloco --sim`).
- Valide status/opções **antes** de chamar a API (previne 400); saneie surrogates com `notion_starter.utils`.
- Ao editar uma linha de database, **comece pelas propriedades** (colunas) com `editar-linha` e só depois escreva o conteúdo (blocos) com `escrever`. `editar-linha` (`services/propriedades.py`) infere o tipo de cada coluna da própria página (`NotionClient.obter_pagina`) e recusa tipos calculados (formula, rollup, created_time…). Não volte a montar payload cru do Notion para isso.
- Código e mensagens em português; Conventional Commits.

## Testar

```bash
python -m pytest
```
