"""Contrast-stretch a raster for display — wraps ``pyramids_eo.enhance.stretch``.

pyramids-eo has no CLI, so this calls the library directly: read the raster into a pyramids
``Dataset``, map its physical values onto a display range and dtype, and write the result.
"""

from __future__ import annotations

from qgis.core import (
    QgsProcessingException,
    QgsProcessingParameterEnum,
    QgsProcessingParameterNumber,
    QgsProcessingParameterRasterDestination,
    QgsProcessingParameterRasterLayer,
    QgsProcessingParameterString,
)

from ..dependencies import ensure_pyramids_eo
from .base import PyramidsAlgorithm, layer_source_path, validate_input_path

#: Stretch curves accepted by ``enhance.stretch(kind=...)``.
KIND = ["linear", "crude", "cira", "histogram"]


class EoStretch(PyramidsAlgorithm):
    """Map a raster's values onto a display range and dtype (contrast stretch)."""

    GROUP = "Earth Observation"
    GROUP_ID = "eo"

    INPUT = "INPUT"
    KIND = "KIND"
    GAMMA = "GAMMA"
    DTYPE = "DTYPE"
    OUTPUT = "OUTPUT"

    def name(self) -> str:
        """Return the stable algorithm id within the provider."""
        return "eo_stretch"

    def displayName(self) -> str:  # noqa: N802
        """Return the human-readable algorithm name."""
        return "Contrast stretch (EO)"

    def shortHelpString(self) -> str:  # noqa: N802
        """Return the help shown in the algorithm dialog."""
        return (
            "Stretch a raster for display, via pyramids-eo. 'linear' percentile-clips then "
            "rescales, 'crude' does a fixed min/max rescale, 'cira' is a logarithmic curve, and "
            "'histogram' equalises. Reflectance is expected in [0, 1]. An integer output dtype "
            "(e.g. uint8) scales onto [0, max]; a float dtype keeps [0, 1]. Optionally apply a "
            "gamma curve after the stretch."
        )

    def initAlgorithm(self, config=None) -> None:  # noqa: N802
        """Declare the algorithm's parameters."""
        self.addParameter(QgsProcessingParameterRasterLayer(self.INPUT, "Input raster"))
        self.addParameter(
            QgsProcessingParameterEnum(self.KIND, "Stretch curve", options=KIND, defaultValue=0)
        )
        self.addParameter(
            QgsProcessingParameterNumber(
                self.GAMMA,
                "Gamma (optional)",
                type=QgsProcessingParameterNumber.Double,
                optional=True,
                minValue=0.0,
            )
        )
        self.addParameter(
            QgsProcessingParameterString(self.DTYPE, "Output dtype", defaultValue="uint8")
        )
        self.addParameter(QgsProcessingParameterRasterDestination(self.OUTPUT, "Stretched raster"))

    def processAlgorithm(self, parameters, context, feedback):  # noqa: N802
        """Read the raster, stretch it, and write the result."""
        self.check_pyramids(feedback)
        ensure_pyramids_eo()

        from pyramids.dataset import Dataset
        from pyramids_eo.enhance import stretch

        layer = self.parameterAsRasterLayer(parameters, self.INPUT, context)
        if layer is None:
            raise QgsProcessingException(self.invalidRasterError(parameters, self.INPUT))
        src = layer_source_path(layer)
        validate_input_path(src, feedback)
        out = self.parameterAsOutputLayer(parameters, self.OUTPUT, context)

        kind = KIND[self.parameterAsEnum(parameters, self.KIND, context)]
        dtype = self.parameterAsString(parameters, self.DTYPE, context).strip() or "uint8"
        gamma = None
        if self.GAMMA in parameters and parameters[self.GAMMA] is not None:
            value = self.parameterAsDouble(parameters, self.GAMMA, context)
            if value > 0:
                gamma = value

        feedback.pushInfo(f"stretch(kind={kind}, gamma={gamma}, dtype={dtype}) on {src}")
        try:
            dataset = Dataset.read_file(src)
            result = stretch(dataset, kind=kind, gamma=gamma, dtype=dtype)
            result.to_file(out)
        except QgsProcessingException:
            raise
        except Exception as exc:  # noqa: BLE001  (report any library error cleanly)
            raise QgsProcessingException(f"EO stretch failed: {exc}") from exc

        return {self.OUTPUT: out}
