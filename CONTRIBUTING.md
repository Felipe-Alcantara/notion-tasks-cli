# 🤝 Contribuindo com o notion-tasks-cli

Obrigado por querer contribuir! Este repositório é a CLI do ecossistema
[Automações do Notion](https://github.com/Felipe-Alcantara/Automa-es-do-Notion),
pensada para pessoas e IAs ("MCP via CLI"): listar/criar/editar tarefas, ler e
escrever conteúdo, clonar estruturas, exportar DOCX e sincronizar GitHub. Issues,
correções de documentação, novos subcomandos, testes e melhorias de UX da saída
JSON são bem-vindos.

> Contribuições devem preservar os contratos existentes (envelope JSON
> `{ok,dados}` / `{ok,erro}`), a documentação viva e o gate de qualidade abaixo.

---

## 🚀 Como Contribuir

1. **Faça um fork** do repositório.
2. **Crie uma branch** descritiva (`fix/...`, `feat/...`, `docs/...`) para mudanças
   grandes; correções pequenas podem ir direto no `main` de quem mantém.
3. **Faça suas mudanças** seguindo os padrões abaixo.
4. **Rode os testes e o lint** antes de abrir o PR.
5. **Abra um Pull Request** explicando o que mudou e por quê.

---

## 🛠️ Ambiente de Desenvolvimento

```bash
git clone https://github.com/Felipe-Alcantara/notion-tasks-cli.git
cd notion-tasks-cli
python start_app.py          # menu: Instalar / Configurar / Status / Usar

# Ou manualmente:
pip install -e ".[dev]"
ruff check .
python -m pytest
```

Requer Python 3.10+. Os testes mockam todo o HTTP — não precisam de token nem
rede. Copie `.env.example` para `.env` só para uso real; nunca versione o `.env`.

---

## ✅ Padrões de Qualidade

- **Entenda o padrão existente antes de alterar.** A CLI é uma **borda fina**:
  valida argumentos, formata saída humana/JSON e delega para os `services`. A regra
  de negócio compartilhada vive no
  [`notion-starter`](https://github.com/Felipe-Alcantara/notion-starter) —
  `integrations/` e os `services/` comuns aqui são shims; corrija a implementação
  real lá.
- **Preserve contratos.** O envelope JSON e os nomes/argumentos dos subcomandos são
  consumidos por IAs e scripts; mudança quebradora precisa ser explícita e
  documentada no `--help`.
- **Tipos e validação.** `TypedDict`/`dataclass`; valide entradas externas. Operações
  destrutivas exigem confirmação explícita (ex.: `apagar-bloco --sim`).
- **Não exponha segredos.** Nada de tokens, IDs reais ou URLs privadas em código,
  testes ou documentação.
- **Teste o comportamento.** Bugs corrigidos viram regressão; HTTP mockado com
  `responses`, serviços injetados com doubles.
- **Código, docstrings e mensagens de erro em português.**
- **Atualize a documentação viva** (`README.md`, `--help`, `IA.md`) no mesmo passo.

---

## ✍️ Padrões de Linguagem (Documentação e Logs)

- Linguagem geral e acessível, sem jargão interno.
- Sem valores hardcoded — placeholders genéricos em vez de caminhos/tokens reais.
- Trabalho futuro como convite à contribuição, não lista de tarefas interna.

---

## 🔄 Fluxo de Pull Request

Um bom PR responde: **o que mudou**, **por que mudou**, **como foi validado**
(ex.: `ruff check .` + `python -m pytest`) e **qual risco sobrou**. Commits
pequenos no formato `tipo: descrição` (`feat`/`fix`/`docs`/`refactor`/`chore`).

---

## 💬 Código de Conduta

Seja respeitoso e acolhedor. Contribuições de pessoas de todos os níveis de
experiência são bem-vindas.
