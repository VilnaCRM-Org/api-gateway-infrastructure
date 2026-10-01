"""The `prd.md` §1 counts are recomputed from the §3 and §4 tables (G3.2).

§1 says "A test in G3.2 recomputes these counts from the tables below". The
classification rules, all read from the tables:

- a FR is live-evidence-only when its bold title names a gate campaign
  (``(gate A-T)``, ``(gate A-P)``); every other FR is offline-testable;
- a NFR is offline-testable when its "How proved" column names an offline
  proof (a test, the policy pack, the simulator matrix, the Coverage check,
  zizmor, actionlint, pip-audit or a grep); otherwise it is evidence-only;
- an offline-testable FR also needs live evidence when its Risk column
  contains ``L``.

P: the committed PRD passes. N: a changed risk letter, count, row or list
fails. E: ranges (``FR-A01…FR-A21``) and the ``-A02`` shorthand expand.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

PRD = Path(__file__).resolve().parents[1] / "specs" / "gateway-wa-plan" / "prd.md"
GATE_TITLE = re.compile(r"\(gate A-\w+\)")
OFFLINE_PROOF = re.compile(
    r"\b(tests?|policy pack|simulator matrix|Coverage check|zizmor|actionlint"
    r"|pip-audit|grep)\b"
)
ID = re.compile(r"(N?FR)-A(\d{2})")
CATEGORIES = {
    "Offline-testable (": "offline",
    "Live-evidence-only FRs": "live_only_frs",
    "Evidence-only NFRs": "evidence_nfrs",
    "Offline-testable FRs that also need live evidence": "offline_live_frs",
}


def section(text: str, number: int) -> str:
    match = re.search(rf"^## {number}\. .*?(?=^## {number + 1}\. )", text, re.M | re.S)
    if not match:
        raise ValueError(f"section {number} not found")
    return match[0]


def rows(text: str, prefix: str) -> dict[str, list[str]]:
    found = {}
    for line in text.splitlines():
        if line.startswith(f"| {prefix}-A"):
            cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
            if cells[0] in found:
                raise ValueError(f"duplicate row {cells[0]}")
            found[cells[0]] = cells
    return found


def expand(listing: str) -> list[str]:
    """Expand `FR-A01…FR-A03, -A05 (n FRs); NFR-A01` into ids."""
    ids, prefix = [], None
    for token in re.split(r"[;,]", re.sub(r"\([^)]*\)", "", listing)):
        token = token.strip()
        if not token:
            continue
        if token.startswith("-A"):
            token = f"{prefix}{token}"
        bounds = [ID.fullmatch(part.strip()) for part in token.split("…")]
        if not all(bounds) or len(bounds) > 2:
            raise ValueError(f"cannot read requirement list item {token!r}")
        prefix = bounds[0][1]
        first, last = int(bounds[0][2]), int(bounds[-1][2])
        ids += [f"{prefix}-A{n:02d}" for n in range(first, last + 1)]
    return ids


def computed(text: str) -> dict[str, set[str]]:
    frs = rows(section(text, 3), "FR")
    nfrs = rows(section(text, 4), "NFR")
    live_only = {i for i, c in frs.items() if GATE_TITLE.search(c[1].split("**")[1])}
    evidence = {i for i, c in nfrs.items() if not OFFLINE_PROOF.search(c[3])}
    offline_frs = set(frs) - live_only
    return {
        "frs": set(frs),
        "nfrs": set(nfrs),
        "offline": offline_frs | (set(nfrs) - evidence),
        "live_only_frs": live_only,
        "evidence_nfrs": evidence,
        "offline_live_frs": {
            i for i in offline_frs if "L" in re.split(r"[,\s]+", frs[i][4])
        },
    }


def check_counts(text: str) -> list[str]:
    """Return every disagreement between §1 and the tables."""
    got = computed(text)
    summary = section(text, 1)
    problems = []
    totals = re.search(
        r"\*\*Counts\.\*\* (\d+) FRs and (\d+) NFRs, (\d+) requirements\.", summary
    )
    stated = tuple(int(n) for n in totals.groups()) if totals else None
    actual = (len(got["frs"]), len(got["nfrs"]), len(got["frs"]) + len(got["nfrs"]))
    if stated != actual:
        problems.append(f"Counts sentence {stated} != tables {actual}")
    seen = set()
    for line in summary.splitlines():
        cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
        label = next((k for k in CATEGORIES if cells[0].startswith(k)), None)
        if label is None or len(cells) != 3:
            continue
        key = CATEGORIES[label]
        seen.add(key)
        listed = expand(cells[2])
        for sub_count, kind in re.findall(r"\((\d+) (N?FR)s\)", cells[2]):
            in_kind = [i for i in listed if i.startswith(f"{kind}-")]
            if int(sub_count) != len(in_kind):
                problems.append(
                    f"{label}: '({sub_count} {kind}s)' lists {len(in_kind)}"
                )
        if int(cells[1]) != len(listed) or set(listed) != got[key]:
            problems.append(
                f"{label}: count {cells[1]}, listed {sorted(listed)}, "
                f"tables {sorted(got[key])}"
            )
    missing = set(CATEGORIES.values()) - seen
    if missing:
        problems.append(f"§1 table rows missing: {sorted(missing)}")
    return problems


TEXT = PRD.read_text(encoding="utf-8")


def test_committed_prd_counts_match_the_tables() -> None:
    assert check_counts(TEXT) == []


def test_committed_prd_has_the_expected_shape() -> None:
    got = computed(TEXT)
    assert len(got["frs"]) == 25
    assert len(got["nfrs"]) == 11
    assert got["live_only_frs"] == {"FR-A22", "FR-A23"}
    assert got["evidence_nfrs"] == {"NFR-A05", "NFR-A06", "NFR-A10"}


def mutate(old: str, new: str) -> str:
    assert TEXT.count(old) == 1, old
    return TEXT.replace(old, new)


@pytest.mark.parametrize(
    ("old", "new"),
    [
        # A risk letter changes the L count.
        ("| AGI | repo | — |\n\n### E-G3", "| AGI | repo | L |\n\n### E-G3"),
        # A stated count.
        ("| Evidence-only NFRs | 3 |", "| Evidence-only NFRs | 4 |"),
        # The totals sentence.
        ("25 FRs and 11 NFRs, 36", "25 FRs and 11 NFRs, 35"),
        # A sub-count.
        ("FR-A24, FR-A25 (23 FRs)", "FR-A24, FR-A25 (22 FRs)"),
        # A listed range.
        ("FR-A01…FR-A21, FR-A24", "FR-A01…FR-A20, FR-A24"),
        # An NFR loses its offline proof.
        ("| Quality | Coverage check |", "| Quality | review |"),
        # A FR becomes a gate campaign.
        ("**Repository controls.**", "**Repository controls (gate A-R).**"),
    ],
)
def test_a_changed_table_or_summary_fails(old: str, new: str) -> None:
    assert check_counts(mutate(old, new))


def test_a_removed_category_row_fails() -> None:
    text = mutate("| Evidence-only NFRs | 3 | NFR-A05, NFR-A06, NFR-A10 |\n", "")
    assert check_counts(text) == ["§1 table rows missing: ['evidence_nfrs']"]


def test_a_removed_counts_sentence_fails() -> None:
    text = mutate("**Counts.** 25 FRs", "**Totals.** 25 FRs")
    assert check_counts(text)[0].startswith("Counts sentence None")


def test_expand_reads_ranges_and_shorthand() -> None:
    assert expand("FR-A01…FR-A03, FR-A07 (4 FRs); NFR-A01, -A02") == [
        "FR-A01",
        "FR-A02",
        "FR-A03",
        "FR-A07",
        "NFR-A01",
        "NFR-A02",
    ]


@pytest.mark.parametrize("bad", ["XR-A01", "FR-A01…FR-A02…FR-A03", "FR-A1"])
def test_expand_rejects_unknown_items(bad: str) -> None:
    with pytest.raises(ValueError):
        expand(bad)


def test_missing_section_and_duplicate_row_fail() -> None:
    with pytest.raises(ValueError):
        section("## 1. x\n", 1)
    with pytest.raises(ValueError):
        rows("| FR-A01 | a |\n| FR-A01 | b |\n", "FR")
