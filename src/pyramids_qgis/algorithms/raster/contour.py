"""Trace contour lines or filled bands from a raster — wraps ``pyramids raster contour``."""

from __future__ import annotations

from qgis.core import (
    QgsProcessingException,
    QgsProcessingParameterBoolean,
    QgsProcessingParameterNumber,
    QgsProcessingParameterRasterLayer,
    QgsProcessingParameterString,
    QgsProcessingParameterVectorDestination,
)

from ..base import PyramidsAlgorithm, layer_source_path, validate_input_path


class RasterContour(PyramidsAlgorithm):
    """Trace contour lines (or filled polygons between levels) from a raster band."""

    INPUT = "INPUT"
    INTERVAL = "INTERVAL"
    FIXED_LEVELS = "FIXED_LEVELS"
    BASE = "BASE"
    BAND = "BAND"
    ATTRIBUTE = "ATTRIBUTE"
    POLYGONIZE = "POLYGONIZE"
    OUTPUT = "OUTPUT"

    def name(self) -> str:
        """Return the stable algorithm id within the provider."""
        return "raster_contour"

    def displayName(self) -> str:  # noqa: N802
        """Return the human-readable algorithm name."""
        return "Contour (lines or filled bands)"

    def shortHelpString(self) -> str:  # noqa: N802
        """Return the help shown in the algorithm dialog."""
        return (
            "Trace contours from a raster band to a vector layer. Give either a spacing interval "
            "(anchored at the base level) or an explicit space/comma-separated list of levels. "
            "Optionally emit filled polygons between levels instead of lines, via pyramids."
        )

    def initAlgorithm(self, config=None) -> None:  # noqa: N802
        """Declare the algorithm's parameters."""
        self.addParameter(QgsProcessingParameterRasterLayer(self.INPUT, "Input raster"))
        self.addParameter(
            QgsProcessingParameterNumber(
                self.INTERVAL,
                "Interval between levels (optional)",
                type=QgsProcessingParameterNumber.Double,
                optional=True,
                minValue=0.0,
            )
        )
        self.addParameter(
            QgsProcessingParameterString(
                self.FIXED_LEVELS,
                "Fixed levels (space/comma-separated; optional)",
                optional=True,
            )
        )
        self.addParameter(
            QgsProcessingParameterNumber(
                self.BASE,
                "Base level the interval is anchored to (optional; default: 0)",
                type=QgsProcessingParameterNumber.Double,
                optional=True,
            )
        )
        self.addParameter(
            QgsProcessingParameterNumber(
                self.BAND,
                "Band index (0-based)",
                type=QgsProcessingParameterNumber.Integer,
                optional=True,
                minValue=0,
                defaultValue=0,
            )
        )
        self.addParameter(
            QgsProcessingParameterString(
                self.ATTRIBUTE,
                "Elevation attribute name (optional; default: elev)",
                optional=True,
            )
        )
        self.addParameter(
            QgsProcessingParameterBoolean(
                self.POLYGONIZE, "Emit filled polygons between levels", defaultValue=False
            )
        )
        self.addParameter(QgsProcessingParameterVectorDestination(self.OUTPUT, "Contours"))

    def processAlgorithm(self, parameters, context, feedback):  # noqa: N802
        """Build and run the ``pyramids raster contour`` command."""
        layer = self.parameterAsRasterLayer(parameters, self.INPUT, context)
        if layer is None:
            raise QgsProcessingException(self.invalidRasterError(parameters, self.INPUT))
        src = layer_source_path(layer)
        validate_input_path(src, feedback)
        out = self.parameterAsOutputLayer(parameters, self.OUTPUT, context)

        has_interval = self.INTERVAL in parameters and parameters[self.INTERVAL] is not None
        levels = (
            self.parameterAsString(parameters, self.FIXED_LEVELS, context).replace(",", " ").split()
        )
        if has_interval == bool(levels):
            raise QgsProcessingException(
                "Provide either an interval or a list of fixed levels (exactly one)."
            )

        argv = ["raster", "contour", src, out, "--overwrite"]
        if has_interval:
            interval = self.parameterAsDouble(parameters, self.INTERVAL, context)
            argv.append(f"--interval={interval}")
        else:
            argv += ["--fixed-levels", *levels]
        if self.BASE in parameters and parameters[self.BASE] is not None:
            # Join with '=' so a negative base is never mistaken for an option by argparse.
            argv.append(f"--base={self.parameterAsDouble(parameters, self.BASE, context)}")
        if self.BAND in parameters and parameters[self.BAND] is not None:
            argv += ["--band", str(self.parameterAsInt(parameters, self.BAND, context))]
        attribute = self.parameterAsString(parameters, self.ATTRIBUTE, context).strip()
        if attribute:
            argv += ["--attribute", attribute]
        if self.parameterAsBool(parameters, self.POLYGONIZE, context):
            argv.append("--polygonize")

        self.run_pyramids(argv, feedback)
        return {self.OUTPUT: out}
