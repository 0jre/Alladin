# Alladin Finance Prompt Engineering

O repositório solicitado foi clonado de
https://github.com/devfinprojects/awesome-claude-finance-prompts no commit
`277112633031228587af3525557b088659a4df4f`. Os 17 arquivos originais estão em
`upstream/`, sem alterações e sem `.git` aninhado. `UPSTREAM.json` registra origem,
commit, árvore, tamanho e SHA-256 de cada arquivo. Não foi encontrada declaração
ou arquivo de licença; nenhuma licença foi presumida ou atribuída ao original.

## O que o Alladin executa

A biblioteca ativa, escrita para o Alladin, está em `alladin/finance_prompts/`.
O loader `alladin/prompts.py` valida seus hashes, versão, tamanho e caminhos.
Nenhum prompt do diretório `upstream/` é carregado como instrução de execução.

| Papel | Responsabilidade |
|---|---|
| Mercado | Regime, tendências, extremos, confluência e invalidação |
| Qualidade | Produto Coinbase, candles fechados, timestamps, livro, trades e dados ausentes |
| Fluxo | Livro Coinbase, amostra de trades, custos e limites de execução |
| Contestador | Pré-mortem, cenários adversos, contradições e custos estressados |
| Gestor | Plano com evidências, condições, saída e submissão ao risco determinístico |

Os três primeiros relatórios são independentes em relação às respostas entre si.
O contestador vê os três; o gestor vê a revisão completa. A execução continua
spot paper SOL-USDC, exclusivamente com dados Coinbase. O agente da sessão não
escolhe tamanho nem altera limites, e o backend pode recusar seu plano.

## Evidência em vez de conhecimento inventado

`alladin/finance.py` monta um envelope com indicadores fechados, snapshot,
carteira, candidatos, prévia de risco, custos de ida e volta e estresse 2x.
Cada observação citável recebe um identificador exato, origem e disponibilidade.
Campos nulos não se tornam evidências disponíveis. Notícias, macro, liquidez DEX,
MEV, rotas e probabilidades calibradas continuam ausentes quando não coletados.

Os prompts não treinam um modelo nem criam dados. Eles organizam a análise do
que foi fornecido. Papéis profissionais e textos extensos não demonstram edge.
Os módulos originais que pedem chain-of-thought integral foram adaptados para
conclusões breves, evidências e invalidação, sem solicitar raciocínio privado.

## Governança do plano

- Recusa econômica antes de preparar uma tarefa externa quando não há candidato viável.
- Referências inexistentes, plano sem stop, tamanho escolhido pelo agente,
  candidato inventado ou contrato inválido produzem abstenção.
- Uma entrada exige suporte de pelo menos dois dos três analistas, sem bloqueio
  nem posição SHORT/CLOSE contrária nos relatórios. Consenso não é prova estatística.
- O gestor pode ajustar stop/target/horizonte dentro do schema, mas o risco
  reavalia o resultado. Não se pode inventar alvo maior só para passar um gate.
- Veto de entrada não impede uma decisão CLOSE para uma posição existente.
- Bundle/version/hash, protocolo, sessão e hash do envelope são registrados na auditoria.
  Fills guardam o contexto de decisão para identificar a origem da decisão na avaliação.

## Interfaces backend

```bash
python -m alladin --config config.json --db data/minha-sessao.sqlite performance
```

Rotas autenticadas: `GET /v1/prompts`, `GET /v1/prompts/manager?regime=trend`,
`GET /v1/performance`. MCP expõe `prompts/list`, `prompts/get` e a ferramenta
`alladin_performance`. Os cinco papéis do catálogo são a allowlist; os agentes
não podem ler arquivos arbitrários por esses endpoints.

## Meta de 900 entradas

O relatório conta operações encerradas com PnL líquido, separa ganho/perda/zero,
mostra expectancy observada, pior perda, profit factor e intervalo Wilson de 95%.
A meta descritiva observa os últimos 900 roundtrips, sem excluir perdas; 0 ou
PnL negativo contam como não-acerto. O intervalo usa todos os roundtrips presentes
no histórico avaliado. Dependência serial limita a interpretação binomial.

898 ganhos e duas perdas grandes ainda podem produzir prejuízo. Até 900 ganhos
em 900 observações não demonstram, com limite inferior de 95%, que a probabilidade
real de ganho é pelo menos 898/900. Fixtures, trades controlados, dados de origem
não registrada e mistura de contextos/bundles não validam uma estratégia autônoma.
Nenhum relatório garante resultados futuros ou substitui teste cronológico fora
da amostra. O pipeline existente de folds e estresse continua disponível.

## Estado de implantação

`external` é o padrão. A biblioteca é entregue aos agentes da sessão via HTTP/MCP;
o backend não chama provedores, não configura modelos nem recebe credenciais de IA.
`rules` permanece como baseline explícito. Fixtures de submissões verificam os
contratos e não demonstram vantagem econômica. Atualizações do bundle exigem revisão,
atualização explícita dos hashes e reinício. Veja [o protocolo](../docs/external-sessions.md).

Bundle ativo 2.0.0, protocolo external-session-v2. Nenhum agente recebe ou afirma verificações on-chain. O papel quality substitui onchain.
