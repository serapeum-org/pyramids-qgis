"""Reproject a vector to a target CRS — wraps ``pyramids vector warp``."""

from __future__ import annotations

from qgis.core import (
    QgsProcessingException,
    QgsProcessingParameterCrs,
    QgsProcessingParameterString,
    QgsProcessingParameterVectorDestination,
    QgsProcessingParameterVectorLayer,
)

from ..base import PyramidsAlgorithm, crs_to_pyramids, layer_source_path, validate_input_path


class WarpVector(PyramidsAlgorithm):
    """Reproject (warp) a vector into another coordinate reference system."""

    GROUP_LABEL = "Vector"
    GROUP_ID = "vector"

    INPUT = "INPUT"
    CRS = "CRS"
    DRIVER = "DRIVER"
    LAYER = "LAYER"
    OUTPUT = "OUTPUT"

    def name(self) -> str:
        """Return the stable algorithm id within the provider."""
        return "vector_warp"

    def displayName(self) -> str:  # noqa: N802
        """Return the human-readable algorithm name."""
        return "Reproject vector (warp)"

    def shortHelpString(self) -> str:  # noqa: N802
        """Return the help shown in the algorithm dialog."""
        return (
            "Reproject a vector to a target CRS, via pyramids. The OGR driver is inferred from "
            "the output file extension unless an explicit driver name is given. For a "
            "multi-layer source, a layer name or index may be selected."
        )

    def initAlgorithm(self, config=None) -> None:  # noqa: N802
        """Declare the algorithm's parameters."""
        self.addParameter(QgsProcessingParameterVectorLayer(self.INPUT, "Input vector"))
        self.addParameter(QgsProcessingParameterCrs(self.CRS, "Target CRS"))
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
        self.addParameter(
            QgsProcessingParameterVectorDestination(self.OUTPUT, "Reprojected vector")
        )

    def processAlgorithm(self, parameters, context, feedback):  # noqa: N802
        """Build and run the ``pyramids vector warp`` command."""
        layer = self.parameterAsVectorLayer(parameters, self.INPUT, context)
        if layer is None:
            raise QgsProcessingException(self.invalidSourceError(parameters, self.INPUT))
        src = layer_source_path(layer)
        validate_input_path(src, feedback)

        target_crs = crs_to_pyramids(self.parameterAsCrs(parameters, self.CRS, context))
        if target_crs is None:
            raise QgsProcessingException("A valid target CRS is required.")

        out = self.parameterAsOutputLayer(parameters, self.OUTPUT, context)

        argv = ["vector", "warp", src, out, "--overwrite"]
        if target_crs:
            argv += ["--crs", target_crs]
        driver = self.parameterAsString(parameters, self.DRIVER, context).strip()
        if driver:
            argv += ["--driver", driver]
        layer_ref = self.parameterAsString(parameters, self.LAYER, context).strip()
        if layer_ref:
            argv += ["--layer", layer_ref]

        self.run_pyramids(argv, feedback)
        return {self.OUTPUT: out}
