# Research references and provenance

This is a reference inventory, not a ranking, dependency list, current license
assessment, or endorsement of profitability. Earlier architecture research
considered the projects below; they are not implicitly installed or incorporated.
Current product behavior is specified in [product.md](product.md).

| Reference | Relevant engineering theme | Alladin boundary |
|---|---|---|
| [TradingAgents](https://github.com/TauricResearch/TradingAgents) | Specialist assessments and structured debate | Reasoning remains in the consuming session |
| [Freqtrade](https://github.com/freqtrade/freqtrade) | Backtesting and causal strategy evaluation | No exchange execution connector is imported |
| [NautilusTrader](https://github.com/nautechsystems/nautilus_trader) | Events, risk, order/account state | Alladin uses its own standard-library paper core |
| [Hummingbot](https://github.com/hummingbot/hummingbot) | Strategy/connector separation and failure handling | No market-making gateway is enabled |
| [Qlib](https://github.com/microsoft/qlib) and [FinRL](https://github.com/AI4Finance-Foundation/FinRL) | Research experiments and evaluation | No training framework or learned policy is bundled |
| [FinRobot](https://github.com/AI4Finance-Foundation/FinRobot) and [AI Hedge Fund](https://github.com/virattt/ai-hedge-fund) | Financial-analysis organization | Not evidence of a complete profitable Solana trader |
| [Solana Agent Kit](https://github.com/sendaifun/solana-agent-kit) and [AgentiPy](https://github.com/niceberginc/agentipy) | Agent tool interfaces | No on-chain collection, wallet tools, or RPC are imported |

The only separately preserved finance-prompt source tree is documented under
[finance_prompt_engineering](../finance_prompt_engineering/README.md), with exact
commit and file hashes. Before any future integration, independently review the
specific commit, license, interfaces, tests, and mandate. Do not assume a URL,
architectural resemblance, or historical mention grants reuse rights or enables
a runtime feature.
