"""Pulumi entry point of the API gateway program (AD-A15, FR-A09).

It loads the closed stack config (`app/config.py`) and then builds, in
order, the modules its feature flags enable: `features.certificate` (the
certificate module, G4.1) and `features.front_door` (every module after it,
G5.1 onwards). No module exists yet, so with both flags off the program
registers nothing, and a flag that is on fails closed instead of previewing
an empty program.
"""

from pathlib import Path

from app.config import ConfigError, load_stack

import pulumi

settings = load_stack(pulumi.get_stack(), Path(__file__).resolve().parent)

enabled = settings.enabled_features()
if enabled:
    raise ConfigError(
        f"Stack {settings.stack!r} enables {list(enabled)}, but this program has "
        "no module for them yet (certificate: G4.1; front_door: G5.1)."
    )
