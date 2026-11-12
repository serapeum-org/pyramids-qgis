"""Write a NumPy array into a template's grid — wraps ``pyramids raster dataset-like``.

Stores a ``.npy`` array as a raster, borrowing a template raster's georeference. The array
must match the template's shape; it is supplied as a file path, not a raster layer.
"""

from __future__ import annotations

from qgis.core import (
    QgsProcessingException,
    QgsProcessingParameterFile,
    QgsProcessingParameterRasterDestination,
    QgsProcessingParameterRasterLayer,
)

from ..base import PyramidsAlgorithm, layer_source_path, validate_input_path


class RasterDatasetLike(PyramidsAlgorithm):
    """Write a NumPy ``.npy`` array as a raster using a template raster's georeference."""

    TEMPLATE = "TEMPLATE"
    ARRAY = "ARRAY"
    OUTPUT = "OUTPUT"

    def name(self) -> str:
        """Return the stable algorithm id within the provider."""
        return "raster_dataset_like"

    def displayName(self) -> str:  # noqa: N802
        """Return the human-readable algorithm name."""
        return "Write array like template"

    def shortHelpString(self) -> str:  # noqa: N802
        """Return the help shown in the algorithm dialog."""
        return (
            "Write a NumPy '.npy' array to a raster, copying a template raster's georeference, "
            "via pyramids. The array's shape must match the template's."
        )

    def initAlgorithm(self, config=None) -> None:  # noqa: N802
        """Declare the algorithm's parameters."""
        self.addParameter(QgsProcessingParameterRasterLayer(self.TEMPLATE, "Template raster"))
        self.addParameter(
            QgsProcessingParameterFile(self.ARRAY, "NumPy array (.npy)", extension="npy")
        )
        self.addParameter(QgsProcessingParameterRasterDestination(self.OUTPUT, "Output raster"))

    def processAlgorithm(self, parameters, context, feedback):  # noqa: N802
        """Build and run the ``pyramids raster dataset-like`` command."""
        template = self.parameterAsRasterLayer(parameters, self.TEMPLATE, context)
        if template is None:
            raise QgsProcessingException(self.invalidRasterError(parameters, self.TEMPLATE))
        src = layer_source_path(template)
        validate_input_path(src, feedback)

        array = self.parameterAsFile(parameters, self.ARRAY, context)
        if not array:
            raise QgsProcessingException("A NumPy '.npy' array file is required.")
        validate_input_path(array, feedback)
        out = self.parameterAsOutputLayer(parameters, self.OUTPUT, context)

        self.run_pyramids(["raster", "dataset-like", src, array, out, "--overwrite"], feedback)
        return {self.OUTPUT: out}
