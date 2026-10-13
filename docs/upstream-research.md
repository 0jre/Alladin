# Seleção técnica — Alladin

Pesquisa consultada em 13/10/2026. Seleção ampla, não inventário exaustivo nem ranking de rentabilidade. Repositórios públicos e documentação não demonstram lucro, segurança operacional ou qualidade de dados. Nenhum código upstream foi copiado ou dependência desses projetos instalada nesta versão.

## Referências prioritárias

| Projeto | Aplicação no Alladin | Decisão e limite |
|---|---|---|
| [TradingAgents](https://github.com/TauricResearch/TradingAgents) | Papéis especializados, debate, decisão estruturada | Prioritário como arquitetura; não fornece execução Solana completa. LICENSE Apache-2.0 consultada. |
| [Freqtrade](https://github.com/freqtrade/freqtrade) | Backtesting, análise de antecipação de dados, avaliação de estratégias | Referência de engenharia; conectores de exchanges não atendem ao requisito Solana exclusivo. LICENSE GPL-3.0 consultada. |
| [NautilusTrader](https://github.com/nautechsystems/nautilus_trader) | Eventos determinísticos, ciclo de ordens, contabilização | Avaliar como motor separado, não incorporar implicitamente. LICENSE LGPL-3.0 consultada. |
| [Solana Agent Kit](https://github.com/sendaifun/solana-agent-kit) | Catálogo de ferramentas e integrações on-chain | TypeScript; referência de contratos de ferramentas para o backend Python. LICENSE Apache-2.0 consultada. |
| [AgentiPy](https://github.com/niceberginc/agentipy) | Ferramentas Python para agentes Solana | Candidato a adaptador restrito; recursos de outras redes devem ser excluídos. LICENSE no caminho consultado retornou 404: licença pendente de verificação. |
| [Hummingbot](https://github.com/hummingbot/hummingbot) | Separação entre estratégias, conectores e execução | Avaliar conceitos e interfaces; não integrar seus conectores indiscriminadamente. |
| [Qlib](https://github.com/microsoft/qlib) | Pesquisa quantitativa e gerenciamento de experimentos | Candidato para processo de pesquisa isolado; não é fonte de dados Solana pronta. |
| [FinRL](https://github.com/AI4Finance-Foundation/FinRL) | Ambientes e experimentos de aprendizado por reforço | Pesquisa futura; não promover políticas treinadas sem validação fora da amostra. |
| [FinRobot](https://github.com/AI4Finance-Foundation/FinRobot) | Organização de análise financeira com agentes | Referência secundária; adaptar hipóteses de ações para dados on-chain exige trabalho próprio. |
| [AI Hedge Fund](https://github.com/virattt/ai-hedge-fund) | Composição de pareceres especializados | Referência de pesquisa, não sistema Solana operacional. |
| [DriftPy](https://github.com/velocity-exchange/driftpy) | Dados de mercados perp Solana | A API GitHub marcou `archived: true` nesta consulta. Não adicionado como dependência; verificar sucessor e compatibilidade do protocolo. |

Também examinados na busca ampla: [RD-Agent](https://github.com/microsoft/RD-Agent), [OctoBot](https://github.com/Drakkar-Software/OctoBot), [AI-Trader](https://github.com/HKUDS/AI-Trader), [Eliza](https://github.com/elizaOS/eliza), [NOFX](https://github.com/NoFxAiOS/nofx). São candidatos complementares, não componentes validados do Alladin.

## Critérios para integração

1. Fixar commit e registrar licença completa, avisos e dependências transitivas.
2. Verificar manutenção, testes, falhas conhecidas e comportamento sob perda de dados.
3. Expor adaptador estreito com timeouts, esquema tipado e limites de custo.
4. Proibir dados futuros na decisão e registrar origem, horário observado e horário disponível.
5. Validar comportamento por replay determinístico, custos adversos e dados fora da amostra.
6. Preservar Python, Solana exclusivo e API/CLI sem frontend.

## Implementado nesta versão

Conselho de agentes com saída estruturada; candidatos quantitativos de tendência, rompimento e reversão; risco determinístico; execução paper na barra seguinte; simulação de taxas, slippage, funding e liquidação aproximada; persistência e idempotência; coleta RPC e consultas Jupiter sem assinatura; avaliação cronológica com estresse de custos; cadeia de hashes na auditoria.

## Trabalho ainda necessário

Integrações upstream reais, dados históricos on-chain verificados, feeds perp, cobertura ampla de tokens, ingestão contínua resiliente, calibração dos scores, avaliação de drift, orçamento LLM persistente, comparação de modelos, teste de carga e observabilidade de produção. Não há garantia de informação completa da blockchain: RPC, indexadores e oráculos possuem escopos e atrasos distintos.

Não há integração de custódia Phantom, assinatura, transmissão de transações ou operação com capital real. Os resultados sintéticos verificam mecânica, não rentabilidade.
