# 🤖 notion-tasks-cli

<div align="center">

![Python 3.10+](https://img.shields.io/badge/Python-3.10%2B-3776AB?style=for-the-badge&logo=python&logoColor=white)
![CLI para IA](https://img.shields.io/badge/CLI-para%20IA-6C63FF?style=for-the-badge&logo=gnubash&logoColor=white)
![Licença MIT](https://img.shields.io/badge/Licen%C3%A7a-MIT-green?style=for-the-badge)

**Um “MCP via CLI” para pessoas e IAs operarem tarefas, páginas, blocos e databases do Notion.**

[📖 Sobre](#-sobre-o-projeto) • [🚀 Funcionalidades](#-funcionalidades) • [🎯 Como usar](#-como-usar) • [✅ Qualidade](#-qualidade)

</div>

---

## 📋 Índice

- [📖 Sobre o Projeto](#-sobre-o-projeto)
- [📁 Estrutura do Projeto](#-estrutura-do-projeto)
- [🚀 Funcionalidades](#-funcionalidades)
- [🎯 Como Usar](#-como-usar)
- [🔑 Perfis e Autenticação](#-perfis-e-autenticação)
- [💻 Desenvolvimento](#-desenvolvimento)
- [✅ Qualidade](#-qualidade)
- [📄 Licença](#-licença)
- [👤 Autor](#-autor)
- [🤝 Contribuições](#-contribuições)

---

## 📖 Sobre o Projeto

O `notion-tasks-cli` foi pensado para qualquer modelo de IA capaz de executar
comandos no terminal, como Claude Code ou
[Openia](https://github.com/Felipe-Alcantara/Openia). Ele cria, edita e manipula
workspaces do Notion sem exigir um servidor MCP em execução.

Servidores MCP dependem da configuração de cada cliente e de um processo ativo.
Este CLI oferece uma alternativa com saída JSON estável: o modelo lê `--help`,
executa comandos e interpreta o resultado. A validação prévia de status e o
saneamento de JSON evitam erros comuns da API.

O projeto faz parte do ecossistema
[Automações do Notion](https://github.com/Felipe-Alcantara/Automa-es-do-Notion) e
usa a biblioteca [notion-starter](https://github.com/Felipe-Alcantara/notion-starter)
como núcleo compartilhado.

---

## 📁 Estrutura do Projeto

```text
notion-tasks-cli/
│
├── 📁 cli/                      # Parse de argumentos e saída pública
│   ├── __main__.py              # Execução com python -m cli
│   └── notion_tasks.py          # Comando notion-tasks e guia --help
├── 📁 core/                     # Configuração e perfis locais
├── 📁 integrations/             # Notion local e shims de adaptadores
├── 📁 services/                 # Shims e operações específicas da CLI
├── 📁 tests/                    # Suíte automatizada sem rede
├── .github/workflows/ci.yml     # Gate em Python 3.10–3.13
├── start_app.py                 # Menu interativo de entrada
├── pyproject.toml               # Pacote e entry point notion-tasks
├── QUALIDADE.md                 # Contrato de qualidade do módulo
├── README.md                    # Este arquivo
└── LICENSE                      # Licença MIT
```

---

## 🚀 Funcionalidades

- **Tarefas** — listar, criar, editar, mover e concluir.
- **Workspace** — mapear o inventário, buscar páginas/databases e listar linhas.
- **Propriedades** — substituir ou acrescentar valores em linhas de database.
- **Conteúdo** — ler Markdown, escrever, substituir, editar ou apagar blocos.
- **Estruturas** — clonar páginas e estruturas do Notion.
- **Relatórios** — exportar relatórios diários para DOCX.
- **Automação para IA** — envelope JSON estável e `--help` escrito para modelos.
- **Múltiplos workspaces** — perfis locais com tokens mascarados nas saídas.

Exemplo de fluxo: intenção da IA → comando validado → JSON estável → alteração no
Notion.

---

## 🎯 Como Usar

### Instalação

```bash
# Instale diretamente do repositório
pip install git+https://github.com/Felipe-Alcantara/notion-tasks-cli.git
```

Prefere um passo a passo guiado? Clone o repositório e use o menu:

```bash
# Instalar, configurar, conferir status ou usar o CLI
python start_app.py
```

### Comandos principais

```bash
# Tarefas
notion-tasks listar
notion-tasks criar --titulo "Revisar proposta" --status "Em andamento"
notion-tasks editar <id> --titulo "Novo título"
notion-tasks mover <id> --status "Concluído"
notion-tasks concluir <id>

# Workspace
notion-tasks --perfil cliente listar
notion-tasks mapear
notion-tasks buscar <termo>
notion-tasks databases
notion-tasks linhas <id>
notion-tasks editar-linha <id> --set "Status=Feito"
notion-tasks editar-linha <id> --append "Resumo=..."

# Conteúdo de páginas
notion-tasks conteudo <id>
notion-tasks blocos <id>
notion-tasks escrever <id> "<markdown>"
notion-tasks escrever <id> "<markdown>" --substituir
notion-tasks editar-bloco <id> "<texto>"
notion-tasks apagar-bloco <id> --sim
notion-tasks limpar <id> --sim
notion-tasks clonar-database <id>

# Relatórios diários
notion-tasks exportar-docx --database <id> --de 2026-07-01 --ate 2026-07-06 --saida ./exports
```

Também funciona como módulo com `python -m cli ...`. Execute
`notion-tasks --help` para consultar o guia completo e os demais subcomandos.

---

## 🔑 Perfis e Autenticação

Use variáveis de ambiente ou um `.env` baseado em `.env.example`:

```bash
export NOTION_TOKEN=ntn_...
export NOTION_DATABASE_ID=<database_id>
```

Para operar vários workspaces sem trocar o `.env`, salve perfis locais. O arquivo
`.notion-workspaces.json` é ignorado pelo Git e as saídas mascaram tokens:

```bash
notion-tasks perfis adicionar cliente --token ntn_... --database <database_id> --ativar
notion-tasks perfis adicionar pessoal --token ntn_... --database <database_id>
notion-tasks perfis listar
notion-tasks --perfil cliente listar
notion-tasks perfis usar pessoal
```

Nunca versione tokens, IDs reais ou `.notion-workspaces.json`.

---

## 💻 Desenvolvimento

```bash
# Clone e instale com as dependências de desenvolvimento
git clone https://github.com/Felipe-Alcantara/notion-tasks-cli.git
cd notion-tasks-cli
pip install -e ".[dev]"

# Execute a suíte
python -m pytest
```

---

## ✅ Qualidade

```bash
python -m ruff check .
python -m pytest
```

A CI executa o gate em Python 3.10, 3.11, 3.12 e 3.13. Consulte
[`QUALIDADE.md`](QUALIDADE.md) para o critério de pronto e a política de
dependências do CLI.

---

## 📄 Licença

Este projeto está sob a licença MIT — veja [`LICENSE`](LICENSE).

---

## 👤 Autor

**Felipe Martin**

- GitHub: [@Felipe-Alcantara](https://github.com/Felipe-Alcantara)
- Repositório: [notion-tasks-cli](https://github.com/Felipe-Alcantara/notion-tasks-cli)

---

## 🤝 Contribuições

Contribuições são bem-vindas. Algumas ideias para quem quiser colaborar:

- ampliar os subcomandos de escrita em databases multi-fonte;
- criar saída paginada para workspaces grandes;
- melhorar o empacotamento e a distribuição;
- expandir testes, exemplos e documentação para IAs.

Leia [`CONTRIBUTING.md`](CONTRIBUTING.md) antes de enviar uma mudança.

---

⭐ Se este CLI foi útil, considere dar uma estrela no
[GitHub](https://github.com/Felipe-Alcantara/notion-tasks-cli).
