"""Test configuration: a minimal ``qgis`` stub so the QGIS-free surface is fully testable.

``pyramids_qgis.dependencies`` imports ``QgsProcessingException`` from ``qgis.core`` inside its
``ensure_*`` guards. PyQGIS cannot be installed on a bare interpreter, so when the real module is
absent we register a tiny stand-in exposing just that one class. This lets the guard/raise paths be
exercised in CI-like environments without QGIS; when real PyQGIS is present it is used unchanged.

The stub intentionally provides only ``QgsProcessingException`` — the algorithm modules (which
import dozens of PyQGIS classes at load) are not imported by these tests and remain out of scope.
"""

from __future__ import annotations

import sys
import types

try:  # pragma: no cover - exercised only where real PyQGIS is installed
    import qgis.core  # noqa: F401
except Exception:  # noqa: BLE001 - any import failure means PyQGIS is unavailable
    _qgis = types.ModuleType("qgis")
    _core = types.ModuleType("qgis.core")

    class QgsProcessingException(Exception):  # noqa: N818 - must match QGIS's class name
        """Stand-in for QGIS's processing exception, used only in tests."""

    _core.QgsProcessingException = QgsProcessingException
    _qgis.core = _core
    sys.modules.setdefault("qgis", _qgis)
    sys.modules.setdefault("qgis.core", _core)
