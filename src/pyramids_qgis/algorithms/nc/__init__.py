"""NetCDF / multidimensional (``nc``) algorithms.

File-output operations over a multidimensional NetCDF cube: pull a sub-group out
(``get-group``), extract one variable to a GDAL raster (``extract``), select a single time
step (``sel``), and crop to a bounding box (``crop``). All wrap the ``pyramids nc`` CLI.

The read-only ``nc`` commands (``info``, ``groups``, ``list-vars``) and the nested ``nc``
sub-groups (``advanced``, ``inspect``, ``vars``, ``select``, ``calc``, ``io``, ``plot``) are
not exposed as algorithms.
"""
