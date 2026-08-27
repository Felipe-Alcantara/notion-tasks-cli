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

- [2026-07-23] ✅ Novo subcomando `reordenar-bloco <pagina_id> <bloco_id>
  (--apos <id> | --inicio) [--forcar-tipos-arriscados]`, borda fina sobre
  `services/reordenacao.reordenar_bloco` do notion-starter. Recusa por padrão
  mover `child_page`/`child_database` (o ID muda e quebra referências
  externas) — a flag de força é obrigatória e o `--help` do comando avisa
  explicitamente do risco. Sempre grava backup em JSON antes de apagar o
  bloco original. Testes de CLI cobrindo o caminho seguro, a rejeição sem
  forçar e a validação de exatamente um alvo (`--apos` xor `--inicio`) em
  `tests/test_cli_notion_tasks.py`; 140 testes verdes, ruff limpo.

- [2026-07-23] ✅ `reordenar-bloco` atualizado: `--help` e o guia de exemplos
  deixam explícito que `child_database` nunca é suportado (mesmo com
  `--forcar-tipos-arriscados`) — acompanha a correção em
  `notion-starter/services/reordenacao.py` que virou `BlocoImpossivelError`.
  Removido o `except BlocoArriscadoError` redundante em `cmd_reordenar_bloco`:
  o catch genérico `(CLIError, ValueError, ...)` do dispatcher já cobre as
  duas exceções (ambas herdam de `ValueError`). Novo teste cobrindo a
  rejeição de `child_database` mesmo com a flag; 141 testes verdes, ruff
  limpo.

- [2026-07-24] ✅ Novo subcomando `garantir-coluna <database_id> <nome_coluna>
  <tipo>`, borda fina sobre `services.schema.garantir_coluna` do
  notion-starter. Reusa `starter_properties.schema_propriedade` para os
  mesmos nomes de tipo em português já usados em `criar-database` (titulo,
  texto, numero, select, …). Idempotente: reporta `criada: false` sem tocar
  em nada se a coluna já existe. TDD: 5 testes de CLI escritos e confirmados
  falhando (comando inexistente) antes da implementação; 146 testes verdes,
  ruff limpo.

---

Ideias abertas à contribuição: mais subcomandos de escrita em databases
multi-fonte, saída paginada para workspaces grandes, empacotamento no PyPI.

---

## [2026-08-17] Comandos que impedem o erro em vez de documentá-lo

**Contexto.** Uma sessão longa operando o Notion de verdade (17 tarefas criadas,
16 reescritas, 48 ligações) mostrou que a CLI documentava as regras certas e não
as **fazia valer**. Quatro mudanças, todas nascidas de fricção medida:

### `schema <database_id>` — a pergunta que antecede toda escrita

Descobrir nome exato de coluna, valores aceitos por select/status, o que o Notion
calcula e como cada relação está configurada exigia chamar a API crua. Agora é um
comando. `--editaveis` esconde o que não aceita PATCH. Implementação em
`notion_starter.schema.descrever_database`.

### `relacionar <a> <b> --coluna "Nome"`

Ligar duas linhas com `editar-linha` na mão exige saber se o Notion espelha a
outra ponta — e **o tipo declarado não permite saber** (ver `IA.md` do
`notion-starter`, mesma data, com o experimento). O comando confere e grava só o
que faltar; idempotente, com `--desfazer`. Mensagens de erro listam as colunas de
relação disponíveis quando o nome não existe, e mandam para `editar-linha` quando
a coluna não é relação.

### `escrever` recusa página que contém database

Era o erro relatado com modelos mais fracos: link de uma página que **contém** a
database, texto escrito solto abaixo da tabela. Agora falha com a lista das
databases (título + ID) e os comandos prontos; `--mesmo-com-database` libera.
`conteudo` também passou a devolver `databases_dentro` + `aviso`, para o problema
aparecer já na **leitura**. A exceção é tratada na borda como erro de uso (código
2, mensagem inteira, sem traceback) — traceback só atrapalha quem lê.

### `criar --set` e `--conteudo`

O ciclo `criar` → `editar-linha` → `escrever` eram três chamadas, e um script que
estourasse no meio deixava linha órfã sem o operador saber o ID. Agora `criar`
aceita qualquer coluna e o corpo em Markdown. Se algo falhar **depois** da linha
existir, o erro traz o ID e a instrução explícita de completar em vez de recriar.

### `--apagar-tudo` em `escrever`/`limpar`

`--substituir` agora preserva blocos não recriáveis por padrão e **relata** o que
manteve. `--apagar-tudo` volta ao comportamento antigo, sob pedido explícito.

**Efeito colateral nos testes**: `test_cli_status_validation` e
`test_integration_status_validation` usavam `Mock()` para os args, e `Mock`
auto-cria atributos — `args.set` virava verdadeiro e o `criar` tentava completar
a linha com um Mock. Os fakes passaram a declarar `set`/`conteudo` como `None`.

**Validação real** (2026-08-17): todos os caminhos rodados contra o workspace do
usuário, com quatro linhas de teste criadas e arquivadas ao fim. 166 testes
verdes, `ruff` limpo.

---

## [2026-08-24] Os perfis saíram de junto do pacote e foram para a pasta de configuração (0.2.1)

### O sintoma

`notion-tasks perfis listar` respondeu **Nenhum perfil configurado** logo depois de
uma reinstalação, com os quatro perfis reais salvos. Pareceu perda de dado — e dado
aqui é token de integração do Notion.

### A causa

`core/workspaces.py` derivava o endereço do store de `__file__`:

```python
ARQUIVO_PADRAO = Path(__file__).resolve().parents[1] / ".notion-workspaces.json"
```

O arquivo morava **ao lado do pacote instalado**. Trocar o modo de instalação
troca o endereço:

| Modo | Onde a CLI procurava |
| --- | --- |
| não editável | `site-packages/.notion-workspaces.json` |
| editável | `modules/notion-tasks-cli/.notion-workspaces.json` |

Nada se perdia, mas só se recuperava quem soubesse procurar. E cada modo deixava
mais uma cópia de tokens espalhada pelo disco — na máquina do Felipe havia duas.
Uma delas dentro de um repositório git, protegida por uma linha de `.gitignore`.

### A decisão

Store na pasta de configuração do usuário, pela convenção do sistema:
`$XDG_CONFIG_HOME/notion-tasks/` (padrão `~/.config/notion-tasks/`) e
`%APPDATA%\notion-tasks\` no Windows. Arquivo `600`, pasta `700`.

**Migração automática na primeira leitura**, uma vez, com aviso em `stderr`. Se ela
falhar (disco somente leitura, permissão), a CLI **continua usando o endereço
antigo** em vez de dizer que não há perfil — manter o usuário funcionando no lugar
errado é melhor do que fingir amnésia.

### Duas armadilhas que a implementação encontrou

**1. `chmod 700` no diretório-pai quase fechou a HOME.** A primeira versão
restringia a pasta do store sempre. Como o parâmetro `caminho` aceita qualquer
lugar, um store apontado para dentro da HOME faria a CLI trancar a HOME inteira.
Agora `_garantir_pasta` só restringe a pasta **que ela mesma criou**; pasta
preexistente não é tocada, e há teste para isso.

**2. O teste que deveria proteger a mudança não protegia.** A asserção rodava no
processo da suíte, onde a fixture `perfis_isolados` (autouse) troca
`ARQUIVO_PADRAO` por `tmp_path` — necessário para o perfil real não vazar, mas
apaga justamente o valor que o teste precisava observar. **Medido:** com a
mutação `ARQUIVO_PADRAO = Path(__file__)...`, os 16 testes passavam. O teste passou
a ler o valor num subprocesso e a mutação passou a derrubá-lo, como devia.

Também por causa do `pathlib`: testar a variante do Windows trocando `os.name` no
processo faz o próprio `pathlib` construir `WindowsPath` e explodir em POSIX. A
decisão virou função pura — `decidir_pasta_configuracao(windows=, ambiente=, home=)`
— e o sistema entra por parâmetro.

### Validação

179 testes verdes, `ruff` limpo. Migração real medida na máquina: os quatro perfis
saíram de `modules/notion-tasks-cli/` para `~/.config/notion-tasks/`, arquivo `600`,
pasta `700`, aviso impresso uma vez só. Critério de ponta: instalação trocada de
editável para não editável e de volta — `perfis listar` devolveu exatamente a mesma
lista nos dois modos. Ao fim, restou **uma** cópia do store no disco, fora de
qualquer repositório git.

### Validação em Windows (27/08/2026) — e um risco real encontrado

A entrada acima media só Linux. Três pontos conferidos agora num Python 3.14 no
Windows, com dados sintéticos (sem tocar no store real desta máquina):

1. **`pasta_configuracao()` devolve o `%APPDATA%` de verdade** —
   `C:\Users\...\AppData\Roaming\notion-tasks`, não o fallback `~/AppData/Roaming`.
2. **A migração funciona** — `.notion-workspaces.json` sintético num "endereço
   antigo" isolado, primeira chamada de `_migrar_legado` move o arquivo, imprime
   o aviso uma vez em stderr, o antigo deixa de existir e `carregar_store` lê os
   perfis migrados sem diferença de conteúdo.
3. **O risco de maior severidade da task era real, e agora está medido.**
   `os.chmod` é, como o próprio código já admitia, um no-op de fato no Windows —
   e a ACL herdada não é equivalente a um `0600` POSIX nesta máquina: a pasta
   `%APPDATA%\Roaming` (e, por herança, `%APPDATA%\notion-tasks\` e qualquer
   arquivo criado dentro) concede `(RX)` — Leitura e Execução — ao grupo local
   `CodexSandboxUsers`, que existe nesta máquina para isolar sessões do Codex CLI
   (`CodexSandboxOffline`, `CodexSandboxOnline`). Confirmado num arquivo real
   criado dentro da pasta (`icacls`): a herança inclui leitura de conteúdo, não
   só listagem de diretório. Isto significa que **um processo sandboxed do Codex
   nesta máquina pode ler o token do Notion do usuário**, e nada no código atual
   detecta ou avisa isso — `_restringir` engole o `OSError` de propósito.

   **Não ficou hipotético.** No meio desta mesma investigação, `carregar_store()`
   disparou a migração real desta máquina (o `.notion-workspaces.json` do
   repositório, com os tokens `felipe`/`flavia` de verdade, ainda não tinha sido
   migrado). O arquivo real resultante em `%APPDATA%\notion-tasks\` tem a mesma
   ACL medida acima — `CodexSandboxUsers:(I)(RX)` — confirmada com `icacls` no
   arquivo de credenciais real, não numa cópia sintética.

   Isto é específico da configuração desta máquina (o grupo é "managed" pelo
   próprio Codex, não algo que o `notion-tasks-cli` controla), não um defeito
   universal do Windows: um perfil sem esse grupo de sandbox teria a ACL
   default de `%APPDATA%` restrita a dono + SYSTEM + Administradores, que já
   seria aceitável. Mas o código não tem como saber disso, e hoje não tenta.
   Virou task própria — não é escopo desta consertar em cima da hora.

---

## [2026-08-25] `criar` funciona fora do database de tarefas

O comando dizia aceitar qualquer `--set`, mas a primeira chamada ainda criava a
linha pelo `TaskList` com o título fixo `Tarefa`. Em `Relatórios diários`, cuja
coluna title é `Relatório`, a API recusava o payload antes de `Data`, `Status` e o
corpo serem preenchidos.

A descoberta do título e a omissão dos campos de tarefa ausentes ficaram no
`notion-starter`; a CLI permaneceu borda fina. O mesmo `TaskList` agora é
reutilizado entre a validação de status e a criação, aproveitando o cache de
schema. Erros HTTP deixaram de virar apenas "Falha ao falar com o Notion": a
saída inclui status e o corpo (truncado e tipado pelo cliente), que normalmente
contém `code` e `message` acionáveis.

**Validação.** 181 testes verdes e `ruff` limpo. Prova real nos perfis
`relatorios` e `home-pessoal`: criação com `--set Data`, `--set Status` e
`--conteudo` no primeiro; criação com `--status`/`--duracao` no segundo. As duas
linhas temporárias foram arquivadas ao fim.
