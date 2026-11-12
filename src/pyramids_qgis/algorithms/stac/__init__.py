"""SpatioTemporal Asset Catalog (``stac``) algorithms.

Download assets matched by a STAC API query into an output directory (``download``). Wraps the
``pyramids stac`` CLI.

The read-only ``stac search`` command is not exposed as an algorithm — it only queries a
catalog and prints the matching items rather than producing an output.
"""
