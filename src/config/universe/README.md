# Point-in-time VN100 universe

Current VN100 membership may be queried only through an explicitly selected provider after that provider passes Source Admission. No automated provider is currently admitted.
Historical backtests MUST NOT pretend current membership was valid in the past.

For strict backtests, add verified effective-dated snapshots as CSV files with:

`index_code,symbol,effective_from,effective_to,source_url,verified_at`

Use HOSE index review publications / official VN100 documents as the primary source.
If a strict historical snapshot is unavailable, run with `universe_mode=current_proxy` and label the result `NOT_TRUE_HISTORICAL_VN100`.
