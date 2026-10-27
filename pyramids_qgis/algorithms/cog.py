"""Write a raster as a Cloud Optimized GeoTIFF — wraps ``pyramids cog create``."""

from __future__ import annotations

from qgis.core import (
    QgsProcessingException,
    QgsProcessingParameterNumber,
    QgsProcessingParameterRasterDestination,
    QgsProcessingParameterRasterLayer,
    QgsProcessingParameterString,
)

from .base import PyramidsAlgorithm, layer_source_path, validate_input_path

#: COG group label, shared by future COG algorithms (validate / info).
_COG_GROUP = "Cloud Optimized GeoTIFF"
_COG_GROUP_ID = "cog"


class CreateCog(PyramidsAlgorithm):
    """Convert a raster into a validated Cloud Optimized GeoTIFF."""

    GROUP = _COG_GROUP
    GROUP_ID = _COG_GROUP_ID

    INPUT = "INPUT"
    COMPRESS = "COMPRESS"
    BLOCKSIZE = "BLOCKSIZE"
    OUTPUT = "OUTPUT"

    def name(self) -> str:
        """Return the stable algorithm id within the provider."""
        return "cog_create"

    def displayName(self) -> str:  # noqa: N802
        """Return the human-readable algorithm name."""
        return "Create Cloud Optimized GeoTIFF"

    def shortHelpString(self) -> str:  # noqa: N802
        """Return the help shown in the algorithm dialog."""
        return (
            "Write a raster as a Cloud Optimized GeoTIFF (COG) and validate it. Leave the "
            "options blank for the default profile, or set a compression method "
            "(e.g. DEFLATE, ZSTD) and an internal tile size."
        )

    def initAlgorithm(self, config=None) -> None:  # noqa: N802
        """Declare the algorithm's parameters."""
        self.addParameter(QgsProcessingParameterRasterLayer(self.INPUT, "Input raster"))
        self.addParameter(
            QgsProcessingParameterString(
                self.COMPRESS, "Compression (optional, e.g. DEFLATE, ZSTD)", optional=True
            )
        )
        self.addParameter(
            QgsProcessingParameterNumber(
                self.BLOCKSIZE,
                "Internal tile size (optional)",
                type=QgsProcessingParameterNumber.Integer,
                optional=True,
                minValue=16,
            )
        )
        self.addParameter(QgsProcessingParameterRasterDestination(self.OUTPUT, "COG output"))

    def processAlgorithm(self, parameters, context, feedback):  # noqa: N802
        """Build and run the ``pyramids cog create`` command."""
        layer = self.parameterAsRasterLayer(parameters, self.INPUT, context)
        if layer is None:
            raise QgsProcessingException(self.invalidRasterError(parameters, self.INPUT))
        src = layer_source_path(layer)
        validate_input_path(src, feedback)
        out = self.parameterAsOutputLayer(parameters, self.OUTPUT, context)

        argv = ["cog", "create", src, out, "--overwrite"]
        compress = self.parameterAsString(parameters, self.COMPRESS, context).strip()
        if compress:
            argv += ["--compress", compress]
        if self.BLOCKSIZE in parameters and parameters[self.BLOCKSIZE] is not None:
            blocksize = self.parameterAsInt(parameters, self.BLOCKSIZE, context)
            if blocksize > 0:
                argv += ["--blocksize", str(blocksize)]

        self.run_pyramids(argv, feedback)
        return {self.OUTPUT: out}
