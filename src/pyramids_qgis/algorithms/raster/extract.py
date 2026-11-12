"""Extract a raster's cell values to a CSV table — wraps ``pyramids raster extract``."""

from __future__ import annotations

from qgis.core import (
    QgsProcessingException,
    QgsProcessingParameterFileDestination,
    QgsProcessingParameterNumber,
    QgsProcessingParameterRasterLayer,
    QgsProcessingParameterVectorLayer,
)

from ..base import PyramidsAlgorithm, layer_source_path, validate_input_path


class RasterExtract(PyramidsAlgorithm):
    """Write a raster's cell values (one row per band) to a CSV table."""

    INPUT = "INPUT"
    BAND = "BAND"
    EXCLUDE_VALUE = "EXCLUDE_VALUE"
    MASK = "MASK"
    OUTPUT = "OUTPUT"

    def name(self) -> str:
        """Return the stable algorithm id within the provider."""
        return "raster_extract"

    def displayName(self) -> str:  # noqa: N802
        """Return the human-readable algorithm name."""
        return "Extract values to CSV"

    def shortHelpString(self) -> str:  # noqa: N802
        """Return the help shown in the algorithm dialog."""
        return (
            "Write a raster's cell values to a CSV (one row per band). Optionally restrict to a "
            "band, drop a value, or read only at the locations of a point vector layer, via "
            "pyramids."
        )

    def initAlgorithm(self, config=None) -> None:  # noqa: N802
        """Declare the algorithm's parameters."""
        self.addParameter(QgsProcessingParameterRasterLayer(self.INPUT, "Input raster"))
        self.addParameter(
            QgsProcessingParameterNumber(
                self.BAND,
                "Band index (0-based; optional)",
                type=QgsProcessingParameterNumber.Integer,
                optional=True,
                minValue=0,
            )
        )
        self.addParameter(
            QgsProcessingParameterNumber(
                self.EXCLUDE_VALUE,
                "Value to drop from the extracted values (optional)",
                type=QgsProcessingParameterNumber.Double,
                optional=True,
            )
        )
        self.addParameter(
            QgsProcessingParameterVectorLayer(
                self.MASK, "Point vector to read values at (optional)", optional=True
            )
        )
        self.addParameter(
            QgsProcessingParameterFileDestination(
                self.OUTPUT, "Output CSV", fileFilter="CSV (*.csv)"
            )
        )

    def processAlgorithm(self, parameters, context, feedback):  # noqa: N802
        """Build and run the ``pyramids raster extract`` command."""
        layer = self.parameterAsRasterLayer(parameters, self.INPUT, context)
        if layer is None:
            raise QgsProcessingException(self.invalidRasterError(parameters, self.INPUT))
        src = layer_source_path(layer)
        validate_input_path(src, feedback)
        out = self.parameterAsFileOutput(parameters, self.OUTPUT, context)

        argv = ["raster", "extract", src, out, "--overwrite"]
        if self.BAND in parameters and parameters[self.BAND] is not None:
            argv += ["--band", str(self.parameterAsInt(parameters, self.BAND, context))]
        if self.EXCLUDE_VALUE in parameters and parameters[self.EXCLUDE_VALUE] is not None:
            # Join with '=' so a negative value is never mistaken for an option by argparse.
            exclude = self.parameterAsDouble(parameters, self.EXCLUDE_VALUE, context)
            argv.append(f"--exclude-value={exclude}")

        mask_layer = self.parameterAsVectorLayer(parameters, self.MASK, context)
        if mask_layer is not None:
            mask_path = layer_source_path(mask_layer)
            validate_input_path(mask_path, feedback)
            argv += ["--mask", mask_path]

        self.run_pyramids(argv, feedback)
        return {self.OUTPUT: out}
