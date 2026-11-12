"""Attach a colour ramp to a raster band — wraps ``pyramids raster set-color-ramp``.

Builds a colour table spanning a value range and attaches it to a band, writing a new raster.
The ramp is defined either by two hex endpoint colours or by a named matplotlib colormap.
"""

from __future__ import annotations

from qgis.core import (
    QgsProcessingException,
    QgsProcessingParameterNumber,
    QgsProcessingParameterRasterDestination,
    QgsProcessingParameterRasterLayer,
    QgsProcessingParameterString,
)

from ..base import PyramidsAlgorithm, layer_source_path, validate_input_path


class RasterSetColorRamp(PyramidsAlgorithm):
    """Attach a colour ramp spanning a value range to a raster band."""

    INPUT = "INPUT"
    BAND = "BAND"
    START_VALUE = "START_VALUE"
    END_VALUE = "END_VALUE"
    START_COLOR = "START_COLOR"
    END_COLOR = "END_COLOR"
    COLORMAP = "COLORMAP"
    OUTPUT = "OUTPUT"

    def name(self) -> str:
        """Return the stable algorithm id within the provider."""
        return "raster_set_color_ramp"

    def displayName(self) -> str:  # noqa: N802
        """Return the human-readable algorithm name."""
        return "Set colour ramp"

    def shortHelpString(self) -> str:  # noqa: N802
        """Return the help shown in the algorithm dialog."""
        return (
            "Attach a colour ramp spanning a value range to a band, writing a new raster, via "
            "pyramids. Define the ramp by two hex endpoint colours (start/end), or by a named "
            "matplotlib colormap instead. The end value must exceed the start value."
        )

    def initAlgorithm(self, config=None) -> None:  # noqa: N802
        """Declare the algorithm's parameters."""
        self.addParameter(QgsProcessingParameterRasterLayer(self.INPUT, "Input raster"))
        self.addParameter(
            QgsProcessingParameterNumber(
                self.BAND,
                "Band to colour (1-based; default 1)",
                type=QgsProcessingParameterNumber.Integer,
                optional=True,
                minValue=1,
            )
        )
        self.addParameter(
            QgsProcessingParameterNumber(
                self.START_VALUE,
                "Ramp start value (>= 0)",
                type=QgsProcessingParameterNumber.Double,
                defaultValue=0.0,
                minValue=0.0,
            )
        )
        self.addParameter(
            QgsProcessingParameterNumber(
                self.END_VALUE,
                "Ramp end value (must exceed the start value)",
                type=QgsProcessingParameterNumber.Double,
                defaultValue=255.0,
            )
        )
        self.addParameter(
            QgsProcessingParameterString(
                self.START_COLOR, "Start colour (hex, optional)", optional=True
            )
        )
        self.addParameter(
            QgsProcessingParameterString(
                self.END_COLOR, "End colour (hex, optional)", optional=True
            )
        )
        self.addParameter(
            QgsProcessingParameterString(
                self.COLORMAP,
                "Matplotlib colormap (optional; instead of endpoint colours)",
                optional=True,
            )
        )
        self.addParameter(QgsProcessingParameterRasterDestination(self.OUTPUT, "Output raster"))

    def processAlgorithm(self, parameters, context, feedback):  # noqa: N802
        """Build and run the ``pyramids raster set-color-ramp`` command."""
        layer = self.parameterAsRasterLayer(parameters, self.INPUT, context)
        if layer is None:
            raise QgsProcessingException(self.invalidRasterError(parameters, self.INPUT))
        src = layer_source_path(layer)
        validate_input_path(src, feedback)
        out = self.parameterAsOutputLayer(parameters, self.OUTPUT, context)

        start_value = self.parameterAsDouble(parameters, self.START_VALUE, context)
        end_value = self.parameterAsDouble(parameters, self.END_VALUE, context)
        if end_value <= start_value:
            raise QgsProcessingException("The ramp end value must exceed the start value.")

        argv = [
            "raster",
            "set-color-ramp",
            src,
            out,
            "--start-value",
            str(start_value),
            "--end-value",
            str(end_value),
        ]
        if self.BAND in parameters and parameters[self.BAND] is not None:
            argv += ["--band", str(self.parameterAsInt(parameters, self.BAND, context))]
        start_color = self.parameterAsString(parameters, self.START_COLOR, context).strip()
        if start_color:
            argv += ["--start-color", start_color]
        end_color = self.parameterAsString(parameters, self.END_COLOR, context).strip()
        if end_color:
            argv += ["--end-color", end_color]
        colormap = self.parameterAsString(parameters, self.COLORMAP, context).strip()
        if colormap:
            argv += ["--colormap", colormap]
        argv.append("--overwrite")

        self.run_pyramids(argv, feedback)
        return {self.OUTPUT: out}
