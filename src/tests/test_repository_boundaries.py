from __future__ import annotations

import hashlib
import importlib.util
from pathlib import Path
import subprocess
import sys
import tomllib
import zipfile


ROOT = Path(__file__).resolve().parents[2]
LEGACY_ARCHIVE = ROOT / "legacy" / "vnquant_realdata_v3_1_gptcode_impl.zip"
RETIRED_TOKENS = ("ssi-sdk", "ssi_sdk", "legacy/")


def test_package_discovery_is_src_only_and_excludes_legacy():
    config = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    setuptools = config["tool"]["setuptools"]
    discovery = setuptools["packages"]["find"]

    assert setuptools["package-dir"] == {"": "src"}
    assert discovery["where"] == ["src"]
    assert discovery["include"] == ["vnquant", "vnquant.*"]
    assert {"legacy", "legacy.*"} <= set(discovery["exclude"])


def test_dependency_resolution_has_no_legacy_or_ssi_input():
    project = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))["project"]
    declared = [*project["dependencies"]]
    for group in project.get("optional-dependencies", {}).values():
        declared.extend(group)
    for requirements in (ROOT / "src" / "requirements.txt", ROOT / "src" / "requirements-local.txt"):
        declared.extend(
            line.strip() for line in requirements.read_text(encoding="utf-8").splitlines()
            if line.strip() and not line.lstrip().startswith("#")
        )

    normalized = "\n".join(declared).lower().replace("\\", "/")
    assert all(token not in normalized for token in RETIRED_TOKENS)
    assert "ssi" not in normalized
    assert not any(" @ " in item or item.startswith(("-e ", "--editable")) for item in declared)


def test_distribution_exclusion_rules_and_checker_are_present():
    manifest = (ROOT / "MANIFEST.in").read_text(encoding="utf-8")
    assert "prune legacy" in manifest
    assert "exclude *.zip" in manifest
    assert (ROOT / "scripts" / "check_distribution.py").is_file()


def test_pytest_discovery_is_pinned_to_active_tests():
    config = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))["tool"]["pytest"]["ini_options"]
    assert config["testpaths"] == ["src/tests"]
    assert "legacy" in config["norecursedirs"]
    assert not (ROOT / "src" / "pytest.ini").exists()


def test_legacy_checkout_import_fails_closed():
    result = subprocess.run(
        [sys.executable, "-c", "import legacy"],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    assert result.returncode != 0
    assert "historical and disabled" in result.stderr


def test_historical_ssi_paths_remain_archived_not_active():
    assert LEGACY_ARCHIVE.is_file()
    assert hashlib.sha256(LEGACY_ARCHIVE.read_bytes()).hexdigest() == (
        "4eff7a9c2b85610305c5aa0744798ab0803c03342187d03855bdbe57016de0a1"
    )
    report = (ROOT / "legacy" / "IMPLEMENTATION_REPORT_GPTCODE_STYLE.md").read_text(encoding="utf-8")
    assert "HISTORICAL ARTIFACT — DISABLED" in report
    with zipfile.ZipFile(LEGACY_ARCHIVE) as archive:
        names = set(archive.namelist())
    assert {
        "vnquant_realdata_v3_1/vnquant/data/ssi.py",
        "vnquant_realdata_v3_1/vnquant/jobs/doctor.py",
        "vnquant_realdata_v3_1/vnquant/jobs/bootstrap.py",
    } <= names
    assert not (ROOT / "src" / "vnquant" / "data" / "ssi.py").exists()
    assert importlib.util.find_spec("vnquant.data.ssi") is None
