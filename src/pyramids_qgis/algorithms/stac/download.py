"""Download assets from a STAC search — wraps ``pyramids stac download``.

A STAC API query (collections, bounding box, time range) can match many items each carrying
several assets, so the fetched files are written into an output *directory* rather than a
single raster.
"""

from __future__ import annotations

from qgis.core import (
    QgsCoordinateReferenceSystem,
    QgsProcessingException,
    QgsProcessingParameterExtent,
    QgsProcessingParameterFolderDestination,
    QgsProcessingParameterNumber,
    QgsProcessingParameterString,
)

from ..base import PyramidsAlgorithm


class StacDownload(PyramidsAlgorithm):
    """Download the assets matched by a STAC API search into a directory."""

    GROUP_LABEL = "STAC"
    GROUP_ID = "stac"

    URL = "URL"
    COLLECTIONS = "COLLECTIONS"
    BBOX = "BBOX"
    DATETIME = "DATETIME"
    ASSETS = "ASSETS"
    MAX_ITEMS = "MAX_ITEMS"
    OUTPUT = "OUTPUT"

    def name(self) -> str:
        """Return the stable algorithm id within the provider."""
        return "stac_download"

    def displayName(self) -> str:  # noqa: N802
        """Return the human-readable algorithm name."""
        return "Download STAC assets"

    def shortHelpString(self) -> str:  # noqa: N802
        """Return the help shown in the algorithm dialog."""
        return (
            "Query a STAC API and download the matched assets into the output directory. Give "
            "the API root URL and one or more collection ids; optionally narrow by bounding box "
            "(interpreted as lon/lat), time range, asset keys, and a maximum item count. "
            "Collections and asset keys are space/comma-separated, via pyramids."
        )

    def initAlgorithm(self, config=None) -> None:  # noqa: N802
        """Declare the algorithm's parameters."""
        self.addParameter(QgsProcessingParameterString(self.URL, "STAC API root URL"))
        self.addParameter(
            QgsProcessingParameterString(
                self.COLLECTIONS, "Collection id(s) (space/comma-separated)"
            )
        )
        self.addParameter(
            QgsProcessingParameterExtent(self.BBOX, "Bounding box (optional)", optional=True)
        )
        self.addParameter(
            QgsProcessingParameterString(
                self.DATETIME,
                "Datetime (optional; RFC3339 instant or range)",
                optional=True,
            )
        )
        self.addParameter(
            QgsProcessingParameterString(
                self.ASSETS,
                "Asset keys (optional; space/comma-separated; default: all)",
                optional=True,
            )
        )
        self.addParameter(
            QgsProcessingParameterNumber(
                self.MAX_ITEMS,
                "Maximum item count (optional)",
                type=QgsProcessingParameterNumber.Integer,
                optional=True,
                minValue=1,
            )
        )
        self.addParameter(
            QgsProcessingParameterFolderDestination(self.OUTPUT, "Output (directory)")
        )

    def processAlgorithm(self, parameters, context, feedback):  # noqa: N802
        """Build and run the ``pyramids stac download`` command."""
        url = self.parameterAsString(parameters, self.URL, context).strip()
        if not url:
            raise QgsProcessingException("A STAC API root URL is required.")

        collections = (
            self.parameterAsString(parameters, self.COLLECTIONS, context).replace(",", " ").split()
        )
        if not collections:
            raise QgsProcessingException("At least one collection id is required.")
        out = self.parameterAsString(parameters, self.OUTPUT, context)

        argv = ["stac", "download", url, "--collections", *collections, "--out", out]

        extent = self.parameterAsExtent(
            parameters, self.BBOX, context, QgsCoordinateReferenceSystem("EPSG:4326")
        )
        if not extent.isNull():
            argv += [
                "--bbox",
                str(extent.xMinimum()),
                str(extent.yMinimum()),
                str(extent.xMaximum()),
                str(extent.yMaximum()),
            ]

        datetime = self.parameterAsString(parameters, self.DATETIME, context).strip()
        if datetime:
            argv += ["--datetime", datetime]

        assets = self.parameterAsString(parameters, self.ASSETS, context).replace(",", " ").split()
        if assets:
            argv += ["--assets", *assets]

        if self.MAX_ITEMS in parameters and parameters[self.MAX_ITEMS] is not None:
            argv += ["--max-items", str(self.parameterAsInt(parameters, self.MAX_ITEMS, context))]

        self.run_pyramids(argv, feedback)
        return {self.OUTPUT: out}
