# Arquitetura alvo — Alladin

Versão de arquitetura: 0.4, implementada no código. O padrão continua paper. Shadow e live existem; live recusa sem `live_arm`, allowlist e teto, e o signer não aceita segredo.

A Coinbase é a única fonte externa de mercado e de execução. O núcleo interno continua o mesmo: decisão causal, risco determinístico, execução paper, idempotência e auditoria. Pares listados saem da Advanced Trade. Swaps saem da Trade API em Ethereum, Base e Arbitrum.

## O que “todos os tokens” significa

O universo externo é o catálogo da Coinbase: produtos da Advanced Trade e tokens com rota de swap na Trade API. Isso não autoriza uma ordem para cada produto.

Um agente que recebe o catálogo inteiro alucina ferramentas e queima orçamento. O funil interno ainda classifica o que entra no livro.

O funil é obrigatório:

1. **Observado** — mint visto, somente leitura.
2. **Classificado** — programa, decimais, autoridades, extensões, metadados, holders.
3. **Elegível** — rota de compra e de venda, liquidez mínima, escudo de segurança, dados com horário de disponibilidade.
4. **Vigiado** — entra em livro de features e cotações.
5. **Negociável** — o risco pode autorizar intenção. Perpétuo só existe se o mercado publicar oracle, funding e conta de mercado verificados.

USDC é a moeda de caixa. SOL cotado na corretora é um produto Advanced Trade. Ethereum, Base e Arbitrum entram pela Trade API.

## Princípios

- O agente propõe. O risco dimensiona e pode vetar. A execução preenche. Nenhum papel acumula os três.
- Horário do evento e horário em que o dado ficou disponível são campos distintos. Decisão não usa dado futuro.
- Paper, sombra e ao vivo compartilham o mesmo contrato de ordem. O adaptador de venue muda; a contabilidade não.
- Seed, signer e `sendTransaction` nunca entram no contexto do modelo. Assinatura, quando existir, fica num processo separado com permissão limitada.
- Falha de dado, rota ou modelo produz abstenção registrada. Não há fallback silencioso para regra nem reenvio automático de ordem rejeitada.
- Uma sessão, um banco. Comandos serializados. Idempotência atômica com o evento de auditoria.
- Monólito Python com portas e adaptadores até o volume exigir processos separados. Não introduzir fila distribuída antes disso.
- O agente não altera configuração, não escolhe notional, não executa shell e não reescreve o próprio código.

## Estado vigente (0.4)

O processo implementa o funil (`universe`, `admit`, `watch`, `unwatch`), barras por ativo com `available_at`, carteira com várias posições spot, conselho, orçamento de chamadas persistido, modo `shadow` e signer isolado para `live`. A validação recusa feed com lookahead. Mercado e ordem externa passam só por `coinbase_products`, `coinbase_candles`, `coinbase_quote`, `coinbase_preview` e `coinbase_order`.

## Estado anterior (0.3)

Por barra fechada o servidor autentica, restaura estado, executa a proposta anterior na abertura seguinte, marca posições, calcula features causais, reúne o conselho e deixa o risco aceitar ou recusar. Modos `rules` e `llm`. `config.json` de sessão existente não muda.

Módulos atuais: `models`, `coinbase`, `transport`, `features`, `strategies`, `agents`, `risk`, `broker`, `engine`, `storage`, `server`, `client`, `research`, `validation`, `universe`, `signer`.

## Camadas alvo

```text
controle          API JSON, CLI, cliente de agentes, contrato de ferramentas
pesquisa          replay, validação cronológica, export, experimentos
conselho          papéis, memória de decisão, proposta estruturada
risco             admissão, gates, tamanho, circuit breaker
execução          OMS, paper, sombra, signer isolado, reconciliação
carteira          caixa, posições, custos, PnL
features          indicadores causais por instrumento e por prazo
universo          registro de mints, livros, relógio de barras e de eventos
dados             Advanced Trade e Trade API da Coinbase
```

Cada camada fala com a de baixo por esquema tipado. Estratégia e modelo não importam cliente HTTP de venue.

### Dados

Fontes, cada uma com adaptador estreito, timeout, teto de resposta e carimbo de disponibilidade:

| Fonte | Uso | Limite |
|---|---|---|
| Advanced Trade, produtos e candles | Catálogo e barras da corretora | Leitura pública. Não é fill. |
| Trade API, cotação de swap | Rota em Ethereum, Base e Arbitrum | Cotação não executa. |
| Advanced Trade, preview e ordem spot | Conferência e envio | Ordem só com `live_arm` e JWT externo. |

Não se fabrica volume de barra a partir de volume de 24 horas. Não se cola snapshot de hoje em barra antiga.

Dois relógios:

- **Pesquisa.** Barras fechadas, intervalo uniforme por instrumento, âncora UTC. Lacuna recusa entrada.
- **Tático.** Evento de pool, listagem ou queda de liquidez. Serve para admissão, halt e saída de proteção. Não reescreve a barra já decidida.

### Universo

O instrumento deixa de ser só SOL. Campos mínimos: identificador na rede ou `product_id` da corretora, decimais, quote (USDC), venue Coinbase, status do funil, motivo da última recusa, liquidez informada, rota de ida e de volta, horário observado.

Política inicial de admissão, todas obrigatórias para status negociável:

- Rota de compra e simulação de venda bem-sucedidas.
- Liquidez e participação máxima configuradas.
- Mint ou freeze authority ativos recusam, salvo lista explícita de exceções.
- Permanent delegate, non-transferable, pausable e default-frozen recusam.
- Transfer hook desconhecido recusa. Transfer fee só entra se a política nomear a taxa e o launchpad.
- Concentração e escrow de pool ficam explícitos: conta não é titular.
- wSOL não usa supply como concentração.

O livro ativo tem teto. O restante permanece observado. Promover e rebaixar é evento auditado.

### Conselho

Inspirado no grafo do TradingAgents e no exemplo LangGraph do Solana Agent Kit, com ferramentas já materializadas pelo backend. O modelo não escolhe URL.

Papéis, em paralelo quando não dependem uns dos outros:

1. Mercado — regime, tendência, volatilidade, prazo maior.
2. On-chain — autoridades, liquidez, holders, extensões, rota.
3. Fluxo — organic score, volume, desequilíbrio de compra e venda quando a fonte existir.
4. Contestação — custo, funding, dado faltante, tese contrária.
5. Gestor — LONG, SHORT, HOLD ou CLOSE, com referências a chaves de evidência.

O gestor escolhe candidato e pode ajustar stop, take e horizonte dentro do contrato. Não escolhe quantidade. Confiança continua score não calibrado.

Memória guarda decisões passadas e o resultado realizado depois do fill, no estilo do reflector do TradingAgents. Não guarda raciocínio interno do provedor. Orçamento de chamadas persiste no banco, por sessão, além do teto por processo.

Modo `rules` permanece como baseline reproduzível e como gerador de candidatos. Modo `llm` não substitui o risco.

### Risco

Todo comando de ordem passa pelo risco, no mesmo espírito do RiskEngine do NautilusTrader, em paper, sombra e ao vivo.

Gates: saldo, distância ao stop, custo, slippage hipotético, participação na liquidez, exposição bruta e líquida por mint e na carteira, correlação tratada como o mesmo fator quando os mints acompanham SOL, drawdown, perda diária UTC, cooldown, preço longe da referência, oracle inválido, dado incompleto, admissão revogada.

Spot não vende a descoberto. Short existe em perp com oracle, funding, mercado e margem. Funding adverso bloqueia perp. VaR/CVaR de uma barra continuam estatística descritiva, não previsão de cauda.

Circuit breaker não se rearma sozinho.

### Execução e carteira

OMS próprio, contabilidade em USDC:

- Intenção no fechamento ou no evento tático.
- Fill paper na abertura seguinte, com snapshot anterior. O snapshot novo não autoriza a entrada retroativamente.
- Stop prioritário sobre take na mesma barra. Gap adverso preenche na abertura. Trailing vale a partir da barra seguinte.
- Custos e slippage em bps explícitos. Taxa fixa por operação.
- Perp: margem isolada aproximada até existir adaptador do protocolo. Não apresentar isso como réplica de Drift.

Estados da ordem: criada, aceita, rejeitada, preenchida, parcial, cancelada, expirada. Estado desconhecido bloqueia nova entrada naquele mint até reconciliação.

Três adaptadores, mesma ordem:

| Modo | O que acontece |
|---|---|
| `paper` | Fill interno. Padrão. |
| `shadow` | Cotação e simulação ao vivo, fill continua interno. Mede desvio contra o paper. |
| `live` | Processo signer recebe intenção já autorizada, simula, assina e submete. O backend reconcilia por assinatura e saldo. |

O modo `live` só existe com flag, teto de notional, allowlist de mints, kill switch persistente e carteira que não entrega seed ao modelo. Inspiração: wallet plugável do Agent Kit v2 e permissão limitada, não a carteira embutida no prompt. Auto-modificação de código, como no agente que reescreve o próprio deploy, fica fora.

Halt bloqueia entradas na hora e fecha na próxima barra ou cotação válida. Finalize encerra a pesquisa ao último preço observado.

### Controle e pesquisa

A API atual permanece: saúde, status, contrato, auditoria, comandos com bearer e idempotência. Comandos novos entram no contrato versionado: `universe`, `admit`, `watch`, `unwatch`. Não há endpoint de shell, de config mutável nem de assinatura direta pelo modelo.

`validate` continua em blocos cronológicos, warmup, custos base e estressados, sem otimizar parâmetros no bloco de teste. Cohorts de universo entram na avaliação: token admitido só com dados disponíveis naquele instante. Avaliação LLM fora da amostra continua pendente até a fase 6.

Auditoria segue com cadeia SHA-256. O `head` fica retido fora do banco. Hash não é assinatura.

## Plano de execução

Cada fase termina com testes e com o modo anterior ainda operável. Não se ativa `live` para “completar” uma fase anterior.

### Fase 1 — Instrumento e funil

Objetivo: o modelo deixa de fixar o mint em SOL.

Entregas: `Instrument`, status do funil, registro persistido, `inspect` para SPL e Token-2022 com extensões decodificadas ou recusa explícita, comandos de leitura do universo.

Pronto quando: um mint desconhecido fica observado; um mint com extensão perigosa não fica negociável; SOL/USDC continua no caminho 0.3.

### Fase 2 — Dados multi-mint

Objetivo: feed e coleta por instrumento, com os dois relógios.

Entregas: produtos e candles da Advanced Trade; barra OHLCV fechada por instrumento; campos `observed_at` e `available_at`; recusa de lacuna e de revisão.

Pronto quando: replay de dois mints não vaza barra de um no outro e não aceita snapshot atrasado como se fosse contemporâneo.

### Fase 3 — Carteira e OMS paper

Objetivo: várias posições spot em USDC, mais perp só em mercado verificado.

Entregas: posição por instrumento, exposição agregada, custos, estados de ordem, risco por mint e na carteira, export por instrumento.

Pronto quando: duas posições abertas respeitam teto bruto e líquido; stop de uma não altera a outra; o replay SOL/USDC reproduz a contabilidade anterior dentro de tolerância definida em teste.

### Fase 4 — Admissão

Objetivo: ninguém opera mint sem rota de saída.

Entregas: política de autoridades e extensões; simulação de venda; liquidez e concentração; promoção e rebaixamento auditados; teto do livro vigiado.

Pronto quando: honeypot simulado, mint authority ativa e pool abaixo do mínimo ficam inegociáveis sem chamada ao modelo.

### Fase 5 — Conselho para o livro

Objetivo: agentes decidem dentro do livro vigiado, com evidência.

Entregas: papéis mercado, on-chain, fluxo, contestação e gestor; ferramentas escopadas; orçamento persistido; memória de resultado; modo `rules` como baseline no mesmo contrato.

Pronto quando: evidência inventada, orçamento esgotado e mint fora do livro produzem HOLD; o gestor não consegue emitir quantidade.

### Fase 6 — Pesquisa

Objetivo: medir o sistema sem olhar o futuro.

Entregas: walk-forward por cohort, estresse de custo, comparação `rules` contra `llm` em respostas controladas e, separadamente, em modelo real com teto de gasto; relatório de cobertura de dados.

Pronto quando: um teste de lookahead falha a build; o relatório separa dado sintético, fixture e ao vivo.

### Fase 7 — Sombra

Objetivo: cotações reais ao lado do fill paper.

Entregas: modo `shadow`, diferença entre preço paper e cotação, saúde dos adaptadores, alerta quando a fonte atrasa.

Pronto quando: falha da cotação Coinbase bloqueia entrada e não inventa preço.

### Fase 8 — Ao vivo, atrás de política

Objetivo: compra e venda reais só com signer isolado.

Entregas: adaptador de submissão, simulação obrigatória, reconciliação de assinatura e saldo, kill switch, teto de notional, allowlist, trilha de auditoria do modo.

Pronto quando: o modelo não possui caminho de código até a chave; ordem rejeitada ou não confirmada não é reenviada; halt fecha o que a política permitir fechar e bloqueia o resto.

## O que permanece de fora

Custódia dentro do prompt, JWT assinado dentro do processo, reset automático de circuit breaker, otimização de parâmetros no conjunto de teste, e agente que altera o próprio código. Optimism, Polygon, futuros e ações da Coinbase ainda não têm livro próprio.

Parâmetros de risco continuam hipóteses de pesquisa até a fase 6 mostrar resultado fora da amostra. Esta arquitetura não é autorização para capital real.

## Coinbase é a única fonte externa

O detalhe está em [Coinbase](coinbase.md). Ethereum, Base e Arbitrum entram pela Trade API. Pares da corretora entram pela Advanced Trade. O simulador paper continua local. Cotação e preview não enviam ordem. A ordem spot só sai com `live_arm` e um JWT ou uma sessão OAuth cujo token não volta ao chat.

Binance, OKX, CoinGecko, CoinMarketCap, DexScreener e GMGN entram só como visão: ranking, classificação, sinais, rastreador, alpha e copy trading observado. `coinbase_connect` devolve o `action_request` com o link Connect account. Cursor, ChatGPT, Claude e os modos Work/sandbox usam o mesmo contrato em `platforms`.

## Referências usadas neste plano

Detalhe e licenças em [seleção técnica](upstream-research.md). Núcleo: NautilusTrader (portas, risco na frente da ordem, OMS), Freqtrade e Hummingbot (estratégia separada de conector, degradação sob falha), TradingAgents (papéis e debate), Solana Agent Kit v2 (plugins e wallet sem seed no agente), Jupiter Tokens/Shield/Swap, leitura de Token-2022 e RugCheck, Helius como plano de dados e, só na fase 8, de envio.
