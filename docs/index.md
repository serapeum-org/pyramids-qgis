# Pyramids QGIS

A QGIS plugin that exposes the [pyramids](https://github.com/serapeum-org/pyramids) GIS toolkit
(`pyramids-core`) as a **QGIS Processing provider**. The algorithms appear in the Processing Toolbox
under **Pyramids**, so they work in the toolbox, the graphical modeler, batch mode, and the Python
`processing.run(...)` API — the same as any native QGIS algorithm.

!!! warning "Status: experimental"
    First release ships file-in / file-out raster, conversion, mesh, and Earth-observation
    algorithms. The raster and conversion algorithms mirror the `pyramids` command-line interface;
    the mesh and EO algorithms call their backing libraries directly (see *How it works* below). The
    plugin is marked `experimental=True` in its metadata.

## How it works

The plugin is a **thin adapter** that carries no GIS logic of its own. There are two ways an
algorithm reaches pyramids:

- **CLI-backed** (most raster + all conversion algorithms). Each algorithm translates its QGIS
  parameters into a `pyramids <command> ...` argument list and calls the pyramids CLI *in-process*
  (`pyramids.cli.main`). The CLI maps 1:1 onto library calls and is pyramids' stable, documented
  contract, so the plugin never re-implements raster logic and never drifts from the library.
- **Library-direct** (mesh + Earth-observation algorithms). Those backing packages have no CLI, so
  the algorithm imports and calls the library directly — `UgridDataset` for mesh, `pyramids_eo` for
  EO.

Work is passed by **file path**, never by in-memory GDAL objects: QGIS hands pyramids an input path,
pyramids writes an output file, and QGIS loads it as a new layer. This deliberately avoids sharing
live `gdal.Dataset` handles across two GDAL builds in one process.

## The dependency tiers

Three backing packages, three tiers of strictness, all checked in the plugin's `dependencies.py`:

| Package | Requirement | Needed for |
|---|---|---|
| `pyramids-core` | **always required** (hard error if missing) | every algorithm |
| `pyramids-eo` | **required for the EO algorithms only** (hard error) | contrast stretch, tasseled cap |
| `pyramids-mesh` | **optional even for the mesh algorithms** (soft warning) | mesh formats other than UGRID NetCDF |

The critical constraint is that `pyramids-core` must be importable from **the interpreter QGIS runs**
and bound to **QGIS's own GDAL** — not a platform wheel that vendors its own GDAL. See
[Installation](installation.md).

## Where to go next

- **[Installation](installation.md)** — install the backing libraries into QGIS's Python and deploy
  the plugin into a QGIS profile.
- **[End-to-end testing](testing.md)** — the by-hand validation guide: what to run, what to watch
  for, and when the plugin is done.
- **[Algorithms](algorithms.md)** — the full list of algorithms the provider ships, grouped by
  raster, conversion, mesh, and Earth observation.
