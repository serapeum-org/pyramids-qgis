# Installation

The plugin is **not** installed with `pip install .`: QGIS discovers plugins in its profile's
`python/plugins/` directory (by folder name + `metadata.txt`), not from site-packages. So you
install the **backing libraries** into QGIS's own Python, then deploy the plugin **package**
(`src/pyramids_qgis/`) into the plugins directory.

## Requirements

- **QGIS 3.22+** (works through 4.x; the plugin uses the `qgis.PyQt` shim for Qt5/Qt6).
- **`pyramids-core` importable from QGIS's own Python**, bound to **QGIS's GDAL**.

!!! danger "Do not use a vendored-GDAL wheel inside QGIS"
    Install pyramids into the interpreter QGIS runs — **not** a platform wheel that vendors its own
    GDAL. Those inject a private `osgeo` and force `GDAL_DRIVER_PATH` at import, which conflicts with
    QGIS's GDAL in-process. The plugin detects a vendored build and warns at runtime.

## 1. Clone the repo

```bash
git clone https://github.com/serapeum-org/pyramids-qgis
cd pyramids-qgis
```

## 2. Install the backing libraries into QGIS's OWN Python

They must bind to QGIS's GDAL. `pyramids-core` is required; `pyramids-mesh` / `pyramids-eo` are only
needed for the mesh / EO algorithms.

=== "conda-based QGIS"

    Activate the environment QGIS runs in. Install the core library from conda-forge (named
    `pyramids`, **not** `pyramids-core`); add the optional backends with pip in the same env:

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
    If you cannot write to the QGIS/OSGeo4W Python (a system or admin install), add `--user` so pip
    installs into your per-user site, which QGIS's interpreter still imports from. Avoid mixing a
    `--user` pyramids with a system one — keep a single copy on the path QGIS uses.

### What each backend unlocks

| Backend | Install | Enables |
|---|---|---|
| `pyramids-core` | required | all raster / conversion algorithms; mesh on UGRID NetCDF |
| `pyramids-mesh` | optional | the other mesh formats (2DM, Selafin, DFSU, XMDF, PLY, …) |
| `pyramids-eo` | optional | the Earth-observation algorithms (contrast stretch, tasseled cap) |

## 3. Deploy the plugin into your QGIS profile

From the repo root, `scripts/deploy.py` copies (or symlinks) `src/pyramids_qgis/` into the active
profile's plugins directory:

```bash
python scripts/deploy.py                        # copy into the default profile
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

**Manual alternative:** copy or symlink `src/pyramids_qgis/` into that `python/plugins/` directory
yourself — the installed folder **must** be named `pyramids_qgis`.

## 4. Enable and verify

Restart QGIS, then enable **Pyramids QGIS** in *Plugins → Manage and Install Plugins* (tick
**Settings → Show also experimental plugins** if it is hidden — the plugin ships `experimental=True`).
The algorithms then appear in the *Processing Toolbox* under **Pyramids**.

If nothing shows up, open *Plugins → Python Console* and read the error — it is almost always a
missing `pyramids-core` in QGIS's own Python (step 2).

Once the plugin loads, work through the [end-to-end testing guide](testing.md) to confirm the
algorithms actually run on real data.
