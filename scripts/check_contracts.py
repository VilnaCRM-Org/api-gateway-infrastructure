"""The `Contract Schema` check (AD-A11, AD-A3, FR-A16; G3.3).

It validates `contracts/schema/` and every file under `contracts/`, and
passes when only the schema is present:

- `contracts/schema/` holds exactly the known schema files. Each is a valid
  JSON Schema (draft 2020-12) and closed: every object schema sets
  `additionalProperties: false`, so a contract with an extra field fails;
- every other file is a per-stack contract,
  `contracts/user-service-backend/{ci,test,prod}.json`, and validates
  against `agi-user-service-backend-v1.json`. Any other file, a symlink, a
  duplicate JSON key or a non-finite number fails.

The cross-field and live checks of FR-A16 (account and region equal the
stack's, the `integration_target` derivation, the certificate) belong to
the program's contract module (G5.1), not to this schema check.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections.abc import Callable, Iterator, Sequence
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator
from jsonschema.exceptions import SchemaError

ROOT = Path(__file__).resolve().parents[1]
SCHEMA_DIR = "schema"
BACKEND_SCHEMA = "agi-user-service-backend-v1.json"
SCHEMAS = frozenset({BACKEND_SCHEMA})
CONTRACT_DIRS = {"user-service-backend": BACKEND_SCHEMA}
STACKS = ("ci", "test", "prod")


class ContractError(ValueError):
    """A file under `contracts/` that cannot be read as strict JSON."""


def _no_duplicates(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    keys = [key for key, _ in pairs]
    duplicates = sorted({key for key in keys if keys.count(key) > 1})
    if duplicates:
        raise ContractError(f"duplicate keys {duplicates}")
    return dict(pairs)


def _no_constant(name: str) -> Any:
    raise ContractError(f"non-finite number {name}")


def load_json(path: Path) -> Any:
    """Parse one file as strict JSON (no duplicate key, no NaN/Infinity)."""
    try:
        return json.loads(
            path.read_text(encoding="utf-8"),
            object_pairs_hook=_no_duplicates,
            parse_constant=_no_constant,
        )
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise ContractError(str(error)) from None


def open_object_schemas(schema: Any, where: str = "#") -> Iterator[str]:
    """Yield the location of every object schema that is not closed."""
    if isinstance(schema, dict):
        is_object = schema.get("type") == "object" or "properties" in schema
        if is_object and schema.get("additionalProperties") is not False:
            yield where
        for key, value in schema.items():
            yield from open_object_schemas(value, f"{where}/{key}")
    elif isinstance(schema, list):
        for index, value in enumerate(schema):
            yield from open_object_schemas(value, f"{where}/{index}")


# JSON Schema searches a pattern, and `$` also matches before a final "\n",
# so every pattern must end with a negative lookahead (gate G33-F03).
PATTERN_END = r"(?!\n)$"
CONTROL_RE = re.compile(r"[\x00-\x1f\x7f]")


def loose_patterns(schema: Any, where: str = "#") -> Iterator[str]:
    """Yield the location of every pattern that is not fully anchored."""
    if isinstance(schema, dict):
        pattern = schema.get("pattern")
        if isinstance(pattern, str) and not (
            pattern.startswith("^") and pattern.endswith(PATTERN_END)
        ):
            yield f"{where}/pattern"
        for key, value in schema.items():
            yield from loose_patterns(value, f"{where}/{key}")
    elif isinstance(schema, list):
        for index, value in enumerate(schema):
            yield from loose_patterns(value, f"{where}/{index}")


def control_characters(document: Any, where: str = "$") -> Iterator[str]:
    """Yield the location of every key or string holding a control character."""
    if isinstance(document, dict):
        for key, value in document.items():
            if CONTROL_RE.search(key):
                yield f"{where} key {key!r}"
            yield from control_characters(value, f"{where}.{key}")
    elif isinstance(document, list):
        for index, value in enumerate(document):
            yield from control_characters(value, f"{where}[{index}]")
    elif isinstance(document, str) and CONTROL_RE.search(document):
        yield where


def check_schema(path: Path) -> list[str]:
    """Problems with one schema file."""
    schema = load_json(path)
    try:
        Draft202012Validator.check_schema(schema)
    except SchemaError as error:
        return [f"not a valid draft 2020-12 schema: {error.message}"]
    problems = [f"open object schema at {w}" for w in open_object_schemas(schema)]
    problems += [
        f"pattern not anchored with ^...{PATTERN_END} at {w}"
        for w in loose_patterns(schema)
    ]
    return problems


def check_contract(path: Path, schema: Any) -> list[str]:
    """Problems with one contract file."""
    document = load_json(path)
    validator = Draft202012Validator(schema)
    errors = sorted(validator.iter_errors(document), key=lambda e: e.json_path)
    problems = [f"{error.json_path}: {error.message}" for error in errors]
    return problems + [f"{w}: control character" for w in control_characters(document)]


def _contract_schema(relative: Path) -> str | None:
    if len(relative.parts) != 2 or relative.suffix != ".json":
        return None
    if relative.stem not in STACKS:
        return None
    return CONTRACT_DIRS.get(relative.parts[0])


def check_tree(contracts: Path) -> list[str]:
    """Every problem under `contracts`, as `relative/path: problem` lines.

    The schemas are checked first; contracts are validated only against
    schemas that passed.
    """
    schema_dir = contracts / SCHEMA_DIR
    if not (schema_dir / BACKEND_SCHEMA).is_file():
        return [f"{SCHEMA_DIR}/{BACKEND_SCHEMA}: missing"]
    files, problems = _collect(contracts)
    schema_files = [item for item in files if item[0].parts[0] == SCHEMA_DIR]
    for relative, path in schema_files:
        problems += _guarded(relative, lambda: _check_schema_file(relative, path))
    if problems:
        return problems
    schemas = {name: load_json(schema_dir / name) for name in SCHEMAS}
    for relative, path in files:
        if (relative, path) not in schema_files:
            problems += _guarded(
                relative, lambda: _check_contract_file(relative, path, schemas)
            )
    return problems


def _collect(contracts: Path) -> tuple[list[tuple[Path, Path]], list[str]]:
    """Every regular file under `contracts`, and a problem per symlink."""
    files: list[tuple[Path, Path]] = []
    problems: list[str] = []
    for path in sorted(contracts.rglob("*")):
        relative = path.relative_to(contracts)
        if path.is_symlink():
            problems.append(f"{relative}: symlinks are not allowed")
        elif path.is_file():
            files.append((relative, path))
    return files, problems


def _guarded(relative: Path, check: Callable[[], list[str]]) -> list[str]:
    try:
        return [f"{relative}: {problem}" for problem in check()]
    except ContractError as error:
        return [f"{relative}: {error}"]


def _check_schema_file(relative: Path, path: Path) -> list[str]:
    if len(relative.parts) != 2 or relative.name not in SCHEMAS:
        return [f"not a known schema ({sorted(SCHEMAS)})"]
    return check_schema(path)


def _check_contract_file(
    relative: Path, path: Path, schemas: dict[str, Any]
) -> list[str]:
    name = _contract_schema(relative)
    if name is None:
        return ["not a contract path (user-service-backend/{ci,test,prod}.json)"]
    return check_contract(path, schemas[name])


def cli(argv: Sequence[str] | None = None) -> int:
    """Check the contracts directory; print every problem; 1 on any."""
    parser = argparse.ArgumentParser(description="Contract Schema check (AD-A11).")
    parser.add_argument("contracts", nargs="?", type=Path, default=ROOT / "contracts")
    args = parser.parse_args(argv)
    problems = check_tree(args.contracts)
    for problem in problems:
        print(f"contract-schema: {problem}", file=sys.stderr)
    if problems:
        return 1
    files = sum(1 for path in args.contracts.rglob("*") if path.is_file())
    print(f"contract-schema: OK ({files} file(s) under {args.contracts})")
    return 0


if __name__ == "__main__":
    raise SystemExit(cli())
