"""Crop a raster by a vector mask or a bounding box — wraps ``pyramids clip``."""

from __future__ import annotations

from qgis.core import (
    QgsProcessingException,
    QgsProcessingParameterExtent,
    QgsProcessingParameterRasterDestination,
    QgsProcessingParameterRasterLayer,
    QgsProcessingParameterVectorLayer,
)

from .base import PyramidsAlgorithm, layer_source_path, validate_input_path


class ClipRaster(PyramidsAlgorithm):
    """Crop a raster to a polygon mask, or to a rectangular extent."""

    INPUT = "INPUT"
    MASK = "MASK"
    EXTENT = "EXTENT"
    OUTPUT = "OUTPUT"

    def name(self) -> str:
        """Return the stable algorithm id within the provider."""
        return "clip"

    def displayName(self) -> str:  # noqa: N802
        """Return the human-readable algorithm name."""
        return "Clip raster (by mask or extent)"

    def shortHelpString(self) -> str:  # noqa: N802
        """Return the help shown in the algorithm dialog."""
        return (
            "Crop a raster. Provide a polygon mask layer to clip by geometry, or an extent "
            "to clip by bounding box. If both are given, the mask wins. The extent is "
            "interpreted in the input raster's CRS."
        )

    def initAlgorithm(self, config=None) -> None:  # noqa: N802
        """Declare the algorithm's parameters."""
        self.addParameter(QgsProcessingParameterRasterLayer(self.INPUT, "Input raster"))
        self.addParameter(
            QgsProcessingParameterVectorLayer(self.MASK, "Mask layer (polygons)", optional=True)
        )
        self.addParameter(
            QgsProcessingParameterExtent(self.EXTENT, "Clip extent", optional=True)
        )
        self.addParameter(
            QgsProcessingParameterRasterDestination(self.OUTPUT, "Clipped raster")
        )

    def processAlgorithm(self, parameters, context, feedback):  # noqa: N802
        """Build and run the ``pyramids clip`` command."""
        layer = self.parameterAsRasterLayer(parameters, self.INPUT, context)
        if layer is None:
            raise QgsProcessingException(self.invalidRasterError(parameters, self.INPUT))
        src = layer_source_path(layer)
        validate_input_path(src, feedback)
        out = self.parameterAsOutputLayer(parameters, self.OUTPUT, context)

        mask_layer = self.parameterAsVectorLayer(parameters, self.MASK, context)
        argv = ["clip", src, out]
        if mask_layer is not None:
            mask_path = layer_source_path(mask_layer)
            validate_input_path(mask_path, feedback)
            argv += ["--vector", mask_path]
        else:
            extent = self.parameterAsExtent(parameters, self.EXTENT, context, layer.crs())
            if extent.isNull():
                raise QgsProcessingException(
                    "Provide either a mask layer or a clip extent."
                )
            argv += [
                "--bbox",
                str(extent.xMinimum()),
                str(extent.yMinimum()),
                str(extent.xMaximum()),
                str(extent.yMaximum()),
            ]
        argv.append("--overwrite")

        self.run_pyramids(argv, feedback)
        return {self.OUTPUT: out}
