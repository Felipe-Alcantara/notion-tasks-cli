# 🤖 notion-tasks-cli

<div align="center">

![Python 3.10+](https://img.shields.io/badge/Python-3.10%2B-3776AB?style=for-the-badge&logo=python&logoColor=white)
![CLI para IA](https://img.shields.io/badge/CLI-para%20IA-6C63FF?style=for-the-badge&logo=gnubash&logoColor=white)
[![PyPI](https://img.shields.io/pypi/v/notion-automacoes?style=for-the-badge&label=PyPI)](https://pypi.org/project/notion-automacoes/)
![Licença MIT](https://img.shields.io/badge/Licen%C3%A7a-MIT-green?style=for-the-badge)

**A CLI única para pessoas e IAs operarem tarefas, páginas, blocos e databases do Notion.**

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
│   ├── atualizacao_nativa.py    # Update seguro dos binários PyInstaller
│   ├── unificada.py             # Entrada distribuída notion-automacoes
│   └── notion_tasks.py          # Comando notion-tasks e guia --help
├── 📁 core/                     # Configuração e perfis locais
├── 📁 integrations/             # Notion local e shims de adaptadores
├── 📁 services/                 # Shims e operações específicas da CLI
├── 📁 tests/                    # Suíte automatizada sem rede
├── 📁 scripts/                  # Builder e smoke dos binários nativos
├── .github/workflows/ci.yml     # Gate em Python 3.10–3.13
├── .github/workflows/native-release.yml # Matriz PyInstaller e assets
├── start_app.py                 # Menu interativo de entrada
├── pyproject.toml               # Pacote e entry points públicos
├── QUALIDADE.md                 # Contrato de qualidade do módulo
├── README.md                    # Este arquivo
└── LICENSE                      # Licença MIT
```

---

## 🚀 Funcionalidades

- **Tarefas** — listar, criar, editar, mover e concluir; `criar` também aceita
  databases genéricos ao descobrir a coluna de título pelo schema.
- **Projetos** — `criar` e `editar-linha` podem resolver a relação `Projeto` a
  partir da URL GitHub; `--strict` valida URL, relação e título antes de escrever.
- **Workspace** — mapear o inventário, buscar páginas/databases e listar linhas;
  `exemplo` devolve uma amostra de linhas com propriedades e corpo completos.
- **Propriedades** — substituir ou acrescentar valores em linhas de database.
- **Conteúdo** — ler Markdown, escrever, substituir, editar ou apagar blocos.
- **Estruturas** — clonar páginas e estruturas do Notion.
- **Relatórios** — exportar relatórios diários para DOCX.
- **Distribuição nativa** — detectar novas Releases, validar SHA-256 e atualizar
  executáveis PyInstaller com backup local; rollback de produto continua manual
  pela Release anterior. O workflow produz Windows x64, macOS Intel, macOS ARM64
  e Linux x64 com assets determinísticos e checksum irmão.
- **Automação para IA** — envelope JSON estável e `--help` escrito para modelos.
- **Múltiplos workspaces** — perfis locais com tokens mascarados nas saídas.

Exemplo de fluxo: intenção da IA → comando validado → JSON estável → alteração no
Notion.

---

## 🎯 Como Usar

### Instalação

```bash
# Instalação completa recomendada (CLI + app + MCP)
pipx install "notion-automacoes[app]"
# alternativa: uv tool install "notion-automacoes[app]"
```

O pacote público [`notion-automacoes==0.3.0`](https://pypi.org/project/notion-automacoes/)
é a fachada distribuída do repositório. A instalação básica, sem a interface
gráfica, é `pipx install notion-automacoes`; o extra `app` adiciona Django, MCP
e a SPA React já compilada no wheel. Não é necessário clonar Git nem instalar
Node/npm para uso distribuído.

Primeiros comandos, sem token:

```bash
notion-automacoes --version
notion-automacoes doctor
```

Uso unificado:

```bash
notion-automacoes auth listar
notion-automacoes tasks listar
notion-automacoes app start
notion-automacoes mcp start
notion-automacoes update
notion-automacoes update --dry-run
```

O alias histórico permanece disponível:

```bash
notion-tasks listar
```

Para conferir a instalação sem credenciais:

```bash
notion-automacoes --version
notion-automacoes --help
notion-automacoes doctor
notion-automacoes auth listar
```

Consulte o [contrato de distribuição do hub](https://github.com/Felipe-Alcantara/Automa-es-do-Notion/blob/main/docs/DISTRIBUICAO.md)
para a matriz de release, a política de perfis e os limites do primeiro release.

Em binários nativos, comandos normais verificam uma Release estável no máximo
uma vez por 24 horas e fazem a troca com checksum; `update --dry-run` mostra o
plano sem alterar o disco. `NOTION_AUTOMACOES_NO_UPDATE=1` desabilita a
verificação automática. Em instalações Python o comando `update` continua
apenas mostrando o comando seguro de `pipx`, `uv` ou `pip`.

O rollback de produto é manual: baixe na Release anterior o asset correspondente
ao sistema, valide assinatura e `.sha256`, encerre o programa e substitua o
executável. A política de publicação mantém pelo menos duas Releases estáveis;
o arquivo `<executável>.previous` é somente uma recuperação local adicional.

### Binários nativos

O workflow `Native binaries` é acionado por tags SemVer (`vX.Y.Z`) e também pode
ser executado manualmente para uma tag existente. Cada runner constrói um
executável PyInstaller `--onefile`, embute a versão da tag, executa o smoke de
`--version`, `--help`, `tasks --help` e `doctor`, e publica o binário junto do
asset `<executável>.sha256` como artefato do workflow.

Os quatro nomes oficiais são:

```text
notion-automacoes-windows-x64.exe
notion-automacoes-macos-x64
notion-automacoes-macos-arm64
notion-automacoes-linux-x64
```

A anexação à GitHub Release é manual (`workflow_dispatch` com
`publicar_release=true`) e passa pelo ambiente protegido `native-release`. Antes
de aprovar essa etapa, os assets precisam passar pelo processo de assinatura e
notarização da task correspondente. A task de empacotamento não altera a Release
`0.3.0` existente.

Prefere um passo a passo guiado? Clone o repositório e use o menu:

```bash
# Instalar, configurar, conferir status ou usar o CLI
python start_app.py
```

### Comandos principais

```bash
# Tarefas
notion-tasks listar
notion-tasks criar "Revisar proposta" --status "Entrada"
notion-tasks editar <id> --nome "Novo título"
notion-tasks mover <id> "Concluído"
notion-tasks concluir <id> "Concluído"

# Linha em qualquer database (a coluna title é descoberta automaticamente)
notion-tasks criar "Relatório — 25/08/2026" \
  --set "Data=2026-08-25" --set "Status=Concluído" --conteudo "# Resultado"

# Projeto GitHub: a URL resolve a única linha correspondente da database GITHUB
notion-tasks criar "Automações-do-Notion/Tasks — nova regra" \
  --set "URL de referência=https://github.com/Felipe-Alcantara/Automa-es-do-Notion.git/tree/main?tab=files" \
  --strict
notion-tasks editar-linha <id> \
  --set "URL de referência=https://github.com/Felipe-Alcantara/Automa-es-do-Notion" \
  --strict

# Lotes de linhas (um único processo; progresso vai para stderr)
notion-tasks criar --arquivo novas-linhas.json --progresso-a-cada 25
notion-tasks editar-linha --arquivo atualizacoes.json --progresso-a-cada 25

# Workspace
notion-tasks --perfil cliente listar
notion-tasks mapear
notion-tasks buscar <termo>
notion-tasks databases
notion-tasks linhas <id>
notion-tasks exemplo --n 3
notion-tasks editar-linha <id> --set "Status=Feito"
notion-tasks editar-linha <id> --append "Resumo=..."

# Relações (o modo de lote reutiliza o mesmo processo e cliente)
notion-tasks relacionar <page_a> <page_b> --coluna "Subtarefas relacionadas"
notion-tasks relacionar --coluna "Subtarefas relacionadas" \
  --par a1:b1 --par a2:b2
notion-tasks relacionar --coluna "Subtarefas relacionadas" --arquivo pares.json

# Conteúdo de páginas
notion-tasks conteudo <id>
notion-tasks blocos <id>
notion-tasks escrever <id> "<markdown>"
notion-tasks escrever <id> "<markdown>" --substituir
notion-tasks editar-bloco <id> "<texto>"
notion-tasks apagar-bloco <id> --sim
notion-tasks limpar <id> --sim
notion-tasks clonar-database <id>

# Estrutura de projeto (subpáginas, databases, padrão do workspace)
notion-tasks criar-subpagina <pagina_pai_id> "Estado atual"
notion-tasks inspecionar-estrutura <pagina_id> --profundidade 3
notion-tasks clonar-estrutura <pagina_referencia_id> <pagina_destino_id>
notion-tasks montar-estrutura-projeto <pagina_id>
notion-tasks reordenar-bloco <pagina_id> <bloco_id> --apos <outro_bloco_id>
notion-tasks reordenar-bloco <pagina_id> <bloco_id> --inicio
notion-tasks garantir-coluna <database_id> Idioma select

# Relatórios diários
notion-tasks exportar-docx --database <id> --de 2026-07-01 --ate 2026-07-06 --saida ./exports
```

`--arquivo` recebe uma lista JSON de objetos com `page_a` e `page_b`. Também são
aceitos itens no formato `"a:b"` ou listas de dois IDs. O resultado em JSON traz
um relatório por par em `resultados`, incluindo sucessos e falhas sem interromper
os demais pares.

Nos comandos `criar` e `editar-linha`, `--arquivo` recebe um lote de linhas sem
abrir um novo processo para cada item. Em JSON, uma edição usa
`{"page_id": "<page_id>", "propriedades": {"Status": "Feito"}}`; uma criação
usa `{"nome": "Nova linha", "propriedades": {"Status": "Entrada"}}`. O campo
`append` é opcional para acrescentar texto em colunas de texto. Também são aceitos
os aliases `id`/`titulo` e a lista de itens `Nome=valor`.

CSV usa `page_id` (ou `id`) para editar e `nome` (ou `titulo`) para criar; todas as
outras colunas são propriedades e colunas com prefixo `append:` fazem append. A
saída JSON traz `total`, `processados`, `sucessos`, `erros`, `pendentes` e um item
em `resultados` para cada linha. Falhas de validação/API ficam na linha afetada e
as demais continuam; uma criação feita cuja complementação falhe fica como
`pendente` com o ID já criado. O progresso periódico é emitido em stderr para
manter stdout como JSON válido.

Quando a entrada informa `URL de referência` (ou uma URL GitHub na coluna
`Projeto`), o CLI normaliza `owner/repo`, ignora `.git`, subcaminho, query e
fragmento, e procura a linha correspondente na database relacionada `GITHUB`.
Uma correspondência única é aplicada com `relacionar` e confirmada por releitura;
URL desconhecida nunca inventa uma relação. `--strict` faz esse preflight antes
da primeira escrita, exige o título no formato
`<projeto>/<contexto> — descrição` e bloqueia URL, projeto ou título
inconsistentes. Sem `--strict`, a URL desconhecida gera aviso e a forma legada
continua compatível. Tarefas pessoais continuam permitidas quando não têm URL
GitHub nem `Projeto`.

Use `--dry-run` para executar o preflight e visualizar as propriedades/relação
planejadas sem criar ou editar nada. Com `--arquivo --strict`, todas as linhas
são validadas primeiro; uma entrada inválida bloqueia o lote inteiro para evitar
escrita parcial. `--arquivo --dry-run` mostra o plano de cada linha.

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

### Onde os perfis ficam guardados

Na pasta de configuração do usuário, seguindo a convenção do sistema:

| Sistema | Caminho |
| --- | --- |
| Linux / macOS | `$XDG_CONFIG_HOME/notion-tasks/` (padrão: `~/.config/notion-tasks/`) |
| Windows | `%APPDATA%\notion-tasks\` |

O arquivo é criado com permissão `600` e a pasta com `700`.

> **Se você tinha perfis salvos antes da versão 0.2.1**, eles moravam ao lado do
> pacote instalado — o que fazia trocar o modo de instalação (editável ↔ não
> editável) parecer apagar os perfis, porque a CLI passava a procurar noutro
> endereço. Não é preciso fazer nada: na primeira execução a CLI move o arquivo
> para o novo lugar e avisa na saída de erro. Se a migração não for possível
> (disco somente leitura, permissão), a CLI continua usando o endereço antigo em
> vez de fingir que não há perfil nenhum.

---

## 💻 Desenvolvimento

```bash
# Clone e instale com as dependências de desenvolvimento
git clone https://github.com/Felipe-Alcantara/notion-tasks-cli.git
cd notion-tasks-cli
python -m pip install -e ".[dev]"

# Para construir binários nativos localmente
python -m pip install -e ".[native]"

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

O build nativo é reproduzível por alvo com:

```bash
python scripts/build_native.py --target linux-x64 --version v0.4.0 --output dist-native
python scripts/smoke_native.py --executable dist-native/notion-automacoes-linux-x64 --version v0.4.0
```

---

## 📄 Licença

Este projeto está sob a licença MIT — veja [`LICENSE`](LICENSE).

---

## 👤 Autor

**Felipe Alcantara**

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
