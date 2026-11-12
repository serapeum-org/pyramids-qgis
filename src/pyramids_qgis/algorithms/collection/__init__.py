"""Raster-collection (time-stack) algorithms.

A *collection* is a stack of co-registered rasters opened as one cube and reduced, resampled,
mosaicked, reprojected, cropped, or aligned across its timesteps. Each algorithm wraps a
``pyramids collection <command>`` call. The stack input is modelled as a directory of
co-registered rasters (the CLI's default ``files`` source); the Zarr/archive openers and the
``--member-glob`` selector are intentionally not exposed here, because they need a single
archive file or an alternate opener that a folder parameter cannot represent.
"""
