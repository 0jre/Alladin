# Operação contínua do Alladin

## Escopo operacional

Backend Python 3.11+ e biblioteca padrão. O worker requer Linux/Unix (`fcntl`).
Configuração padrão: Solana, SOL-USDC spot paper, 250 USDC, candles de 15 minutos.
Dimensionamento padrão `available_balance`: usa o caixa disponível após reservar
o custo da compra; não aplica o antigo teto de 15% por posição. O risco máximo
estimado é 2% por entrada, limitado também pela perda diária restante de 2% e
pelo drawdown máximo de 6%. Stops, liquidez ou exposição que não comportem o
saldo inteiro bloqueiam a entrada; não há redução silenciosa para um lote menor.
Limites de perda usam estimativas do modelo; um gap pode ultrapassar o stop.
O padrão `external` aguarda agentes da sessão; `rules` é um baseline quantitativo explícito.
HOLD é uma decisão válida. O serviço não força entradas para produzir trades. O risco inclui custos variáveis e taxas fixas de ida e volta, relevantes numa conta pequena.

## Iniciar servidor e worker

Configure `LAB_API_TOKEN` no ambiente, com pelo menos 32 caracteres. Não há endpoint RPC ou configuração de blockchain.

```bash
python -m alladin --config config.json --db data/paper-250.sqlite serve --paper-worker --poll-seconds 30
```

O servidor permanece em `127.0.0.1:8080`. Um único worker pode usar cada banco;
a trava é liberada pelo sistema operacional quando o processo termina.
Mantenha o mesmo SQLite, configuração e modo de agentes ao reiniciar. Alterar
o saldo inicial de um banco existente é recusado; use outro arquivo para outra sessão.
Trocar `risk_budget` por `available_balance` também exige outra sessão. Se houver
continuidade de saldo, preserve custos, peak e orçamento diário consumido, e
registre uma transferência referenciando o head da auditoria anterior.
Não misture ingest/replay com paper-live na mesma sessão.

Para rodar só o worker ou um teste limitado:

```bash
python -m alladin --db data/paper-250.sqlite paper-live --poll-seconds 30
python -m alladin --db data/smoke.sqlite paper-live --cycles 2
```

`--cycles` conta chamadas concluídas, inclusive aquecimento e espera por candle.
Falhas temporárias continuam em retry até sucesso ou parada. SIGTERM/Ctrl-C
param a coleta; posições paper permanecem persistidas para o próximo início.
Não deixe o worker em um terminal temporário esperando continuidade 24/7.

## Saúde e monitoramento

| Rota | Significado |
|---|---|
| `GET /health` | Liveness: processo HTTP responde; não indica feed pronto |
| `GET /ready` | 200 se worker ativo, coleta recente, feed recente e sem halt/erro do conselho; 503 nos demais casos |
| `GET /v1/health` | Autenticado: worker, falhas, retry, última barra, modo e erro de decisão |
| `GET /v1/status` | Autenticado: saldo, equity, posições, diagnóstico da decisão e bloqueios |
| `GET /v1/audit/verify` | Autenticado: valida encadeamento de eventos |

Snapshots de livro exigem o produto esperado e horário da fonte com no máximo
30 segundos. Preço antigo não ganha
um timestamp novo depois de uma chamada lenta. Se o conselho demora e o preço
expira, uma nova entrada é bloqueada e o orçamento usado pelo conselho é persistido.

HTTP 429/503 externo causa retry limitado com jitter e `Retry-After`. Falha
persistente resulta em 503 no Alladin com `Retry-After` quando disponível.
O worker espera a partir da conclusão da tentativa; não recupera atrasos em rajadas.
O sistema não controla os limites do provedor externo.

## Gaps e retomada

Sem posição: o feed atual reaquece os indicadores e não cria fills históricos.
Com posição: um snapshot atual verificado fecha a posição paper ao preço atual,
registra `feed_gap_current_mark` e mantém o circuit breaker `feed_gap` acionado.
Não se presume que o stop foi respeitado durante o intervalo não observado.
A sessão fica bloqueada para novas entradas. Revise o evento e inicie outra
sessão depois da revisão; não há reset automático do circuit breaker.

Candles que começaram antes da abertura da posição não podem disparar stops
retroativos. Cotações atuais ainda podem disparar stops/targets ao preço observado.
Não há observação de cada tick entre polls; execução paper não replica DEX/MEV.
Volume em USDC é estimado por volume-base vezes fechamento em 24h de candles
completos; não é volume exato de cada negócio. O cache horário guarda estatística
de candles completos, nunca preço para preenchimento.

## Supervisão Linux

O modelo `deploy/alladin.service` assume checkout em `/opt/alladin`, usuário/grupo
`alladin`, arquivo de ambiente em `/etc/alladin/alladin.env` e estado em
`/var/lib/alladin`. Ele reinicia falhas de processo e preserva SQLite e auditoria.
Uma falha inesperada do worker encerra o servidor com código 1 para o supervisor
reiniciar. Falhas temporárias dos provedores mantêm o processo vivo e readiness 503.
Depois de instalar/configurar esses caminhos no host:

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now alladin
sudo journalctl -u alladin -f
```

O ambiente HTTP deve conter somente `LAB_API_TOKEN` para autenticar o acesso ao
backend. Nenhuma credencial de IA é necessária. MCP stdio dispensa esse token.
O worker padrão coleta dados, administra proteção das posições e aguarda decisões
externas. Para operar novas entradas, a sessão consumidora precisa chamar
`prepare_decision` e `submit_decision`; iniciar o worker não inicia inferência.
Veja [o protocolo externo](external-sessions.md). Bancos anteriores `rules` exigem
`--agents rules` antes de `serve`, sem reescrever seu histórico.

## Container

```bash
docker build -t alladin .
docker run --name alladin --restart unless-stopped --network host --env-file /etc/alladin/alladin.env -v alladin-data:/app/data alladin
```

O container inclui worker e healthcheck de readiness. O volume é obrigatório para
reter a sessão quando o container for recriado. `--network host` é para Linux.
O healthcheck indica degradação; Docker não reinicia automaticamente só porque
um container está unhealthy. Erros inesperados do worker encerram o processo.

## Integridade e backup

Faça backup SQLite consistente com a API `sqlite3.Connection.backup` ou com o
serviço parado; não copie apenas o arquivo principal durante escrita em WAL.
Retenha o `head` da auditoria fora do banco. A cadeia de hash detecta alteração
acidental; não é assinatura contra um administrador que reescreva todo o banco.

Os testes de fixtures exercitam entradas, saídas, custos, gaps e reinícios.
O teste de mercado ao vivo mede a integração e pode terminar em HOLD; nenhum
dos dois mede lucro futuro. A disponibilização 24/7 depende de instalar e manter
este serviço em um host persistente.

## Prazos de coleta e demonstração

Cada comando `paper_tick`, `prepare_decision` e `submit_decision` compartilha um
prazo monotônico de 45 segundos entre todas as chamadas HTTP, retries e espera
por capacidade. Cada requisição também tem seu prazo total, além do timeout do
socket. DNS ou leitura lenta não mantêm a chamada do backend bloqueada além do
orçamento: a resposta tardia é descartada e nunca aplica uma operação na carteira.

A biblioteca limita a quatro leituras HTTP concorrentes por processo. Uma leitura
que o sistema operacional ainda não encerrou ocupa uma dessas vagas até sair;
não são criadas threads ilimitadas. Se todas as vagas estiverem ocupadas, a coleta
falha dentro do prazo. Isso não promete disponibilidade de Coinbase.

Uma demonstração usa a mesma camada de orçamento, limitada também pelo tempo
restante da janela inteira:

```bash
python -m alladin --config config.json --db data/demo-nova.sqlite demo-live --seconds 60 --poll-seconds 5 --output results/demo-nova
```

O comando preserva saldo e histórico se o banco já existir; use um caminho novo
para uma conta demo independente. Não modifica o timeframe da configuração.
`report.json` inclui tempo solicitado, tempo de coleta observado, erros, saldo e
auditoria. A gravação final do relatório acontece depois da janela de coleta.
`decision-task.json` disponibiliza a tarefa à sessão consumidora; ela ainda deve
raciocinar e chamar `submit_decision`. A demonstração nunca fabrica pareceres ou
ordens para produzir um trade obrigatório.

O aquecimento continua sem fill. Logo após ele, `prepare_decision` pode coletar o
primeiro snapshot atual e analisar as barras fechadas já carregadas. Não exige
esperar outra barra nem misturar `ingest` e paper-live. `waiting_for_closed_bar`
é um estado normal, não erro de feed ou sinal de negociação.

## Diagnóstico antes de uma sessão

```bash
python -m alladin --config config.json doctor
```

O diagnóstico é somente leitura, retorna código de saída 0 quando suas condições
necessárias passam e 2 quando há bloqueio. Também está em `GET /v1/diagnostics`
(autenticado) e MCP `alladin_diagnostics`. Não grava feed, modifica saldo ou opera.
`checks` verifica somente a Coinbase; `sources_ready` não implica sinal
nem aprovação de risco. Cada grupo tem até 45 segundos, até 45 no diagnóstico todo.

Falhas expõem somente `code`, `stage` e `source` conhecidos. `proxy_tunnel`
identifica falha na conexão CONNECT ao proxy, antes do TLS e da resposta da API.
`dns_failure`, `connection`, `tls_handshake`, `response_headers` e `response_body`
ajudam a distinguir rede de dados inválidos. Nunca são exibidos URLs com segredo,
credenciais, cabeçalhos de autenticação ou corpos de erro do provedor.

A versão atual usa apenas a Coinbase. Em sessões anteriores havia também RPC,
removido por solicitação do usuário. Para coletar mercado, o ambiente precisa de
acesso HTTPS a api.coinbase.com. Remover RPC não libera automaticamente esse
acesso no proxy. Não contornar regras de rede nem fabricar snapshots.

`profile_feasibility` verifica uma condição necessária dos planos padrão em uma
conta inicialmente sem posições. O perfil demo atual mantém saldo integral, custos,
risco de 2% por operação/diário e drawdown de 6%, com retorno/risco líquido mínimo de
1,5. O mínimo anterior de 1,8 era incompatível com esses planos e custos. A revisão
reduz o retorno exigido; não altera o stop, os alvos, as taxas ou o orçamento de perda.
Isso torna alguns planos possíveis, sem garantir sinal, aprovação ou lucro.

O cliente HTTP público retorna agora o resultado do comando já desembrulhado,
como MCP e Service.command; a resposta HTTP bruta continua `{ "result": ... }`.
A integração controlada testa dados brutos de fonte → indicadores → contexto →
submissão externa → risco → OPEN/CLOSE → saldo/auditoria em HTTP e MCP. Essas
fixtures são sintéticas, usam perfil de pesquisa próprio e não validam desempenho
nem operações com mercado atual no perfil integral do usuário.

## Revisão explícita do critério de retorno

O perfil em config.json declara `min_reward_risk=1.5`. O default da classe Config
continua 1,8 para interpretar corretamente arquivos e fingerprints antigos.
A política não é migrada implicitamente ao iniciar uma sessão.

```bash
python -m alladin --config config-novo.json --db data/sessao.sqlite revise-policy --from-config config-anterior.json
```

Essa operação administrativa permite exclusivamente mudar `min_reward_risk`.
Exige a configuração anterior exata, sessão existente e mesmo modo; não cria uma
carteira nem altera limites de perda. Saldo, posições, custos, PnL, pico, perda
consumida no dia, cooldown e histórico são preservados. Cancela planos/tarefas
pendentes para exigir nova avaliação e registra hashes da carteira e das políticas
na cadeia de auditoria. Repetição da mesma revisão é idempotente. Não está exposta
como ferramenta de agentes HTTP/MCP nem aceita mudanças de risco/execução/ativos.

O transporte Coinbase tem orçamento de 20 segundos por requisição e 45 para a
coleta completa. O livro continua sendo obtido por último: aumentar a espera de
rede não aumenta a idade permitida da cotação, que permanece no máximo 30 segundos.
Uma janela demo de 60 segundos limita também cada comando ao tempo restante.

## Checagem operacional com cotações atuais

`execution_check` é uma ação explícita de validação de execução spot paper. Ela
não é uma estratégia, não inventa confluência e não é acionada automaticamente
quando uma estratégia decide HOLD. Exige `purpose=execution_validation`, um
`check_id` e ação OPEN ou CLOSE. OPEN também exige proposal com LONG, spot,
strategy execution_validation e horizonte máximo de quatro barras.

O backend aquece/atualiza dados reais Coinbase, exige cotação fresca e histórico
fechado atual, aplica o mesmo approve, custos, saldo integral e limites de perda.
Recusa abertura se já há posição/checagem ativa, replay, sessão rules, halt,
risco excessivo ou dados inválidos. CLOSE só alcança a posição identificada pela
checagem correspondente, nunca outra posição. Repita cada ação com a mesma chave
de idempotência após falha de conexão; consulte execution_check em status para
recuperar uma checagem aberta. Falha de fechamento mantém a posição registrada,
sem fabricar liquidação ou ocultar exposição.

Por HTTP/MCP, OPEN recebe:

```json
{
  "command": "execution_check",
  "args": {
    "action": "OPEN",
    "check_id": "identificador-unico-do-teste",
    "purpose": "execution_validation",
    "proposal": {
      "action": "LONG", "market": "spot", "confidence": 0.75,
      "stop_fraction": 0.013, "take_fraction": 0.0286, "horizon_bars": 1,
      "thesis": "Checagem operacional controlada; sem alegacao de sinal",
      "strategy": "execution_validation"
    }
  }
}
```

Os parâmetros são exemplo de teste, não recomendação ou sinal. Uma entrada pode
ser recusada integralmente pelo risco. CLOSE usa action CLOSE, o mesmo check_id e
purpose, sem proposal. Checagens não passam pelo consenso de alpha porque validam
somente execução; essa distinção é explícita na ferramenta e nos eventos.

Entradas são rotuladas controlled_execution_check e validation_only; registram
separadamente quote_source Coinbase. O dinheiro, custos, perdas e cooldown afetam
a carteira normalmente. performance separa execution_validation_roundtrips e seu
PnL das operações de estratégia; memory não usa checagens como evidência de edge.
Nenhuma negociação real ou chamada a carteira é implementada.

## Coleta e proteção entre candles

A preparação reaproveita observação Coinbase de até 15 segundos apenas quando o
contexto fechado ainda é válido, preservando o timestamp original. Submissão
externa continua buscando cotação nova e reaplicando o risco. Uma coleta que
atravessa fechamento de barra atualiza os candles e recusa dados expirados.
Reaquecimento de gap conserva o snapshot atual coletado para a preparação.

Com posição aberta, paper_tick coleta também o mark quando não surgiu candle
novo; stops, saídas por tempo e circuit breakers são processados nesse mark real.
Isso depende de o consumidor/worker continuar chamando paper_tick e de dados
válidos; não garante preço de stop nem disponibilidade contínua da fonte.

## External strategy proposals (prompt bundle 2.1.0)

`prepare_decision` delivers a task after valid feed/security checks even when the
quantitative candidate list is empty or its suggestions fail economics. Candidates
are advisory. The external session may HOLD or propose its own named spot strategy,
with observed feature/snapshot references, entry conditions, invalidation, stop,
target and horizon supported by those observations. Do not invent targets to pass
risk. The backend cannot establish whether a cited hypothesis has predictive edge.

`submit_decision` still requires four structured assessments, directional consensus,
no veto/contrary report, and final deterministic approval of the actual proposal.
Freshness, context hashes, idempotency, full-balance loss/exposure limits and costs
remain enforced. No task auto-submits itself; `demo-live` alone only collects and
exports tasks. The consuming session must inspect and submit them. A successful
software roundtrip does not establish profitability or mandate an entry.
