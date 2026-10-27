"""Re-save a raster in another format — wraps ``pyramids convert``."""

from __future__ import annotations

from qgis.core import (
    QgsProcessingException,
    QgsProcessingParameterRasterDestination,
    QgsProcessingParameterRasterLayer,
    QgsProcessingParameterString,
)

from .base import PyramidsAlgorithm, layer_source_path, validate_input_path


class ConvertRaster(PyramidsAlgorithm):
    """Convert a raster to another format (driver inferred from the output extension)."""

    INPUT = "INPUT"
    DRIVER = "DRIVER"
    OUTPUT = "OUTPUT"

    def name(self) -> str:
        """Return the stable algorithm id within the provider."""
        return "convert"

    def displayName(self) -> str:  # noqa: N802
        """Return the human-readable algorithm name."""
        return "Convert raster format"

    def shortHelpString(self) -> str:  # noqa: N802
        """Return the help shown in the algorithm dialog."""
        return (
            "Re-save a raster in another format. The driver is inferred from the output file "
            "extension unless an explicit driver name is given (a pyramids catalog name such "
            "as 'geotiff', or a GDAL driver name such as 'GTiff')."
        )

    def initAlgorithm(self, config=None) -> None:  # noqa: N802
        """Declare the algorithm's parameters."""
        self.addParameter(QgsProcessingParameterRasterLayer(self.INPUT, "Input raster"))
        self.addParameter(
            QgsProcessingParameterString(
                self.DRIVER, "Driver (optional; default: from extension)", optional=True
            )
        )
        self.addParameter(
            QgsProcessingParameterRasterDestination(self.OUTPUT, "Converted raster")
        )

    def processAlgorithm(self, parameters, context, feedback):  # noqa: N802
        """Build and run the ``pyramids convert`` command."""
        layer = self.parameterAsRasterLayer(parameters, self.INPUT, context)
        if layer is None:
            raise QgsProcessingException(self.invalidRasterError(parameters, self.INPUT))
        src = layer_source_path(layer)
        validate_input_path(src, feedback)
        out = self.parameterAsOutputLayer(parameters, self.OUTPUT, context)

        argv = ["convert", src, out, "--overwrite"]
        driver = self.parameterAsString(parameters, self.DRIVER, context).strip()
        if driver:
            argv += ["--driver", driver]

        self.run_pyramids(argv, feedback)
        return {self.OUTPUT: out}
