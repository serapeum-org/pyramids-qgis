# Changelog

All notable changes to this project are documented here. The format is based on
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and this project adheres to
[Semantic Versioning](https://semver.org/spec/v2.0.0.html).

This file is the single source of the plugin's changelog: `qgis-plugin-ci` injects the latest entry into
`metadata.txt` at package time, so the QGIS Plugin Manager shows it without the history being duplicated.

## [Unreleased]

### Changed

- `metadata.txt`: set `category=Raster` (was the invalid `Analysis`), switched the plugin icon to a web-friendly
  PNG, and declared `supportsQt6=True` so QGIS 4 (Qt6) offers the plugin.

### Added

- Packaging and release automation with `qgis-plugin-ci`: a tag-triggered workflow builds the plugin zip and
  publishes it (plus a custom-repository `plugins.xml`) as a GitHub Release asset.

## [0.1.0]

### Added

- First experimental release: a QGIS Processing provider exposing the pyramids GIS toolkit. File-in / file-out
  raster and vector algorithms (reproject/warp, clip, merge, raster calculator, assign CRS/NoData, convert,
  rasterize, polygonize, Cloud Optimized GeoTIFF), plus mesh (pyramids-mesh) and Earth-observation (pyramids-eo)
  algorithms. The raster/conversion algorithms call the `pyramids` CLI in-process; the mesh/EO algorithms call the
  library directly.

[Unreleased]: https://github.com/serapeum-org/pyramids-qgis/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/serapeum-org/pyramids-qgis/releases/tag/v0.1.0
