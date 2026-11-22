# Algorithms

Every algorithm is **file-in / file-out** — work is passed by file path, never by a live in-memory
`gdal.Dataset` handle. They appear in the Processing Toolbox under **Pyramids**, split into the groups below.

Each algorithm's own help text (the right-hand pane of its dialog) is the authoritative description of its
parameters; this page is the map of what exists and what it maps to in pyramids.

The **Processing id** column is what you pass to `processing.run(...)`, e.g.
`processing.run("pyramids:raster_align", {...})`. Most algorithms are **CLI-backed**: the plugin builds a
`pyramids <command> ...` argument list and runs it in-process, so the command column is the pyramids CLI
invocation behind the algorithm. The Mesh and Earth-observation groups call their library directly instead.

There are **92 algorithms** across **10 groups**:

| Group | Algorithms |
|---|---|
| [Raster](#raster) | 33 |
| [Vector](#vector) | 36 |
| [Collection](#collection) | 6 |
| [NetCDF](#netcdf) | 4 |
| [Mesh](#mesh) | 2 |
| [Earth Observation](#earth-observation) | 2 |
| [Fetch](#fetch) | 5 |
| [STAC](#stac) | 1 |
| [Process](#process) | 2 |
| [Cloud Optimized GeoTIFF](#cloud-optimized-geotiff) | 1 |

## Raster

The largest group: the raster engine surface, plus the format-conversion algorithms (convert,
rasterize, polygonize) that have no group of their own and therefore appear here.

| Algorithm | Processing id | pyramids command |
|---|---|---|
| Add band from raster | `pyramids:raster_add_band` | `raster add-band` |
| Align raster to reference grid | `pyramids:raster_align` | `raster align` |
| Animate bands | `pyramids:raster_animate` | `raster animate` |
| Assign CRS / NoData (edit info) | `pyramids:edit_info` | `raster convert` + `raster edit-info` |
| Clip raster (by mask or extent) | `pyramids:clip` | `raster crop` |
| Cluster (label value range) | `pyramids:raster_cluster` | `raster cluster` |
| Combine rasters (element-wise) | `pyramids:raster_combine` | `raster combine` |
| Contour (lines or filled bands) | `pyramids:raster_contour` | `raster contour` |
| Convert raster format | `pyramids:convert` | `raster convert` |
| Convert units | `pyramids:raster_convert_units` | `raster convert-units` |
| Create empty raster | `pyramids:raster_create_empty` | `raster create-empty` |
| Create empty raster like template | `pyramids:raster_empty_like` | `raster empty-like` |
| Create raster | `pyramids:raster_create` | `raster create` |
| Extract subdataset | `pyramids:raster_subdataset` | `raster subdataset` |
| Extract values to CSV | `pyramids:raster_extract` | `raster extract` |
| Fill no-data gaps (constant) | `pyramids:raster_fillna` | `raster fillna` |
| Match histogram to reference | `pyramids:raster_match_histogram` | `raster match-histogram` |
| Merge rasters (mosaic) | `pyramids:merge` | `raster merge` |
| Orthorectify (RPC) | `pyramids:raster_orthorectify` | `raster orthorectify` |
| Pan-sharpen | `pyramids:raster_pan_sharpen` | `raster pan-sharpen` |
| Percentile stretch | `pyramids:raster_percentile_stretch` | `raster percentile-stretch` |
| Polygonize raster (one feature per cell) | `pyramids:polygonize` | `raster shapes` |
| Proximity (distance to targets) | `pyramids:raster_proximity` | `raster proximity` |
| Raster calculator | `pyramids:calc` | `raster calc` |
| Raster footprint (data coverage) | `pyramids:raster_footprint` | `raster footprint` |
| Rasterize (vector to raster) | `pyramids:rasterize` | `raster rasterize` |
| Render raster to image | `pyramids:raster_render` | `raster render` |
| Reproject raster (warp) | `pyramids:warp` | `raster warp` |
| Select bands | `pyramids:raster_select_bands` | `raster select-bands` |
| Set colour ramp | `pyramids:raster_set_color_ramp` | `raster set-color-ramp` |
| Where (conditional mask) | `pyramids:raster_where` | `raster where` |
| Write array like template | `pyramids:raster_dataset_like` | `raster dataset-like` |
| Zonal statistics to CSV | `pyramids:raster_zonal_stats` | `raster zonal-stats` |

## Vector

Vector geometry, overlay and tessellation operations. All CLI-backed via `pyramids vector ...`.

| Algorithm | Processing id | pyramids command |
|---|---|---|
| Buffer vector geometries | `pyramids:vector_geom_buffer` | `vector geom buffer` |
| Clip by rectangle (overlay) | `pyramids:vector_overlay_clip_by_rect` | `vector overlay clip-by-rect` |
| Clip vector (by mask or extent) | `pyramids:vector_clip` | `vector clip` |
| Concave hull of vector geometries | `pyramids:vector_geom_concave_hull` | `vector geom concave-hull` |
| Constrained Delaunay triangles | `pyramids:vector_tess_constrained_delaunay_triangles` | `vector tess constrained-delaunay-triangles` |
| Convert vector format | `pyramids:vector_convert` | `vector convert` |
| Delaunay triangles | `pyramids:vector_tess_delaunay_triangles` | `vector tess delaunay-triangles` |
| Difference (overlay) | `pyramids:vector_overlay_difference` | `vector overlay difference` |
| Dissolve | `pyramids:vector_overlay_dissolve` | `vector overlay dissolve` |
| Explode (multi-part to single-part) | `pyramids:vector_overlay_explode` | `vector overlay explode` |
| Filter by spatial predicate | `pyramids:vector_overlay_filter` | `vector overlay filter` |
| Fishnet grid | `pyramids:vector_tess_fishnet` | `vector tess fishnet` |
| Get coordinates (to CSV) | `pyramids:vector_tess_get_coordinates` | `vector tess get-coordinates` |
| H3 bin (aggregate) | `pyramids:vector_tess_h3_bin` | `vector tess h3-bin` |
| Interpolate to raster (IDW) | `pyramids:vector_tess_interpolate_to_raster` | `vector tess interpolate-to-raster` |
| Intersection (all, self-overlay) | `pyramids:vector_overlay_intersection_all` | `vector overlay intersection-all` |
| Intersection (overlay) | `pyramids:vector_overlay_intersection` | `vector overlay intersection` |
| Make vector geometries valid | `pyramids:vector_geom_make_valid` | `vector geom make-valid` |
| Minimum bounding circle of vector geometries | `pyramids:vector_geom_minimum_bounding_circle` | `vector geom minimum-bounding-circle` |
| Overlay (general) | `pyramids:vector_overlay_overlay` | `vector overlay apply` |
| Polygonize lines | `pyramids:vector_tess_polygonize` | `vector tess polygonize` |
| Quadtree aggregation | `pyramids:vector_tess_quadtree` | `vector tess quadtree` |
| Reproject vector (warp) | `pyramids:vector_warp` | `vector warp` |
| Rotate vector geometries | `pyramids:vector_geom_rotate` | `vector geom rotate` |
| Sample points | `pyramids:vector_tess_sample_points` | `vector tess sample-points` |
| Scale vector geometries | `pyramids:vector_geom_scale` | `vector geom scale` |
| Simplify vector geometries | `pyramids:vector_geom_simplify` | `vector geom simplify` |
| Spatial join | `pyramids:vector_overlay_sjoin` | `vector overlay sjoin` |
| Spatial join (nearest) | `pyramids:vector_overlay_sjoin_nearest` | `vector overlay sjoin-nearest` |
| Symmetric difference (overlay) | `pyramids:vector_overlay_symmetric_difference` | `vector overlay symmetric-difference` |
| To H3 cells | `pyramids:vector_tess_to_h3` | `vector tess to-h3` |
| Translate vector geometries | `pyramids:vector_geom_translate` | `vector geom translate` |
| Union (all, dissolve to one) | `pyramids:vector_overlay_union_all` | `vector overlay union-all` |
| Union (overlay) | `pyramids:vector_overlay_union` | `vector overlay union` |
| Voronoi diagram | `pyramids:vector_tess_voronoi` | `vector tess voronoi` |
| Voronoi polygons | `pyramids:vector_tess_voronoi_polygons` | `vector tess voronoi-polygons` |

## Collection

Operations over a *stack* of rasters (a datacube / time series) rather than a single file.

| Algorithm | Processing id | pyramids command |
|---|---|---|
| Align raster collection (to reference grid) | `pyramids:collection_align` | `collection align` |
| Crop raster collection (by mask or bbox) | `pyramids:collection_crop` | `collection crop` |
| Merge raster collection (mosaic) | `pyramids:collection_merge` | `collection merge` |
| Reduce raster collection (over time) | `pyramids:collection_reduce` | `collection reduce` |
| Reproject raster collection | `pyramids:collection_reproject` | `collection reproject` |
| Resample raster collection (temporal) | `pyramids:collection_resample` | `collection resample` |

## NetCDF

Reach into a NetCDF file: crop it, pull a variable or group out, or select a time step.

| Algorithm | Processing id | pyramids command |
|---|---|---|
| Crop NetCDF (by bounding box) | `pyramids:nc_crop` | `nc crop` |
| Extract NetCDF group | `pyramids:nc_get_group` | `nc get-group` |
| Extract NetCDF variable to raster | `pyramids:nc_extract` | `nc extract` |
| Select NetCDF time step | `pyramids:nc_sel` | `nc sel` |

## Mesh

These wrap pyramids' `MeshDataset` directly rather than the CLI, since pyramids-mesh has no CLI.
UGRID NetCDF is built in; other formats (2DM, Selafin, DFSU, XMDF, PLY, …) need
[pyramids-mesh](https://github.com/serapeum-org/pyramids-mesh) installed.

| Algorithm | Processing id | pyramids API |
|---|---|---|
| Convert mesh format | `pyramids:mesh_convert` | `MeshDataset.read_file` / `to_file` |
| Mesh to vector | `pyramids:mesh_to_vector` | `MeshDataset.to_geodataframe` → `FeatureCollection.to_file` |

## Earth Observation

These wrap [pyramids-eo](https://github.com/serapeum-org/pyramids-eo) directly, since it has no
CLI. They require `pyramids-eo` to be installed — it is a hard requirement for this group only.

| Algorithm | Processing id | pyramids API |
|---|---|---|
| Contrast stretch (EO) | `pyramids:eo_stretch` | `pyramids_eo.enhance.stretch` |
| Tasseled cap transform | `pyramids:tasseled_cap` | `pyramids_eo.spectral.tasseled_cap` |

## Fetch

Pull a window (or features) from a remote OGC service straight to a local file.

| Algorithm | Processing id | pyramids command |
|---|---|---|
| Fetch OGC API Coverages window | `pyramids:fetch_ogc_coverages` | `fetch ogc-coverages` |
| Fetch WCS window | `pyramids:fetch_wcs` | `fetch wcs` |
| Fetch WFS features | `pyramids:fetch_wfs` | `fetch wfs` |
| Fetch WMS window | `pyramids:fetch_wms` | `fetch wms` |
| Fetch WMTS window | `pyramids:fetch_wmts` | `fetch wmts` |

## STAC

Search a STAC catalogue and download the matching assets.

| Algorithm | Processing id | pyramids command |
|---|---|---|
| Download STAC assets | `pyramids:stac_download` | `stac download` |

## Process

Drive pyramids' own processing registry: apply a single tool, or run a whole pipeline.

| Algorithm | Processing id | pyramids command |
|---|---|---|
| Apply processing tool | `pyramids:process_apply` | `process apply` |
| Run processing pipeline | `pyramids:process_run` | `process run` |

## Cloud Optimized GeoTIFF

A single algorithm, in its own toolbox group.

| Algorithm | Processing id | pyramids command |
|---|---|---|
| Create Cloud Optimized GeoTIFF | `pyramids:cog_create` | `raster cog create` |

## Example data

The repo ships a tiny, self-contained dataset under
[`examples/data/`](https://github.com/serapeum-org/pyramids-qgis/tree/main/examples/data) to try the
algorithms on: a 32×32 EPSG:4326 DEM (`dem.tif`) and a polygon AOI (`aoi.geojson`). See
[`examples/README.md`](https://github.com/serapeum-org/pyramids-qgis/blob/main/examples/README.md) for
copy-paste `processing.run(...)` snippets.

## Not covered yet

- **Terrain derivatives** — slope, aspect and hillshade have no algorithm yet.
- **An interactive dock widget** for COG preview / STAC browsing. The plugin is deliberately
  Processing-only today: it registers a provider and adds no toolbar, menu or panel.
