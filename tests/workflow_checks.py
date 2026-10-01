"""Fail-closed checks for GitHub workflow and composite-action files.

G2.1 added the shape checks; G3.2 adds the PR quality battery checks
(``check_battery``) and the G2.1 hand-offs F-34 (pinned autorelease
``concurrency``, checkout ``with`` and ``if`` values), F-35 (``&``, ``<``
and ``>`` in autorelease run commands) and F-36 (whitespace forms of
``secrets`` and non-core YAML tags).

Files are parsed with a PyYAML ``SafeLoader`` subclass that rejects duplicate
keys, merge keys and non-core tags. PyYAML is a G3.1 dev dependency; when it
is not importable every check raises, so the tests fail instead of skipping.
Anything the checks cannot interpret is reported as a violation.
"""

import re
from pathlib import Path

try:
    import yaml
except ImportError:  # pragma: no cover - exercised only without PyYAML
    yaml = None

SHA_RE = re.compile(r"^[0-9a-f]{40}$")
SECRET_RES = (
    re.compile(r"\bsecrets\s*\."),
    re.compile(r"\bsecrets\s*\["),
    re.compile(r"toJSON\(\s*secrets\b", re.IGNORECASE),
    re.compile(r"\bsecrets\s*:\s*inherit\b"),
)
EXPRESSION_RE = re.compile(r"\$\{\{(.*?)\}\}", re.DOTALL)
QUOTED_RE = re.compile(r"'(?:[^']|'')*'")
SECRETS_CONTEXT_RE = re.compile(r"(?<![\w.-])secrets(?![\w-])")
# YAML 1.1 types that the GitHub (YAML 1.2 core schema) parser reads as
# strings or does not support. PyYAML would build other values from them.
NON_CORE_TAGS = ("binary", "timestamp", "omap", "pairs", "set")


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
            if key_node.tag == "tag:yaml.org,2002:merge":
                raise yaml.constructor.ConstructorError(
                    None, None, "merge keys (<<) are not allowed", key_node.start_mark
                )
            key = loader.construct_object(key_node, deep=True)
            if key in seen:
                raise yaml.constructor.ConstructorError(
                    None, None, f"duplicate key {key!r}", key_node.start_mark
                )
            seen.add(key)
        return yaml.SafeLoader.construct_mapping(loader, node, deep)

    def reject(loader, node):
        raise yaml.constructor.ConstructorError(
            None, None, f"non-core YAML tag {node.tag!r}", node.start_mark
        )

    Loader.add_constructor(yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, construct)
    for tag in NON_CORE_TAGS:
        Loader.add_constructor(f"tag:yaml.org,2002:{tag}", reject)
    return Loader


def load(text, violations):
    """Parse exactly one document; multi-document files are violations."""
    require_yaml()
    loader = _loader()(text)
    try:
        doc = loader.get_single_data()
    except yaml.YAMLError as exc:
        violations.append(f"unparseable YAML: {exc}")
        return None
    finally:
        loader.dispose()
    if not isinstance(doc, dict):
        violations.append("top level must be a mapping")
        return None
    return doc


def iter_strings(node):
    """Yield every string (keys and values) in a parsed document."""
    if isinstance(node, str):
        yield node
    elif isinstance(node, dict):
        for k, val in node.items():
            yield from iter_strings(k)
            yield from iter_strings(val)
    elif isinstance(node, list):
        for item in node:
            yield from iter_strings(item)


def iter_if_values(node):
    """Yield every ``if:`` value; GitHub reads them as expressions."""
    if isinstance(node, dict):
        for k, val in node.items():
            if k == "if" and isinstance(val, str):
                yield val
            yield from iter_if_values(val)
    elif isinstance(node, list):
        for item in node:
            yield from iter_if_values(item)


def has_secrets_key(node):
    if isinstance(node, dict):
        return "secrets" in node or any(has_secrets_key(v) for v in node.values())
    if isinstance(node, list):
        return any(has_secrets_key(i) for i in node)
    return False


def expression_uses_secrets(expression):
    """True when an expression names the ``secrets`` context in any form."""
    return bool(SECRETS_CONTEXT_RE.search(QUOTED_RE.sub("''", expression)))


def mentions_secrets(doc):
    """True when any string, expression, ``if:`` value or key uses secrets."""
    strings = list(iter_strings(doc))
    expressions = [e for s in strings for e in EXPRESSION_RE.findall(s)]
    expressions += list(iter_if_values(doc))
    return (
        has_secrets_key(doc)
        or any(rx.search(s) for s in strings for rx in SECRET_RES)
        or any(expression_uses_secrets(e) for e in expressions)
    )


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


def _jobs(doc, violations):
    jobs = doc.get("jobs")
    if not isinstance(jobs, dict) or not jobs:
        violations.append("`jobs:` must be a non-empty mapping")
        return {}
    for name, job in jobs.items():
        if not isinstance(job, dict):
            violations.append(f"job {name}: must be a mapping")
            continue
        if "uses" in job:
            _check_uses(f"job {name}", job["uses"], violations)
        _check_steps(f"job {name}", job.get("steps"), violations)
    return jobs


def _check_pull_request(doc, jobs, violations):
    top = doc.get("permissions")
    for name, job in jobs.items():
        if not isinstance(job, dict):
            continue
        perms = job["permissions"] if "permissions" in job else top
        if not _perms_ok(perms):
            violations.append(
                f"job {name}: pull_request job must be contents: read only"
            )
    if mentions_secrets(doc):
        violations.append("secrets are forbidden in pull_request workflows")


def check_workflow(text):
    """Return a list of violation strings for one workflow file."""
    v = []
    doc = load(text, v)
    if doc is None:
        return v
    events = get_events(doc, v)
    jobs = _jobs(doc, v)
    if events is None:
        return v
    if "pull_request_target" in events:
        v.append("pull_request_target is forbidden")
    if "pull_request" in events:
        _check_pull_request(doc, jobs, v)
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


def commands(run):
    """Split a ``run:`` script into commands, joining ``\\`` continuations."""
    cmds, acc = [], ""
    for raw in str(run).splitlines():
        line = raw.strip()
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


def _steps(job):
    steps = job.get("steps")
    if not isinstance(steps, list):
        return []
    return [step for step in steps if isinstance(step, dict)]


def _job_items(doc):
    jobs = doc.get("jobs")
    if not isinstance(jobs, dict):
        return []
    return [(name, job) for name, job in jobs.items() if isinstance(job, dict)]


# --- autorelease (PD-11) ---------------------------------------------------

ALLOWED_RUN = re.compile(
    r"^(python3 scripts/next_release_version\.py|gh release create)(\s|$)"
)
FORBIDDEN_RUN = re.compile(
    r"\bgh\s+api\b|\bcurl\b|\bwget\b|\bgit\s+(push|commit|add|tag(?!\s+--list))\b"
)
# F-35: `&` (background and `&&`), `<`/`>` (redirection and `<( >(`
# process substitution) join the G2.1 list.
SHELL_CHAINING = re.compile(r"[;&|`#<>]|\$\(")
TOP_KEYS = {"name", "on", True, "concurrency", "permissions", "jobs"}
JOB_KEYS = {"name", "runs-on", "timeout-minutes", "permissions", "steps"}
AUTORELEASE_JOB_NAME = "Release"
STEP_KEYS = {"name", "id", "uses", "with", "run", "if", "env"}
ENV_KEYS = {"GH_TOKEN", "TAG"}
GH_TOKEN = "${{ github.token }}"  # nosec B105  # expression text, not a token
CHECKOUT_RE = re.compile(r"^actions/checkout@[0-9a-f]{40}$")
# F-34: values pinned exactly, not only key names.
AUTORELEASE_CONCURRENCY = {"group": "autorelease", "cancel-in-progress": False}
AUTORELEASE_CHECKOUT_WITH = {"fetch-depth": 0, "persist-credentials": False}
AUTORELEASE_IFS = {"steps.version.outputs.skipped == 'false'"}


def _autorelease_top(doc, v):
    on = doc.get("on", doc.get(True))
    if not (isinstance(on, dict) and set(on) == {"push"}):
        v.append("autorelease must trigger on push only")
    elif on["push"] != {"branches": ["main"]}:
        v.append(f"push filters must be exactly branches: [main], got {on['push']}")
    if doc.get("permissions") != {}:
        v.append("autorelease top-level permissions must be {}")
    strings = iter_strings(doc)
    if any(re.search(r"\bsecrets\b", s) for s in strings) or has_secrets_key(doc):
        v.append("autorelease must not reference secrets (use github.token)")
    extra = set(doc) - TOP_KEYS
    if extra:
        v.append(f"top-level keys not allowed: {sorted(map(str, extra))}")
    if doc.get("concurrency") != AUTORELEASE_CONCURRENCY:
        v.append(f"concurrency must be exactly {AUTORELEASE_CONCURRENCY}")


def _autorelease_job(name, job, v):
    if job.get("permissions") != {"contents": "write"}:
        v.append(f"job {name}: permissions must be exactly contents: write")
    if "uses" in job:
        v.append(f"job {name}: reusable workflows are not allowed")
    bad = set(job) - JOB_KEYS
    if bad:
        v.append(f"job {name}: keys not allowed: {sorted(bad)}")
    if job.get("runs-on") != "ubuntu-latest":
        v.append(f"job {name}: runs-on must be ubuntu-latest")
    if job.get("name") != AUTORELEASE_JOB_NAME:
        v.append(f"job {name}: name must be {AUTORELEASE_JOB_NAME!r}")


def _autorelease_step_keys(step, v):
    bad = set(step) - STEP_KEYS
    if bad:
        v.append(f"step keys not allowed: {sorted(bad)}")
    env = step.get("env") or {}
    if not isinstance(env, dict) or set(env) - ENV_KEYS:
        v.append(f"step env keys must be within {sorted(ENV_KEYS)}")
    elif env.get("GH_TOKEN", GH_TOKEN) != GH_TOKEN:
        v.append("env.GH_TOKEN must be ${{ github.token }}")
    if "if" in step and step["if"] not in AUTORELEASE_IFS:
        v.append(f"step if must be one of {sorted(AUTORELEASE_IFS)}")


def _autorelease_step_token(step, v):
    for key, val in step.items():
        if key == "env" and isinstance(val, dict):
            val = {k: x for k, x in val.items() if k != "GH_TOKEN"}
        if any("github.token" in x for x in iter_strings(val)):
            v.append(f"github.token is only allowed as env.GH_TOKEN (step key {key})")


def _autorelease_step_uses(step, v):
    if "uses" not in step:
        if "with" in step:
            v.append("step with is only allowed on the checkout step")
        return
    if not CHECKOUT_RE.match(str(step["uses"])):
        v.append(f"uses {step['uses']!r}: only actions/checkout@<sha> is allowed")
    if step.get("with") != AUTORELEASE_CHECKOUT_WITH:
        v.append(f"checkout with must be exactly {AUTORELEASE_CHECKOUT_WITH}")


def _autorelease_run(step, v):
    ran = 0
    for cmd in commands(step.get("run", "")):
        ran += 1
        if SHELL_CHAINING.search(cmd):
            v.append(f"shell chaining in run command: {cmd!r}")
        if FORBIDDEN_RUN.search(cmd):
            v.append(f"forbidden command in run step: {cmd!r}")
        if not ALLOWED_RUN.match(cmd):
            v.append(f"run command not on the allow list: {cmd!r}")
    return ran


def check_autorelease(text):
    """Extra shape rules for autorelease.yml (PD-11)."""
    v = check_workflow(text)
    doc = load(text, [])
    if doc is None:
        return v
    _autorelease_top(doc, v)
    ran = 0
    for name, job in _job_items(doc):
        _autorelease_job(name, job, v)
        for step in _steps(job):
            _autorelease_step_keys(step, v)
            _autorelease_step_token(step, v)
            _autorelease_step_uses(step, v)
            ran += _autorelease_run(step, v)
    if not ran:
        v.append("autorelease has no run commands to inspect")
    return v


# --- PR quality battery (G3.2, AD-A11, FR-A08, FR-A10) ---------------------

BATTERY_EVENTS = {"push", "pull_request", "schedule"}
BATTERY_RUN = re.compile(
    r"^(make (build|test-[a-z-]+)|python3 scripts/codeql_sarif_gate\.py "
    r'"\$RUNNER_TEMP/codeql-results")$'
)
BATTERY_FORBIDDEN_JOB_KEYS = {
    "container",
    "environment",
    "permissions",
    "secrets",
    "services",
    "uses",
}
BATTERY_CHECKOUT_WITH_KEYS = {"persist-credentials", "fetch-depth"}


def _battery_top(doc, v):
    events = get_events(doc, []) or set()
    if "pull_request" not in events:
        v.append("battery workflows must run on pull_request")
    if events - BATTERY_EVENTS:
        v.append(f"battery events must be within {sorted(BATTERY_EVENTS)}")
    on = doc.get("on", doc.get(True))
    if isinstance(on, dict):
        if on.get("pull_request") is not None:
            v.append("pull_request must have no filters, so every PR runs it")
        if "push" in on and on["push"] != {"branches": ["main"]}:
            v.append("push filters must be exactly branches: [main]")
    if doc.get("permissions") != {"contents": "read"}:
        v.append("battery top-level permissions must be exactly contents: read")
    if "env" in doc:
        v.append("battery workflows must not set top-level env")
    if any("github.token" in s for s in iter_strings(doc)):
        v.append("battery workflows must not reference github.token")


def _battery_checkout(where, step, v):
    with_ = step.get("with")
    if not isinstance(with_, dict) or with_.get("persist-credentials") is not False:
        v.append(f"{where}: checkout needs persist-credentials: false")
        return
    if set(with_) - BATTERY_CHECKOUT_WITH_KEYS:
        v.append(f"{where}: checkout with keys not allowed: {sorted(with_)}")
    if with_.get("fetch-depth", 0) != 0:
        v.append(f"{where}: checkout fetch-depth may only be 0")


def _battery_step(where, step, v):
    uses = str(step.get("uses", ""))
    if uses.startswith("actions/checkout@"):
        _battery_checkout(where, step, v)
    if "env" in step:
        v.append(f"{where}: battery steps must not set env")
    run = step.get("run")
    if run is None:
        return
    if "${{" in str(run):
        v.append(f"{where}: run must not interpolate expressions")
    for cmd in commands(run):
        if not BATTERY_RUN.match(cmd):
            v.append(f"{where}: run command not on the battery allow list: {cmd!r}")


def check_battery(text):
    """Shape rules for the battery workflows (python-quality, security-scans,
    codeql): every job is unprivileged, secret-free and runs only make
    targets or the SARIF gate."""
    v = check_workflow(text)
    doc = load(text, [])
    if doc is None:
        return v
    _battery_top(doc, v)
    for name, job in _job_items(doc):
        bad = set(job) & BATTERY_FORBIDDEN_JOB_KEYS
        if bad:
            v.append(f"job {name}: keys not allowed in the battery: {sorted(bad)}")
        if job.get("runs-on") != "ubuntu-latest":
            v.append(f"job {name}: runs-on must be ubuntu-latest")
        if not isinstance(job.get("name"), str):
            v.append(f"job {name}: needs a check name")
        for i, step in enumerate(_steps(job)):
            _battery_step(f"job {name} step {i}", step, v)
    return v


def job_check_names(text):
    """Return the check names a workflow's jobs report, matrix-expanded."""
    doc = load(text, [])
    names = []
    for _, job in _job_items(doc or {}):
        matrix = (job.get("strategy") or {}).get("matrix") or {}
        if not isinstance(matrix, dict) or {"include", "exclude"} & set(matrix):
            raise ValueError("only plain list matrices can be expanded")
        expanded = [str(job.get("name"))]
        for axis, values in matrix.items():
            if not isinstance(values, list):
                raise ValueError(f"matrix axis {axis!r} is not a list")
            token = "${{ matrix." + axis + " }}"
            expanded = [n.replace(token, str(x)) for n in expanded for x in values]
        names.extend(expanded)
    return names


# --- repository grep -------------------------------------------------------

FORBIDDEN_STRINGS = (
    "PERSONAL_ACCESS_TOKEN",
    "VILNACRM_APP_",
    "git-auto-commit-action",
    "pull_request_target",
    "TERRAFORM_PLAN_AWS_",
)
GITHUB_DIR_FORBIDDEN = ("aws-secret-access-key", "AWS_SECRET_ACCESS_KEY")
SKIP_TOP = {".git", "specs", "tests"}
SKIP_ANY = {
    ".venv",
    "__pycache__",
    "node_modules",
    ".mypy_cache",
    ".pytest_cache",
    ".ruff_cache",
}


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
