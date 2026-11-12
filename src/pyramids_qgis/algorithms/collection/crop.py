"""Crop a raster collection by a mask or a bbox — wraps ``pyramids collection crop``.

Every timestep is cropped to the same window and written out, so the output is a *directory*
holding one file per timestep. Provide either a mask raster (its footprint crops the stack) or a
bounding box; if both are given, the mask wins.
"""

from __future__ import annotations

from qgis.core import (
    QgsProcessingException,
    QgsProcessingParameterBoolean,
    QgsProcessingParameterExtent,
    QgsProcessingParameterFile,
    QgsProcessingParameterFolderDestination,
    QgsProcessingParameterRasterLayer,
    QgsProcessingParameterString,
)

from ..base import PyramidsAlgorithm, layer_source_path, validate_input_path


class CollectionCrop(PyramidsAlgorithm):
    """Crop every timestep of a raster collection to a mask footprint or a bounding box."""

    GROUP_LABEL = "Collection"
    GROUP_ID = "collection"

    INPUT = "INPUT"
    MASK = "MASK"
    BBOX = "BBOX"
    NO_TOUCH = "NO_TOUCH"
    DATE_FORMAT = "DATE_FORMAT"
    OUTPUT = "OUTPUT"

    def name(self) -> str:
        """Return the stable algorithm id within the provider."""
        return "collection_crop"

    def displayName(self) -> str:  # noqa: N802
        """Return the human-readable algorithm name."""
        return "Crop raster collection (by mask or bbox)"

    def shortHelpString(self) -> str:  # noqa: N802
        """Return the help shown in the algorithm dialog."""
        return (
            "Crop every timestep of a stack of co-registered rasters. Provide a mask raster "
            "whose footprint crops the stack, or a bounding box. If both are given, the mask "
            "wins. One file per timestep is written into the output directory, via pyramids."
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
            QgsProcessingParameterRasterLayer(self.MASK, "Mask raster (footprint)", optional=True)
        )
        self.addParameter(
            QgsProcessingParameterExtent(self.BBOX, "Crop bounding box", optional=True)
        )
        self.addParameter(
            QgsProcessingParameterBoolean(
                self.NO_TOUCH, "Keep only cells whose centre is inside", defaultValue=False
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
            QgsProcessingParameterFolderDestination(self.OUTPUT, "Cropped collection (directory)")
        )

    def processAlgorithm(self, parameters, context, feedback):  # noqa: N802
        """Build and run the ``pyramids collection crop`` command."""
        src = self.parameterAsFile(parameters, self.INPUT, context)
        validate_input_path(src, feedback)
        out = self.parameterAsString(parameters, self.OUTPUT, context)

        argv = ["collection", "crop", src, out]
        mask_layer = self.parameterAsRasterLayer(parameters, self.MASK, context)
        if mask_layer is not None:
            mask_path = layer_source_path(mask_layer)
            validate_input_path(mask_path, feedback)
            argv += ["--mask", mask_path]
        else:
            extent = self.parameterAsExtent(parameters, self.BBOX, context)
            if extent.isNull():
                raise QgsProcessingException("Provide either a mask raster or a crop bounding box.")
            argv += [
                "--bbox",
                str(extent.xMinimum()),
                str(extent.yMinimum()),
                str(extent.xMaximum()),
                str(extent.yMaximum()),
            ]
            crs = self.parameterAsExtentCrs(parameters, self.BBOX, context)
            auth_id = crs.authid() if crs is not None and crs.isValid() else ""
            if auth_id.upper().startswith("EPSG:"):
                argv += ["--epsg", auth_id.split(":", 1)[1]]
            elif crs is not None and crs.isValid():
                # 'collection crop' accepts only an EPSG code (--epsg), so a non-EPSG (e.g. custom
                # WKT) extent CRS cannot be forwarded; warn instead of silently cropping the wrong
                # window in the collection's own CRS.
                feedback.pushWarning(
                    "The crop extent's CRS is not an EPSG code, which 'collection crop' cannot "
                    "accept; the bounding box will be interpreted in the collection's own CRS and "
                    "may crop the wrong area. Reproject the extent to an EPSG CRS to be safe."
                )

        if self.parameterAsBool(parameters, self.NO_TOUCH, context):
            argv.append("--no-touch")
        date_format = self.parameterAsString(parameters, self.DATE_FORMAT, context).strip()
        if date_format:
            argv += ["--date-format", date_format]
        argv.append("--overwrite")

        self.run_pyramids(argv, feedback)
        return {self.OUTPUT: out}
