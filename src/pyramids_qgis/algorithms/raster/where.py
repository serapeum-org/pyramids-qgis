"""Keep cells matching a condition, else fill — wraps ``pyramids raster where``."""

from __future__ import annotations

from qgis.core import (
    QgsProcessingException,
    QgsProcessingParameterBoolean,
    QgsProcessingParameterRasterDestination,
    QgsProcessingParameterRasterLayer,
    QgsProcessingParameterString,
)

from ..base import PyramidsAlgorithm, layer_source_path, validate_input_path


class RasterWhere(PyramidsAlgorithm):
    """Keep the cells where a condition over band A holds, filling the rest."""

    INPUT = "INPUT"
    COND = "COND"
    OTHER = "OTHER"
    DROP = "DROP"
    OUTPUT = "OUTPUT"

    def name(self) -> str:
        """Return the stable algorithm id within the provider."""
        return "raster_where"

    def displayName(self) -> str:  # noqa: N802
        """Return the human-readable algorithm name."""
        return "Where (conditional mask)"

    def shortHelpString(self) -> str:  # noqa: N802
        """Return the help shown in the algorithm dialog."""
        return (
            "Keep the cells where a condition over the input (bound to A, e.g. 'A > 5') holds, "
            "and fill the rest. Unselected cells take the 'other' value (a number, 'nan', or "
            "'none'; default: the raster's no-data value). Optionally trim the result to the "
            "selected rows/columns/bands, via pyramids."
        )

    def initAlgorithm(self, config=None) -> None:  # noqa: N802
        """Declare the algorithm's parameters."""
        self.addParameter(QgsProcessingParameterRasterLayer(self.INPUT, "Input raster"))
        self.addParameter(
            QgsProcessingParameterString(self.COND, "Condition (bound to A, e.g. 'A > 5')")
        )
        self.addParameter(
            QgsProcessingParameterString(
                self.OTHER,
                "Value for unselected cells (number, 'nan', or 'none'; optional)",
                optional=True,
            )
        )
        self.addParameter(
            QgsProcessingParameterBoolean(
                self.DROP, "Trim to the selected rows/columns/bands", defaultValue=False
            )
        )
        self.addParameter(QgsProcessingParameterRasterDestination(self.OUTPUT, "Result raster"))

    def processAlgorithm(self, parameters, context, feedback):  # noqa: N802
        """Build and run the ``pyramids raster where`` command."""
        layer = self.parameterAsRasterLayer(parameters, self.INPUT, context)
        if layer is None:
            raise QgsProcessingException(self.invalidRasterError(parameters, self.INPUT))
        src = layer_source_path(layer)
        validate_input_path(src, feedback)
        out = self.parameterAsOutputLayer(parameters, self.OUTPUT, context)

        cond = self.parameterAsString(parameters, self.COND, context).strip()
        if not cond:
            raise QgsProcessingException("A condition is required.")

        argv = ["raster", "where", src, out, "--cond", cond, "--overwrite"]
        other = self.parameterAsString(parameters, self.OTHER, context).strip()
        if other:
            # Join with '=' so a negative number value is never mistaken for an option by argparse.
            argv.append(f"--other={other}")
        if self.parameterAsBool(parameters, self.DROP, context):
            argv.append("--drop")

        self.run_pyramids(argv, feedback)
        return {self.OUTPUT: out}
