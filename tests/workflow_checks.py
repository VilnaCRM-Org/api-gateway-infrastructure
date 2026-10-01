"""Fail-closed, stdlib-only checks for GitHub workflow files (G2.1).

PyYAML is not in the standard library, so these checks scan lines. To stay
safe without a parser, every construct they cannot recognise is reported as
a violation instead of being skipped. Supported shape: plain block-style
YAML with two-space indentation, which is what this repository writes.
"""

import re
from pathlib import Path

SHA_RE = re.compile(r"^[0-9a-f]{40}$")
USES_RE = re.compile(r"""\buses:\s*["']?([^\s"',}\]]+)""")
JOB_RE = re.compile(r"^  ([A-Za-z_][A-Za-z0-9_-]*):\s*(?:#.*)?$")
EVENT_RE = re.compile(r"^  ([a-z_]+):\s*(?:#.*)?$")
SECRET_RES = (
    re.compile(r"\bsecrets\."),
    re.compile(r"\bsecrets\["),
    re.compile(r"toJSON\(\s*secrets\b", re.IGNORECASE),
    re.compile(r"\bsecrets:\s*inherit\b"),
)


def strip_comment(line):
    return re.sub(r"(?:^|\s)#.*$", "", line).rstrip()


def _indent(line):
    return len(line) - len(line.lstrip(" "))


def _code_lines(text):
    """Yield (number, raw line, comment-stripped line) for non-blank code."""
    for n, raw in enumerate(text.splitlines(), 1):
        code = strip_comment(raw)
        if code.strip():
            yield n, raw, code


def parse_triggers(text, violations):
    """Return the set of events, or None after recording a violation."""
    lines = list(_code_lines(text))
    for n, raw, code in lines:
        if re.match(r"""^["'](?:on|true)["']\s*:""", code):
            violations.append(f"line {n}: quoted `on` key is not supported")
            return None
    starts = [i for i, (_, _, c) in enumerate(lines) if re.match(r"^on:", c)]
    if len(starts) != 1:
        violations.append("exactly one top-level `on:` is required")
        return None
    i = starts[0]
    n, _, code = lines[i]
    rest = code[len("on:"):].strip()
    if rest:
        if re.fullmatch(r"[a-z_]+", rest):
            return {rest}
        violations.append(f"line {n}: `on:` form {rest!r} is not supported")
        return None
    events, first = set(), True
    for n, raw, code in lines[i + 1:]:
        if _indent(code) == 0:
            break
        if first and _indent(code) != 2:
            violations.append(f"line {n}: `on:` children must use 2 spaces")
            return None
        first = False
        if _indent(code) == 2:
            m = EVENT_RE.match(code)
            if not m:
                violations.append(f"line {n}: unrecognised `on:` entry")
                return None
            events.add(m.group(1))
        elif _indent(code) < 2:
            violations.append(f"line {n}: bad `on:` indentation")
            return None
    if not events:
        violations.append("`on:` has no events")
        return None
    return events


def parse_permissions(lines, violations, where):
    """Return dict, or None when absent. Scalars and bad shapes are marked."""
    for i, (n, raw, code) in enumerate(lines):
        m = re.match(r"^(\s*)permissions:\s*(.*)$", code)
        if not m:
            continue
        indent, rest = len(m.group(1)), m.group(2).strip()
        if rest:
            flow = re.fullmatch(r"\{(.*)\}", rest)
            if not flow:
                return {"*": rest}
            perms = {}
            for part in filter(None, (p.strip() for p in flow.group(1).split(","))):
                k, sep, v = part.partition(":")
                if not sep:
                    violations.append(f"{where}: bad permissions flow map")
                    return {"*": "?"}
                perms[k.strip()] = v.strip()
            return perms
        perms = {}
        for _, _, nxt in lines[i + 1:]:
            if _indent(nxt) <= indent:
                break
            pm = re.match(r"^\s+([a-z-]+):\s*(\S+)$", nxt)
            if not pm:
                violations.append(f"{where}: unrecognised permissions line")
                return {"*": "?"}
            perms[pm.group(1)] = pm.group(2)
        return perms
    return None


def parse_jobs(text, violations):
    """Return {job: [(n, raw, code), ...]}; unrecognised job lines fail."""
    jobs, cur, in_jobs, seen = {}, None, False, False
    for n, raw, code in _code_lines(text):
        if _indent(code) == 0:
            in_jobs = bool(re.match(r"^jobs:", code))
            if in_jobs:
                seen = True
                if not re.fullmatch(r"jobs:", code):
                    violations.append(f"line {n}: `jobs:` must be a block")
                    in_jobs = False
            continue
        if not in_jobs:
            continue
        if _indent(code) <= 2:
            m = JOB_RE.match(code)
            if not m:
                violations.append(f"line {n}: unrecognised job line {raw!r}")
                cur = None
                continue
            cur = m.group(1)
            jobs[cur] = []
        elif cur is not None:
            jobs[cur].append((n, raw, code))
    if not seen:
        violations.append("no `jobs:` block")
    return jobs


def check_uses(text, violations):
    for n, _, code in _code_lines(text):
        for ref_full in USES_RE.findall(code):
            if ref_full.startswith("./"):
                continue
            ref = ref_full.rpartition("@")[2] if "@" in ref_full else ""
            if not SHA_RE.match(ref):
                violations.append(f"line {n}: `uses: {ref_full}` is not SHA-pinned")


def check_workflow(text):
    """Return a list of violation strings for one workflow file."""
    v = []
    events = parse_triggers(text, v)
    jobs = parse_jobs(text, v)
    check_uses(text, v)
    if events is None:
        return v
    if "pull_request_target" in events:
        v.append("pull_request_target is forbidden")
    if "pull_request" in events:
        head = text.split("\njobs:")[0]
        top = parse_permissions(list(_code_lines(head)), v, "top level")
        for job, body in jobs.items():
            perms = parse_permissions(body, v, f"job {job}")
            if perms is None:
                perms = top
            if perms is None or perms.get("contents") != "read" or any(
                val != "read" for val in perms.values()
            ):
                v.append(f"job {job}: pull_request job must be contents: read only")
        for n, _, code in _code_lines(text):
            for rx in SECRET_RES:
                if rx.search(code):
                    v.append(f"line {n}: secrets are forbidden in pull_request workflows")
    return v


def check_action(text):
    """Return violations for a composite action file."""
    v = []
    check_uses(text, v)
    return v


def _push_branches(text):
    """Return normalised non-comment lines under `push:` in `on:`."""
    lines = [c for _, _, c in _code_lines(text)]
    out, i = [], 0
    while i < len(lines) and not re.match(r"^  push:\s*$", lines[i]):
        i += 1
    for line in lines[i + 1:]:
        if _indent(line) <= 2:
            break
        out.append(re.sub(r"[\"']", "", line.strip()))
    return out


ALLOWED_RUN = re.compile(
    r"^(python3 scripts/next_release_version\.py|gh release create)(\s|$)"
)
FORBIDDEN_RUN = re.compile(
    r"\bgh\s+api\b|\bcurl\b|\bwget\b|\bgit\s+(push|commit|add|tag(?!\s+--list))\b"
)


def _join_continuations(block):
    cmds, acc = [], ""
    for line in block:
        if line.endswith("\\"):
            acc += line[:-1] + " "
        else:
            cmds.append((acc + line).strip())
            acc = ""
    if acc.strip():
        cmds.append(acc.strip())
    return cmds


def _run_commands(text):
    lines = list(_code_lines(text))
    cmds = []
    for i, (n, _, code) in enumerate(lines):
        m = re.match(r"^\s*(?:-\s+)?run:\s*(.*)$", code)
        if not m:
            continue
        rest = m.group(1).strip()
        if rest in ("|", ">", "|-", ">-"):
            base, block = _indent(code), []
            for _, _, nxt in lines[i + 1:]:
                if _indent(nxt) <= base:
                    break
                block.append(nxt.strip())
            cmds.extend(_join_continuations(block))
        else:
            cmds.append(rest)
    return cmds


def check_autorelease(text):
    """Extra shape rules for autorelease.yml (PD-11)."""
    v = check_workflow(text)
    if parse_triggers(text, []) != {"push"}:
        v.append("autorelease must trigger on push only")
    branches = _push_branches(text)
    if branches not in (["branches:", "- main"], ["branches: [main]"]):
        v.append(f"push filters must be exactly branches: [main], got {branches}")
    for tok in re.findall(r"secrets\.([A-Za-z0-9_]+)", text):
        if tok != "GITHUB_TOKEN":
            v.append(f"secret {tok} is not allowed")
    cmds = _run_commands(text)
    if not cmds:
        v.append("autorelease has no run commands to inspect")
    for cmd in cmds:
        if FORBIDDEN_RUN.search(cmd):
            v.append(f"forbidden command in run step: {cmd!r}")
        if cmd and not ALLOWED_RUN.match(cmd):
            v.append(f"run command not on the allow list: {cmd!r}")
    jobs = parse_jobs(text, [])
    for job, body in jobs.items():
        if parse_permissions(body, [], job) != {"contents": "write"}:
            v.append(f"job {job}: permissions must be exactly contents: write")
    if parse_permissions(list(_code_lines(text.split("\njobs:")[0])), [], "top") != {}:
        v.append("autorelease top-level permissions must be {}")
    return v


# --- repository grep ---------------------------------------------------

FORBIDDEN_STRINGS = (
    "PERSONAL_ACCESS_TOKEN",
    "VILNACRM_APP_",
    "git-auto-commit-action",
    "pull_request_target",
)
GITHUB_DIR_FORBIDDEN = ("aws-secret-access-key", "AWS_SECRET_ACCESS_KEY")
SKIP_TOP = {".git", "specs", "tests"}
SKIP_ANY = {".venv", "__pycache__", "node_modules", ".mypy_cache",
            ".pytest_cache", ".ruff_cache"}


def iter_repo_files(root):
    root = Path(root)
    for path in sorted(root.rglob("*")):
        rel = path.relative_to(root)
        if rel.parts[0] in SKIP_TOP or SKIP_ANY & set(rel.parts):
            continue
        if path.is_file():
            yield path


def scan_repo(root):
    """Return 'relpath: string' hits across the whole tree."""
    hits = []
    for path in iter_repo_files(root):
        rel = path.relative_to(root)
        try:
            text = path.read_text()
        except UnicodeDecodeError:
            continue
        needles = FORBIDDEN_STRINGS
        if rel.parts[0] == ".github":
            needles = needles + GITHUB_DIR_FORBIDDEN
        hits.extend(f"{rel}: {s}" for s in needles if s in text)
    return hits
