"""Clip a vector by a mask layer or a bounding box — wraps ``pyramids vector clip``."""

from __future__ import annotations

from qgis.core import (
    QgsProcessingException,
    QgsProcessingParameterExtent,
    QgsProcessingParameterString,
    QgsProcessingParameterVectorDestination,
    QgsProcessingParameterVectorLayer,
)

from ..base import PyramidsAlgorithm, layer_source_path, validate_input_path


class ClipVector(PyramidsAlgorithm):
    """Clip a vector to a polygon mask, or to a rectangular extent."""

    GROUP_LABEL = "Vector"
    GROUP_ID = "vector"

    INPUT = "INPUT"
    MASK = "MASK"
    EXTENT = "EXTENT"
    DRIVER = "DRIVER"
    LAYER = "LAYER"
    OUTPUT = "OUTPUT"

    def name(self) -> str:
        """Return the stable algorithm id within the provider."""
        return "vector_clip"

    def displayName(self) -> str:  # noqa: N802
        """Return the human-readable algorithm name."""
        return "Clip vector (by mask or extent)"

    def shortHelpString(self) -> str:  # noqa: N802
        """Return the help shown in the algorithm dialog."""
        return (
            "Clip a vector. Provide a polygon mask layer to clip by geometry, or an extent to "
            "clip by bounding box. If both are given, the mask wins. The extent is interpreted "
            "in the input vector's CRS. The OGR driver is inferred from the output file "
            "extension unless an explicit driver name is given."
        )

    def initAlgorithm(self, config=None) -> None:  # noqa: N802
        """Declare the algorithm's parameters."""
        self.addParameter(QgsProcessingParameterVectorLayer(self.INPUT, "Input vector"))
        self.addParameter(
            QgsProcessingParameterVectorLayer(self.MASK, "Mask layer (polygons)", optional=True)
        )
        self.addParameter(QgsProcessingParameterExtent(self.EXTENT, "Clip extent", optional=True))
        self.addParameter(
            QgsProcessingParameterString(
                self.DRIVER, "Driver (optional; default: from extension)", optional=True
            )
        )
        self.addParameter(
            QgsProcessingParameterString(
                self.LAYER, "Layer name/index (optional; multi-layer sources)", optional=True
            )
        )
        self.addParameter(QgsProcessingParameterVectorDestination(self.OUTPUT, "Clipped vector"))

    def processAlgorithm(self, parameters, context, feedback):  # noqa: N802
        """Build and run the ``pyramids vector clip`` command."""
        layer = self.parameterAsVectorLayer(parameters, self.INPUT, context)
        if layer is None:
            raise QgsProcessingException(self.invalidSourceError(parameters, self.INPUT))
        src = layer_source_path(layer)
        validate_input_path(src, feedback)
        out = self.parameterAsOutputLayer(parameters, self.OUTPUT, context)

        mask_layer = self.parameterAsVectorLayer(parameters, self.MASK, context)
        argv = ["vector", "clip", src, out]
        if mask_layer is not None:
            mask_path = layer_source_path(mask_layer)
            validate_input_path(mask_path, feedback)
            argv += ["--mask", mask_path]
        else:
            extent = self.parameterAsExtent(parameters, self.EXTENT, context, layer.crs())
            if extent.isNull():
                raise QgsProcessingException("Provide either a mask layer or a clip extent.")
            argv += [
                "--bbox",
                str(extent.xMinimum()),
                str(extent.yMinimum()),
                str(extent.xMaximum()),
                str(extent.yMaximum()),
            ]
        argv.append("--overwrite")

        driver = self.parameterAsString(parameters, self.DRIVER, context).strip()
        if driver:
            argv += ["--driver", driver]
        layer_ref = self.parameterAsString(parameters, self.LAYER, context).strip()
        if layer_ref:
            argv += ["--layer", layer_ref]

        self.run_pyramids(argv, feedback)
        return {self.OUTPUT: out}
