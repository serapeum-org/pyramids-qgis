"""Stretch a band between two percentiles — wraps ``pyramids raster percentile-stretch``."""

from __future__ import annotations

from qgis.core import (
    QgsProcessingException,
    QgsProcessingParameterNumber,
    QgsProcessingParameterRasterDestination,
    QgsProcessingParameterRasterLayer,
)

from ..base import PyramidsAlgorithm, layer_source_path, validate_input_path


class RasterPercentileStretch(PyramidsAlgorithm):
    """Rescale a band so its lower/upper percentiles map to 0 and 1."""

    INPUT = "INPUT"
    LOWER = "LOWER"
    UPPER = "UPPER"
    BAND = "BAND"
    OUTPUT = "OUTPUT"

    def name(self) -> str:
        """Return the stable algorithm id within the provider."""
        return "raster_percentile_stretch"

    def displayName(self) -> str:  # noqa: N802
        """Return the human-readable algorithm name."""
        return "Percentile stretch"

    def shortHelpString(self) -> str:  # noqa: N802
        """Return the help shown in the algorithm dialog."""
        return (
            "Linearly rescale a band so the lower percentile maps to 0 and the upper percentile "
            "maps to 1 (contrast stretch), via pyramids. Defaults: 2nd and 98th percentiles."
        )

    def initAlgorithm(self, config=None) -> None:  # noqa: N802
        """Declare the algorithm's parameters."""
        self.addParameter(QgsProcessingParameterRasterLayer(self.INPUT, "Input raster"))
        self.addParameter(
            QgsProcessingParameterNumber(
                self.LOWER,
                "Lower percentile (optional; default: 2)",
                type=QgsProcessingParameterNumber.Double,
                optional=True,
                minValue=0.0,
                maxValue=100.0,
            )
        )
        self.addParameter(
            QgsProcessingParameterNumber(
                self.UPPER,
                "Upper percentile (optional; default: 98)",
                type=QgsProcessingParameterNumber.Double,
                optional=True,
                minValue=0.0,
                maxValue=100.0,
            )
        )
        self.addParameter(
            QgsProcessingParameterNumber(
                self.BAND,
                "Band index (0-based)",
                type=QgsProcessingParameterNumber.Integer,
                optional=True,
                minValue=0,
                defaultValue=0,
            )
        )
        self.addParameter(QgsProcessingParameterRasterDestination(self.OUTPUT, "Stretched raster"))

    def processAlgorithm(self, parameters, context, feedback):  # noqa: N802
        """Build and run the ``pyramids raster percentile-stretch`` command."""
        layer = self.parameterAsRasterLayer(parameters, self.INPUT, context)
        if layer is None:
            raise QgsProcessingException(self.invalidRasterError(parameters, self.INPUT))
        src = layer_source_path(layer)
        validate_input_path(src, feedback)
        out = self.parameterAsOutputLayer(parameters, self.OUTPUT, context)

        argv = ["raster", "percentile-stretch", src, out, "--overwrite"]
        if self.LOWER in parameters and parameters[self.LOWER] is not None:
            argv += ["--lower", str(self.parameterAsDouble(parameters, self.LOWER, context))]
        if self.UPPER in parameters and parameters[self.UPPER] is not None:
            argv += ["--upper", str(self.parameterAsDouble(parameters, self.UPPER, context))]
        if self.BAND in parameters and parameters[self.BAND] is not None:
            argv += ["--band", str(self.parameterAsInt(parameters, self.BAND, context))]

        self.run_pyramids(argv, feedback)
        return {self.OUTPUT: out}
