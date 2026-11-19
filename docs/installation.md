# Installation

Pyramids QGIS is published on the official QGIS plugin repository, so **most users install it from inside QGIS**
with the Plugin Manager — no cloning, no scripts. Whichever way you install the plugin, you also need its backing
library **`pyramids-core`** available in the Python that QGIS runs.

## Requirements

- **QGIS 3.22+** (works through 4.x; the plugin uses the `qgis.PyQt` shim for Qt5/Qt6).
- **`pyramids-core` importable from QGIS's own Python**, bound to **QGIS's GDAL** (see
  [Install the backing library](#install-the-backing-library-required)).

## Install from the QGIS Plugin Manager (recommended)

1. In QGIS, open **Plugins → Manage and Install Plugins…**
2. Go to the **Settings** tab and tick **"Show also experimental plugins"** — the plugin is currently published as
   *experimental*, so it is hidden otherwise. (Click **Reload Repository** if it was just published.)
3. Go to the **All** tab, search for **Pyramids**, select **Pyramids QGIS**, and click **Install Plugin** (the
   button may read *Install Experimental Plugin*).

That's it — the plugin is installed and enabled. It is a **Processing-only** plugin, so it adds no toolbar or menu:
its algorithms appear in the **Processing Toolbox** under **Pyramids**. See the [Usage tutorial](usage.md) for how
to run them.

!!! note "Install by URL (alternative channel)"
    Each GitHub release also ships a custom-repository feed. In *Plugins → Manage and Install Plugins → Settings →
    Add…* you can add the `plugins.xml` from a release
    (`https://github.com/serapeum-org/pyramids-qgis/releases/latest/download/plugins.xml`) and install from there
    without using plugins.qgis.org.

## Install the backing library (required)

The plugin carries **no GIS logic of its own** — it calls `pyramids`. So `pyramids-core` must be importable from
the interpreter QGIS runs, bound to **QGIS's GDAL**. Without it the plugin still loads, but every algorithm fails
immediately with a clear dependency error.

!!! danger "Do not use a vendored-GDAL wheel inside QGIS"
    Install pyramids into the interpreter QGIS runs — **not** a platform wheel that vendors its own GDAL. Those
    inject a private `osgeo` and force `GDAL_DRIVER_PATH` at import, which conflicts with QGIS's GDAL in-process.
    The plugin detects a vendored build and warns at runtime.

=== "conda-based QGIS"

    Activate the environment QGIS runs in. Install the core library from conda-forge (named `pyramids`, **not**
    `pyramids-core`); add the optional backends with pip in the same env:

    ```bash
    conda install -c conda-forge pyramids
    python -m pip install pyramids-mesh pyramids-eo   # optional: mesh / EO algorithms
    ```

=== "Windows (OSGeo4W)"

    Open the *OSGeo4W Shell*, then:

    ```bash
    python -m pip install pyramids-core pyramids-mesh pyramids-eo
    ```

=== "Linux / macOS (system QGIS)"

    Use the interpreter QGIS runs. Find it via *Plugins → Python Console*:
    `import sys; print(sys.executable)`, then:

    ```bash
    <qgis-python> -m pip install pyramids-core pyramids-mesh pyramids-eo
    ```

!!! note "User site vs. admin install"
    If you cannot write to the QGIS/OSGeo4W Python (a system or admin install), add `--user` so pip installs into
    your per-user site, which QGIS's interpreter still imports from. Avoid mixing a `--user` pyramids with a system
    one — keep a single copy on the path QGIS uses.

### What each backend unlocks

| Backend | Install | Enables |
|---|---|---|
| `pyramids-core` | required | all raster / conversion algorithms; mesh on UGRID NetCDF |
| `pyramids-mesh` | optional | the other mesh formats (2DM, Selafin, DFSU, XMDF, PLY, …) |
| `pyramids-eo` | optional | the Earth-observation algorithms (contrast stretch, tasseled cap) |

## Verify

Restart QGIS if needed, then open **Processing → Toolbox** (`Ctrl+Alt+T`) and expand **Pyramids**. If the group is
there, you are ready — head to the [Usage tutorial](usage.md).

If **Pyramids** does not appear, open *Plugins → Python Console* and run `import pyramids`. An `ImportError` means
`pyramids-core` is not installed in QGIS's own Python — fix that (above) and restart QGIS.

## Install from source (for development)

If you are developing the plugin rather than using a release, QGIS discovers plugins in its profile's
`python/plugins/` directory (by folder name + `metadata.txt`), not from site-packages — so you deploy the plugin
**package** (`src/pyramids_qgis/`) there yourself. You still need the backing library (above) in QGIS's Python.

```bash
git clone https://github.com/serapeum-org/pyramids-qgis
cd pyramids-qgis
python scripts/deploy.py                        # copy src/pyramids_qgis/ into the default profile
python scripts/deploy.py --symlink              # symlink instead (dev: edits apply after a restart)
python scripts/deploy.py --profile <name>       # a non-default profile
python scripts/deploy.py --plugins-dir "<path>" # an explicit plugins dir (overrides --profile)
```

It installs the plugin as the folder **`pyramids_qgis`** under (default profile):

| OS | Plugins directory |
|---|---|
| Windows | `%APPDATA%\QGIS\QGIS3\profiles\default\python\plugins\pyramids_qgis` |
| Linux | `~/.local/share/QGIS/QGIS3/profiles/default/python/plugins/pyramids_qgis` |
| macOS | `~/Library/Application Support/QGIS/QGIS3/profiles/default/python/plugins/pyramids_qgis` |

**Manual alternative:** copy or symlink `src/pyramids_qgis/` into that `python/plugins/` directory yourself — the
installed folder **must** be named `pyramids_qgis`. Then enable **Pyramids QGIS** in *Plugins → Manage and Install
Plugins* (ticking *Settings → Show also experimental plugins* if hidden). To confirm the algorithms actually run on
real data, work through the [end-to-end testing guide](testing.md).
