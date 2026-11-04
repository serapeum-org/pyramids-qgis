# Example data

Tiny, self-contained fixtures used both by the documentation / algorithm help and by the
integration tests (`tests/integration/test_example_dataset.py`), so there is one source of truth.
They are deliberately small (well under 1 KB each) and are regenerated deterministically with:

```bash
pixi run -e dev python examples/data/make_example_data.py
```

| File | What it is |
|------|------------|
| `data/dem.tif` | 32×32 Int16 "elevation" raster, EPSG:4326, 0.01° pixels, with a gradient and a `-9999` NoData corner |
| `data/aoi.geojson` | one EPSG:4326 polygon over the centre of the raster, with an integer `value` attribute |

## Try an algorithm on it

With the **Pyramids** provider enabled, in the QGIS *Python Console* (paths are relative to this
repo — use absolute paths in your own session):

```python
import processing

# Reproject the DEM to Web Mercator
processing.run(
    "pyramids:warp",
    {
        "INPUT": "examples/data/dem.tif",
        "CRS": "EPSG:3857",
        "RESAMPLING": 0,
        "OUTPUT": "dem_3857.tif",
    },
)

# Clip the DEM to the AOI polygon
processing.run(
    "pyramids:clip",
    {
        "INPUT": "examples/data/dem.tif",
        "MASK": "examples/data/aoi.geojson",
        "OUTPUT": "dem_clipped.tif",
    },
)
```

The same two files back the end-to-end tests in `tests/integration/test_example_dataset.py`, which
run every one of these through real PyQGIS + pyramids.
