"""Tasseled-cap transform of a reflectance band stack — wraps ``pyramids_eo.spectral``.

Reads a reflectance raster into a pyramids ``Dataset``, applies the sensor's tasseled-cap
coefficients, and writes a raster whose bands are the requested components (brightness,
greenness, wetness, ...). The input bands must be in the sensor's reflectance domain and band
order; pyramids-eo validates this by band name when present, else by count.
"""

from __future__ import annotations

from qgis.core import (
    QgsProcessingException,
    QgsProcessingParameterEnum,
    QgsProcessingParameterRasterDestination,
    QgsProcessingParameterRasterLayer,
    QgsProcessingParameterString,
)

from ...dependencies import ensure_pyramids_eo
from ..base import PyramidsAlgorithm, layer_source_path, validate_input_path

#: Sensors with a bundled tasseled-cap coefficient table.
SENSOR = ["landsat8_oli", "landsat7_etm", "landsat5_tm"]


class TasseledCap(PyramidsAlgorithm):
    """Rotate a reflectance band stack into tasseled-cap components."""

    GROUP_LABEL = "Earth Observation"
    GROUP_ID = "eo"

    INPUT = "INPUT"
    SENSOR = "SENSOR"
    COMPONENTS = "COMPONENTS"
    OUTPUT = "OUTPUT"

    def name(self) -> str:
        """Return the stable algorithm id within the provider."""
        return "tasseled_cap"

    def displayName(self) -> str:  # noqa: N802
        """Return the human-readable algorithm name."""
        return "Tasseled cap transform"

    def shortHelpString(self) -> str:  # noqa: N802
        """Return the help shown in the algorithm dialog."""
        return (
            "Apply a sensor's tasseled-cap coefficients to a reflectance band stack, via "
            "pyramids-eo. The input must be the sensor's reflectance bands (TOA / reflectance "
            "factor, not raw DN) in the sensor's band order. Components are a comma-separated "
            "list in output-band order; the default is brightness,greenness,wetness."
        )

    def initAlgorithm(self, config=None) -> None:  # noqa: N802
        """Declare the algorithm's parameters."""
        self.addParameter(QgsProcessingParameterRasterLayer(self.INPUT, "Input reflectance raster"))
        self.addParameter(
            QgsProcessingParameterEnum(self.SENSOR, "Sensor", options=SENSOR, defaultValue=0)
        )
        self.addParameter(
            QgsProcessingParameterString(
                self.COMPONENTS,
                "Components (comma-separated)",
                defaultValue="brightness,greenness,wetness",
            )
        )
        self.addParameter(
            QgsProcessingParameterRasterDestination(self.OUTPUT, "Tasseled-cap raster")
        )

    def processAlgorithm(self, parameters, context, feedback):  # noqa: N802
        """Read the reflectance stack, apply the transform, and write the components."""
        self.check_pyramids(feedback)
        ensure_pyramids_eo()

        from pyramids.dataset import Dataset
        from pyramids_eo.spectral import tasseled_cap

        layer = self.parameterAsRasterLayer(parameters, self.INPUT, context)
        if layer is None:
            raise QgsProcessingException(self.invalidRasterError(parameters, self.INPUT))
        src = layer_source_path(layer)
        validate_input_path(src, feedback)
        out = self.parameterAsOutputLayer(parameters, self.OUTPUT, context)

        sensor = SENSOR[self.parameterAsEnum(parameters, self.SENSOR, context)]
        raw = self.parameterAsString(parameters, self.COMPONENTS, context)
        components = [part.strip() for part in raw.split(",") if part.strip()]
        if not components:
            raise QgsProcessingException("Give at least one tasseled-cap component.")

        feedback.pushInfo(f"tasseled_cap(sensor={sensor}, components={components}) on {src}")
        try:
            dataset = Dataset.read_file(src)
            result = tasseled_cap(dataset, sensor=sensor, components=components)
            result.to_file(out)
        except QgsProcessingException:
            raise
        except Exception as exc:  # noqa: BLE001  (report any library error cleanly)
            raise QgsProcessingException(f"tasseled cap failed: {exc}") from exc

        return {self.OUTPUT: out}
