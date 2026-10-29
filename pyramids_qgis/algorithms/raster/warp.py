"""Reproject a raster to a target CRS — wraps ``pyramids warp``."""

from __future__ import annotations

from qgis.core import (
    QgsProcessingException,
    QgsProcessingParameterCrs,
    QgsProcessingParameterEnum,
    QgsProcessingParameterRasterDestination,
    QgsProcessingParameterRasterLayer,
)

from ..base import PyramidsAlgorithm, crs_to_pyramids, layer_source_path, validate_input_path

#: Resampling methods forwarded verbatim to ``Dataset.to_crs(method=...)``. Each must be an exact
#: key of pyramids' ``INTERPOLATION_METHODS`` (pyramids/base/_utils.py): snake_case, plus the
#: historical ``"nearest neighbor"`` alias. ``resolve_resampling`` only lowercases/strips and does
#: not map a space to an underscore, so ``"cubic_spline"`` must carry the underscore (review H1).
RESAMPLING = ["nearest neighbor", "bilinear", "cubic", "cubic_spline", "lanczos", "average", "mode"]


class WarpRaster(PyramidsAlgorithm):
    """Reproject (warp) a raster into another coordinate reference system."""

    INPUT = "INPUT"
    CRS = "CRS"
    RESAMPLING = "RESAMPLING"
    OUTPUT = "OUTPUT"

    def name(self) -> str:
        """Return the stable algorithm id within the provider."""
        return "warp"

    def displayName(self) -> str:  # noqa: N802  (QGIS-mandated method name)
        """Return the human-readable algorithm name."""
        return "Reproject raster (warp)"

    def shortHelpString(self) -> str:  # noqa: N802  (QGIS-mandated method name)
        """Return the help shown in the algorithm dialog."""
        return "Reproject a raster to a target CRS using GDAL warp, via pyramids."

    def initAlgorithm(self, config=None) -> None:  # noqa: N802  (QGIS-mandated name)
        """Declare the algorithm's parameters."""
        self.addParameter(QgsProcessingParameterRasterLayer(self.INPUT, "Input raster"))
        self.addParameter(QgsProcessingParameterCrs(self.CRS, "Target CRS"))
        self.addParameter(
            QgsProcessingParameterEnum(
                self.RESAMPLING, "Resampling method", options=RESAMPLING, defaultValue=0
            )
        )
        self.addParameter(
            QgsProcessingParameterRasterDestination(self.OUTPUT, "Reprojected raster")
        )

    def processAlgorithm(self, parameters, context, feedback):  # noqa: N802
        """Build and run the ``pyramids warp`` command."""
        layer = self.parameterAsRasterLayer(parameters, self.INPUT, context)
        if layer is None:
            raise QgsProcessingException(self.invalidRasterError(parameters, self.INPUT))
        src = layer_source_path(layer)
        validate_input_path(src, feedback)

        target_crs = crs_to_pyramids(self.parameterAsCrs(parameters, self.CRS, context))
        if target_crs is None:
            raise QgsProcessingException("A valid target CRS is required.")

        resampling = RESAMPLING[self.parameterAsEnum(parameters, self.RESAMPLING, context)]
        out = self.parameterAsOutputLayer(parameters, self.OUTPUT, context)

        self.run_pyramids(
            ["warp", src, out, "--crs", target_crs, "--resampling", resampling, "--overwrite"],
            feedback,
        )
        return {self.OUTPUT: out}
