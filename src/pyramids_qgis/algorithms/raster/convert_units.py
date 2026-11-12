"""Convert a raster's values to another unit — wraps ``pyramids raster convert-units``."""

from __future__ import annotations

from qgis.core import (
    QgsProcessingException,
    QgsProcessingParameterNumber,
    QgsProcessingParameterRasterDestination,
    QgsProcessingParameterRasterLayer,
    QgsProcessingParameterString,
)

from ..base import PyramidsAlgorithm, layer_source_path, validate_input_path


class RasterConvertUnits(PyramidsAlgorithm):
    """Convert a raster's physical values to a target unit."""

    INPUT = "INPUT"
    TARGET = "TARGET"
    BAND = "BAND"
    OUTPUT = "OUTPUT"

    def name(self) -> str:
        """Return the stable algorithm id within the provider."""
        return "raster_convert_units"

    def displayName(self) -> str:  # noqa: N802
        """Return the human-readable algorithm name."""
        return "Convert units"

    def shortHelpString(self) -> str:  # noqa: N802
        """Return the help shown in the algorithm dialog."""
        return (
            "Convert a raster's physical values to a target unit (e.g. celsius, hPa, knots), "
            "via pyramids. Optionally restrict the conversion to a single band."
        )

    def initAlgorithm(self, config=None) -> None:  # noqa: N802
        """Declare the algorithm's parameters."""
        self.addParameter(QgsProcessingParameterRasterLayer(self.INPUT, "Input raster"))
        self.addParameter(
            QgsProcessingParameterString(self.TARGET, "Target unit (e.g. celsius, hPa, knots)")
        )
        self.addParameter(
            QgsProcessingParameterNumber(
                self.BAND,
                "Band to convert (optional; default: every band)",
                type=QgsProcessingParameterNumber.Integer,
                optional=True,
                minValue=0,
            )
        )
        self.addParameter(QgsProcessingParameterRasterDestination(self.OUTPUT, "Converted raster"))

    def processAlgorithm(self, parameters, context, feedback):  # noqa: N802
        """Build and run the ``pyramids raster convert-units`` command."""
        layer = self.parameterAsRasterLayer(parameters, self.INPUT, context)
        if layer is None:
            raise QgsProcessingException(self.invalidRasterError(parameters, self.INPUT))
        src = layer_source_path(layer)
        validate_input_path(src, feedback)
        out = self.parameterAsOutputLayer(parameters, self.OUTPUT, context)

        target = self.parameterAsString(parameters, self.TARGET, context).strip()
        if not target:
            raise QgsProcessingException("A target unit is required.")

        argv = ["raster", "convert-units", src, out, "--target", target, "--overwrite"]
        if self.BAND in parameters and parameters[self.BAND] is not None:
            argv += ["--band", str(self.parameterAsInt(parameters, self.BAND, context))]

        self.run_pyramids(argv, feedback)
        return {self.OUTPUT: out}
