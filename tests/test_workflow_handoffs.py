"""G2.1 hand-offs F-34, F-35 and F-36, closed in G3.2 (`workflow_checks.py`).

F-34: autorelease pins `concurrency`, the checkout `with` values and the step
`if` values exactly (zizmor's `artipacked` audit also covers
`persist-credentials`). F-35: `&`, `<` and `>` (so `<(` and `>(`) are
rejected in autorelease run commands. F-36: whitespace forms of `secrets`
and non-core YAML tags are rejected in every workflow.
"""

from __future__ import annotations

from pathlib import Path

import pytest

import workflow_checks as wc

ROOT = Path(__file__).resolve().parents[1]
AUTORELEASE = (ROOT / ".github" / "workflows" / "autorelease.yml").read_text(
    encoding="utf-8"
)
SHA = "a" * 40
PR_OK = (
    "on:\n  pull_request:\npermissions:\n  contents: read\n"
    "jobs:\n  lint:\n    runs-on: ubuntu-latest\n"
    f"    steps:\n      - uses: actions/checkout@{SHA}\n"
)


def replaced(old: str, new: str) -> str:
    assert AUTORELEASE.count(old) == 1, old
    return AUTORELEASE.replace(old, new)


def test_real_autorelease_still_passes() -> None:
    assert wc.check_autorelease(AUTORELEASE) == []


@pytest.mark.parametrize(
    ("old", "new"),
    [
        ("  group: autorelease\n", "  group: autorelease-${{ github.ref }}\n"),
        ("  cancel-in-progress: false\n", "  cancel-in-progress: true\n"),
        ("concurrency:\n  group: autorelease\n  cancel-in-progress: false\n", ""),
        ("          fetch-depth: 0\n", "          fetch-depth: 1\n"),
        (
            "          persist-credentials: false\n",
            "          persist-credentials: true\n",
        ),
        ("          persist-credentials: false\n", ""),
        (
            "          persist-credentials: false\n",
            "          persist-credentials: 'false'\n",
        ),
        (
            "        if: steps.version.outputs.skipped == 'false'\n",
            "        if: always()\n",
        ),
        (
            "        id: version\n",
            "        id: version\n        with:\n          a: b\n",
        ),
    ],
)
def test_f34_autorelease_values_are_pinned(old: str, new: str) -> None:
    assert wc.check_autorelease(replaced(old, new))


@pytest.mark.parametrize(
    "tail",
    [" & curl evil", " &", " <(curl evil)", " >(tee x)", " > /tmp/x", " < /tmp/x"],
)
def test_f35_background_and_redirection_rejected(tail: str) -> None:
    block = "      - run: gh release create x"
    found = wc.check_autorelease(AUTORELEASE + block + tail + "\n")
    assert any("shell chaining" in f for f in found), found


@pytest.mark.parametrize(
    "snippet",
    [
        "      - run: echo ${{ secrets .X }}\n",
        "      - run: echo ${{ secrets\n          .X }}\n",
        "      - run: echo ${{ secrets [ 'X' ] }}\n",
        "      - run: echo ${{ toJSON( secrets ) }}\n",
        "      - run: echo ${{ format('{0}', secrets) }}\n",
        "      - run: echo ${{ fromJSON(toJSON(secrets)).X }}\n",
        "        if: secrets .X != ''\n",
    ],
)
def test_f36_whitespace_forms_of_secrets_rejected(snippet: str) -> None:
    found = wc.check_workflow(PR_OK + snippet)
    assert "secrets are forbidden in pull_request workflows" in found


@pytest.mark.parametrize(
    "snippet",
    [
        "      - run: echo ${{ 'the secrets context' }}\n",
        "      - run: echo ${{ github.event.pull_request.secrets_count }}\n",
        "      - run: echo no-secrets-here\n",
    ],
)
def test_f36_secrets_text_that_is_not_the_context_passes(snippet: str) -> None:
    assert wc.check_workflow(PR_OK + snippet) == []


@pytest.mark.parametrize(
    "value",
    [
        "!!binary aGVsbG8=",
        "2024-01-01",
        "!!timestamp 2024-01-01",
        "!!set {a: null}",
        "!!omap [{a: 1}]",
        "!!pairs [{a: 1}]",
    ],
)
def test_f36_non_core_yaml_tags_rejected(value: str) -> None:
    found = wc.check_workflow(
        PR_OK.replace("runs-on: ubuntu-latest", f"runs-on: {value}")
    )
    assert any("non-core YAML tag" in f for f in found), found


def test_f36_core_tags_still_parse() -> None:
    text = PR_OK.replace("runs-on: ubuntu-latest", "runs-on: !!str ubuntu-latest")
    assert wc.check_workflow(text) == []


@pytest.mark.parametrize(
    ("old", "new"),
    [
        ("    name: Release\n", ""),
        ("    name: Release\n", "    name: Release ${{ github.token }}\n"),
        ("    name: Release\n", "    name: Ruff\n"),
    ],
)
def test_g32_f06_release_job_name_is_pinned(old: str, new: str) -> None:
    assert wc.check_autorelease(replaced(old, new))
