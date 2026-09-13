from __future__ import annotations
import importlib.util

def local_dependency_report() -> dict[str,bool]:
    return {name: importlib.util.find_spec(name) is not None for name in ("pyarrow","duckdb","ssi_sdk")}

def assert_local_dependencies() -> None:
    report=local_dependency_report(); missing=[k for k,v in report.items() if not v]
    if missing:
        raise RuntimeError("Missing local dependencies: "+", ".join(missing)+". Run: pip install -r requirements-local.txt")
