# End-to-end testing

The unit / integration suite runs against **real PyQGIS** in CI and exercises every algorithm's
`initAlgorithm` / parameter construction. What it does **not** cover is running an algorithm
end-to-end (`processAlgorithm`) in a real QGIS session on real data, nor the GUI / dialog behaviour.
That still has to be done by hand, and it is the gate before a non-experimental release.

This page is that by-hand validation guide. Install the plugin first — see
[Installation](installation.md).

## What to run — cover both wiring paths and all four groups

The raster / conversion algorithms call the pyramids CLI in-process; the mesh / EO ones call the
library directly. Run at least one of each path:

- [ ] **Raster (CLI path):** Reproject (warp) a GeoTIFF to another CRS; confirm the output layer
      loads and looks right.
- [ ] **Raster:** Clip (by mask and by extent), Merge, Raster calculator (e.g. NDVI over two
      inputs), Assign CRS / NoData.
- [ ] **Conversion:** Rasterize a vector, Polygonize a raster (GeoJSON output), Create COG, Convert
      format.
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
- [ ] **Error surfacing** — a bad CRS / missing file should come back as a clean
      `QgsProcessingException` in the Processing log, not a raw traceback.
- [ ] **Qt5 / Qt6** — ideally smoke-test on a QGIS 3.x (Qt5) and a 4.x (Qt6) build, since the plugin
      uses the `qgis.PyQt` shim.

## Done when

- [ ] At least one algorithm per group runs successfully on real data and loads a correct output
      layer.
- [ ] The dependency-guard and error-surfacing behaviour is confirmed.
- [ ] Any bugs found are filed as their own issues (and fixed) before flipping `experimental=False`
      in `metadata.txt`.
