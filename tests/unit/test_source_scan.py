"""Account ids live only in stack config and contracts (FR-A09; G3.1 E).

E: an account id in a Python constant fails this source scan. The scan
covers every Python file of the repository except `tests/` (fixtures) and
`specs/` (plan evidence), so new program, policy and script directories are
covered without a list to maintain.
"""

from __future__ import annotations

import ast
import re
from pathlib import Path

from stack_fixtures import ROOT, committed_documents, key

ACCOUNT_RUN = re.compile(r"(?<![0-9])[0-9]{12}(?![0-9])")
EXCLUDED_TOP_LEVEL = {"tests", "specs", ".git", ".venv", "node_modules"}


def scanned_files(root: Path = ROOT) -> list[Path]:
    return sorted(
        path
        for path in root.rglob("*.py")
        if path.relative_to(root).parts[0] not in EXCLUDED_TOP_LEVEL
        and "site-packages" not in path.parts
    )


def account_constants(path: Path) -> list[str]:
    """Return `file:line` for every constant holding a 12-digit run."""
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    hits = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Constant):
            continue
        value = node.value
        if isinstance(value, bool):
            continue
        if isinstance(value, (int, str, bytes)):
            text = value.decode("latin-1") if isinstance(value, bytes) else str(value)
            if ACCOUNT_RUN.search(text):
                hits.append(f"{path}:{node.lineno}")
    return hits


def test_scan_covers_the_program() -> None:
    files = {p.relative_to(ROOT).as_posix() for p in scanned_files()}
    assert "pulumi/__main__.py" in files
    assert "pulumi/app/config.py" in files


def test_no_account_id_in_python_constants() -> None:
    hits = [hit for path in scanned_files() for hit in account_constants(path)]
    assert hits == []


def test_scan_flags_an_account_constant(tmp_path: Path) -> None:
    account = committed_documents()["test"]["config"][key("awsAccountId")]
    module = tmp_path / "pulumi" / "app" / "leak.py"
    module.parent.mkdir(parents=True)
    module.write_text(
        f'ACCOUNT_ID = "{account}"\n'
        f"ACCOUNT_NUMBER = {int(account)}\n"
        f'ARN = f"arn:aws:iam::{account}:role/x"\n'
        "SAFE = 'eu-central-1'\n",
        encoding="utf-8",
    )
    assert scanned_files(tmp_path) == [module]
    assert account_constants(module) == [f"{module}:1", f"{module}:2", f"{module}:3"]


def test_scan_skips_tests_and_specs(tmp_path: Path) -> None:
    for top in ("tests", "specs"):
        path = tmp_path / top / "fixture.py"
        path.parent.mkdir()
        path.write_text("ACCOUNT = '000000000000'\n", encoding="utf-8")
    assert scanned_files(tmp_path) == []
