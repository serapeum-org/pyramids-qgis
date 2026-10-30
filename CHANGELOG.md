# Changelog

All notable changes to this project are documented here. The format is based on
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and this project adheres to
[Semantic Versioning](https://semver.org/spec/v2.0.0.html).

This file is the single source of the plugin's changelog: `qgis-plugin-ci` injects the latest entry into
`metadata.txt` at package time, so the QGIS Plugin Manager shows it without the history being duplicated.

## [Unreleased]

## [0.1.0] - 2026-10-30

### Added

- First experimental release: a QGIS Processing provider exposing the pyramids GIS toolkit. File-in / file-out
  raster and vector algorithms (reproject/warp, clip, merge, raster calculator, assign CRS/NoData, convert,
  rasterize, polygonize, Cloud Optimized GeoTIFF), plus mesh (pyramids-mesh) and Earth-observation (pyramids-eo)
  algorithms. The raster/conversion algorithms call the `pyramids` CLI in-process; the mesh/EO algorithms call the
  library directly.
- Release automation matching the serapeum stack: an admin-only `github-release` workflow (commitizen bumps the
  version in `metadata.txt` and regenerates this changelog, then tags and publishes a GitHub Release) and a
  downstream `publish` workflow that builds the plugin zip with `qgis-plugin-ci` and attaches it, plus a
  custom-repository `plugins.xml`, to that Release.

### Changed

- `metadata.txt`: set `category=Raster` (was the invalid `Analysis`); set the Plugin Manager listing `icon` to a
  web-friendly PNG (the in-QGIS Processing provider icon still uses the SVG); and added `qgisMaximumVersion=4.99` so
  the plugin is offered in QGIS 4. The retired `supportsQt6` flag is not set — QGIS 4 no longer recognises it.

[Unreleased]: https://github.com/serapeum-org/pyramids-qgis/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/serapeum-org/pyramids-qgis/releases/tag/v0.1.0
