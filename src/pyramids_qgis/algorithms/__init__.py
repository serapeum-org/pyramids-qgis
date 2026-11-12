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
from .vector.geom_buffer import VectorGeomBuffer
from .vector.geom_concave_hull import VectorGeomConcaveHull
from .vector.geom_make_valid import VectorGeomMakeValid
from .vector.geom_minimum_bounding_circle import VectorGeomMinimumBoundingCircle
from .vector.geom_rotate import VectorGeomRotate
from .vector.geom_scale import VectorGeomScale
from .vector.geom_simplify import VectorGeomSimplify
from .vector.geom_translate import VectorGeomTranslate
from .vector.overlay_clip_by_rect import VectorOverlayClipByRect
from .vector.overlay_difference import VectorOverlayDifference
from .vector.overlay_dissolve import VectorOverlayDissolve
from .vector.overlay_explode import VectorOverlayExplode
from .vector.overlay_filter import VectorOverlayFilter
from .vector.overlay_intersection import VectorOverlayIntersection
from .vector.overlay_intersection_all import VectorOverlayIntersectionAll
from .vector.overlay_overlay import VectorOverlayOverlay
from .vector.overlay_sjoin import VectorOverlaySjoin
from .vector.overlay_sjoin_nearest import VectorOverlaySjoinNearest
from .vector.overlay_symmetric_difference import VectorOverlaySymmetricDifference
from .vector.overlay_union import VectorOverlayUnion
from .vector.overlay_union_all import VectorOverlayUnionAll
from .vector.tess_constrained_delaunay_triangles import VectorTessConstrainedDelaunayTriangles
from .vector.tess_delaunay_triangles import VectorTessDelaunayTriangles
from .vector.tess_fishnet import VectorTessFishnet
from .vector.tess_get_coordinates import VectorTessGetCoordinates
from .vector.tess_h3_bin import VectorTessH3Bin
from .vector.tess_interpolate_to_raster import VectorTessInterpolateToRaster
from .vector.tess_polygonize import VectorTessPolygonize
from .vector.tess_quadtree import VectorTessQuadtree
from .vector.tess_sample_points import VectorTessSamplePoints
from .vector.tess_to_h3 import VectorTessToH3
from .vector.tess_voronoi import VectorTessVoronoi
from .vector.tess_voronoi_polygons import VectorTessVoronoiPolygons
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
    VectorGeomBuffer,
    VectorGeomConcaveHull,
    VectorGeomMakeValid,
    VectorGeomMinimumBoundingCircle,
    VectorGeomRotate,
    VectorGeomScale,
    VectorGeomSimplify,
    VectorGeomTranslate,
    VectorOverlayClipByRect,
    VectorOverlayDifference,
    VectorOverlayDissolve,
    VectorOverlayExplode,
    VectorOverlayFilter,
    VectorOverlayIntersection,
    VectorOverlayIntersectionAll,
    VectorOverlayOverlay,
    VectorOverlaySjoin,
    VectorOverlaySjoinNearest,
    VectorOverlaySymmetricDifference,
    VectorOverlayUnion,
    VectorOverlayUnionAll,
    VectorTessConstrainedDelaunayTriangles,
    VectorTessDelaunayTriangles,
    VectorTessFishnet,
    VectorTessGetCoordinates,
    VectorTessH3Bin,
    VectorTessInterpolateToRaster,
    VectorTessPolygonize,
    VectorTessQuadtree,
    VectorTessSamplePoints,
    VectorTessToH3,
    VectorTessVoronoi,
    VectorTessVoronoiPolygons,
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
