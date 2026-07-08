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

---

Ideias abertas à contribuição: mais subcomandos de escrita em databases
multi-fonte, saída paginada para workspaces grandes, empacotamento no PyPI.
