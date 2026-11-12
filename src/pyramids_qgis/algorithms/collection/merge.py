"""Mosaic a raster collection into one raster — wraps ``pyramids collection merge``.

The timesteps of the stack are flattened into a single mosaic, with overlaps resolved by the
chosen ``--method``. The output is one raster.
"""

from __future__ import annotations

from qgis.core import (
    QgsProcessingParameterEnum,
    QgsProcessingParameterExtent,
    QgsProcessingParameterFile,
    QgsProcessingParameterNumber,
    QgsProcessingParameterRasterDestination,
    QgsProcessingParameterString,
)

from ..base import PyramidsAlgorithm, crs_to_pyramids, validate_input_path

#: Overlap-resolution rules accepted by ``--method`` (default ``last``).
MERGE_METHODS = ["first", "last", "min", "max", "sum", "count", "mean"]


class CollectionMerge(PyramidsAlgorithm):
    """Merge (mosaic) the timesteps of a raster collection into one raster."""

    GROUP_LABEL = "Collection"
    GROUP_ID = "collection"

    INPUT = "INPUT"
    METHOD = "METHOD"
    NODATA = "NODATA"
    BBOX = "BBOX"
    DATE_FORMAT = "DATE_FORMAT"
    OUTPUT = "OUTPUT"

    def name(self) -> str:
        """Return the stable algorithm id within the provider."""
        return "collection_merge"

    def displayName(self) -> str:  # noqa: N802
        """Return the human-readable algorithm name."""
        return "Merge raster collection (mosaic)"

    def shortHelpString(self) -> str:  # noqa: N802
        """Return the help shown in the algorithm dialog."""
        return (
            "Flatten a stack of co-registered rasters (a directory of files) into a single "
            "mosaic, resolving overlaps with the chosen method (default: last), via pyramids."
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
            QgsProcessingParameterEnum(
                self.METHOD, "Overlap-resolution method", options=MERGE_METHODS, defaultValue=1
            )
        )
        self.addParameter(
            QgsProcessingParameterNumber(
                self.NODATA,
                "No-data value for the mosaic (optional)",
                type=QgsProcessingParameterNumber.Double,
                optional=True,
            )
        )
        self.addParameter(
            QgsProcessingParameterExtent(
                self.BBOX, "Restrict to this window (optional)", optional=True
            )
        )
        self.addParameter(
            QgsProcessingParameterString(
                self.DATE_FORMAT,
                "Filename date format (optional, e.g. %Y.%m.%d)",
                optional=True,
            )
        )
        self.addParameter(QgsProcessingParameterRasterDestination(self.OUTPUT, "Merged raster"))

    def processAlgorithm(self, parameters, context, feedback):  # noqa: N802
        """Build and run the ``pyramids collection merge`` command."""
        src = self.parameterAsFile(parameters, self.INPUT, context)
        validate_input_path(src, feedback)
        out = self.parameterAsOutputLayer(parameters, self.OUTPUT, context)

        method = MERGE_METHODS[self.parameterAsEnum(parameters, self.METHOD, context)]
        argv = ["collection", "merge", src, out, "--method", method]

        if parameters.get(self.NODATA) is not None:
            # =-join: a negative scientific-notation NoData (e.g. the float32 fill -3.4e+38) would
            # otherwise be read by argparse as an unknown option and raise SystemExit (not caught
            # by run_pyramids). Matches the sibling edit_info/pan_sharpen/proximity convention.
            argv.append(f"--nodata={self.parameterAsDouble(parameters, self.NODATA, context)}")

        extent = self.parameterAsExtent(parameters, self.BBOX, context)
        if not extent.isNull():
            argv += [
                "--bbox",
                str(extent.xMinimum()),
                str(extent.yMinimum()),
                str(extent.xMaximum()),
                str(extent.yMaximum()),
            ]
            bbox_crs = crs_to_pyramids(self.parameterAsExtentCrs(parameters, self.BBOX, context))
            if bbox_crs:
                argv += ["--bbox-crs", bbox_crs]

        date_format = self.parameterAsString(parameters, self.DATE_FORMAT, context).strip()
        if date_format:
            argv += ["--date-format", date_format]
        argv.append("--overwrite")

        self.run_pyramids(argv, feedback)
        return {self.OUTPUT: out}
