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

Última atualização: [2026-09-04]

- Fase: fachada distribuída `notion-automacoes==0.3.0` publicada, com alias
  histórico `notion-tasks`, saída JSON estável e perfis persistentes.
- Qualidade: 198 testes verdes e `ruff` limpo; CI cobre Python 3.10–3.13.
- Documentação: README alinhado ao Felixo System Design e contrato de qualidade
  centralizado em `QUALIDADE.md`.
- Próximos passos abertos: escrita multi-fonte e paginação de saídas grandes,
  como contribuições isoladas.
- Risco conhecido: ambientes consumidores devem fixar sua própria resolução
  quando precisarem de builds reproduzíveis; o pacote público usa faixas
  compatíveis para evitar conflitos no ambiente consumidor.

---

## 🎯 OBJETIVO DO PROJETO

[2026-07-02] `notion-tasks-cli` é a CLI do ecossistema para pessoas e IAs
("MCP via CLI"): tarefas (listar/criar/editar/mover/concluir), conteúdo
(ler/escrever/editar blocos), busca, mapeamento do workspace, clonagem,
exportação DOCX e sincronização de repositórios GitHub. Expõe o comando
`notion-tasks` com envelope JSON estável para automação e, desde a preparação da
distribuição, também fornece a fachada `notion-automacoes`.

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

- Python 3.10+ (CI: 3.10–3.13). Runtime: `notion-starter>=0.3.0,<0.4.0`.
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

## [2026-08-24] Escolher database e escolher perfil passam a gravar no mesmo lugar

**Contexto.** O caminho documentado para uma IA começar a operar um workspace —
`escolher-database <id>` e depois `criar` — não funcionava com perfil ativo.
Medido: `escolher-database` respondia sucesso, mas gravava em um `.env` **dentro
de `site-packages/`**; o perfil ativo continuava com `database_id` vazio e, como
o perfil vence o `.env` na resolução, o `criar` seguinte falhava com
"NOTION_DATABASE_ID não configurado". Dois comandos sobre a mesma configuração
escrevendo em arquivos diferentes — e o que o usuário lê (`perfis mostrar`) não
era o que o comando tinha gravado.

`cmd_escolher_database` agora resolve o perfil (o de `--perfil`, ou o ativo) e
grava nele, via `workspaces.definir_database`. Sem nenhum perfil, o `.env`
continua valendo — é o modo sem perfil, não um fallback silencioso. A resposta
passa a dizer **onde** gravou e **em qual perfil**.

### O 400 do Notion parou de ser engolido

Todo erro que não fosse 404 virava `"Falha ao falar com o Notion."`. O corpo do
400 — o único lugar que nomeia a propriedade recusada, ex.: *"Etapa is expected
to be select"* — era descartado. Quem lê a saída (pessoa ou modelo) ficava sem o
dado que resolveria o problema, e a reação natural era repetir a tentativa.

`_mensagem_erro_notion` mantém 404 curto (é diagnóstico de compartilhamento, não
de payload) e devolve `HTTP <status>: <message> [<code>]` para o resto,
com o corpo cru de reserva quando não é JSON.

`NotionSchemaError`, que a biblioteca passou a levantar antes de chamar a API,
é tratado como **erro de uso** (exit 2) e ganha o caminho de saída na mensagem:
`rode 'schema <database_id>' para ver as colunas reais`.

### Validação

182 testes verdes e `ruff` limpo. Contra o workspace real, com o código do
módulo: `listar --status "Entrada"` → 31 linhas (antes, 400 genérico);
`listar --area a1` numa base sem a coluna → mensagem nomeando
`Áreas da vida` em vez de traceback.

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

---

## [2026-08-28] O token deixa de confiar na ACL herdada no Windows

**Continuação da entrada de 24/08 e da validação de 27/08 acima.** O achado real
era: `_restringir` chamava `os.chmod(alvo, 0o600)` e engolia o `OSError` — mas
`os.chmod` **não aplica ACL no Windows**, então o store de perfis continuava com
a herança de `%APPDATA%\Roaming`. Medido nesta mesma máquina: o grupo
`CodexSandboxUsers` tinha `(RX)` herdado, ou seja, conseguia ler o token.

### O que mudou

`_restringir` passa a se ramificar por `os.name`:

- **POSIX**: continua `os.chmod`, sem regressão — mas a falha agora também vira
  aviso em stderr em vez de silêncio, pelo mesmo motivo do Windows abaixo.
- **Windows**: `_restringir_windows` chama `icacls /inheritance:r` e concede
  acesso só ao dono (via `%USERNAME%`), `SYSTEM` e Administradores — este
  último pelo SID bem-conhecido `*S-1-5-32-544`, não pelo nome (que muda com o
  idioma do Windows). Sem `pywin32`: `subprocess` + `icacls` evita adicionar
  dependência específica de plataforma a um projeto que hoje não tem nenhuma.

A falha deixou de ser um `except OSError: pass` mudo nos dois sistemas — é
exatamente o padrão que deixou o achado original passar despercebido até ser
medido em 27/08. Falha vira `print(..., file=sys.stderr)`, sempre.

### Validação

Sem máquina Windows disponível nesta sessão, então o comportamento do `icacls`
foi coberto por teste que mocka `subprocess.run` e força `os.name = "nt"` — a
mesma técnica que `decidir_pasta_configuracao` já usa para testar o ramo Windows
em máquina POSIX (ver comentário na função, entrada de 24/08). Três testes
novos: comando sem herança e com os três `/grant:r` corretos; falha do `icacls`
vira aviso em stderr; `USERNAME` ausente não chama `icacls` e avisa em vez de
arriscar um comando sem dono. 184 testes verdes (181 + 3), suíte completa.

**Não medido**: `icacls` de verdade numa máquina Windows real, confirmando com
`icacls <arquivo>` que o grupo de sandbox perdeu o acesso. Fica como o próximo
passo natural — mockar prova a chamada certa, não o efeito real na ACL do
sistema operacional. Task original permanece aberta até essa medição.

---

## [2026-08-31] A ACL do store foi confirmada no Windows real

**Continuação direta da entrada de 28/08.** A máquina Windows desta sessão
permitiu fechar a lacuna que mantinha a task de segurança aberta: medir o efeito
do `icacls`, e não apenas a montagem do comando em um mock.

### Medição real

Foi criado um arquivo sintético temporário dentro de `%APPDATA%\notion-tasks\`,
sem ler nem alterar o store de credenciais. A ACL foi capturada antes e depois
de chamar `_restringir`:

- **Antes:** `CodexSandboxUsers:(I)(RX)`, além de SYSTEM, Administradores e o
  usuário dono com herança `(I)`.
- **Depois:** somente Administradores, SYSTEM e o usuário dono, todos com
  `(F)` direto; `CodexSandboxUsers` e a herança desapareceram.

O arquivo temporário foi removido ao fim da medição. Portanto, o critério de
aceite desta task foi confirmado no Windows real: um novo arquivo do store não
mantém o acesso herdado do grupo de sandbox.

### Ajuste de portabilidade encontrado no gate

O primeiro `python -m pytest` encontrou uma falha no teste
`test_endereco_do_store_nao_depende_de_onde_o_pacote_esta_instalado`: o teste
usava `.split()` para ler caminhos impressos por um subprocesso, quebrando o
caminho Windows que contém espaços. O teste passou a ler as duas linhas com
`.splitlines()`, preservando o comportamento medido.

### Validação final e estado

`python -m pytest`: **188 passed, 2 skipped**. `ruff check .`: **All checks
passed**. A correção da ACL, o aviso visível em caso de falha e a validação
POSIX existente permanecem cobertos; esta task pode ser marcada como concluída.

## [2026-09-04] Fachada única e pacote instalável sem checkout

O pacote público candidato passou a se chamar tecnicamente `notion-automacoes`
na versão `0.3.0`. `cli/unificada.py` é uma borda fina: expõe `tasks`/`tarefas`,
`auth`/`perfis`, `doctor`, `app start`, `mcp start` e `update`/`atualizar`,
delegando a implementação existente de `notion-tasks`, perfis, launcher e MCP.
Os dois entry points (`notion-automacoes` e `notion-tasks`) convivem no mesmo
wheel, e `notion-starter` agora é resolvido por faixa versionada, sem
`Requires-Dist` apontando para Git.

Durante a validação foi corrigido um risco de instalação conjunta: o CLI não
insere mais o diretório `server/` do app no `sys.path`, pois isso fazia o pacote
legado `core` do app sombrear o `core` da CLI. O MCP é iniciado em processo
separado pela fachada para manter as duas árvores de importação isoladas.

**Validação:** `ruff check .` limpo, **198 testes verdes**, `twine check` aprovado
para wheel e sdist, `--version`/`--help`/`doctor`/`auth listar` exercitados em
ambiente limpo e o alias `notion-tasks` preservado. A publicação efetiva não foi
executada até confirmar nome, ownership, metadados legais e Trusted Publishing.

## [2026-09-04] Documentação e estado público atualizados

O README, `AGENTS.md`, `CONTRIBUTING.md` e `QUALIDADE.md` agora tratam
`notion-automacoes==0.3.0` como pacote público, mantendo `notion-tasks` como
alias de compatibilidade. O guia separa instalação distribuída de desenvolvimento,
documenta `doctor`/`auth` e aponta para as evidências de release. A titularidade
legal registrada no pacote é `Felipe Alcantara`; a publicação e o Trusted
Publishing deixam de ser descritos como pendência.
