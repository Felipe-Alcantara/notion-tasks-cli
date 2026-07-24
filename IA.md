# 🤖 IA.md — Contexto operacional do notion-tasks-cli

> **O que é**: Memória técnica deste repositório para retomada de contexto por IA ou
> por um novo mantenedor, sem reler todo o código. Baseado no template de contexto do
> Felixo System Design.
>
> **Histórico anterior**: este módulo nasceu da separação do monorepo
> [Automações do Notion](https://github.com/Felipe-Alcantara/Automa-es-do-Notion)
> em 2026-07-02. A linha do tempo anterior (decisões da CLI dentro do monorepo)
> permanece no `IA.md` do hub — este arquivo cobre a vida do módulo a partir da
> separação.

---

## 📊 ESTADO ATUAL (RESUMO VIVO)

Última atualização: [2026-07-18]

- Fase: CLI funcional e instalável, com saída JSON estável e perfis para múltiplos
  workspaces.
- Qualidade: 127 testes verdes e `ruff` limpo; CI cobre Python 3.10–3.13.
- Documentação: README alinhado ao Felixo System Design e contrato de qualidade
  centralizado em `QUALIDADE.md`.
- Próximos passos abertos: escrita multi-fonte, paginação de saídas grandes e
  melhorias de distribuição.
- Risco conhecido: ambientes consumidores devem fixar sua própria resolução de
  dependências quando precisarem de builds reproduzíveis.

---

## 🎯 OBJETIVO DO PROJETO

[2026-07-02] `notion-tasks-cli` é a CLI do ecossistema para pessoas e IAs
("MCP via CLI"): tarefas (listar/criar/editar/mover/concluir), conteúdo
(ler/escrever/editar blocos), busca, mapeamento do workspace, clonagem,
exportação DOCX e sincronização de repositórios GitHub. Instalável via pip
(`pip install git+https://github.com/Felipe-Alcantara/notion-tasks-cli.git`),
expõe o comando `notion-tasks` com envelope JSON estável para automação.

---

## 📐 DECISÕES DE ARQUITETURA

- [2026-07-02] A CLI é **borda fina**: `cli/notion_tasks.py` valida argumentos e
  formata saída; a regra de negócio compartilhada vive no `notion-starter`
  (`integrations/github.py`, `integrations/openrouter.py` e os `services/` comuns
  aqui são shims). O que é específico da CLI permanece aqui (ex.:
  `services/propriedades.py`).
- [2026-07-02] Contrato público: envelope JSON `{ok,dados}` / `{ok,erro}`;
  `--help` é o guia completo, escrito para ser lido por modelos.
- [2026-07-08] `start_app.py` adicionado como porta de entrada interativa
  (Instalar / Configurar `.env` / Status / Usar), conforme o contrato de menu de
  entrada do padrão de qualidade.
- [2026-07-08] Suporte inicial a múltiplos workspaces no CLI por perfis locais:
  `core/workspaces.py` guarda aliases em `.notion-workspaces.json` (ignorado pelo
  Git), mascara tokens em saídas públicas e aplica o perfil escolhido ao ambiente
  antes de criar `NotionClient`/`TaskList`. O `.env` segue compatível como fallback.

---

## 🛠️ STACK & DEPENDÊNCIAS

- Python 3.10+ (CI: 3.10–3.13). Runtime: `notion-starter` (dependência git direta).
- Dev: `pytest`, `responses`, `ruff`. Menu: `questionary` + `rich` (instaladas pelo
  próprio menu quando faltam).

---

## 🧪 TESTES & GATE

- Gate: `ruff check .` + `python -m pytest` (109 testes em 2026-07-08, sem rede).
- CI: GitHub Actions (`.github/workflows/ci.yml`) com matriz Python 3.10–3.13.

---

## 🧠 LINHA DO TEMPO

- [2026-07-02] ✅ Módulo extraído do monorepo; depois consolidado sobre o
  `notion-starter` (shims em `integrations/` e `services/` comuns).
- [2026-07-08] ✅ Alinhamento ao padrão de qualidade Felixo: adicionados
  `CONTRIBUTING.md`, `IA.md`, `start_app.py` (menu de entrada) e CI GitHub Actions.
  Validação: `ruff check .` limpo e 109 testes verdes; menu verificado manualmente
  (Status e fluxo de instalação).
- [2026-07-08] ✅ Perfis de workspaces/keys adicionados ao CLI (`perfis adicionar`,
  `perfis listar`, `perfis usar`, `perfis mostrar`, `perfis remover` e `--perfil`).
  Decisão: entregar primeiro na borda CLI, onde a necessidade operacional já existe,
  sem levar regra de perfis para os services compartilhados.
- [2026-07-13] ✅ Novos subcomandos como bordas finas sobre o notion-starter:
  `criar-database` (schema tipado via --prop), `importar-planilha` (.xlsx/.csv,
  upsert idempotente por Origem, tipos BR), `anexar-arquivo` (File Upload API,
  preservando anexos) e `mover-pagina`/`mover-database` (re-parent). Validação:
  124 testes verdes e ruff limpo.
- [2026-07-18] ✅ Documentação alinhada ao Felixo System Design: README passou a
  ter badges, índice, árvore real, guia operacional e rodapé open source;
  `QUALIDADE.md` centralizou o gate e registrou a exceção motivada de versões
  mínimas para um CLI instalável. Motivo: facilitar uso e contribuição sem impor
  pins incompatíveis ao ambiente consumidor. Validação: 127 testes verdes e
  `ruff` limpo.

- [2026-07-23] ✅ `atualizar-github --contas` passa a aceitar repositório
  específico (`owner/repo`/URL do repo), não só contas inteiras — mudança feita
  na implementação real em `notion-starter` (`services/inventario_github.py`,
  este módulo consome via shim). Motivo: trazer um projeto pontual de terceiros
  para o database sem importar toda a conta dele. Testes cobrindo o
  reconhecimento de formato e a coleta sem duplicar em
  `tests/test_services_inventario_github.py`; 132 testes verdes, ruff limpo.

- [2026-07-23] ✅ Quatro novos subcomandos como bordas finas sobre o
  `notion-starter` (`services/estrutura_projeto.py`): `criar-subpagina`,
  `inspecionar-estrutura`, `clonar-estrutura` e `montar-estrutura-projeto` —
  cobrem investigar e replicar a moldura fixa de projeto do workspace
  (README + Acompanhamento com 4 subpáginas + Planejamento e documentação com
  2 databases). Testes de CLI ponta a ponta com `FakeEstruturaClient` em
  `tests/test_cli_notion_tasks.py`; 137 testes verdes, ruff limpo.

---

Ideias abertas à contribuição: mais subcomandos de escrita em databases
multi-fonte, saída paginada para workspaces grandes, empacotamento no PyPI.
