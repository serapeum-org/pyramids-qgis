"""Compute per-cell distance to target pixels — wraps ``pyramids raster proximity``."""

from __future__ import annotations

from qgis.core import (
    QgsProcessingException,
    QgsProcessingParameterEnum,
    QgsProcessingParameterNumber,
    QgsProcessingParameterRasterDestination,
    QgsProcessingParameterRasterLayer,
    QgsProcessingParameterString,
)

from ..base import PyramidsAlgorithm, layer_source_path, validate_input_path

#: Distance units, passed to ``--distance-units`` (order matches the pyramids CLI choices).
DISTANCE_UNITS = ["GEO", "PIXEL"]


class RasterProximity(PyramidsAlgorithm):
    """Write a raster of each cell's distance to the nearest target pixel."""

    INPUT = "INPUT"
    BAND = "BAND"
    TARGET_VALUES = "TARGET_VALUES"
    DISTANCE_UNITS = "DISTANCE_UNITS"
    MAX_DISTANCE = "MAX_DISTANCE"
    NODATA = "NODATA"
    OUTPUT = "OUTPUT"

    def name(self) -> str:
        """Return the stable algorithm id within the provider."""
        return "raster_proximity"

    def displayName(self) -> str:  # noqa: N802
        """Return the human-readable algorithm name."""
        return "Proximity (distance to targets)"

    def shortHelpString(self) -> str:  # noqa: N802
        """Return the help shown in the algorithm dialog."""
        return (
            "Write a raster whose cells hold the distance to the nearest target pixel. Targets "
            "default to every non-zero pixel, or give a space/comma-separated list of target "
            "values. Distance is measured in georeferenced units (GEO) or pixels (PIXEL), via "
            "pyramids."
        )

    def initAlgorithm(self, config=None) -> None:  # noqa: N802
        """Declare the algorithm's parameters."""
        self.addParameter(QgsProcessingParameterRasterLayer(self.INPUT, "Input raster"))
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
                self.TARGET_VALUES,
                "Target values (space/comma-separated; default: every non-zero pixel)",
                optional=True,
            )
        )
        self.addParameter(
            QgsProcessingParameterEnum(
                self.DISTANCE_UNITS, "Distance units", options=DISTANCE_UNITS, defaultValue=0
            )
        )
        self.addParameter(
            QgsProcessingParameterNumber(
                self.MAX_DISTANCE,
                "Maximum search distance (optional)",
                type=QgsProcessingParameterNumber.Double,
                optional=True,
                minValue=0.0,
            )
        )
        self.addParameter(
            QgsProcessingParameterNumber(
                self.NODATA,
                "No-data value (also fills beyond max distance; optional)",
                type=QgsProcessingParameterNumber.Double,
                optional=True,
            )
        )
        self.addParameter(QgsProcessingParameterRasterDestination(self.OUTPUT, "Proximity raster"))

    def processAlgorithm(self, parameters, context, feedback):  # noqa: N802
        """Build and run the ``pyramids raster proximity`` command."""
        layer = self.parameterAsRasterLayer(parameters, self.INPUT, context)
        if layer is None:
            raise QgsProcessingException(self.invalidRasterError(parameters, self.INPUT))
        src = layer_source_path(layer)
        validate_input_path(src, feedback)
        out = self.parameterAsOutputLayer(parameters, self.OUTPUT, context)

        units = DISTANCE_UNITS[self.parameterAsEnum(parameters, self.DISTANCE_UNITS, context)]
        argv = ["raster", "proximity", src, out, "--distance-units", units, "--overwrite"]
        if self.BAND in parameters and parameters[self.BAND] is not None:
            argv += ["--band", str(self.parameterAsInt(parameters, self.BAND, context))]

        targets = self.parameterAsString(parameters, self.TARGET_VALUES, context)
        tokens = targets.replace(",", " ").split()
        if tokens:
            argv += ["--target-values", *tokens]

        if self.MAX_DISTANCE in parameters and parameters[self.MAX_DISTANCE] is not None:
            max_distance = self.parameterAsDouble(parameters, self.MAX_DISTANCE, context)
            argv += ["--max-distance", str(max_distance)]
        if self.NODATA in parameters and parameters[self.NODATA] is not None:
            # Join with '=' so a scientific-notation negative (e.g. -3.4e+38) is not mistaken for
            # an option by argparse's negative-number heuristic.
            argv.append(f"--nodata={self.parameterAsDouble(parameters, self.NODATA, context)}")

        self.run_pyramids(argv, feedback)
        return {self.OUTPUT: out}
