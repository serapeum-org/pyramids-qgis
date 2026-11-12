"""Fetch-a-window algorithms for OGC web services.

Each algorithm requests a single window from a remote OGC service and writes it to a file:
the raster services (WMS, WCS, WMTS, OGC API - Coverages) produce a raster, and WFS produces
a vector. They take a service URL plus a layer/coverage id and a bounding box rather than a
local input layer. All wrap the ``pyramids fetch`` CLI.
"""
