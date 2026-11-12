"""Create an empty raster matching a template's grid — wraps ``pyramids raster empty-like``.

Copies a template raster's footprint (size, geotransform and CRS) into a new empty raster,
optionally overriding the dtype, band count and no-data value.
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


class RasterEmptyLike(PyramidsAlgorithm):
    """Create a new empty raster that copies a template raster's footprint."""

    TEMPLATE = "TEMPLATE"
    DTYPE = "DTYPE"
    BANDS = "BANDS"
    NODATA = "NODATA"
    OUTPUT = "OUTPUT"

    def name(self) -> str:
        """Return the stable algorithm id within the provider."""
        return "raster_empty_like"

    def displayName(self) -> str:  # noqa: N802
        """Return the human-readable algorithm name."""
        return "Create empty raster like template"

    def shortHelpString(self) -> str:  # noqa: N802
        """Return the help shown in the algorithm dialog."""
        return (
            "Create a new empty raster whose footprint (size, geotransform and CRS) copies a "
            "template raster, via pyramids. The dtype, band count and no-data value default to "
            "the template's unless overridden."
        )

    def initAlgorithm(self, config=None) -> None:  # noqa: N802
        """Declare the algorithm's parameters."""
        self.addParameter(QgsProcessingParameterRasterLayer(self.TEMPLATE, "Template raster"))
        self.addParameter(
            QgsProcessingParameterString(
                self.DTYPE, "Numpy dtype (optional; default: the template's)", optional=True
            )
        )
        self.addParameter(
            QgsProcessingParameterNumber(
                self.BANDS, "Bands (optional; default: the template's)",
                type=QgsProcessingParameterNumber.Integer, optional=True, minValue=1,
            )
        )
        self.addParameter(
            QgsProcessingParameterNumber(
                self.NODATA, "No-data value (optional; default: inherit)",
                type=QgsProcessingParameterNumber.Double, optional=True,
            )
        )
        self.addParameter(QgsProcessingParameterRasterDestination(self.OUTPUT, "Output raster"))

    def processAlgorithm(self, parameters, context, feedback):  # noqa: N802
        """Build and run the ``pyramids raster empty-like`` command."""
        template = self.parameterAsRasterLayer(parameters, self.TEMPLATE, context)
        if template is None:
            raise QgsProcessingException(self.invalidRasterError(parameters, self.TEMPLATE))
        src = layer_source_path(template)
        validate_input_path(src, feedback)
        out = self.parameterAsOutputLayer(parameters, self.OUTPUT, context)

        argv = ["raster", "empty-like", src, out]
        dtype = self.parameterAsString(parameters, self.DTYPE, context).strip()
        if dtype:
            argv += ["--dtype", dtype]
        if self.BANDS in parameters and parameters[self.BANDS] is not None:
            argv += ["--bands", str(self.parameterAsInt(parameters, self.BANDS, context))]
        if self.NODATA in parameters and parameters[self.NODATA] is not None:
            nodata = self.parameterAsDouble(parameters, self.NODATA, context)
            # '=' join keeps a negative / scientific-notation sentinel from being parsed as an
            # option rather than this flag's value (review R2-L4).
            argv.append(f"--no-data-value={nodata}")

        argv.append("--overwrite")
        self.run_pyramids(argv, feedback)
        return {self.OUTPUT: out}
