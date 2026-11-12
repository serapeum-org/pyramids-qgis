"""Scale geometries about their center — wraps ``pyramids vector geom scale``."""

from __future__ import annotations

from qgis.core import (
    QgsProcessingException,
    QgsProcessingParameterNumber,
    QgsProcessingParameterString,
    QgsProcessingParameterVectorDestination,
    QgsProcessingParameterVectorLayer,
)

from ..base import PyramidsAlgorithm, layer_source_path, validate_input_path


class VectorGeomScale(PyramidsAlgorithm):
    """Scale every geometry about its center by per-axis factors."""

    GROUP_LABEL = "Vector"
    GROUP_ID = "vector"

    INPUT = "INPUT"
    XFACT = "XFACT"
    YFACT = "YFACT"
    ZFACT = "ZFACT"
    LAYER = "LAYER"
    OUTPUT = "OUTPUT"

    def name(self) -> str:
        """Return the stable algorithm id within the provider."""
        return "vector_geom_scale"

    def displayName(self) -> str:  # noqa: N802
        """Return the human-readable algorithm name."""
        return "Scale vector geometries"

    def shortHelpString(self) -> str:  # noqa: N802
        """Return the help shown in the algorithm dialog."""
        return (
            "Scale every geometry about its center by per-axis factors, via pyramids. A factor of "
            "1 leaves an axis unchanged; a negative factor mirrors it. Scaling is applied about "
            "each geometry's own bounding-box center."
        )

    def initAlgorithm(self, config=None) -> None:  # noqa: N802
        """Declare the algorithm's parameters."""
        self.addParameter(QgsProcessingParameterVectorLayer(self.INPUT, "Input vector"))
        self.addParameter(
            QgsProcessingParameterNumber(
                self.XFACT,
                "X scale factor",
                type=QgsProcessingParameterNumber.Double,
                defaultValue=1.0,
            )
        )
        self.addParameter(
            QgsProcessingParameterNumber(
                self.YFACT,
                "Y scale factor",
                type=QgsProcessingParameterNumber.Double,
                defaultValue=1.0,
            )
        )
        self.addParameter(
            QgsProcessingParameterNumber(
                self.ZFACT,
                "Z scale factor",
                type=QgsProcessingParameterNumber.Double,
                defaultValue=1.0,
            )
        )
        self.addParameter(
            QgsProcessingParameterString(
                self.LAYER, "Layer name/index (optional; multi-layer sources)", optional=True
            )
        )
        self.addParameter(QgsProcessingParameterVectorDestination(self.OUTPUT, "Scaled vector"))

    def processAlgorithm(self, parameters, context, feedback):  # noqa: N802
        """Build and run the ``pyramids vector geom scale`` command."""
        layer = self.parameterAsVectorLayer(parameters, self.INPUT, context)
        if layer is None:
            raise QgsProcessingException(self.invalidSourceError(parameters, self.INPUT))
        src = layer_source_path(layer)
        validate_input_path(src, feedback)
        out = self.parameterAsOutputLayer(parameters, self.OUTPUT, context)

        xfact = self.parameterAsDouble(parameters, self.XFACT, context)
        yfact = self.parameterAsDouble(parameters, self.YFACT, context)
        zfact = self.parameterAsDouble(parameters, self.ZFACT, context)
        # '=' join keeps a negative (mirroring) factor from being parsed as an option.
        argv = ["vector", "geom", "scale", src, out, "--overwrite"]
        argv += [f"--xfact={xfact}", f"--yfact={yfact}", f"--zfact={zfact}"]
        layer_ref = self.parameterAsString(parameters, self.LAYER, context).strip()
        if layer_ref:
            argv += ["--layer", layer_ref]

        self.run_pyramids(argv, feedback)
        return {self.OUTPUT: out}
