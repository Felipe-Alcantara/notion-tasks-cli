# notion-tasks-cli

CLI do Notion **pensado para IAs**: um "MCP via CLI". Qualquer modelo de IA capaz de rodar comandos no terminal (Claude Code, [Openia](https://github.com/Felipe-Alcantara/Openia), etc.) consegue criar, editar e manipular **qualquer workspace do Notion** — tarefas, páginas, blocos, databases — sem precisar de um servidor MCP rodando.

> Parte do ecossistema [Automações do Notion](https://github.com/Felipe-Alcantara/Automa-es-do-Notion). Construído sobre a biblioteca [notion-starter](https://github.com/Felipe-Alcantara/notion-starter).

## Instalação

```bash
pip install git+https://github.com/Felipe-Alcantara/notion-tasks-cli.git
```

Configure o token (ou use um arquivo `.env`, veja `.env.example`):

```bash
export NOTION_TOKEN=ntn_...
export NOTION_DATABASE_ID=...
```

## Uso

```bash
# Tarefas
notion-tasks listar
notion-tasks criar --titulo "Revisar proposta" --status "Em andamento"
notion-tasks editar <id> --titulo "Novo título"
notion-tasks mover <id> --status "Concluído"
notion-tasks concluir <id>

# Workspace
notion-tasks mapear              # resume o inventário do workspace
notion-tasks buscar <termo>      # pesquisa páginas e databases
notion-tasks databases           # lista databases visíveis
notion-tasks linhas <id>         # lista as linhas de um database
notion-tasks editar-linha <id> --set "Status=Feito"   # edita propriedades (colunas) de uma linha

# Conteúdo de páginas
notion-tasks conteudo <id>       # lê uma página como Markdown
notion-tasks escrever <id>       # anexa Markdown a uma página
notion-tasks editar-bloco <id>   # substitui o texto de um bloco
notion-tasks clonar <id>         # clona páginas/estruturas
```

Também funciona como módulo: `python -m cli ...` — e `--help` traz o guia completo, escrito para ser lido por modelos de IA.

### Por que "MCP via CLI"?

Servidores MCP exigem configuração por cliente e um processo rodando. Um CLI com saída JSON estável dá à IA a mesma capacidade com custo zero de setup: o modelo lê `--help`, executa comandos e interpreta o resultado. Validação prévia de status e saneamento de JSON evitam os erros 400 mais comuns da API do Notion.

## Desenvolvimento

```bash
git clone https://github.com/Felipe-Alcantara/notion-tasks-cli.git
cd notion-tasks-cli
pip install -e ".[dev]"
pytest
```

## Licença

MIT
