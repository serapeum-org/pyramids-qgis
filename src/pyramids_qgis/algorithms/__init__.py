"""Algorithm registry for the Pyramids Processing provider.

Algorithms are grouped into subpackages by origin and theme, each mirroring a pyramids 0.77 CLI
command group (``pyramids <group> <command> ...``): ``raster``, ``conversion``, ``vector``,
``collection``, ``fetch``, ``nc`` (NetCDF), ``mesh`` (pyramids-mesh), ``eo`` (pyramids-eo).

Each algorithm is a thin adapter over the pyramids stack. To add one, implement a
:class:`~pyramids_qgis.algorithms.base.PyramidsAlgorithm` subclass in the right subpackage; this
registry is generated from the filesystem, so the provider picks it up with no manual wiring here.
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
from .nc.crop import NcCrop
from .nc.extract import NcExtract
from .nc.get_group import NcGetGroup
from .nc.sel import NcSel
from .raster.add_band import RasterAddBand
from .raster.align import RasterAlign
from .raster.animate import RasterAnimate
from .raster.calc import RasterCalc
from .raster.clip import ClipRaster
from .raster.cluster import RasterCluster
from .raster.combine import RasterCombine
from .raster.contour import RasterContour
from .raster.convert_units import RasterConvertUnits
from .raster.create import RasterCreate
from .raster.create_empty import RasterCreateEmpty
from .raster.dataset_like import RasterDatasetLike
from .raster.edit_info import EditRasterInfo
from .raster.empty_like import RasterEmptyLike
from .raster.extract import RasterExtract
from .raster.fillna import RasterFillna
from .raster.footprint import RasterFootprint
from .raster.match_histogram import RasterMatchHistogram
from .raster.merge import MergeRasters
from .raster.orthorectify import RasterOrthorectify
from .raster.pan_sharpen import RasterPanSharpen
from .raster.percentile_stretch import RasterPercentileStretch
from .raster.proximity import RasterProximity
from .raster.render import RasterRender
from .raster.select_bands import RasterSelectBands
from .raster.set_color_ramp import RasterSetColorRamp
from .raster.subdataset import RasterSubdataset
from .raster.warp import WarpRaster
from .raster.where import RasterWhere
from .raster.zonal_stats import RasterZonalStats
from .vector.clip import ClipVector
from .vector.convert import ConvertVector
from .vector.warp import WarpVector

#: Every algorithm class the provider registers, grouped by subpackage.
ALGORITHMS = [
    # raster
    ClipRaster,
    EditRasterInfo,
    MergeRasters,
    RasterAddBand,
    RasterAlign,
    RasterAnimate,
    RasterCalc,
    RasterCluster,
    RasterCombine,
    RasterContour,
    RasterConvertUnits,
    RasterCreate,
    RasterCreateEmpty,
    RasterDatasetLike,
    RasterEmptyLike,
    RasterExtract,
    RasterFillna,
    RasterFootprint,
    RasterMatchHistogram,
    RasterOrthorectify,
    RasterPanSharpen,
    RasterPercentileStretch,
    RasterProximity,
    RasterRender,
    RasterSelectBands,
    RasterSetColorRamp,
    RasterSubdataset,
    RasterWhere,
    RasterZonalStats,
    WarpRaster,
    # conversion
    ConvertRaster,
    CreateCog,
    Polygonize,
    Rasterize,
    # vector
    ClipVector,
    ConvertVector,
    WarpVector,
    # collection
    CollectionAlign,
    CollectionCrop,
    CollectionMerge,
    CollectionReduce,
    CollectionReproject,
    CollectionResample,
    # fetch
    FetchOgcCoverages,
    FetchWcs,
    FetchWfs,
    FetchWms,
    FetchWmts,
    # nc (NetCDF / multidim)
    NcCrop,
    NcExtract,
    NcGetGroup,
    NcSel,
    # mesh (pyramids-mesh)
    MeshConvert,
    MeshToVector,
    # eo (pyramids-eo)
    EoStretch,
    TasseledCap,
]

__all__ = ["ALGORITHMS"]
