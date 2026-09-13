# Point-in-time VN100 universe

`current VN100` can be queried from SSI FastConnect v3 (`get_securities_info_by_index("VN100")`).
Historical backtests MUST NOT pretend current membership was valid in the past.

For strict backtests, add verified effective-dated snapshots as CSV files with:

`index_code,symbol,effective_from,effective_to,source_url,verified_at`

Use HOSE index review publications / official VN100 documents as the primary source.
If a strict historical snapshot is unavailable, run with `universe_mode=current_proxy` and label the result `NOT_TRUE_HISTORICAL_VN100`.
