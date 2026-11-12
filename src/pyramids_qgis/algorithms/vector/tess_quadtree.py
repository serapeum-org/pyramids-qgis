"""Adaptive quadtree aggregation of points — wraps ``pyramids vector tess quadtree``."""

from __future__ import annotations

from qgis.core import (
    QgsProcessingException,
    QgsProcessingParameterNumber,
    QgsProcessingParameterString,
    QgsProcessingParameterVectorDestination,
    QgsProcessingParameterVectorLayer,
)

from ..base import PyramidsAlgorithm, layer_source_path, validate_input_path


class VectorTessQuadtree(PyramidsAlgorithm):
    """Build an adaptive quadtree over a point layer and aggregate per cell."""

    GROUP_LABEL = "Vector"
    GROUP_ID = "vector"

    INPUT = "INPUT"
    COLUMN = "COLUMN"
    AGG = "AGG"
    NMAX = "NMAX"
    NMIN = "NMIN"
    CLIP = "CLIP"
    DRIVER = "DRIVER"
    LAYER = "LAYER"
    OUTPUT = "OUTPUT"

    def name(self) -> str:
        """Return the stable algorithm id within the provider."""
        return "vector_tess_quadtree"

    def displayName(self) -> str:  # noqa: N802
        """Return the human-readable algorithm name."""
        return "Quadtree aggregation"

    def shortHelpString(self) -> str:  # noqa: N802
        """Return the help shown in the algorithm dialog."""
        return (
            "Build an adaptive quadtree over a point layer, splitting a cell once it holds more "
            "than the maximum number of points, and aggregate the points per cell, via pyramids. "
            "By default each cell carries a point count; give a numeric column and a reducer to "
            "aggregate that column instead. Optionally drop sparse cells, clip to a boundary "
            "vector, and pick the output OGR driver. For a multi-layer source, a layer name or "
            "index may be selected."
        )

    def initAlgorithm(self, config=None) -> None:  # noqa: N802
        """Declare the algorithm's parameters."""
        self.addParameter(QgsProcessingParameterVectorLayer(self.INPUT, "Input vector (points)"))
        self.addParameter(
            QgsProcessingParameterString(
                self.COLUMN, "Numeric column to aggregate (optional; default count)", optional=True
            )
        )
        self.addParameter(
            QgsProcessingParameterString(
                self.AGG, "Per-cell reducer applied to the column (optional)", optional=True
            )
        )
        self.addParameter(
            QgsProcessingParameterNumber(
                self.NMAX,
                "Max points in a cell before it splits (optional)",
                type=QgsProcessingParameterNumber.Integer,
                optional=True,
                minValue=1,
            )
        )
        self.addParameter(
            QgsProcessingParameterNumber(
                self.NMIN,
                "Drop cells with fewer than this many points (optional)",
                type=QgsProcessingParameterNumber.Integer,
                optional=True,
                minValue=0,
            )
        )
        self.addParameter(
            QgsProcessingParameterVectorLayer(
                self.CLIP, "Boundary vector to clip cells to (optional)", optional=True
            )
        )
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
        self.addParameter(QgsProcessingParameterVectorDestination(self.OUTPUT, "Quadtree cells"))

    def processAlgorithm(self, parameters, context, feedback):  # noqa: N802
        """Build and run the ``pyramids vector tess quadtree`` command."""
        layer = self.parameterAsVectorLayer(parameters, self.INPUT, context)
        if layer is None:
            raise QgsProcessingException(self.invalidSourceError(parameters, self.INPUT))
        src = layer_source_path(layer)
        validate_input_path(src, feedback)
        out = self.parameterAsOutputLayer(parameters, self.OUTPUT, context)

        argv = ["vector", "tess", "quadtree", src, out, "--overwrite"]
        column = self.parameterAsString(parameters, self.COLUMN, context).strip()
        if column:
            argv += ["--column", column]
        agg = self.parameterAsString(parameters, self.AGG, context).strip()
        if agg:
            argv += ["--agg", agg]
        if self.NMAX in parameters and parameters[self.NMAX] is not None:
            argv += ["--nmax", str(self.parameterAsInt(parameters, self.NMAX, context))]
        if self.NMIN in parameters and parameters[self.NMIN] is not None:
            argv += ["--nmin", str(self.parameterAsInt(parameters, self.NMIN, context))]
        clip_layer = self.parameterAsVectorLayer(parameters, self.CLIP, context)
        if clip_layer is not None:
            clip_path = layer_source_path(clip_layer)
            validate_input_path(clip_path, feedback)
            argv += ["--clip", clip_path]
        driver = self.parameterAsString(parameters, self.DRIVER, context).strip()
        if driver:
            argv += ["--driver", driver]
        layer_ref = self.parameterAsString(parameters, self.LAYER, context).strip()
        if layer_ref:
            argv += ["--layer", layer_ref]

        self.run_pyramids(argv, feedback)
        return {self.OUTPUT: out}
