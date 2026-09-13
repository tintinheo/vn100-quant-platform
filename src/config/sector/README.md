# Point-in-time sector membership

For a true historical sector-relative backtest, provide `sector_membership.csv` with:

```csv
symbol,sector,effective_from,effective_to,source
VCB,Banks,2025-01-01,,verified-source
```

If this file is absent, the pipeline may use current provider-supplied sector mapping and labels results `CURRENT_ICB_PROXY / NOT_TRUE_HISTORICAL_SECTOR_CLASSIFICATION`.
