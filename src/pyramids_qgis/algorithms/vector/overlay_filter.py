"""Filter features by a spatial predicate — wraps ``pyramids vector overlay filter``."""

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

#: Spatial-predicate choices, passed to ``--predicate``.
PREDICATES = [
    "contains",
    "within",
    "intersects",
    "covers",
    "covered_by",
    "crosses",
    "disjoint",
    "overlaps",
    "touches",
    "dwithin",
]


class VectorOverlayFilter(PyramidsAlgorithm):
    """Keep only the features whose geometry relates to a mask by a chosen predicate."""

    GROUP_LABEL = "Vector"
    GROUP_ID = "vector"

    INPUT = "INPUT"
    MASK = "MASK"
    PREDICATE = "PREDICATE"
    DISTANCE = "DISTANCE"
    LAYER = "LAYER"
    OUTPUT = "OUTPUT"

    def name(self) -> str:
        """Return the stable algorithm id within the provider."""
        return "vector_overlay_filter"

    def displayName(self) -> str:  # noqa: N802
        """Return the human-readable algorithm name."""
        return "Filter by spatial predicate"

    def shortHelpString(self) -> str:  # noqa: N802
        """Return the help shown in the algorithm dialog."""
        return (
            "Filter a vector by a spatial relationship to a mask, via pyramids: only the source "
            "features that relate to the mask geometry by the chosen predicate (contains, within, "
            "intersects, ...) are kept. The 'dwithin' predicate needs a distance (in the source "
            "CRS units). For a multi-layer source, a layer name or index may be selected."
        )

    def initAlgorithm(self, config=None) -> None:  # noqa: N802
        """Declare the algorithm's parameters."""
        self.addParameter(QgsProcessingParameterVectorLayer(self.INPUT, "Input vector"))
        self.addParameter(QgsProcessingParameterVectorLayer(self.MASK, "Mask vector"))
        self.addParameter(
            QgsProcessingParameterEnum(
                self.PREDICATE, "Spatial predicate", options=PREDICATES, defaultValue=2
            )
        )
        self.addParameter(
            QgsProcessingParameterNumber(
                self.DISTANCE,
                "Distance (optional; required for 'dwithin', source CRS units)",
                type=QgsProcessingParameterNumber.Double,
                optional=True,
                minValue=0,
            )
        )
        self.addParameter(
            QgsProcessingParameterString(
                self.LAYER, "Layer name/index (optional; multi-layer sources)", optional=True
            )
        )
        self.addParameter(QgsProcessingParameterVectorDestination(self.OUTPUT, "Filtered vector"))

    def processAlgorithm(self, parameters, context, feedback):  # noqa: N802
        """Build and run the ``pyramids vector overlay filter`` command."""
        layer = self.parameterAsVectorLayer(parameters, self.INPUT, context)
        if layer is None:
            raise QgsProcessingException(self.invalidSourceError(parameters, self.INPUT))
        src = layer_source_path(layer)
        validate_input_path(src, feedback)

        mask_layer = self.parameterAsVectorLayer(parameters, self.MASK, context)
        if mask_layer is None:
            raise QgsProcessingException(self.invalidSourceError(parameters, self.MASK))
        mask = layer_source_path(mask_layer)
        validate_input_path(mask, feedback)

        out = self.parameterAsOutputLayer(parameters, self.OUTPUT, context)

        predicate = PREDICATES[self.parameterAsEnum(parameters, self.PREDICATE, context)]
        argv = ["vector", "overlay", "filter", src, out, "--predicate", predicate, "--mask", mask]
        if parameters.get(self.DISTANCE) is not None:
            argv += ["--distance", str(self.parameterAsDouble(parameters, self.DISTANCE, context))]
        argv.append("--overwrite")
        layer_ref = self.parameterAsString(parameters, self.LAYER, context).strip()
        if layer_ref:
            argv += ["--layer", layer_ref]

        self.run_pyramids(argv, feedback)
        return {self.OUTPUT: out}
