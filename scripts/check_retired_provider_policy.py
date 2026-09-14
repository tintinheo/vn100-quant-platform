"""Reject retired SSI runtime imports and dependencies without banning policy text."""
from __future__ import annotations

import ast
from pathlib import Path
import re
import sys
import tomllib


ROOT = Path(__file__).resolve().parents[1]
ACTIVE_PYTHON = (Path("src/vnquant"), Path("src/app.py"))
REQUIREMENTS = (Path("src/requirements.txt"), Path("src/requirements-local.txt"))


def _is_ssi_name(value: str) -> bool:
    return any(part == "ssi" or part.startswith("ssi_") for part in re.split(r"[-_.]+", value.lower()))


def prohibited_runtime_imports(root: Path) -> list[str]:
    violations: list[str] = []
    paths: list[Path] = []
    for relative in ACTIVE_PYTHON:
        candidate = root / relative
        paths.extend(candidate.rglob("*.py") if candidate.is_dir() else [candidate])
    for path in paths:
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            names: list[str] = []
            if isinstance(node, ast.Import):
                names = [alias.name for alias in node.names]
            elif isinstance(node, ast.ImportFrom) and node.module:
                names = [node.module]
            elif (
                isinstance(node, ast.Call)
                and (
                    (isinstance(node.func, ast.Attribute) and node.func.attr == "import_module")
                    or (isinstance(node.func, ast.Name) and node.func.id == "__import__")
                )
                and node.args
                and isinstance(node.args[0], ast.Constant)
                and isinstance(node.args[0].value, str)
            ):
                names = [node.args[0].value]
            for name in names:
                if _is_ssi_name(name):
                    violations.append(f"{path.relative_to(root)}:{node.lineno}: {name}")
    return violations


def _requirement_name(requirement: str) -> str:
    return re.split(r"[<>=!~;\[\s@]", requirement.strip(), maxsplit=1)[0]


def prohibited_dependencies(root: Path) -> list[str]:
    declared: list[str] = []
    project = tomllib.loads((root / "pyproject.toml").read_text(encoding="utf-8"))["project"]
    declared.extend(project.get("dependencies", []))
    for group in project.get("optional-dependencies", {}).values():
        declared.extend(group)
    for relative in REQUIREMENTS:
        declared.extend(
            line.strip()
            for line in (root / relative).read_text(encoding="utf-8").splitlines()
            if line.strip() and not line.lstrip().startswith("#")
        )
    return [item for item in declared if _is_ssi_name(_requirement_name(item))]


def main(root: Path = ROOT) -> int:
    imports = prohibited_runtime_imports(root)
    dependencies = prohibited_dependencies(root)
    if imports or dependencies:
        for violation in imports:
            print(f"prohibited SSI runtime import: {violation}", file=sys.stderr)
        for violation in dependencies:
            print(f"prohibited SSI dependency: {violation}", file=sys.stderr)
        return 1
    print("PASS: SSI retirement policy permits documentation/tests but excludes runtime imports and dependencies")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
