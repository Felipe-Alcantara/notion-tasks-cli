# AGENTS.md — notion-tasks-cli

CLI do Notion **feito para IAs** ("MCP via CLI"), módulo do ecossistema [Automações do Notion](https://github.com/Felipe-Alcantara/Automa-es-do-Notion) — o hub tem o roteamento completo entre módulos.

## Arquitetura (fronteiras sagradas)

```
cli/notion_tasks.py   → borda: parse de argumentos, saída humana/JSON, --help para IAs
services/             → shims para notion_starter.services; exceção: propriedades.py é específico do CLI
integrations/         → Notion local + shims para adaptadores GitHub/OpenRouter do notion-starter
core/config.py        → configuração (.env, token) — imutável, nunca vaza segredo em repr
```

- A borda (`cli/`) **não monta payload cru do Notion** nem contém regra de negócio.
- `services` não conhece argparse nem HTTP de borda.
- A base Notion vem da lib [notion-starter](https://github.com/Felipe-Alcantara/notion-starter) (dependência via git).

## Camada compartilhada

`integrations/github.py`, `integrations/openrouter.py` e os `services` comuns são shims para
`notion-starter`. Bugfix de regra compartilhada deve ser feito em
`modules/notion-starter/src/notion_starter/`. `services/propriedades.py` continua específico do
CLI.

## Convenções do CLI

- Toda saída de máquina é JSON estável; o `--help` é um guia escrito para modelos de IA — mantenha-o atualizado ao mexer nos subcomandos.
- Comando destrutivo exige confirmação explícita (`apagar-bloco --sim`).
- Valide status/opções **antes** de chamar a API (previne 400); saneie surrogates com `notion_starter.utils`.
- Ao editar uma linha de database, **comece pelas propriedades** (colunas) com `editar-linha` e só depois escreva o conteúdo (blocos) com `escrever`. `editar-linha` (`services/propriedades.py`) infere o tipo de cada coluna da própria página (`NotionClient.obter_pagina`) e recusa tipos calculados (formula, rollup, created_time…). `--set "Nome=valor"` substitui; `--append "Nome=texto"` acrescenta ao final de colunas de texto (title/rich_text) preservando o conteúdo atual. Texto longo é fatiado em ≤2000 unidades pelos builders da lib (`properties.title`/`rich_text`). Não volte a montar payload cru do Notion para isso.
- Código e mensagens em português; Conventional Commits.

## Testar

```bash
python -m pytest
```
