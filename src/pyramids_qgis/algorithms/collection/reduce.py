"""Collapse a raster collection over time — wraps ``pyramids collection reduce``."""

from __future__ import annotations

from qgis.core import (
    QgsProcessingParameterEnum,
    QgsProcessingParameterFile,
    QgsProcessingParameterRasterDestination,
    QgsProcessingParameterString,
)

from ..base import PyramidsAlgorithm, validate_input_path

#: Time-reduction functions accepted by ``--reduce``.
REDUCE_OPS = ["mean", "sum", "min", "max", "std", "var"]


class CollectionReduce(PyramidsAlgorithm):
    """Reduce a time-stack of co-registered rasters to a single raster."""

    GROUP_LABEL = "Collection"
    GROUP_ID = "collection"

    INPUT = "INPUT"
    REDUCE = "REDUCE"
    DATE_FORMAT = "DATE_FORMAT"
    OUTPUT = "OUTPUT"

    def name(self) -> str:
        """Return the stable algorithm id within the provider."""
        return "collection_reduce"

    def displayName(self) -> str:  # noqa: N802  (QGIS-mandated method name)
        """Return the human-readable algorithm name."""
        return "Reduce raster collection (over time)"

    def shortHelpString(self) -> str:  # noqa: N802  (QGIS-mandated method name)
        """Return the help shown in the algorithm dialog."""
        return (
            "Collapse a stack of co-registered rasters (a directory of files) along time into "
            "one raster using a reduction such as mean, sum, min, max, std or var, via pyramids."
        )

    def initAlgorithm(self, config=None) -> None:  # noqa: N802  (QGIS-mandated name)
        """Declare the algorithm's parameters."""
        self.addParameter(
            QgsProcessingParameterFile(
                self.INPUT,
                "Input raster collection (directory)",
                behavior=QgsProcessingParameterFile.Folder,
            )
        )
        self.addParameter(
            QgsProcessingParameterEnum(
                self.REDUCE, "Reduction", options=REDUCE_OPS, defaultValue=0
            )
        )
        self.addParameter(
            QgsProcessingParameterString(
                self.DATE_FORMAT,
                "Filename date format (optional, e.g. %Y.%m.%d)",
                optional=True,
            )
        )
        self.addParameter(QgsProcessingParameterRasterDestination(self.OUTPUT, "Reduced raster"))

    def processAlgorithm(self, parameters, context, feedback):  # noqa: N802
        """Build and run the ``pyramids collection reduce`` command."""
        src = self.parameterAsFile(parameters, self.INPUT, context)
        validate_input_path(src, feedback)
        out = self.parameterAsOutputLayer(parameters, self.OUTPUT, context)

        reduce_op = REDUCE_OPS[self.parameterAsEnum(parameters, self.REDUCE, context)]
        argv = ["collection", "reduce", src, out, "--reduce", reduce_op]

        date_format = self.parameterAsString(parameters, self.DATE_FORMAT, context).strip()
        if date_format:
            argv += ["--date-format", date_format]
        argv.append("--overwrite")

        self.run_pyramids(argv, feedback)
        return {self.OUTPUT: out}
