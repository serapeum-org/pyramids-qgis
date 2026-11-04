# Algorithms

Every algorithm is **file-in / file-out** — work is passed by file path, never by a live in-memory
`gdal.Dataset` handle. They are grouped in the Processing Toolbox under **Pyramids**, by origin and
theme.

## Raster

Most raster algorithms are **CLI-backed**: the plugin builds a `pyramids <command> ...` argument list
and runs it in-process.

| Algorithm | pyramids command | Notes |
|---|---|---|
| Reproject raster (warp) | `warp` | target CRS + resampling |
| Clip raster | `clip` | by polygon mask or extent |
| Assign CRS / NoData (edit info) | `edit-info` | stamp CRS / nodata, no reprojection |
| Merge rasters (mosaic) | `merge` | two or more inputs |
| Raster calculator | `calc` | expression over A, B, C … (safe AST) |

## Conversion

Also **CLI-backed**.

| Algorithm | pyramids command | Notes |
|---|---|---|
| Convert raster format | `convert` | driver from extension or explicit |
| Rasterize (vector → raster) | `rasterize` | cell size or template grid |
| Polygonize raster | `shapes` | one feature per cell, GeoJSON out |
| Create Cloud Optimized GeoTIFF | `cog create` | validated COG |

## Mesh

These wrap pyramids' `UgridDataset` (with [pyramids-mesh](https://github.com/serapeum-org/pyramids-mesh)
providing the format drivers) rather than the CLI, since pyramids-mesh has no CLI. UGRID NetCDF is
built in; other formats (2DM, Selafin, DFSU, XMDF, PLY, …) need `pyramids-mesh` installed.

| Algorithm | pyramids API | Notes |
|---|---|---|
| Convert mesh format | `UgridDataset.read_file` / `to_file` | any format → UGRID NetCDF or a driver |
| Mesh to vector | `UgridDataset.to_geodataframe` | faces / nodes / edges → GeoJSON |

## Earth observation

These wrap [pyramids-eo](https://github.com/serapeum-org/pyramids-eo) (the EO tier on top of pyramids)
directly, since it has no CLI. They need `pyramids-eo` installed.

| Algorithm | pyramids-eo API | Notes |
|---|---|---|
| Contrast stretch (EO) | `enhance.stretch` | linear / crude / cira / histogram + gamma, to dtype |
| Tasseled cap transform | `spectral.tasseled_cap` | Landsat 5/7/8 reflectance → brightness / greenness / wetness |

## Example data

The repo ships a tiny, self-contained dataset under
[`examples/data/`](https://github.com/serapeum-org/pyramids-qgis/tree/main/examples/data) to try the
algorithms on: a 32×32 EPSG:4326 DEM (`dem.tif`) and a polygon AOI (`aoi.geojson`). The same two files
back the end-to-end tests in `tests/integration/test_example_dataset.py`. See
[`examples/README.md`](https://github.com/serapeum-org/pyramids-qgis/blob/main/examples/README.md) for
copy-paste `processing.run(...)` snippets.

## Roadmap

More of the pyramids surface is planned:

- Auto-generate algorithms from pyramids' `processing/schema.py` registry (slope, aspect, hillshade,
  resample, sieve, fill, voronoi, quadtree, H3 …).
- Vector-native outputs (GPKG) and multi-band / NetCDF subdataset handling.
- STAC search / download and datacube temporal reductions.
- An optional dock widget for interactive COG preview and STAC browsing.
