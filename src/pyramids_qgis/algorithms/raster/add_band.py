"""Append a band from another raster — wraps ``pyramids raster add-band``.

Reads one band of a source raster and appends it to the input raster's bands, writing the
stacked result to a new file.
"""

from __future__ import annotations

from qgis.core import (
    QgsProcessingException,
    QgsProcessingParameterNumber,
    QgsProcessingParameterRasterDestination,
    QgsProcessingParameterRasterLayer,
    QgsProcessingParameterString,
)

from ..base import PyramidsAlgorithm, layer_source_path, validate_input_path


class RasterAddBand(PyramidsAlgorithm):
    """Append a band read from a source raster onto the input raster."""

    INPUT = "INPUT"
    SOURCE = "SOURCE"
    SOURCE_BAND = "SOURCE_BAND"
    UNIT = "UNIT"
    OUTPUT = "OUTPUT"

    def name(self) -> str:
        """Return the stable algorithm id within the provider."""
        return "raster_add_band"

    def displayName(self) -> str:  # noqa: N802
        """Return the human-readable algorithm name."""
        return "Add band from raster"

    def shortHelpString(self) -> str:  # noqa: N802
        """Return the help shown in the algorithm dialog."""
        return (
            "Append a band read from a source raster onto the input raster's bands, writing the "
            "stacked result to a new file, via pyramids. Choose which band of the source to "
            "append and optionally label the new band's unit."
        )

    def initAlgorithm(self, config=None) -> None:  # noqa: N802
        """Declare the algorithm's parameters."""
        self.addParameter(QgsProcessingParameterRasterLayer(self.INPUT, "Input raster"))
        self.addParameter(
            QgsProcessingParameterRasterLayer(self.SOURCE, "Source raster (band to append)")
        )
        self.addParameter(
            QgsProcessingParameterNumber(
                self.SOURCE_BAND, "Source band index (0-based; default 0)",
                type=QgsProcessingParameterNumber.Integer, optional=True, minValue=0,
            )
        )
        self.addParameter(
            QgsProcessingParameterString(
                self.UNIT, "Unit of the new band (optional)", optional=True
            )
        )
        self.addParameter(QgsProcessingParameterRasterDestination(self.OUTPUT, "Output raster"))

    def processAlgorithm(self, parameters, context, feedback):  # noqa: N802
        """Build and run the ``pyramids raster add-band`` command."""
        layer = self.parameterAsRasterLayer(parameters, self.INPUT, context)
        if layer is None:
            raise QgsProcessingException(self.invalidRasterError(parameters, self.INPUT))
        src = layer_source_path(layer)
        validate_input_path(src, feedback)

        source_layer = self.parameterAsRasterLayer(parameters, self.SOURCE, context)
        if source_layer is None:
            raise QgsProcessingException(self.invalidRasterError(parameters, self.SOURCE))
        source_path = layer_source_path(source_layer)
        validate_input_path(source_path, feedback)
        out = self.parameterAsOutputLayer(parameters, self.OUTPUT, context)

        argv = ["raster", "add-band", src, out, "--source", source_path]
        if self.SOURCE_BAND in parameters and parameters[self.SOURCE_BAND] is not None:
            source_band = self.parameterAsInt(parameters, self.SOURCE_BAND, context)
            argv += ["--source-band", str(source_band)]
        unit = self.parameterAsString(parameters, self.UNIT, context).strip()
        if unit:
            argv += ["--unit", unit]
        argv.append("--overwrite")

        self.run_pyramids(argv, feedback)
        return {self.OUTPUT: out}
