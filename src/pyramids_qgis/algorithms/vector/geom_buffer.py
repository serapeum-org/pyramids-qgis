"""Buffer every geometry by a distance — wraps ``pyramids vector geom buffer``."""

from __future__ import annotations

from qgis.core import (
    QgsProcessingException,
    QgsProcessingParameterEnum,
    QgsProcessingParameterNumber,
    QgsProcessingParameterString,
    QgsProcessingParameterVectorDestination,
    QgsProcessingParameterVectorLayer,
)

from ..base import PyramidsAlgorithm, layer_source_path, validate_input_path

#: End-cap styles forwarded verbatim to ``--cap-style``.
CAP_STYLE = ["round", "flat", "square"]
#: Segment join styles forwarded verbatim to ``--join-style``.
JOIN_STYLE = ["round", "mitre", "bevel"]


class VectorGeomBuffer(PyramidsAlgorithm):
    """Buffer every geometry in a vector by a (possibly negative) distance."""

    GROUP_LABEL = "Vector"
    GROUP_ID = "vector"

    INPUT = "INPUT"
    DISTANCE = "DISTANCE"
    RESOLUTION = "RESOLUTION"
    CAP_STYLE = "CAP_STYLE"
    JOIN_STYLE = "JOIN_STYLE"
    LAYER = "LAYER"
    OUTPUT = "OUTPUT"

    def name(self) -> str:
        """Return the stable algorithm id within the provider."""
        return "vector_geom_buffer"

    def displayName(self) -> str:  # noqa: N802
        """Return the human-readable algorithm name."""
        return "Buffer vector geometries"

    def shortHelpString(self) -> str:  # noqa: N802
        """Return the help shown in the algorithm dialog."""
        return (
            "Buffer every geometry by a distance, via pyramids. A negative distance shrinks "
            "(erodes) polygons. Resolution sets the number of segments per quadrant used to "
            "approximate round corners; the cap and join styles control how line ends and "
            "corners are rendered. The distance is in the input vector's CRS units."
        )

    def initAlgorithm(self, config=None) -> None:  # noqa: N802
        """Declare the algorithm's parameters."""
        self.addParameter(QgsProcessingParameterVectorLayer(self.INPUT, "Input vector"))
        self.addParameter(
            QgsProcessingParameterNumber(
                self.DISTANCE,
                "Buffer distance",
                type=QgsProcessingParameterNumber.Double,
                defaultValue=0.0,
            )
        )
        self.addParameter(
            QgsProcessingParameterNumber(
                self.RESOLUTION,
                "Segments per quadrant",
                type=QgsProcessingParameterNumber.Integer,
                defaultValue=16,
                minValue=1,
            )
        )
        self.addParameter(
            QgsProcessingParameterEnum(
                self.CAP_STYLE, "End-cap style", options=CAP_STYLE, defaultValue=0
            )
        )
        self.addParameter(
            QgsProcessingParameterEnum(
                self.JOIN_STYLE, "Segment join style", options=JOIN_STYLE, defaultValue=0
            )
        )
        self.addParameter(
            QgsProcessingParameterString(
                self.LAYER, "Layer name/index (optional; multi-layer sources)", optional=True
            )
        )
        self.addParameter(QgsProcessingParameterVectorDestination(self.OUTPUT, "Buffered vector"))

    def processAlgorithm(self, parameters, context, feedback):  # noqa: N802
        """Build and run the ``pyramids vector geom buffer`` command."""
        layer = self.parameterAsVectorLayer(parameters, self.INPUT, context)
        if layer is None:
            raise QgsProcessingException(self.invalidSourceError(parameters, self.INPUT))
        src = layer_source_path(layer)
        validate_input_path(src, feedback)
        out = self.parameterAsOutputLayer(parameters, self.OUTPUT, context)

        distance = self.parameterAsDouble(parameters, self.DISTANCE, context)
        resolution = self.parameterAsInt(parameters, self.RESOLUTION, context)
        cap_style = CAP_STYLE[self.parameterAsEnum(parameters, self.CAP_STYLE, context)]
        join_style = JOIN_STYLE[self.parameterAsEnum(parameters, self.JOIN_STYLE, context)]

        # '=' join keeps a negative distance from being parsed as an option rather than a value.
        argv = ["vector", "geom", "buffer", src, out, "--overwrite", f"--distance={distance}"]
        argv += ["--resolution", str(resolution)]
        argv += ["--cap-style", cap_style, "--join-style", join_style]
        layer_ref = self.parameterAsString(parameters, self.LAYER, context).strip()
        if layer_ref:
            argv += ["--layer", layer_ref]

        self.run_pyramids(argv, feedback)
        return {self.OUTPUT: out}
