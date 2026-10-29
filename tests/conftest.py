"""Test configuration: a ``qgis`` stub so the plugin is importable on a bare interpreter.

PyQGIS cannot be installed on a bare runner, but the plugin modules import ``qgis.core`` (and one
``qgis.PyQt.QtGui`` name) at load. When the real package is absent we register a stand-in exposing
every name the plugin imports — as inert placeholder classes — so ``pyramids_qgis.algorithms.base``,
``pyramids_qgis.provider`` and the algorithm modules import and their QGIS-free logic (the CLI
runner, the SystemExit handling, the capture lock, the CRS/path helpers, the provider's forced
output extension) can be exercised in tests. When real PyQGIS is present it is used unchanged.

The stubs are inert: they stand in only for *importability* and for the handful of class attributes
read at import. Behaviour that needs a real ``QgsProcessingContext`` / live QGIS (``initAlgorithm``,
``processAlgorithm``) is not exercised here.
"""

from __future__ import annotations

import sys
import types

_PARAMETER_CLASSES = (
    "QgsProcessingParameterBoolean",
    "QgsProcessingParameterCrs",
    "QgsProcessingParameterEnum",
    "QgsProcessingParameterExtent",
    "QgsProcessingParameterField",
    "QgsProcessingParameterFile",
    "QgsProcessingParameterFileDestination",
    "QgsProcessingParameterMultipleLayers",
    "QgsProcessingParameterNumber",
    "QgsProcessingParameterRasterDestination",
    "QgsProcessingParameterRasterLayer",
    "QgsProcessingParameterString",
    "QgsProcessingParameterVectorDestination",
    "QgsProcessingParameterVectorLayer",
)


def _install_qgis_stub() -> None:
    """Register inert ``qgis`` / ``qgis.PyQt`` stand-in modules in :data:`sys.modules`."""
    qgis = types.ModuleType("qgis")
    core = types.ModuleType("qgis.core")

    class QgsProcessingException(Exception):  # noqa: N818 - must match QGIS's class name
        """Stand-in for QGIS's processing exception."""

    class QgsProcessingAlgorithm:
        """Placeholder base so ``PyramidsAlgorithm`` can subclass and instantiate."""

    class QgsProcessingProvider:
        """Placeholder base so ``PyramidsProvider`` can subclass and instantiate."""

        def icon(self):
            """Return ``None`` as the default provider icon."""
            return None

    class QgsCoordinateReferenceSystem:
        """Placeholder; ``base.py`` uses it only in an annotation."""

    class QgsProcessing:
        """Placeholder carrying the layer-type enums the algorithms reference."""

        TypeRaster = 3
        TypeVectorAnyGeometry = -1

    class QgsApplication:
        """Placeholder so ``plugin.py`` imports; its registry is not exercised in tests."""

    core.QgsProcessingException = QgsProcessingException
    core.QgsProcessingAlgorithm = QgsProcessingAlgorithm
    core.QgsProcessingProvider = QgsProcessingProvider
    core.QgsCoordinateReferenceSystem = QgsCoordinateReferenceSystem
    core.QgsProcessing = QgsProcessing
    core.QgsApplication = QgsApplication
    for name in _PARAMETER_CLASSES:
        setattr(core, name, type(name, (), {}))
    # A couple of class-level enums the algorithm dialogs read at initAlgorithm time.
    core.QgsProcessingParameterNumber.Double = 1
    core.QgsProcessingParameterNumber.Integer = 0
    core.QgsProcessingParameterFile.File = 0
    qgis.core = core

    pyqt = types.ModuleType("qgis.PyQt")
    qtgui = types.ModuleType("qgis.PyQt.QtGui")

    class QIcon:
        """Inert QIcon stand-in accepting any constructor arguments."""

        def __init__(self, *args, **kwargs):
            """Ignore all arguments."""

    qtgui.QIcon = QIcon
    pyqt.QtGui = qtgui
    qgis.PyQt = pyqt

    sys.modules.setdefault("qgis", qgis)
    sys.modules.setdefault("qgis.core", core)
    sys.modules.setdefault("qgis.PyQt", pyqt)
    sys.modules.setdefault("qgis.PyQt.QtGui", qtgui)


try:  # pragma: no cover - exercised only where real PyQGIS is installed
    import qgis.core  # noqa: F401
except Exception:  # noqa: BLE001 - any import failure means PyQGIS is unavailable
    _install_qgis_stub()
