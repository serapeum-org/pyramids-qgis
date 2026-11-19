# Installation

Pyramids QGIS is on the official QGIS plugin repository, so you install it from inside QGIS:

1. **Plugins → Manage and Install Plugins…**
2. On the **Settings** tab, tick **"Show also experimental plugins"** (the plugin is published as experimental, so
   it is hidden otherwise).
3. On the **All** tab, search for **Pyramids QGIS** and click **Install Plugin**.

The algorithms then appear in the **Processing Toolbox** under **Pyramids** — see the [Usage tutorial](usage.md).

!!! note "If every algorithm errors right after installing"
    The plugin calls the `pyramids` library, so **`pyramids-core` must be importable from the Python QGIS runs**.
    If it is missing, the plugin loads but each algorithm fails with a dependency error. Install it into QGIS's own
    interpreter — `conda install -c conda-forge pyramids` (conda/OSGeo4W QGIS) or `pip install pyramids-core` — and
    restart QGIS. The Earth-observation algorithms additionally need `pyramids-eo`.
