"""Rotate geometries about an origin — wraps ``pyramids vector geom rotate``."""

from __future__ import annotations

from qgis.core import (
    QgsProcessingException,
    QgsProcessingParameterBoolean,
    QgsProcessingParameterEnum,
    QgsProcessingParameterNumber,
    QgsProcessingParameterString,
    QgsProcessingParameterVectorDestination,
    QgsProcessingParameterVectorLayer,
)

from ..base import PyramidsAlgorithm, layer_source_path, validate_input_path

#: Rotation origins the CLI accepts (passed verbatim to shapely's ``origin=``). A coordinate
#: origin cannot be expressed through this command — the CLI forwards the raw ``--origin`` string
#: to shapely, which only recognizes the keywords ``center`` / ``centroid`` as strings.
ORIGIN = ["center", "centroid"]


class VectorGeomRotate(PyramidsAlgorithm):
    """Rotate every geometry about a common origin."""

    GROUP_LABEL = "Vector"
    GROUP_ID = "vector"

    INPUT = "INPUT"
    ANGLE = "ANGLE"
    ORIGIN = "ORIGIN"
    RADIANS = "RADIANS"
    LAYER = "LAYER"
    OUTPUT = "OUTPUT"

    def name(self) -> str:
        """Return the stable algorithm id within the provider."""
        return "vector_geom_rotate"

    def displayName(self) -> str:  # noqa: N802
        """Return the human-readable algorithm name."""
        return "Rotate vector geometries"

    def shortHelpString(self) -> str:  # noqa: N802
        """Return the help shown in the algorithm dialog."""
        return (
            "Rotate every geometry about an origin, via pyramids. The angle is in degrees "
            "(positive is counter-clockwise) unless 'Angle in radians' is enabled. The origin is "
            "either the bounding-box center or the geometry's centroid."
        )

    def initAlgorithm(self, config=None) -> None:  # noqa: N802
        """Declare the algorithm's parameters."""
        self.addParameter(QgsProcessingParameterVectorLayer(self.INPUT, "Input vector"))
        self.addParameter(
            QgsProcessingParameterNumber(
                self.ANGLE,
                "Rotation angle",
                type=QgsProcessingParameterNumber.Double,
                defaultValue=0.0,
            )
        )
        self.addParameter(
            QgsProcessingParameterEnum(
                self.ORIGIN, "Rotation origin", options=ORIGIN, defaultValue=0
            )
        )
        self.addParameter(
            QgsProcessingParameterBoolean(self.RADIANS, "Angle in radians", defaultValue=False)
        )
        self.addParameter(
            QgsProcessingParameterString(
                self.LAYER, "Layer name/index (optional; multi-layer sources)", optional=True
            )
        )
        self.addParameter(QgsProcessingParameterVectorDestination(self.OUTPUT, "Rotated vector"))

    def processAlgorithm(self, parameters, context, feedback):  # noqa: N802
        """Build and run the ``pyramids vector geom rotate`` command."""
        layer = self.parameterAsVectorLayer(parameters, self.INPUT, context)
        if layer is None:
            raise QgsProcessingException(self.invalidSourceError(parameters, self.INPUT))
        src = layer_source_path(layer)
        validate_input_path(src, feedback)
        out = self.parameterAsOutputLayer(parameters, self.OUTPUT, context)

        angle = self.parameterAsDouble(parameters, self.ANGLE, context)
        origin = ORIGIN[self.parameterAsEnum(parameters, self.ORIGIN, context)]
        # '=' join keeps a negative angle from being parsed as an option rather than a value.
        argv = ["vector", "geom", "rotate", src, out, "--overwrite", f"--angle={angle}"]
        argv += ["--origin", origin]
        if self.parameterAsBool(parameters, self.RADIANS, context):
            argv.append("--radians")
        layer_ref = self.parameterAsString(parameters, self.LAYER, context).strip()
        if layer_ref:
            argv += ["--layer", layer_ref]

        self.run_pyramids(argv, feedback)
        return {self.OUTPUT: out}
