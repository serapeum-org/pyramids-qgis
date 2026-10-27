# pyramids-qgis

A QGIS plugin that exposes the [pyramids](https://github.com/serapeum-org/pyramids) GIS toolkit (`pyramids-core`) as a
**QGIS Processing provider**. The algorithms appear in the Processing
Toolbox under **Pyramids**, so they work in the toolbox, the graphical modeler, batch mode, and
the Python `processing.run(...)` API — the same as any native QGIS algorithm.

> Status: **experimental**, v0.1.0. First release ships file-in / file-out raster & vector
> algorithms that mirror the `pyramids` command-line interface.

## How it works

The plugin is a **thin adapter**. Each algorithm translates its QGIS parameters into a
`pyramids <command> ...` argument list and calls the pyramids CLI *in-process*
(`pyramids.cli.main`). The CLI maps 1:1 onto library calls and is pyramids' stable, documented
contract, so the plugin carries no raster logic of its own and does not drift from the library.

Work is passed by **file path**, never by in-memory GDAL objects: QGIS hands pyramids an input
path, pyramids writes an output file, and QGIS loads it as a new layer. This deliberately avoids
sharing live `gdal.Dataset` handles across two GDAL builds in one process.

## Algorithms in v0.1.0

| Algorithm                      | pyramids command | Notes                                |
|--------------------------------|------------------|--------------------------------------|
| Reproject raster (warp)        | `warp`           | target CRS + resampling              |
| Clip raster                    | `clip`           | by polygon mask or extent            |
| Merge rasters (mosaic)         | `merge`          | two or more inputs                   |
| Raster calculator              | `calc`           | expression over A, B, C … (safe AST) |
| Convert raster format          | `convert`        | driver from extension or explicit    |
| Rasterize (vector → raster)    | `rasterize`      | cell size or template grid           |
| Polygonize raster              | `shapes`         | one feature per cell, GeoJSON out    |
| Create Cloud Optimized GeoTIFF | `cog create`     | validated COG                        |

### Mesh algorithms

These wrap pyramids' `UgridDataset` (with [pyramids-mesh](https://github.com/serapeum-org/pyramids-mesh)
providing the format drivers) rather than the CLI, since pyramids-mesh has no CLI. UGRID NetCDF is
built in; other formats (2DM, Selafin, DFSU, XMDF, PLY, …) need pyramids-mesh installed.

| Algorithm           | pyramids API                      | Notes                                   |
|---------------------|-----------------------------------|-----------------------------------------|
| Convert mesh format | `UgridDataset.read_file/to_file`  | any format → UGRID NetCDF or a driver   |
| Mesh to vector      | `UgridDataset.to_geodataframe`    | faces/nodes/edges → GeoJSON             |

### Earth-observation algorithms

These wrap [pyramids-eo](https://github.com/serapeum-org/pyramids-eo) (the EO tier on top of
pyramids) directly, since it has no CLI. They need `pyramids-eo` installed.

| Algorithm             | pyramids-eo API         | Notes                                        |
|-----------------------|-------------------------|----------------------------------------------|
| Contrast stretch (EO) | `enhance.stretch`       | linear/crude/cira/histogram + gamma, to dtype |
| Tasseled cap transform| `spectral.tasseled_cap` | Landsat 5/7/8 reflectance → brightness/greenness/wetness |

More of the pyramids surface (terrain: slope/aspect/hillshade; sieve/fill/proximity; vector
H3 / voronoi / quadtree; STAC; datacube reductions) is planned — see **Roadmap**.

## Requirements

- **QGIS 3.22+** (works through 4.x; the plugin uses the `qgis.PyQt` shim for Qt5/Qt6).
- **`pyramids-core` importable from QGIS's own Python**, bound to **QGIS's GDAL**.

Install pyramids into the interpreter QGIS runs — **not** a platform wheel that vendors its own
GDAL (those inject a private `osgeo` and force `GDAL_DRIVER_PATH`, which conflicts with QGIS's
GDAL in-process). The plugin detects a vendored build and warns.

```bash
# Windows (OSGeo4W shell):
python -m pip install pyramids-core

# conda-based QGIS:
conda install -c conda-forge pyramids-core

# Linux / macOS:
<qgis-python> -m pip install pyramids-core
```

**Optional — mesh formats.** The two mesh algorithms work on UGRID NetCDF with `pyramids-core`
alone. To read or write the other mesh formats (2DM, Selafin, DFSU, XMDF, PLY, …), also install
`pyramids-mesh` into the same QGIS Python (`<qgis-python> -m pip install pyramids-mesh`); the
plugin warns when it is absent.

**Optional — Earth observation.** The EO algorithms (contrast stretch, tasseled cap) need
`pyramids-eo` in the same QGIS Python (`<qgis-python> -m pip install pyramids-eo`); they raise a
clear message when it is absent.

## Install the plugin

Copy (or symlink) the `pyramids_qgis/` folder into your QGIS profile's plugin directory, then
enable **Pyramids** in *Plugins → Manage and Install Plugins*. The deploy helper does this:

```bash
python scripts/deploy.py            # copy into the default profile
python scripts/deploy.py --symlink  # symlink instead (dev: edits apply live)
python scripts/deploy.py --profile myprofile
```

Default plugin directories:

- Windows: `%APPDATA%\QGIS\QGIS3\profiles\default\python\plugins`
- Linux: `~/.local/share/QGIS/QGIS3/profiles/default/python/plugins`
- macOS: `~/Library/Application Support/QGIS/QGIS3/profiles/default/python/plugins`

## Repository layout

```
pyramids_qgis/              the plugin package (this is what gets deployed)
  __init__.py               classFactory — QGIS entry point
  metadata.txt              QGIS plugin metadata (hasProcessingProvider=yes)
  plugin.py                 registers/unregisters the provider
  provider.py               QgsProcessingProvider listing the algorithms
  dependencies.py           pyramids / pyramids-mesh / pyramids-eo checks + GDAL warning
  algorithms/
    base.py                 PyramidsAlgorithm base + CLI runner + CRS/path helpers
    __init__.py             the ALGORITHMS registry
    raster/                 reproject, clip, merge, calc
    conversion/             convert, rasterize, polygonize, cog
    mesh/                   pyramids-mesh: convert, to_vector
    eo/                     pyramids-eo: stretch, tasseled_cap
  resources/icon.svg
scripts/deploy.py           copy/symlink the plugin into a QGIS profile
```

## Roadmap

- Auto-generate algorithms from pyramids' `processing/schema.py` registry (slope, aspect,
  hillshade, resample, sieve, fill, voronoi, quadtree, H3 …).
- Vector-native outputs (GPKG) and multi-band / NetCDF subdataset handling.
- STAC search/download and datacube temporal reductions.
- An optional dock widget for interactive COG preview and STAC browsing.

## License

GPL-3.0-or-later, matching pyramids. See `LICENSE`.
