"""Fail unless a built vnquant distribution contains active-package files only."""
from __future__ import annotations

import argparse
from email.parser import Parser
from pathlib import Path, PurePosixPath
import tarfile
import zipfile


def members(path: Path) -> tuple[list[str], str]:
    if path.suffix == ".whl":
        with zipfile.ZipFile(path) as archive:
            names = archive.namelist()
            metadata_name = next(name for name in names if name.endswith(".dist-info/METADATA"))
            metadata = archive.read(metadata_name).decode("utf-8")
        return names, metadata
    with tarfile.open(path, "r:gz") as archive:
        names = archive.getnames()
        metadata_name = next(name for name in names if name.endswith("/PKG-INFO"))
        metadata_file = archive.extractfile(metadata_name)
        assert metadata_file is not None
        metadata = metadata_file.read().decode("utf-8")
    return names, metadata


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("artifact", type=Path)
    args = parser.parse_args()
    names, raw_metadata = members(args.artifact)
    normalized = [name.lower().replace("\\", "/") for name in names]
    forbidden = [name for name in normalized if "/legacy/" in f"/{name}" or "implementation_report_gptcode_style" in name or name.endswith(".zip")]
    if forbidden:
        raise SystemExit(f"forbidden historical files in distribution: {forbidden}")
    metadata = Parser().parsestr(raw_metadata)
    dependencies = "\n".join(metadata.get_all("Requires-Dist", []))
    if "ssi" in dependencies.lower() or "legacy" in dependencies.lower():
        raise SystemExit(f"retired dependency in distribution metadata: {dependencies}")
    if not any(PurePosixPath(name).parts[-2:] == ("vnquant", "__init__.py") for name in names):
        raise SystemExit("active vnquant package missing from distribution")
    print(f"PASS: {args.artifact} contains active vnquant only ({len(names)} files)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
