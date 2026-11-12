"""Algorithm registry for the Pyramids Processing provider.

Algorithms are grouped into subpackages by origin and theme, each mirroring a pyramids 0.77 CLI
command group (``pyramids <group> <command> ...``):

- ``raster`` — single-raster operations (reproject, clip/crop, merge, calc, …).
- ``conversion`` — format / representation conversion (convert, rasterize, polygonize, COG).
- ``vector`` — vector (FeatureCollection) operations.
- ``collection`` — temporal raster-stack operations.
- ``fetch`` — fetch a window from an OGC web service (WMS/WCS/WMTS/OGC-Coverages/WFS).
- ``mesh`` — pyramids-mesh-backed mesh algorithms.
- ``eo`` — pyramids-eo-backed Earth-observation algorithms.

Each algorithm is a thin adapter over the pyramids stack. To add one, implement a
:class:`~pyramids_qgis.algorithms.base.PyramidsAlgorithm` subclass in the right subpackage and
append it to :data:`ALGORITHMS` — the provider picks it up with no further wiring.
"""

from __future__ import annotations

from .collection.align import CollectionAlign
from .collection.crop import CollectionCrop
from .collection.merge import CollectionMerge
from .collection.reduce import CollectionReduce
from .collection.reproject import CollectionReproject
from .collection.resample import CollectionResample
from .conversion.cog import CreateCog
from .conversion.convert import ConvertRaster
from .conversion.polygonize import Polygonize
from .conversion.rasterize import Rasterize
from .eo.stretch import EoStretch
from .eo.tasseled_cap import TasseledCap
from .fetch.ogc_coverages import FetchOgcCoverages
from .fetch.wcs import FetchWcs
from .fetch.wfs import FetchWfs
from .fetch.wms import FetchWms
from .fetch.wmts import FetchWmts
from .mesh.convert import MeshConvert
from .mesh.to_vector import MeshToVector
from .raster.calc import RasterCalc
from .raster.clip import ClipRaster
from .raster.edit_info import EditRasterInfo
from .raster.merge import MergeRasters
from .raster.warp import WarpRaster
from .vector.clip import ClipVector
from .vector.convert import ConvertVector
from .vector.warp import WarpVector

#: Every algorithm class the provider registers, grouped by subpackage.
ALGORITHMS = [
    # raster
    WarpRaster,
    ClipRaster,
    MergeRasters,
    RasterCalc,
    EditRasterInfo,
    # conversion
    ConvertRaster,
    Rasterize,
    Polygonize,
    CreateCog,
    # vector
    ConvertVector,
    WarpVector,
    ClipVector,
    # collection
    CollectionReduce,
    CollectionResample,
    CollectionMerge,
    CollectionReproject,
    CollectionCrop,
    CollectionAlign,
    # fetch
    FetchWms,
    FetchWcs,
    FetchWmts,
    FetchOgcCoverages,
    FetchWfs,
    # mesh (pyramids-mesh)
    MeshConvert,
    MeshToVector,
    # eo (pyramids-eo)
    EoStretch,
    TasseledCap,
]

__all__ = ["ALGORITHMS"]
