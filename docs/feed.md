# Feed e contrato temporal

Este exemplo é fictício. Timestamp da candle é a abertura; timestamp do snapshot é quando os dados se tornaram disponíveis. Uma barra de 900 segundos com timestamp 1767225600 fecha em 1767226500.

```json
{
  "candle": {
    "timestamp": 1767225600,
    "open": 150.0,
    "high": 152.0,
    "low": 149.0,
    "close": 151.0,
    "volume": 100000.0,
    "funding_rate": 0.0,
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
    "mint_authority": null,
    "freeze_authority": null,
    "top10_account_share": null,
    "account_checked": true,
    "cluster_verified": true,
    "oracle_price": null,
    "oracle_timestamp": null,
    "expected_funding_hourly": null,
    "perp_market_verified": false,
    "source": "EXEMPLO_FICTICIO",
    "warnings": ["Sem oracle/funding: perp será bloqueado"]
  }
}
```

No endpoint, coloque o objeto acima dentro de `args` e envie `command=ingest`. Em um JSONL, use uma linha por objeto, sem indentação. `token_program` omitido usa o SPL clássico. `slot` é opcional. Candle.volume é volume **da barra** em USDC; snapshot.volume_24h_usd é volume das últimas 24 horas em USD, informado pelo indexador. Buy_sell_imbalance deve ficar entre -1 e 1.

Não substitua oracle_price por preço de DEX para liberar perp. Um adaptador deve obter oracle, market account e funding do protocolo escolhido, registrar origem/horários e verificar disponibilidade das informações no tempo da decisão. Snapshot com timestamp posterior ao fechamento é recusado. Se faltar uma barra, reconstitua o feed antes de continuar; não avance por cima da lacuna.

Configurações e statements de verificação provenientes do chamador autenticado são tratados como dados confiáveis pelo simulador. Esta interface não prova a origem dos dados; a implantação precisa controlar quem fornece o feed.
