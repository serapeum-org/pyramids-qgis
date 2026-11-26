# pyramids-qgis

A QGIS plugin that exposes the [pyramids](https://github.com/serapeum-org/pyramids) GIS toolkit (`pyramids-core`) as a
**QGIS Processing provider**. The algorithms appear in the Processing
Toolbox under **Pyramids**, so they work in the toolbox, the graphical modeler, batch mode, the
Python `processing.run(...)` API, and the `qgis_process` command line — the same as any native QGIS
algorithm.

> Status: v0.2.1, installable from the official QGIS plugin repository. File-in / file-out algorithms that
> mirror the `pyramids` command-line interface.

## How it works

The plugin is a **thin adapter**. Each algorithm translates its QGIS parameters into a
`pyramids <command> ...` argument list and calls the pyramids CLI *in-process*
(`pyramids.cli.main`). The CLI maps 1:1 onto library calls and is pyramids' stable, documented
contract, so the plugin carries no raster logic of its own and does not drift from the library.

Work is passed by **file path**, never by in-memory GDAL objects: QGIS hands pyramids an input
path, pyramids writes an output file, and QGIS loads it as a new layer. This deliberately avoids
sharing live `gdal.Dataset` handles across two GDAL builds in one process.

## Algorithms

**92 algorithms** in ten Processing-Toolbox groups under **Pyramids**. The
[Algorithms reference](https://serapeum-org.github.io/pyramids-qgis/algorithms/) lists every one with its
Processing id and the pyramids command behind it.

| Group | Algorithms | Covers |
|---|---|---|
| Raster | 33 | warp, crop, calc, merge, edit-info, convert, rasterize, polygonize, contour, proximity, zonal stats, … |
| Vector | 36 | geometry ops, overlays (clip, union, intersection, dissolve, spatial joins), tessellation (fishnet, Voronoi, Delaunay, quadtree, H3) |
| Collection | 6 | whole-stack raster ops: align, crop, merge, reduce over time, reproject, resample |
| Fetch | 5 | WMS, WMTS, WFS, WCS, OGC API Coverages |
| NetCDF | 4 | crop, extract a variable, extract a group, select a time step |
| Earth Observation | 2 | contrast stretch, tasseled cap — needs `pyramids-eo` |
| Mesh | 2 | convert mesh format, mesh to vector — other formats need `pyramids-mesh` |
| Process | 2 | apply a processing tool, run a pipeline |
| Cloud Optimized GeoTIFF | 1 | create a validated COG |
| STAC | 1 | download STAC assets |

Note that the toolbox group is **not** the source subpackage: `conversion/`'s convert, rasterize and polygonize
appear under **Raster**, while its COG algorithm has its own group. There is no "Conversion" group.

**Two wiring paths.** 88 of the 92 are CLI-backed as described above. The Mesh and Earth-observation groups call
their library directly (`MeshDataset`, `pyramids_eo`), because neither backing package ships a CLI.

## Requirements

- **QGIS 3.40+** (through 4.99 — see `qgisMinimumVersion` in `metadata.txt`; the plugin uses the `qgis.PyQt`
  shim for Qt5/Qt6).
- **`pyramids-core` >= 0.81.0 importable from QGIS's own Python**, bound to **QGIS's GDAL**.

**You usually do not have to do this by hand.** The plugin checks on load and offers to install — or upgrade —
`pyramids-core` into the interpreter QGIS runs; accept the prompt, let it finish, then restart QGIS. 0.81.0 is the
floor because that release honours the `PYRAMIDS_MANAGE_GDAL_ENV` opt-out the plugin sets, which stops pyramids
rewriting QGIS's own global GDAL environment.

To install it yourself instead, target the interpreter QGIS runs — and **not** a platform wheel that vendors its
own GDAL (those inject a private `osgeo` and force `GDAL_DRIVER_PATH`, which conflicts with QGIS's GDAL
in-process). The plugin detects a vendored build and warns.

```bash
# Windows (OSGeo4W shell):
python -m pip install "pyramids-core>=0.81.0"

# conda-based QGIS (conda-forge names the package `pyramids`):
conda install -c conda-forge "pyramids>=0.81"

# Linux / macOS:
<qgis-python> -m pip install "pyramids-core>=0.81.0"
```

**Optional — mesh formats.** The two mesh algorithms work on UGRID NetCDF with `pyramids-core`
alone. To read or write the other mesh formats (2DM, Selafin, DFSU, XMDF, PLY, …), also install
`pyramids-mesh` into the same QGIS Python (`<qgis-python> -m pip install pyramids-mesh`); the
plugin warns when it is absent.

**Optional — Earth observation.** The EO algorithms (contrast stretch, tasseled cap) need
`pyramids-eo` in the same QGIS Python (`<qgis-python> -m pip install pyramids-eo`); they raise a
clear message when it is absent.

## Install the plugin

From inside QGIS:

1. **Plugins → Manage and Install Plugins…**
2. On the **All** tab, search for **Pyramids QGIS** and click **Install Plugin**.

For development, deploy the working tree instead: copy (or symlink) `src/pyramids_qgis/` into your QGIS profile's
plugin directory (as `pyramids_qgis`) and enable **Pyramids QGIS**. The deploy helper does this:

```bash
python scripts/deploy.py            # copy into the default profile
python scripts/deploy.py --symlink  # symlink instead (dev: edits apply live)
python scripts/deploy.py --profile myprofile
```

Default plugin directories:

- Windows: `%APPDATA%\QGIS\QGIS3\profiles\default\python\plugins`
- Linux: `~/.local/share/QGIS/QGIS3/profiles/default/python/plugins`
- macOS: `~/Library/Application Support/QGIS/QGIS3/profiles/default/python/plugins`

## Releases

Releases follow the same commitizen-driven flow as the rest of the serapeum stack, in two workflows. A maintainer
runs **`github-release`** (manual, admin-only): [commitizen](https://commitizen-tools.github.io/commitizen/) bumps
the version (in `metadata.txt`, via `pyproject.toml`'s `version_files`), regenerates
[`CHANGELOG.md`](CHANGELOG.md) from the Conventional Commits, tags `vX.Y.Z`, and publishes the GitHub Release. Its
completion triggers **`publish`**, which builds the plugin zip with
[`qgis-plugin-ci`](https://qgis.github.io/qgis-plugin-ci/) and attaches it — plus a custom-repository `plugins.xml`
— to that Release. To install a build without cloning, add the `plugins.xml` URL as a plugin repository in
*Plugins → Manage and Install Plugins → Settings*.

### Publishing to plugins.qgis.org

The `publish` workflow can also push each release to the official
[plugins.qgis.org](https://plugins.qgis.org/) repository, so users can install the plugin straight from the in-app
Plugin Manager. This is **off until a maintainer configures it** (one-time):

1. Sign in to [plugins.qgis.org](https://plugins.qgis.org/) (a GitHub, GitLab, Google, or OSGeo account works).
2. Do the **first upload by hand** at [plugins.qgis.org/plugins/add/](https://plugins.qgis.org/plugins/add/) — the
   first submission of a new plugin is staff-approved. (The API token in step 3 can only *add a version* to an
   already-existing plugin, so it cannot perform this first submission.)
3. Generate a plugins.qgis.org **API token** (your profile → API tokens) and add it as the repository secret
   **`QGIS_TOKEN`** (*Settings → Secrets and variables → Actions*).

Once `QGIS_TOKEN` exists, every release the `publish` workflow publishes is also uploaded to plugins.qgis.org via
`qgis-plugin-ci release --qgis-token`; until then that step is skipped and only the GitHub Release + `plugins.xml`
are produced. Re-running `publish` for an already-released version fails at the GitHub Release step —
`qgis-plugin-ci` does not overwrite existing release assets (and plugins.qgis.org likewise rejects re-uploading an
existing version) — so a re-run is not a recovery path; cut a new version instead.

## Repository layout

```
pyproject.toml              package metadata (pip-installable), pixi workspace, tooling config
src/pyramids_qgis/          the plugin package (this is what gets deployed)
  __init__.py               classFactory — QGIS entry point
  metadata.txt              QGIS plugin metadata (hasProcessingProvider=yes)
  plugin.py                 registers/unregisters the provider
  provider.py               QgsProcessingProvider listing the algorithms
  dependencies.py           pyramids / pyramids-mesh / pyramids-eo checks + GDAL warning
  algorithms/
    base.py                 PyramidsAlgorithm base + CLI runner + CRS/path helpers
    __init__.py             the ALGORITHMS registry
    raster/                 33 algorithms: warp, crop, calc, merge, edit-info, contour, proximity, …
    vector/                 36 algorithms: geometry ops, overlays, tessellation
    collection/             6: whole-stack (datacube) operations
    conversion/             convert, rasterize, polygonize (group Raster) + cog (its own group)
    fetch/                  5: WMS / WMTS / WFS / WCS / OGC API Coverages
    nc/                     4: NetCDF crop, extract variable/group, select time step
    process/                2: apply a processing tool, run a pipeline
    stac/                   1: download STAC assets
    mesh/                   pyramids-mesh: convert, to_vector
    eo/                     pyramids-eo: stretch, tasseled_cap
  resources/icon.png        Plugin Manager / plugins.qgis.org listing icon (metadata.txt)
  resources/icon.svg        in-QGIS Processing provider icon (provider.py)
scripts/deploy.py           copy/symlink the plugin into a QGIS profile
```

## Roadmap

- **Terrain derivatives** — slope, aspect, hillshade and sieve have no algorithm yet.
- **Vector-native outputs** — the provider pins vector destinations to GeoJSON
  (`provider.py:supportedOutputVectorLayerExtensions`), so GPKG output is not available.
- **An optional dock widget** for interactive COG preview and STAC browsing; the plugin is Processing-only today
  and adds no toolbar, menu or panel.

## License

GPL-3.0-or-later, matching pyramids. See `LICENSE`.
