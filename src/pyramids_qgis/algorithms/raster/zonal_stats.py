"""Summarise a raster over zones to a CSV table — wraps ``pyramids raster zonal-stats``."""

from __future__ import annotations

from qgis.core import (
    QgsProcessingException,
    QgsProcessingParameterFileDestination,
    QgsProcessingParameterNumber,
    QgsProcessingParameterRasterLayer,
    QgsProcessingParameterString,
    QgsProcessingParameterVectorLayer,
)

from ..base import PyramidsAlgorithm, layer_source_path, validate_input_path


class RasterZonalStats(PyramidsAlgorithm):
    """Aggregate a raster's values within polygon zones (or a categorical class raster)."""

    INPUT = "INPUT"
    ZONES = "ZONES"
    CLASSES = "CLASSES"
    STATS = "STATS"
    BAND = "BAND"
    OUTPUT = "OUTPUT"

    def name(self) -> str:
        """Return the stable algorithm id within the provider."""
        return "raster_zonal_stats"

    def displayName(self) -> str:  # noqa: N802
        """Return the human-readable algorithm name."""
        return "Zonal statistics to CSV"

    def shortHelpString(self) -> str:  # noqa: N802
        """Return the help shown in the algorithm dialog."""
        return (
            "Aggregate a raster's values within zones to a CSV. Zones come from a polygon vector "
            "layer, or from a categorical raster whose distinct values define the zones (give one "
            "of the two). Stats are a space/comma-separated subset of: mean sum min max std var "
            "count (default: mean), via pyramids."
        )

    def initAlgorithm(self, config=None) -> None:  # noqa: N802
        """Declare the algorithm's parameters."""
        self.addParameter(QgsProcessingParameterRasterLayer(self.INPUT, "Input raster"))
        self.addParameter(
            QgsProcessingParameterVectorLayer(
                self.ZONES, "Zone polygons (optional)", optional=True
            )
        )
        self.addParameter(
            QgsProcessingParameterRasterLayer(
                self.CLASSES, "Categorical zone raster (optional)", optional=True
            )
        )
        self.addParameter(
            QgsProcessingParameterString(
                self.STATS,
                "Stats (space/comma-separated; default: mean)",
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
            QgsProcessingParameterFileDestination(
                self.OUTPUT, "Output CSV", fileFilter="CSV (*.csv)"
            )
        )

    def processAlgorithm(self, parameters, context, feedback):  # noqa: N802
        """Build and run the ``pyramids raster zonal-stats`` command."""
        layer = self.parameterAsRasterLayer(parameters, self.INPUT, context)
        if layer is None:
            raise QgsProcessingException(self.invalidRasterError(parameters, self.INPUT))
        src = layer_source_path(layer)
        validate_input_path(src, feedback)
        out = self.parameterAsFileOutput(parameters, self.OUTPUT, context)

        zones_layer = self.parameterAsVectorLayer(parameters, self.ZONES, context)
        classes_layer = self.parameterAsRasterLayer(parameters, self.CLASSES, context)
        if zones_layer is None and classes_layer is None:
            raise QgsProcessingException(
                "Provide zone polygons or a categorical zone raster to define the zones."
            )

        argv = ["raster", "zonal-stats", src]
        if zones_layer is not None:
            zones_path = layer_source_path(zones_layer)
            validate_input_path(zones_path, feedback)
            argv.append(zones_path)
        if classes_layer is not None:
            classes_path = layer_source_path(classes_layer)
            validate_input_path(classes_path, feedback)
            argv += ["--classes", classes_path]

        stats = self.parameterAsString(parameters, self.STATS, context).replace(",", " ").split()
        if stats:
            argv += ["--stats", *stats]
        if self.BAND in parameters and parameters[self.BAND] is not None:
            argv += ["--band", str(self.parameterAsInt(parameters, self.BAND, context))]
        argv += ["--output", out, "--overwrite"]

        self.run_pyramids(argv, feedback)
        return {self.OUTPUT: out}
