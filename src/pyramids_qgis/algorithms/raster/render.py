"""Render a raster band to an image — wraps ``pyramids raster render``.

Produces a plot image (PNG) of one band, not a GIS raster — the output is therefore a plain
file destination rather than a raster layer.
"""

from __future__ import annotations

from qgis.core import (
    QgsProcessingException,
    QgsProcessingParameterFileDestination,
    QgsProcessingParameterNumber,
    QgsProcessingParameterRasterLayer,
    QgsProcessingParameterString,
)

from ..base import PyramidsAlgorithm, layer_source_path, validate_input_path


class RasterRender(PyramidsAlgorithm):
    """Render a raster band to a PNG plot image."""

    INPUT = "INPUT"
    BAND = "BAND"
    TITLE = "TITLE"
    DPI = "DPI"
    OUTPUT = "OUTPUT"

    def name(self) -> str:
        """Return the stable algorithm id within the provider."""
        return "raster_render"

    def displayName(self) -> str:  # noqa: N802
        """Return the human-readable algorithm name."""
        return "Render raster to image"

    def shortHelpString(self) -> str:  # noqa: N802
        """Return the help shown in the algorithm dialog."""
        return (
            "Render a raster band to a plot image (e.g. a PNG), via pyramids. The output is a "
            "picture, not a GIS raster. Leave the band blank to auto-select; optionally set a "
            "title and the output DPI."
        )

    def initAlgorithm(self, config=None) -> None:  # noqa: N802
        """Declare the algorithm's parameters."""
        self.addParameter(QgsProcessingParameterRasterLayer(self.INPUT, "Input raster"))
        self.addParameter(
            QgsProcessingParameterNumber(
                self.BAND,
                "Band to render (optional; default: auto)",
                type=QgsProcessingParameterNumber.Integer,
                optional=True,
                minValue=1,
            )
        )
        self.addParameter(
            QgsProcessingParameterString(self.TITLE, "Plot title (optional)", optional=True)
        )
        self.addParameter(
            QgsProcessingParameterNumber(
                self.DPI,
                "Output DPI (optional; default 150)",
                type=QgsProcessingParameterNumber.Integer,
                optional=True,
                minValue=1,
            )
        )
        self.addParameter(
            QgsProcessingParameterFileDestination(
                self.OUTPUT, "Output image", fileFilter="PNG image (*.png);;All files (*.*)"
            )
        )

    def processAlgorithm(self, parameters, context, feedback):  # noqa: N802
        """Build and run the ``pyramids raster render`` command."""
        layer = self.parameterAsRasterLayer(parameters, self.INPUT, context)
        if layer is None:
            raise QgsProcessingException(self.invalidRasterError(parameters, self.INPUT))
        src = layer_source_path(layer)
        validate_input_path(src, feedback)
        out = self.parameterAsFileOutput(parameters, self.OUTPUT, context)

        argv = ["raster", "render", src, out]
        if self.BAND in parameters and parameters[self.BAND] is not None:
            argv += ["--band", str(self.parameterAsInt(parameters, self.BAND, context))]
        title = self.parameterAsString(parameters, self.TITLE, context).strip()
        if title:
            argv += ["--title", title]
        if self.DPI in parameters and parameters[self.DPI] is not None:
            argv += ["--dpi", str(self.parameterAsInt(parameters, self.DPI, context))]
        argv.append("--overwrite")

        self.run_pyramids(argv, feedback)
        return {self.OUTPUT: out}
