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
