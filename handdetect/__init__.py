from __future__ import annotations

from pathlib import Path
from pkgutil import extend_path
import sys

__path__ = extend_path(__path__, __name__)  # type: ignore[name-defined]

ROOT = Path(__file__).resolve().parent.parent
APP_PATH = ROOT / "apps" / "handdetect-cli" / "src" / "handdetect"
PACKAGE_SRC_ROOTS = sorted((ROOT / "packages").glob("*/src"))

for package_root in PACKAGE_SRC_ROOTS:
    package_root_str = str(package_root)
    if package_root_str not in sys.path:
        sys.path.insert(0, package_root_str)

app_path_str = str(APP_PATH)
if app_path_str not in __path__:
    __path__.append(app_path_str)
