"""Fuse a multispectral raster with a panchromatic band — wraps ``pyramids raster pan-sharpen``."""

from __future__ import annotations

from qgis.core import (
    QgsProcessingException,
    QgsProcessingParameterNumber,
    QgsProcessingParameterRasterDestination,
    QgsProcessingParameterRasterLayer,
    QgsProcessingParameterString,
)

from ..base import PyramidsAlgorithm, layer_source_path, validate_input_path


class RasterPanSharpen(PyramidsAlgorithm):
    """Sharpen a coarse multispectral raster with a fine panchromatic band."""

    MULTISPECTRAL = "MULTISPECTRAL"
    PAN = "PAN"
    ALGORITHM = "ALGORITHM"
    WEIGHTS = "WEIGHTS"
    RESAMPLING = "RESAMPLING"
    BANDS = "BANDS"
    NODATA = "NODATA"
    OUTPUT = "OUTPUT"

    def name(self) -> str:
        """Return the stable algorithm id within the provider."""
        return "raster_pan_sharpen"

    def displayName(self) -> str:  # noqa: N802
        """Return the human-readable algorithm name."""
        return "Pan-sharpen"

    def shortHelpString(self) -> str:  # noqa: N802
        """Return the help shown in the algorithm dialog."""
        return (
            "Fuse a coarse multispectral raster with a fine single-band panchromatic raster to "
            "produce a sharpened multispectral output (default: Brovey). Weights and bands take "
            "space/comma-separated lists, via pyramids."
        )

    def initAlgorithm(self, config=None) -> None:  # noqa: N802
        """Declare the algorithm's parameters."""
        self.addParameter(
            QgsProcessingParameterRasterLayer(self.MULTISPECTRAL, "Multispectral raster")
        )
        self.addParameter(
            QgsProcessingParameterRasterLayer(self.PAN, "Panchromatic raster (single band)")
        )
        self.addParameter(
            QgsProcessingParameterString(
                self.ALGORITHM, "Algorithm (optional; default: brovey)", optional=True
            )
        )
        self.addParameter(
            QgsProcessingParameterString(
                self.WEIGHTS,
                "Per-band Brovey weights (space/comma-separated; optional)",
                optional=True,
            )
        )
        self.addParameter(
            QgsProcessingParameterString(
                self.RESAMPLING,
                "Spectral upsampling (optional; e.g. bilinear, cubic)",
                optional=True,
            )
        )
        self.addParameter(
            QgsProcessingParameterString(
                self.BANDS,
                "Multispectral bands to sharpen (0-based, space/comma-separated; optional)",
                optional=True,
            )
        )
        self.addParameter(
            QgsProcessingParameterNumber(
                self.NODATA,
                "No-data value set on the output (optional)",
                type=QgsProcessingParameterNumber.Double,
                optional=True,
            )
        )
        self.addParameter(QgsProcessingParameterRasterDestination(self.OUTPUT, "Sharpened raster"))

    def processAlgorithm(self, parameters, context, feedback):  # noqa: N802
        """Build and run the ``pyramids raster pan-sharpen`` command."""
        ms_layer = self.parameterAsRasterLayer(parameters, self.MULTISPECTRAL, context)
        if ms_layer is None:
            raise QgsProcessingException(self.invalidRasterError(parameters, self.MULTISPECTRAL))
        ms = layer_source_path(ms_layer)
        validate_input_path(ms, feedback)

        pan_layer = self.parameterAsRasterLayer(parameters, self.PAN, context)
        if pan_layer is None:
            raise QgsProcessingException(self.invalidRasterError(parameters, self.PAN))
        pan = layer_source_path(pan_layer)
        validate_input_path(pan, feedback)
        out = self.parameterAsOutputLayer(parameters, self.OUTPUT, context)

        argv = ["raster", "pan-sharpen", ms, pan, out, "--overwrite"]
        algorithm = self.parameterAsString(parameters, self.ALGORITHM, context).strip()
        if algorithm:
            argv += ["--algorithm", algorithm]
        weights_raw = self.parameterAsString(parameters, self.WEIGHTS, context)
        weights = weights_raw.replace(",", " ").split()
        if weights:
            argv += ["--weights", *weights]
        resampling = self.parameterAsString(parameters, self.RESAMPLING, context).strip()
        if resampling:
            argv += ["--resampling", resampling]
        bands = self.parameterAsString(parameters, self.BANDS, context).replace(",", " ").split()
        if bands:
            argv += ["--bands", *bands]
        if self.NODATA in parameters and parameters[self.NODATA] is not None:
            # Join with '=' so a scientific-notation negative is not mistaken for an option.
            argv.append(f"--nodata={self.parameterAsDouble(parameters, self.NODATA, context)}")

        self.run_pyramids(argv, feedback)
        return {self.OUTPUT: out}
