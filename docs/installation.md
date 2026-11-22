# Installation

Pyramids QGIS is on the official QGIS plugin repository, so you install it from inside QGIS:

1. **Plugins → Manage and Install Plugins…**
2. On the **Settings** tab, tick **"Show also experimental plugins"** (the plugin is published as experimental, so
   it is hidden otherwise).
3. On the **All** tab, search for **Pyramids QGIS** and click **Install Plugin**.

The algorithms then appear in the **Processing Toolbox** under **Pyramids** — see the [Usage tutorial](usage.md).

!!! note "The plugin installs `pyramids-core` for you"
    The algorithms call the `pyramids` library, so **`pyramids-core` 0.81.0 or newer** must be importable from the
    Python QGIS runs. The plugin checks on load and offers to install — or upgrade — it into QGIS's own interpreter:
    choose **Yes**, let it finish (QGIS is unresponsive for a few minutes, with no progress bar), then restart QGIS.
    **Not now** asks again next start; **Don't ask again** suppresses the offer.

    To do it yourself instead — or if the install fails — run `pip install 'pyramids-core>=0.81.0'` against the
    Python QGIS runs, then restart QGIS. On a conda/OSGeo4W QGIS the conda-forge package is named **`pyramids`**
    (the PyPI distribution is `pyramids-core`; both import as `pyramids`). The Earth-observation algorithms
    additionally need `pyramids-eo`.
