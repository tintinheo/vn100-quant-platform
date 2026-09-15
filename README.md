# vn100-quant-platform

Project overview and setup notes.

## Active package boundary

The installable runtime is packaged only from `src/vnquant`. Content under
`legacy/` is historical and disabled; it is excluded from distributions,
dependencies, imports, and test discovery. Build and inspect a release artifact
with:

```bash
python -m pip wheel . --no-deps --no-build-isolation -w dist
python scripts/check_distribution.py dist/*.whl
```

## Documentation

Start with the [current baseline](docs/CURRENT_BASELINE.md), then read the
[canonical English BRD](docs/BRD-VN100-Quant-Platform.md), its
[Vietnamese companion](docs/BRD-VN100-Quant-Platform-VI.md), the
[canonical SRD](docs/SRD-VN100-Quant-Platform.md), and the
[provider research report](docs/PROVIDER-RESEARCH-REPORT.md). The complete
current document index is in [`docs/DOCUMENTS.md`](docs/DOCUMENTS.md).
Versioned copies and `LATEST` bundles are historical Git artifacts, not current
specifications.

## Multi-source data implementation

The unrecovered standalone name `vn100_multisource_feed_v1` is not an active
package. Its maintained, unversioned equivalent is included in this distribution:

- `vnquant.data.providers`: read-only DNSE, contract-gated Vietstock DataFeed,
  and explicit opt-in CafeF reference adapters;
- `vnquant.data.source_sync`: the incremental VN100 scanner/orchestrator;
- `vnquant.data.storage` and `vnquant.data.quality`: persistent cache/warehouse,
  immutable raw lineage, and data-quality gates;
- `vnquant.jobs.doctor`: the admission-gated read-only provider preflight.

The complete integrated offline suite is under `src/tests`. Offline results do
not establish provider admission, live connectivity, or real-data validation.
