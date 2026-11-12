"""Match a raster's histogram to a reference — wraps ``pyramids raster match-histogram``."""

from __future__ import annotations

from qgis.core import (
    QgsProcessingException,
    QgsProcessingParameterNumber,
    QgsProcessingParameterRasterDestination,
    QgsProcessingParameterRasterLayer,
)

from ..base import PyramidsAlgorithm, layer_source_path, validate_input_path


class RasterMatchHistogram(PyramidsAlgorithm):
    """Remap a raster band so its value distribution matches a reference band."""

    INPUT = "INPUT"
    REFERENCE = "REFERENCE"
    BAND = "BAND"
    REFERENCE_BAND = "REFERENCE_BAND"
    BINS = "BINS"
    OUTPUT = "OUTPUT"

    def name(self) -> str:
        """Return the stable algorithm id within the provider."""
        return "raster_match_histogram"

    def displayName(self) -> str:  # noqa: N802
        """Return the human-readable algorithm name."""
        return "Match histogram to reference"

    def shortHelpString(self) -> str:  # noqa: N802
        """Return the help shown in the algorithm dialog."""
        return (
            "Remap a raster band so its value distribution matches a reference raster's band "
            "(histogram matching), via pyramids."
        )

    def initAlgorithm(self, config=None) -> None:  # noqa: N802
        """Declare the algorithm's parameters."""
        self.addParameter(QgsProcessingParameterRasterLayer(self.INPUT, "Input raster"))
        self.addParameter(
            QgsProcessingParameterRasterLayer(self.REFERENCE, "Reference raster")
        )
        self.addParameter(
            QgsProcessingParameterNumber(
                self.BAND,
                "Input band index (0-based)",
                type=QgsProcessingParameterNumber.Integer,
                optional=True,
                minValue=0,
                defaultValue=0,
            )
        )
        self.addParameter(
            QgsProcessingParameterNumber(
                self.REFERENCE_BAND,
                "Reference band index (optional; default: same as input band)",
                type=QgsProcessingParameterNumber.Integer,
                optional=True,
                minValue=0,
            )
        )
        self.addParameter(
            QgsProcessingParameterNumber(
                self.BINS,
                "Quantile levels sampled (optional; default: 256)",
                type=QgsProcessingParameterNumber.Integer,
                optional=True,
                minValue=1,
            )
        )
        self.addParameter(QgsProcessingParameterRasterDestination(self.OUTPUT, "Matched raster"))

    def processAlgorithm(self, parameters, context, feedback):  # noqa: N802
        """Build and run the ``pyramids raster match-histogram`` command."""
        layer = self.parameterAsRasterLayer(parameters, self.INPUT, context)
        if layer is None:
            raise QgsProcessingException(self.invalidRasterError(parameters, self.INPUT))
        src = layer_source_path(layer)
        validate_input_path(src, feedback)

        reference = self.parameterAsRasterLayer(parameters, self.REFERENCE, context)
        if reference is None:
            raise QgsProcessingException(self.invalidRasterError(parameters, self.REFERENCE))
        ref = layer_source_path(reference)
        validate_input_path(ref, feedback)
        out = self.parameterAsOutputLayer(parameters, self.OUTPUT, context)

        argv = ["raster", "match-histogram", src, ref, out, "--overwrite"]
        if self.BAND in parameters and parameters[self.BAND] is not None:
            argv += ["--band", str(self.parameterAsInt(parameters, self.BAND, context))]
        if self.REFERENCE_BAND in parameters and parameters[self.REFERENCE_BAND] is not None:
            argv += [
                "--reference-band",
                str(self.parameterAsInt(parameters, self.REFERENCE_BAND, context)),
            ]
        if self.BINS in parameters and parameters[self.BINS] is not None:
            argv += ["--bins", str(self.parameterAsInt(parameters, self.BINS, context))]

        self.run_pyramids(argv, feedback)
        return {self.OUTPUT: out}
