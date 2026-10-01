"""Fail-closed checks for GitHub workflow and composite-action files (G2.1).

Files are parsed with PyYAML ``safe_load`` (duplicate keys rejected). PyYAML
is a G3.1 dev dependency; when it is not importable every check raises, so
the tests fail instead of skipping. Anything the checks cannot interpret is
reported as a violation.
"""

import re
from pathlib import Path

try:
    import yaml
except ImportError:  # pragma: no cover - exercised only without PyYAML
    yaml = None

SHA_RE = re.compile(r"^[0-9a-f]{40}$")
SECRET_RES = (
    re.compile(r"\bsecrets\."),
    re.compile(r"\bsecrets\["),
    re.compile(r"toJSON\(\s*secrets\b", re.IGNORECASE),
    re.compile(r"\bsecrets:\s*inherit\b"),
)


def require_yaml():
    if yaml is None:
        raise RuntimeError("PyYAML is required (G3.1 dev dependency); failing closed")


def strip_comment(line):
    return re.sub(r"(?:^|\s)#.*$", "", line).rstrip()


def _loader():
    require_yaml()

    class Loader(yaml.SafeLoader):
        pass

    def construct(loader, node, deep=False):
        seen = set()
        for key_node, _ in node.value:
            key = loader.construct_object(key_node, deep=True)
            if key in seen:
                raise yaml.constructor.ConstructorError(
                    None, None, f"duplicate key {key!r}", key_node.start_mark
                )
            seen.add(key)
        return yaml.SafeLoader.construct_mapping(loader, node, deep)

    Loader.add_constructor(yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, construct)
    return Loader


def load(text, violations):
    try:
        doc = yaml.load(text, Loader=_loader())  # noqa: S506 - safe subclass
    except yaml.YAMLError as exc:
        violations.append(f"unparseable YAML: {exc}")
        return None
    if not isinstance(doc, dict):
        violations.append("top level must be a mapping")
        return None
    return doc


def get_events(doc, violations):
    """`on:` parses as True under YAML 1.1; a quoted key stays a string."""
    on = doc.get("on", doc.get(True))
    if isinstance(on, str):
        return {on}
    if isinstance(on, list) and all(isinstance(x, str) for x in on):
        return set(on)
    if isinstance(on, dict) and all(isinstance(k, str) for k in on):
        return set(on)
    violations.append("`on:` is missing or has an unsupported shape")
    return None


def _check_uses(where, ref, violations):
    if not isinstance(ref, str):
        violations.append(f"{where}: `uses` must be a string")
    elif ref.startswith("./"):
        return
    elif not SHA_RE.match(ref.rpartition("@")[2] if "@" in ref else ""):
        violations.append(f"{where}: `uses: {ref}` is not SHA-pinned")


def _check_steps(where, steps, violations):
    if steps is None:
        return
    if not isinstance(steps, list):
        violations.append(f"{where}: steps must be a list")
        return
    for i, step in enumerate(steps):
        if not isinstance(step, dict):
            violations.append(f"{where}: step {i} is not a mapping")
        elif "uses" in step:
            _check_uses(f"{where} step {i}", step["uses"], violations)


def _perms_ok(perms):
    return (
        isinstance(perms, dict)
        and perms.get("contents") == "read"
        and all(v == "read" for v in perms.values())
    )


def check_workflow(text):
    """Return a list of violation strings for one workflow file."""
    v = []
    doc = load(text, v)
    if doc is None:
        return v
    events = get_events(doc, v)
    jobs = doc.get("jobs")
    if not isinstance(jobs, dict) or not jobs:
        v.append("`jobs:` must be a non-empty mapping")
        jobs = {}
    for name, job in jobs.items():
        if not isinstance(job, dict):
            v.append(f"job {name}: must be a mapping")
            continue
        if "uses" in job:
            _check_uses(f"job {name}", job["uses"], v)
        _check_steps(f"job {name}", job.get("steps"), v)
    if events is None:
        return v
    if "pull_request_target" in events:
        v.append("pull_request_target is forbidden")
    if "pull_request" in events:
        top = doc.get("permissions")
        for name, job in jobs.items():
            if not isinstance(job, dict):
                continue
            perms = job["permissions"] if "permissions" in job else top
            if not _perms_ok(perms):
                v.append(f"job {name}: pull_request job must be contents: read only")
        for n, line in enumerate(text.splitlines(), 1):
            code = strip_comment(line)
            if any(rx.search(code) for rx in SECRET_RES):
                v.append(f"line {n}: secrets are forbidden in pull_request workflows")
    return v


def check_action(text):
    """Return violations for a composite action file."""
    v = []
    doc = load(text, v)
    if doc is None:
        return v
    runs = doc.get("runs")
    if not isinstance(runs, dict):
        v.append("composite action needs a `runs` mapping")
        return v
    _check_steps("runs", runs.get("steps"), v)
    return v


ALLOWED_RUN = re.compile(
    r"^(python3 scripts/next_release_version\.py|gh release create)(\s|$)"
)
FORBIDDEN_RUN = re.compile(
    r"\bgh\s+api\b|\bcurl\b|\bwget\b|\bgit\s+(push|commit|add|tag(?!\s+--list))\b"
)
SHELL_CHAINING = re.compile(r";|&&|\|\||\||`|\$\(")
CHECKOUT_RE = re.compile(r"^actions/checkout@[0-9a-f]{40}$")


def _commands(run):
    cmds, acc = [], ""
    for raw in str(run).splitlines():
        line = strip_comment(raw).strip()
        if not line:
            continue
        if line.endswith("\\"):
            acc += line[:-1] + " "
        else:
            cmds.append((acc + line).strip())
            acc = ""
    if acc.strip():
        cmds.append(acc.strip())
    return cmds


def check_autorelease(text):
    """Extra shape rules for autorelease.yml (PD-11)."""
    v = check_workflow(text)
    doc = load(text, [])
    if doc is None:
        return v
    on = doc.get("on", doc.get(True))
    if not (isinstance(on, dict) and set(on) == {"push"}):
        v.append("autorelease must trigger on push only")
    elif on["push"] != {"branches": ["main"]}:
        v.append(f"push filters must be exactly branches: [main], got {on['push']}")
    if doc.get("permissions") != {}:
        v.append("autorelease top-level permissions must be {}")
    if re.search(r"\bsecrets\b", "\n".join(strip_comment(x) for x in text.splitlines())):
        v.append("autorelease must not reference secrets (use github.token)")
    jobs = doc.get("jobs") if isinstance(doc.get("jobs"), dict) else {}
    ran = 0
    for name, job in jobs.items():
        if not isinstance(job, dict):
            continue
        if job.get("permissions") != {"contents": "write"}:
            v.append(f"job {name}: permissions must be exactly contents: write")
        if "uses" in job:
            v.append(f"job {name}: reusable workflows are not allowed")
        for step in job.get("steps") or []:
            if not isinstance(step, dict):
                continue
            if "uses" in step and not CHECKOUT_RE.match(str(step["uses"])):
                v.append(f"uses {step['uses']!r}: only actions/checkout@<sha> is allowed")
            if "run" in step:
                for cmd in _commands(step["run"]):
                    ran += 1
                    if SHELL_CHAINING.search(cmd):
                        v.append(f"shell chaining in run command: {cmd!r}")
                    if FORBIDDEN_RUN.search(cmd):
                        v.append(f"forbidden command in run step: {cmd!r}")
                    if not ALLOWED_RUN.match(cmd):
                        v.append(f"run command not on the allow list: {cmd!r}")
    if not ran:
        v.append("autorelease has no run commands to inspect")
    return v


# --- repository grep ---------------------------------------------------

FORBIDDEN_STRINGS = (
    "PERSONAL_ACCESS_TOKEN",
    "VILNACRM_APP_",
    "git-auto-commit-action",
    "pull_request_target",
    "TERRAFORM_PLAN_AWS_",
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
