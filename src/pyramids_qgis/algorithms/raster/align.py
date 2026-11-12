"""Align a raster onto a reference raster's grid — wraps ``pyramids raster align``."""

from __future__ import annotations

from qgis.core import (
    QgsProcessingException,
    QgsProcessingParameterEnum,
    QgsProcessingParameterRasterDestination,
    QgsProcessingParameterRasterLayer,
)

from ..base import PyramidsAlgorithm, layer_source_path, validate_input_path

#: Resampling methods forwarded verbatim to pyramids. Each must be an exact key of pyramids'
#: ``INTERPOLATION_METHODS`` (snake_case, plus the historical ``"nearest neighbor"`` alias); the
#: resolver only lowercases/strips, so ``"cubic_spline"`` must carry the underscore.
RESAMPLING = ["nearest neighbor", "bilinear", "cubic", "cubic_spline", "lanczos", "average", "mode"]


class RasterAlign(PyramidsAlgorithm):
    """Resample a raster onto a reference raster's grid and CRS."""

    INPUT = "INPUT"
    REFERENCE = "REFERENCE"
    RESAMPLING = "RESAMPLING"
    OUTPUT = "OUTPUT"

    def name(self) -> str:
        """Return the stable algorithm id within the provider."""
        return "raster_align"

    def displayName(self) -> str:  # noqa: N802
        """Return the human-readable algorithm name."""
        return "Align raster to reference grid"

    def shortHelpString(self) -> str:  # noqa: N802
        """Return the help shown in the algorithm dialog."""
        return (
            "Resample a raster so its grid and CRS match a reference raster (same cell size, "
            "extent and alignment), via pyramids."
        )

    def initAlgorithm(self, config=None) -> None:  # noqa: N802
        """Declare the algorithm's parameters."""
        self.addParameter(QgsProcessingParameterRasterLayer(self.INPUT, "Input raster"))
        self.addParameter(
            QgsProcessingParameterRasterLayer(self.REFERENCE, "Reference raster (grid/CRS)")
        )
        self.addParameter(
            QgsProcessingParameterEnum(
                self.RESAMPLING, "Resampling method", options=RESAMPLING, defaultValue=0
            )
        )
        self.addParameter(QgsProcessingParameterRasterDestination(self.OUTPUT, "Aligned raster"))

    def processAlgorithm(self, parameters, context, feedback):  # noqa: N802
        """Build and run the ``pyramids raster align`` command."""
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

        resampling = RESAMPLING[self.parameterAsEnum(parameters, self.RESAMPLING, context)]
        out = self.parameterAsOutputLayer(parameters, self.OUTPUT, context)

        self.run_pyramids(
            ["raster", "align", src, ref, out, "--resampling", resampling, "--overwrite"],
            feedback,
        )
        return {self.OUTPUT: out}
