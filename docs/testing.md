# End-to-end testing

The unit / integration suite runs against **real PyQGIS** in CI and exercises every algorithm's
`initAlgorithm` / parameter construction, and — since the `gui` tests landed — the `pyramids-core`
install dialog itself, clicked offscreen. What it does **not** cover is running an algorithm
end-to-end (`processAlgorithm`) in a real QGIS session on real data, nor *when* the install offer
appears relative to the main window. That still has to be done by hand, and it is the gate before a
non-experimental release.

This page is that by-hand validation guide. Install the plugin first — see
[Installation](installation.md).

## What to run — cover both wiring paths and every group

88 of the 92 algorithms call the pyramids CLI in-process; only the Mesh and Earth-observation groups call their
library directly. Run at least one of each path, and at least one per group:

- [ ] **Raster (CLI path):** Reproject (warp) a GeoTIFF to another CRS; confirm the output layer
      loads and looks right.
- [ ] **Raster:** Clip (by mask and by extent), Merge, Raster calculator (e.g. NDVI over two
      inputs), Assign CRS / NoData — and the format-conversion ones that also live in this group:
      Rasterize a vector, Polygonize a raster (GeoJSON output), Convert format.
- [ ] **Cloud Optimized GeoTIFF:** Create COG, and confirm the result validates as a COG.
- [ ] **Vector:** one of each kind — a geometry op (buffer / simplify), an overlay (clip or
      intersection), and a tessellation (fishnet or Voronoi).
- [ ] **Collection:** one whole-stack operation (align or reduce over time) on a small stack.
- [ ] **NetCDF:** extract a variable to raster, and select a time step.
- [ ] **Fetch:** pull a small window from a public WMS or WFS (needs network).
- [ ] **STAC:** download an asset from a public catalogue (needs network).
- [ ] **Process:** apply a processing tool, and run a short pipeline.
- [ ] **Mesh (library path):** Convert a `.2dm` / Selafin mesh to UGRID NetCDF, and Mesh → vector
      (needs `pyramids-mesh`).
- [ ] **EO (library path):** Contrast stretch, and Tasseled cap on a Landsat reflectance stack
      (needs `pyramids-eo`).

## What to watch for — things CI cannot catch

- [ ] **PyQGIS parameter wiring** — each algorithm's `parameterAs*` calls, enum / attribute names,
      and the dialog rendering. (`initAlgorithm` / parameter construction is covered automatically by
      the real-QGIS integration tests; the dialog rendering and actual execution are not.)
- [ ] **Forced-GeoJSON output** — the provider pins vector outputs to `.geojson`; confirm Polygonize
      / Mesh → vector produce loadable GeoJSON and the extension matches the content.
- [ ] **Dependency guards** — with `pyramids-mesh` / `pyramids-eo` absent, the mesh / EO algorithms
      should raise a clear "install ..." message; the vendored-GDAL warning should appear only for a
      vendored build.
- [ ] **The `pyramids-core` install offer — startup ordering only.** The dialog itself is now
      automated: `pytest -m gui` clicks the real `QMessageBox` offscreen and covers all three
      buttons, the per-state decline, upgrade-vs-fresh-install and all three outcome dialogs, so
      none of that needs checking by hand. What no test can reach yet is the *ordering*: with
      `pyramids-core` absent (and again with a version below 0.81.0), starting QGIS should show the
      offer **after** the main window appears, not block startup. That is the only part to verify
      here; see issue #46 (tier B) for automating it.
- [ ] **Error surfacing** — a bad CRS / missing file should come back as a clean
      `QgsProcessingException` in the Processing log, not a raw traceback.
- [ ] **Headless (`qgis_process`)** — enable it in that profile first
      (`qgis_process plugins enable pyramids_qgis`), or it reports no algorithms for the ordinary
      reason that it is switched off. Then `qgis_process plugins` must list `* pyramids_qgis` (the `*`
      means it loaded as a Processing provider) and `qgis_process list` must show the `pyramids:`
      algorithms; then run one to an output file. This path is separate from the GUI: QGIS starts
      the plugin through `initProcessing` rather than `initGui`, so a missing hook shows up here and
      nowhere else.
- [ ] **Qt5 / Qt6** — ideally smoke-test on a QGIS 3.x (Qt5) and a 4.x (Qt6) build, since the plugin
      uses the `qgis.PyQt` shim.

## Done when

- [ ] At least one algorithm per group runs successfully on real data and loads a correct output
      layer.
- [ ] The dependency-guard and error-surfacing behaviour is confirmed.
- [ ] Any bugs found are filed as their own issues (and fixed) before flipping `experimental=False`
      in `metadata.txt`.
