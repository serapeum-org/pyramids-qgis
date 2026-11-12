"""Extract a raster's data footprint as a vector — wraps ``pyramids raster footprint``.

Traces the boundary of the covered (non-no-data) pixels of a band and writes it as a polygon
vector. Output is written as GeoJSON regardless of the chosen file extension.
"""

from __future__ import annotations

from qgis.core import (
    QgsProcessingException,
    QgsProcessingParameterNumber,
    QgsProcessingParameterRasterLayer,
    QgsProcessingParameterVectorDestination,
)

from ..base import PyramidsAlgorithm, layer_source_path, validate_input_path


class RasterFootprint(PyramidsAlgorithm):
    """Trace a raster band's data coverage into a polygon vector (written as GeoJSON)."""

    INPUT = "INPUT"
    BAND = "BAND"
    MAX_SAMPLES = "MAX_SAMPLES"
    OUTPUT = "OUTPUT"

    def name(self) -> str:
        """Return the stable algorithm id within the provider."""
        return "raster_footprint"

    def displayName(self) -> str:  # noqa: N802
        """Return the human-readable algorithm name."""
        return "Raster footprint (data coverage)"

    def shortHelpString(self) -> str:  # noqa: N802
        """Return the help shown in the algorithm dialog."""
        return (
            "Trace the boundary of a band's covered (non-no-data) pixels and write it as a "
            "polygon vector, via pyramids. Capping the samples read yields a faster, approximate "
            "footprint. The output is written as GeoJSON regardless of the chosen file extension."
        )

    def initAlgorithm(self, config=None) -> None:  # noqa: N802
        """Declare the algorithm's parameters."""
        self.addParameter(QgsProcessingParameterRasterLayer(self.INPUT, "Input raster"))
        self.addParameter(
            QgsProcessingParameterNumber(
                self.BAND, "Band index (0-based; default 0)",
                type=QgsProcessingParameterNumber.Integer, optional=True, minValue=0,
            )
        )
        self.addParameter(
            QgsProcessingParameterNumber(
                self.MAX_SAMPLES, "Max samples (optional; approximate footprint)",
                type=QgsProcessingParameterNumber.Integer, optional=True, minValue=1,
            )
        )
        self.addParameter(
            QgsProcessingParameterVectorDestination(
                self.OUTPUT, "Footprint vector (GeoJSON)", defaultValue=None
            )
        )

    def processAlgorithm(self, parameters, context, feedback):  # noqa: N802
        """Build and run the ``pyramids raster footprint`` command."""
        layer = self.parameterAsRasterLayer(parameters, self.INPUT, context)
        if layer is None:
            raise QgsProcessingException(self.invalidRasterError(parameters, self.INPUT))
        src = layer_source_path(layer)
        validate_input_path(src, feedback)
        out = self.parameterAsOutputLayer(parameters, self.OUTPUT, context)

        # Force the GeoJSON driver so the written content matches what QGIS loads back,
        # independent of the file extension the destination picks.
        argv = ["raster", "footprint", src, out, "--driver", "geojson", "--overwrite"]
        if self.BAND in parameters and parameters[self.BAND] is not None:
            argv += ["--band", str(self.parameterAsInt(parameters, self.BAND, context))]
        if self.MAX_SAMPLES in parameters and parameters[self.MAX_SAMPLES] is not None:
            max_samples = self.parameterAsInt(parameters, self.MAX_SAMPLES, context)
            argv += ["--max-samples", str(max_samples)]

        self.run_pyramids(argv, feedback)
        return {self.OUTPUT: out}
