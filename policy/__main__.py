"""CrossGuard entry point: the Pulumi engine runs this file (AD-A10).

The engine starts it with only the pack directory on `sys.path`, so the
repository root is added first and the pack imports as the `policy`
package, exactly as the tests import it.
"""

import importlib
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
importlib.import_module("policy.pack").serve()
