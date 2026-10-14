# Feed e contrato temporal

O fluxo live coleta exclusivamente candles e snapshots SOL-USDC da Coinbase; não há RPC. A identificação Solana é metadado do ativo. `ingest` é reservado a replay/testes e conserva compatibilidade com dados históricos. O timestamp do candle marca sua abertura; o do snapshot marca quando a observação ficou disponível. Candles abertos, futuros ou fora de sequência são recusados.

```json
{
  "candle": {
    "timestamp": 1767225600,
    "open": 150.0,
    "high": 152.0,
    "low": 149.0,
    "close": 151.0,
    "volume": 100000.0,
    "chain": "solana",
    "mint": "So11111111111111111111111111111111111111112"
  },
  "snapshot": {
    "timestamp": 1767226500,
    "mint": "So11111111111111111111111111111111111111112",
    "chain": "solana",
    "price": 151.0,
    "liquidity_usd": 10000000.0,
    "volume_24h_usd": 50000000.0,
    "buy_sell_imbalance": 0.1,
    "product_id": "SOL-USDC",
    "source": "coinbase_advanced_sol_spot",
    "warnings": ["Exemplo sintético; não usar como sinal ou preço real."]
  }
}
```

No endpoint, coloque os dois objetos em `args` e envie `command=ingest`. Em um JSONL, use uma linha por objeto. `token_program` omitido usa o SPL clássico; `slot` é opcional. `candle.volume` representa volume da barra em USDC; `snapshot.volume_24h_usd` representa volume observado nas últimas 24 horas pelo indexador. `buy_sell_imbalance` varia de -1 a 1.

O feed manual é uma interface para testes e ingestão controlada. Os campos `account_checked` e `cluster_verified` só são confiáveis quando o backend autenticado controla o produtor; prefira `paper_tick` para usar as fontes implementadas.

Replay sintético testa causalidade e contabilidade do motor. Não representa mercado histórico e não mede rentabilidade.
