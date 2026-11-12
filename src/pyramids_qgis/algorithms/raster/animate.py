"""Animate a multiband raster to a file — wraps ``pyramids raster animate``."""

from __future__ import annotations

from qgis.core import (
    QgsProcessingException,
    QgsProcessingParameterFileDestination,
    QgsProcessingParameterNumber,
    QgsProcessingParameterRasterLayer,
    QgsProcessingParameterString,
)

from ..base import PyramidsAlgorithm, layer_source_path, validate_input_path


class RasterAnimate(PyramidsAlgorithm):
    """Render a multiband raster's bands as frames of an animation file (e.g. GIF)."""

    INPUT = "INPUT"
    BANDS = "BANDS"
    INTERVAL = "INTERVAL"
    DPI = "DPI"
    OUTPUT = "OUTPUT"

    def name(self) -> str:
        """Return the stable algorithm id within the provider."""
        return "raster_animate"

    def displayName(self) -> str:  # noqa: N802
        """Return the human-readable algorithm name."""
        return "Animate bands"

    def shortHelpString(self) -> str:  # noqa: N802
        """Return the help shown in the algorithm dialog."""
        return (
            "Render a multiband raster's bands as the frames of an animation (e.g. a GIF). By "
            "default every band (>= 2) is animated in order; give a space/comma-separated list of "
            "band indices to choose and order them, via pyramids."
        )

    def initAlgorithm(self, config=None) -> None:  # noqa: N802
        """Declare the algorithm's parameters."""
        self.addParameter(QgsProcessingParameterRasterLayer(self.INPUT, "Input raster"))
        self.addParameter(
            QgsProcessingParameterString(
                self.BANDS,
                "Band indices to animate (0-based, space/comma-separated; optional)",
                optional=True,
            )
        )
        self.addParameter(
            QgsProcessingParameterNumber(
                self.INTERVAL,
                "Milliseconds between frames (optional)",
                type=QgsProcessingParameterNumber.Double,
                optional=True,
                minValue=0.0,
            )
        )
        self.addParameter(
            QgsProcessingParameterNumber(
                self.DPI,
                "Output DPI (optional; default: 100)",
                type=QgsProcessingParameterNumber.Integer,
                optional=True,
                minValue=1,
            )
        )
        self.addParameter(
            QgsProcessingParameterFileDestination(
                self.OUTPUT, "Output animation", fileFilter="GIF (*.gif);;MP4 (*.mp4)"
            )
        )

    def processAlgorithm(self, parameters, context, feedback):  # noqa: N802
        """Build and run the ``pyramids raster animate`` command."""
        layer = self.parameterAsRasterLayer(parameters, self.INPUT, context)
        if layer is None:
            raise QgsProcessingException(self.invalidRasterError(parameters, self.INPUT))
        src = layer_source_path(layer)
        validate_input_path(src, feedback)
        out = self.parameterAsFileOutput(parameters, self.OUTPUT, context)

        argv = ["raster", "animate", src, out, "--overwrite"]
        bands = self.parameterAsString(parameters, self.BANDS, context).replace(",", " ").split()
        if bands:
            argv += ["--bands", *bands]
        if self.INTERVAL in parameters and parameters[self.INTERVAL] is not None:
            argv += ["--interval", str(self.parameterAsDouble(parameters, self.INTERVAL, context))]
        if self.DPI in parameters and parameters[self.DPI] is not None:
            argv += ["--dpi", str(self.parameterAsInt(parameters, self.DPI, context))]

        self.run_pyramids(argv, feedback)
        return {self.OUTPUT: out}
