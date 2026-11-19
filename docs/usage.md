# Usage tutorial

Pyramids QGIS is a **Processing provider** — it adds algorithms, not a toolbar or a menu. Everything you run lives
in the **Processing Toolbox**, so the algorithms work the same way as any native QGIS tool: in the toolbox, the
graphical modeler, batch mode, and the Python `processing.run(...)` API.

This page walks through finding the algorithms and running a couple of them end to end. For the full catalogue of
what each algorithm does, see the [Algorithms reference](algorithms.md).

## Before you start

Install the plugin from the QGIS Plugin Manager (and its `pyramids-core` dependency into QGIS's Python) — see
[Installation](installation.md).

## 1. Find the algorithms

Open the toolbox with **Processing → Toolbox** (or `Ctrl+Alt+T`), then expand the **Pyramids** provider. The
algorithms are grouped by theme:

- **Raster** — reproject (warp), clip, raster calculator, merge, edit info, and more.
- **Conversion** — convert format, rasterize, polygonize, create Cloud Optimized GeoTIFF.
- **Mesh** — UGRID/mesh conversions.
- **Earth Observation** — contrast stretch, tasseled cap.

If the **Pyramids** group is not there, the plugin did not load — recheck the install and that `pyramids-core`
imports in the QGIS Python console (`import pyramids`).

## 2. Worked example — reproject a raster (warp)

1. Load a raster into QGIS (**Layer → Add Layer → Add Raster Layer…**), or just have the file path handy.
2. In the toolbox, open **Pyramids → Raster → Reproject raster (warp)**.
3. Fill the dialog:
     - **Input raster** — your layer (or *…* → choose a file).
     - **Target CRS** — the CRS to reproject into, e.g. *EPSG:3857*.
     - **Resampling method** — defaults to *nearest neighbor*; pick *bilinear* or *cubic* for continuous data.
     - **Reprojected raster** — an output path (or leave it to a temporary file).
4. Click **Run**. The algorithm writes the output file and loads it as a new layer.

That is the whole pattern: pick an input, set parameters, give an output path, **Run**. Every Pyramids algorithm
follows it.

## 3. Worked example — clip a raster

**Pyramids → Raster → Clip raster (by mask or extent)** crops a raster two ways:

- **By mask** — set **Mask layer (polygons)** to a polygon layer; the raster is cut to those polygons.
- **By extent** — leave the mask empty and set **Clip extent** (drag on the canvas, or type a bounding box). The
  extent is read in the input raster's CRS.

If you give both, the mask wins. Set an output path and **Run**.

## 4. The file-in / file-out model

Pyramids algorithms are **file-in / file-out**: QGIS hands pyramids an input *path*, pyramids writes an output
*file*, and QGIS loads that file as a new layer. They never operate on a live in-memory raster.

The practical consequence: a **scratch / memory layer must be saved to disk first**. If an input only exists in
memory (for example the output of another tool kept as a temporary layer), export it (**right-click → Export → Save
As…**) and point the algorithm at the saved file.

## 5. Beyond the toolbox

Because these are standard Processing algorithms, they also run:

- **Batch** — right-click an algorithm → **Execute as Batch Process…** to run it over many inputs at once.
- **Graphical Modeler** — drag a Pyramids algorithm into a model to chain it with other steps.
- **Python console** — call it by its provider-qualified id, `pyramids:<name>`:

    ```python
    import processing

    # Reproject to Web Mercator with bilinear resampling.
    processing.run(
        "pyramids:warp",
        {
            "INPUT": "C:/data/dem.tif",  # a file path or a loaded layer
            "CRS": "EPSG:3857",
            "RESAMPLING": 1,  # index into [nearest, bilinear, cubic, cubic_spline, lanczos, average, mode]
            "OUTPUT": "C:/data/dem_3857.tif",
        },
    )

    # Clip to a polygon mask.
    processing.run(
        "pyramids:clip",
        {
            "INPUT": "C:/data/dem.tif",
            "MASK": "C:/data/aoi.gpkg",
            "OUTPUT": "C:/data/dem_clipped.tif",
        },
    )
    ```

    The parameter keys are the UPPERCASE names shown here (`INPUT`, `CRS`, `OUTPUT`, …); `RESAMPLING` is an enum, so
    it takes the integer index of the method.

## Troubleshooting

- **"pyramids is not importable" / every algorithm fails immediately** — `pyramids-core` is not installed in the
  QGIS Python. Install it (see *Before you start*) and restart QGIS.
- **The Earth-observation algorithms fail with a dependency error** — those need **`pyramids-eo`** (a hard
  requirement for the EO group only). Install it into the QGIS interpreter.
- **A non-UGRID mesh format fails** — mesh formats beyond UGRID NetCDF need the optional **`pyramids-mesh`**; the
  plugin warns rather than hard-fails when it is absent.
- **An in-memory layer is rejected** — save it to a file first (see *The file-in / file-out model*).

## Where to go next

- [Algorithms reference](algorithms.md) — every algorithm, grouped by theme, with the pyramids command it maps to.
- [Installation](installation.md) — plugin install, the experimental-plugins toggle, and the `pyramids-core` setup.
