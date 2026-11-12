"""Resample a raster collection onto a new time frequency — ``pyramids collection resample``.

The stack is binned to a pandas offset frequency (e.g. ``1MS``, ``7D``, ``6h``) and each window is
reduced with ``--op``. One raster is written per window, so the output is a *directory*.
"""

from __future__ import annotations

from qgis.core import (
    QgsProcessingParameterBoolean,
    QgsProcessingParameterEnum,
    QgsProcessingParameterFile,
    QgsProcessingParameterFolderDestination,
    QgsProcessingParameterNumber,
    QgsProcessingParameterString,
)

from ..base import PyramidsAlgorithm, validate_input_path

#: Per-window reduction operations accepted by ``--op``.
RESAMPLE_OPS = [
    "mean",
    "sum",
    "min",
    "max",
    "std",
    "var",
    "median",
    "quantile",
    "percentile",
    "mode",
    "trend",
    "sens_slope",
]


class CollectionResample(PyramidsAlgorithm):
    """Resample a time-stack of co-registered rasters to a new temporal frequency."""

    GROUP_LABEL = "Collection"
    GROUP_ID = "collection"

    INPUT = "INPUT"
    FREQ = "FREQ"
    OP = "OP"
    Q = "Q"
    NO_SKIPNA = "NO_SKIPNA"
    TIMES = "TIMES"
    PATTERN = "PATTERN"
    DATE_FORMAT = "DATE_FORMAT"
    OUTPUT = "OUTPUT"

    def name(self) -> str:
        """Return the stable algorithm id within the provider."""
        return "collection_resample"

    def displayName(self) -> str:  # noqa: N802
        """Return the human-readable algorithm name."""
        return "Resample raster collection (temporal)"

    def shortHelpString(self) -> str:  # noqa: N802
        """Return the help shown in the algorithm dialog."""
        return (
            "Bin a stack of co-registered rasters to a pandas offset frequency (e.g. 1MS, 7D, "
            "6h) and reduce each window with the chosen operation. One raster is written per "
            "window into the output directory, via pyramids. A filename date format is usually "
            "needed so the stack has a time axis."
        )

    def initAlgorithm(self, config=None) -> None:  # noqa: N802
        """Declare the algorithm's parameters."""
        self.addParameter(
            QgsProcessingParameterFile(
                self.INPUT,
                "Input raster collection (directory)",
                behavior=QgsProcessingParameterFile.Folder,
            )
        )
        self.addParameter(
            QgsProcessingParameterString(self.FREQ, "Frequency (pandas offset, e.g. 1MS, 7D, 6h)")
        )
        self.addParameter(
            QgsProcessingParameterEnum(self.OP, "Operation", options=RESAMPLE_OPS, defaultValue=0)
        )
        self.addParameter(
            QgsProcessingParameterNumber(
                self.Q,
                "Quantile/percentile level (for quantile/percentile op)",
                type=QgsProcessingParameterNumber.Double,
                optional=True,
            )
        )
        self.addParameter(
            QgsProcessingParameterBoolean(
                self.NO_SKIPNA, "Propagate NaN within each window", defaultValue=False
            )
        )
        self.addParameter(
            QgsProcessingParameterString(
                self.TIMES, "Timestamps, comma-separated, one per step (optional)", optional=True
            )
        )
        self.addParameter(
            QgsProcessingParameterString(
                self.PATTERN, "Per-window filename template with {i} (optional)", optional=True
            )
        )
        self.addParameter(
            QgsProcessingParameterString(
                self.DATE_FORMAT,
                "Filename date format (optional, e.g. %Y.%m.%d)",
                optional=True,
            )
        )
        self.addParameter(
            QgsProcessingParameterFolderDestination(self.OUTPUT, "Resampled collection (directory)")
        )

    def processAlgorithm(self, parameters, context, feedback):  # noqa: N802
        """Build and run the ``pyramids collection resample`` command."""
        src = self.parameterAsFile(parameters, self.INPUT, context)
        validate_input_path(src, feedback)
        out = self.parameterAsString(parameters, self.OUTPUT, context)

        freq = self.parameterAsString(parameters, self.FREQ, context).strip()
        op = RESAMPLE_OPS[self.parameterAsEnum(parameters, self.OP, context)]
        argv = ["collection", "resample", src, out, "--freq", freq, "--op", op]

        if parameters.get(self.Q) is not None:
            argv += ["--q", str(self.parameterAsDouble(parameters, self.Q, context))]
        if self.parameterAsBool(parameters, self.NO_SKIPNA, context):
            argv.append("--no-skipna")
        times = self.parameterAsString(parameters, self.TIMES, context).strip()
        if times:
            argv += ["--times", times]
        pattern = self.parameterAsString(parameters, self.PATTERN, context).strip()
        if pattern:
            argv += ["--pattern", pattern]
        date_format = self.parameterAsString(parameters, self.DATE_FORMAT, context).strip()
        if date_format:
            argv += ["--date-format", date_format]
        argv.append("--overwrite")

        self.run_pyramids(argv, feedback)
        return {self.OUTPUT: out}
