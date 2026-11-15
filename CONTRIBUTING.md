# Contributing

Thanks for your interest in improving `pyramids-qgis`. Please discuss any substantial change via an
issue before opening a pull request, and follow the [Code of Conduct](CODE_OF_CONDUCT.md) in all
interactions with the project.

## What this project is

`pyramids-qgis` is a **thin QGIS Processing adapter** over the pyramids stack. Each algorithm
translates its QGIS parameters into a call to `pyramids-core` (its CLI, in-process) or, for meshes,
the `pyramids.netcdf.ugrid` / `pyramids-mesh` API. The plugin deliberately carries **no GIS logic of
its own**: a capability that is missing belongs upstream in `pyramids` (raster/vector),
`pyramids-mesh` (mesh formats), or `cleopatra` (plotting) — report it there and forward it here,
rather than reimplementing it in the plugin.

## Development setup

The plugin runs inside QGIS's own Python, which provides PyQGIS and GDAL — there is no separate
environment to build. Install the library dependencies into the interpreter QGIS runs (see the
[README](README.md)), then deploy the plugin into a QGIS profile:

```bash
python scripts/deploy.py --symlink   # symlink so edits apply after a QGIS restart
```

Enable **Pyramids** in *Plugins → Manage and Install Plugins*, then use the algorithms from the
Processing Toolbox.

## Before you open a pull request

- **Lint and format** with ruff (the version is pinned in `.pre-commit-config.yaml` and the CI
  workflow):

  ```bash
  ruff check .
  ruff format --check .
  ```

  Or install the hooks once with `pre-commit install` and let them run on each commit.

- **Byte-compile** to catch syntax errors without QGIS:

  ```bash
  python -m compileall pyramids_qgis scripts
  ```

- **Build the docs** if you touched anything under `docs/` or `mkdocs.yml`. The CI gate is a
  warnings-as-errors build, so a broken nav entry or a dangling link fails the run:

  ```bash
  pixi run -e docs docs-strict        # mkdocs build --strict, output in site/
  ```

  Pull requests no longer publish a preview to the live site. The `build-strict` job uploads the
  rendered site as a run artifact instead — open the workflow run and download `site-pr-<number>` to
  look at the pages.

- **Verify in QGIS.** CI cannot import PyQGIS, so it only lints and compiles. Run the affected
  algorithm inside QGIS and confirm it loads a correct output layer. Describe that check in the PR.

- Bump the plugin version in `pyramids_qgis/metadata.txt` when the change is user-visible.

## Keeping your clone small

The published documentation lives on a `gh-pages` branch that holds a full copy of the site for
`main` and for every retained release. You never need it to work on the plugin, and fetching it makes
your clone considerably larger than the source warrants. Drop it:

```bash
git remote set-branches origin main
git fetch --prune origin
git update-ref -d refs/remotes/origin/gh-pages   # not optional, see below
git gc --prune=now
```

The `git update-ref` line is the one people miss. `fetch --prune` only removes refs the refspec still
covers, and the first command has just narrowed that refspec to `main` — so `origin/gh-pages` is left
orphaned, and while it exists its objects stay reachable and `gc` reclaims nothing.

This is purely local. It does not touch the remote, and `git remote set-branches origin '*'` undoes
the narrowing if you ever want the branch back.

## Commit and branch conventions

Follow [Conventional Commits](https://www.conventionalcommits.org/): a branch named
`<type>/<short-description>` and a PR title `<type>: <imperative summary>`, where `<type>` is one of
`feat`, `fix`, `docs`, `style`, `refactor`, `perf`, `test`, `chore`, `ci`. Keep body text wrapped at
120 characters.

## Pull request process

1. Open your change against `main` from a feature branch.
2. Fill in the pull request template, including how you tested it in QGIS.
3. CI (ruff + byte-compile + secret scan) must be green.
4. A maintainer reviews and merges; `main` only ever changes through a merged, approved PR.
