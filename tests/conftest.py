"""Import Flight Wall modules without loading Home Assistant."""

from __future__ import annotations

import sys
import types
from pathlib import Path

PKG_DIR = Path(__file__).resolve().parents[1] / "custom_components" / "flightwall"

if "flightwall" not in sys.modules:
    pkg = types.ModuleType("flightwall")
    pkg.__path__ = [str(PKG_DIR)]
    pkg.__package__ = "flightwall"
    pkg.__file__ = str(PKG_DIR / "__init__.py")
    sys.modules["flightwall"] = pkg
