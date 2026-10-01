"""The `Contract Schema` check (G3.3, AD-A11, AD-A3, FR-A16, FR-A25).

P: the committed tree (only the schema) passes, and a complete contract
passes. N: a contract file with an extra field fails, at every level, and
so does any other deviation from the closed schema. E: the schema itself is
checked (valid draft 2020-12, closed at every object level), unknown files
and symlinks fail, and duplicate keys or non-finite numbers fail.

The descriptor fields and patterns are USI's closed
`poc-api-gateway-backend/v1` (USI `scripts/poc_gateway_backend.py`
`project_gateway_backend`; `specs/poc-api-gateway-backend.md`). Fixture ids
use the AWS documentation account, never a VilnaCRM one.
"""

from __future__ import annotations

import copy
import hashlib
import json
import runpy
import shutil
from pathlib import Path

import pytest

import check_contracts as cc

ROOT = Path(__file__).resolve().parents[2]
CONTRACTS = ROOT / "contracts"
SCHEMA = json.loads(
    (CONTRACTS / "schema" / cc.BACKEND_SCHEMA).read_text(encoding="utf-8")
)
ACCOUNT = "123456789012"
LB = "app/user-service-alb/0123456789abcdef"
DESCRIPTOR = {
    "schema_version": "poc-api-gateway-backend/v1",
    "account_id": ACCOUNT,
    "region": "eu-central-1",
    "integration_type": "HTTP_PROXY",
    "connection_type": "VPC_LINK",
    "listener_arn": f"arn:aws:elasticloadbalancing:eu-central-1:{ACCOUNT}:"
    f"listener/{LB}/fedcba9876543210",
    "vpc_id": "vpc-0123456789abcdef0",
    "subnet_ids": ["subnet-0123456789abcdef0", "subnet-0123abcd"],
    "alb_security_group_id": "sg-0123456789abcdef0",
    "vpc_link_security_group_id": "sg-0fedcba987654321f",
    "tls_server_name": "user.vilnacrmtest.com",
    "certificate_arn": f"arn:aws:acm:eu-central-1:{ACCOUNT}:certificate/"
    "01234567-89ab-cdef-0123-456789abcdef",
    "request_parameters": {"overwrite:path": "$request.path"},
}
RUN = "https://github.com/VilnaCRM-Org/user-service-infrastructure/actions/runs/"
CONTRACT = {
    "schema_version": "agi-user-service-backend/v1",
    "descriptor": DESCRIPTOR,
    "source": {
        "usi_commit": "0123456789abcdef0123456789abcdef01234567",
        "usi_run_url": RUN + "123456789",
        "descriptor_sha256": hashlib.sha256(
            json.dumps(DESCRIPTOR, sort_keys=True).encode()
        ).hexdigest(),
        "usi_step20_run_url": RUN + "123456790/attempts/2",
    },
    "integration_target": f"arn:aws:elasticloadbalancing:eu-central-1:{ACCOUNT}:"
    f"loadbalancer/{LB}",
}


@pytest.fixture
def tree(tmp_path: Path) -> Path:
    """A copy of the committed contracts/ tree."""
    target = tmp_path / "contracts"
    shutil.copytree(CONTRACTS, target)
    return target


def add_contract(tree: Path, document: object, name: str = "test.json") -> Path:
    path = tree / "user-service-backend" / name
    path.parent.mkdir(exist_ok=True)
    text = document if isinstance(document, str) else json.dumps(document)
    path.write_text(text, encoding="utf-8")
    return path


# --- P ------------------------------------------------------------------------------


def test_p_committed_tree_with_only_the_schema_passes(
    capsys: pytest.CaptureFixture[str],
) -> None:
    files = sorted(p.relative_to(CONTRACTS) for p in CONTRACTS.rglob("*"))
    assert files == [Path("schema"), Path("schema") / cc.BACKEND_SCHEMA]
    assert cc.cli([str(CONTRACTS)]) == 0
    assert "OK (1 file(s)" in capsys.readouterr().out


@pytest.mark.parametrize("stack", ["ci", "test", "prod"])
def test_p_complete_contract_passes(stack: str, tree: Path) -> None:
    add_contract(tree, CONTRACT, f"{stack}.json")
    assert cc.check_tree(tree) == []


def test_p_step20_run_is_optional(tree: Path) -> None:
    """FR-A25 needs it in TEST; G5.1 enforces that with the stack."""
    document = copy.deepcopy(CONTRACT)
    del document["source"]["usi_step20_run_url"]
    add_contract(tree, document, "prod.json")
    assert cc.check_tree(tree) == []


# --- N: an extra field, at every level ---------------------------------------------


@pytest.mark.parametrize("level", [(), ("descriptor",), ("source",)])
def test_n_extra_field_fails(level: tuple[str, ...], tree: Path) -> None:
    document = copy.deepcopy(CONTRACT)
    node = document
    for key in level:
        node = node[key]
    node["extra"] = "x"
    add_contract(tree, document)
    (problem,) = cc.check_tree(tree)
    assert problem.startswith("user-service-backend/test.json: ")
    assert "Additional properties are not allowed ('extra' was unexpected)" in problem


def test_n_extra_field_fails_through_the_cli(
    tree: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    add_contract(tree, dict(CONTRACT, extra=1))
    assert cc.cli([str(tree)]) == 1
    assert "'extra' was unexpected" in capsys.readouterr().err


def mutate(path: tuple, value: object) -> dict:
    document = copy.deepcopy(CONTRACT)
    node = document
    for key in path[:-1]:
        node = node[key]
    if value is DELETE:
        del node[path[-1]]
    else:
        node[path[-1]] = value
    return document


DELETE = object()
BAD = [
    (("schema_version",), "agi-user-service-backend/v2"),
    (("integration_target",), DELETE),
    (("integration_target",), DESCRIPTOR["listener_arn"]),
    (("descriptor", "schema_version"), "poc-api-gateway-backend/v2"),
    (("descriptor", "account_id"), "12345678901"),
    (("descriptor", "region"), "EU"),
    (("descriptor", "integration_type"), "HTTP"),
    (("descriptor", "connection_type"), "INTERNET"),
    (("descriptor", "listener_arn"), "arn:aws:elasticloadbalancing:x"),
    (("descriptor", "vpc_id"), "vpc-xyz"),
    (("descriptor", "subnet_ids"), ["subnet-0123456789abcdef0"]),
    (("descriptor", "subnet_ids"), ["subnet-0123abcd", "subnet-0123abcd"]),
    (("descriptor", "subnet_ids"), ["subnet-0123abcd", "subnet-1", "subnet-2"]),
    (("descriptor", "alb_security_group_id"), "sg-"),
    (("descriptor", "vpc_link_security_group_id"), DELETE),
    (("descriptor", "tls_server_name"), "User.Example.COM"),
    (("descriptor", "tls_server_name"), "https://user.vilnacrmtest.com/"),
    (("descriptor", "certificate_arn"), "arn:aws:acm:eu-central-1:1:certificate/x"),
    (("descriptor", "request_parameters"), {"integration.request.path.proxy": "x"}),
    (("descriptor", "request_parameters"), {}),
    (("source", "usi_commit"), "abc"),
    (("source", "usi_run_url"), "https://github.com/someone/else/actions/runs/1"),
    (("source", "usi_step20_run_url"), RUN + "0"),
    (("source", "descriptor_sha256"), "0" * 63),
    (("source",), DELETE),
]


@pytest.mark.parametrize(("path", "value"), BAD, ids=[".".join(p) for p, _ in BAD])
def test_n_closed_schema_rejects(path: tuple, value: object, tree: Path) -> None:
    add_contract(tree, mutate(path, value))
    assert cc.check_tree(tree)


# --- E: tree and schema rules -----------------------------------------------------


@pytest.mark.parametrize(
    "relative",
    [
        "user-service-backend/dev.json",
        "user-service-backend/test.yaml",
        "user-service-backend/nested/test.json",
        "other/test.json",
        "README.md",
    ],
)
def test_e_unknown_files_fail(relative: str, tree: Path) -> None:
    path = tree / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(CONTRACT), encoding="utf-8")
    (problem,) = cc.check_tree(tree)
    assert problem == f"{relative}: not a contract path " + (
        "(user-service-backend/{ci,test,prod}.json)"
    )


def test_e_unknown_schema_file_fails(tree: Path) -> None:
    (tree / "schema" / "other.json").write_text("{}", encoding="utf-8")
    (tree / "schema" / "sub").mkdir()
    (tree / "schema" / "sub" / cc.BACKEND_SCHEMA).write_text("{}", encoding="utf-8")
    problems = cc.check_tree(tree)
    assert [p.split(":")[0] for p in problems] == [
        "schema/other.json",
        f"schema/sub/{cc.BACKEND_SCHEMA}",
    ]


def test_e_symlink_fails(tree: Path) -> None:
    target = add_contract(tree, CONTRACT)
    (tree / "user-service-backend" / "prod.json").symlink_to(target)
    assert cc.check_tree(tree) == [
        "user-service-backend/prod.json: symlinks are not allowed"
    ]


def test_e_missing_schema_fails(tmp_path: Path) -> None:
    assert cc.check_tree(tmp_path) == [f"schema/{cc.BACKEND_SCHEMA}: missing"]


@pytest.mark.parametrize(
    ("text", "needle"),
    [
        ('{"schema_version": "a", "schema_version": "b"}', "duplicate keys"),
        ('{"x": NaN}', "non-finite number NaN"),
        ("{", "Expecting property name"),
        (b"\xff\xfe", "codec"),
    ],
)
def test_e_strict_json(text: str | bytes, needle: str, tree: Path) -> None:
    path = tree / "user-service-backend" / "ci.json"
    path.parent.mkdir()
    if isinstance(text, bytes):
        path.write_bytes(text)
    else:
        path.write_text(text, encoding="utf-8")
    (problem,) = cc.check_tree(tree)
    assert needle in problem


def write_schema(tree: Path, schema: object) -> None:
    (tree / "schema" / cc.BACKEND_SCHEMA).write_text(
        json.dumps(schema), encoding="utf-8"
    )


def test_e_open_schema_fails_and_skips_contracts(tree: Path) -> None:
    schema = copy.deepcopy(SCHEMA)
    del schema["properties"]["source"]["additionalProperties"]
    write_schema(tree, schema)
    add_contract(tree, dict(CONTRACT, extra=1))
    assert cc.check_tree(tree) == [
        f"schema/{cc.BACKEND_SCHEMA}: open object schema at #/properties/source"
    ]


def test_e_invalid_schema_fails(tree: Path) -> None:
    write_schema(tree, {"type": 12})
    (problem,) = cc.check_tree(tree)
    assert "not a valid draft 2020-12 schema" in problem


def test_open_object_schemas_walks_lists() -> None:
    schema = {"anyOf": [{"type": "object"}, {"properties": {}}]}
    assert list(cc.open_object_schemas(schema)) == ["#/anyOf/0", "#/anyOf/1"]
    assert list(cc.open_object_schemas(SCHEMA)) == []


def test_committed_schema_is_closed_and_names_every_descriptor_field() -> None:
    assert cc.check_schema(CONTRACTS / "schema" / cc.BACKEND_SCHEMA) == []
    descriptor = SCHEMA["properties"]["descriptor"]
    assert sorted(descriptor["required"]) == sorted(DESCRIPTOR)
    assert sorted(descriptor["properties"]) == sorted(DESCRIPTOR)
    assert SCHEMA["properties"]["schema_version"] == {
        "const": "agi-user-service-backend/v1"
    }


def test_main_runs_the_cli(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("sys.argv", ["check_contracts.py", str(CONTRACTS)])
    with pytest.raises(SystemExit) as raised:
        runpy.run_path(cc.__file__, run_name="__main__")
    assert raised.value.code == 0
