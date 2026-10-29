"""Deploy the ``pyramids_qgis`` plugin into a QGIS profile's plugin directory.

Copies (default) or symlinks the plugin package so QGIS can load it. Run it with the QGIS
profile open closed — restart QGIS (or re-enable the plugin) afterwards to pick up changes
when copying; a symlink deploy reflects edits live after a QGIS restart.

Usage:
    python scripts/deploy.py                 # copy into the 'default' profile
    python scripts/deploy.py --symlink       # symlink instead (developer workflow)
    python scripts/deploy.py --profile foo   # target a non-default profile
    python scripts/deploy.py --plugins-dir "C:/path/to/python/plugins"
"""

from __future__ import annotations

import argparse
import os
import platform
import re
import shutil
import sys
from pathlib import Path

PLUGIN_NAME = "pyramids_qgis"
_REPO_ROOT = Path(__file__).resolve().parent.parent
_PLUGIN_SRC = _REPO_ROOT / PLUGIN_NAME

#: A QGIS profile name is a single path component — letters, digits, '.', '_' or '-'. Validating it
#: rejects a path-traversal attempt (e.g. ``--profile ../../etc``) before it reaches the plugins
#: directory, so the deploy target cannot escape the QGIS profiles tree (sonar S8707).
_PROFILE_RE = re.compile(r"[A-Za-z0-9._-]+")


def default_plugins_dir(profile: str) -> Path:
    """Return the QGIS plugins directory for ``profile`` on this OS.

    Args:
        profile: The QGIS profile name (usually ``"default"``). Must be a single safe path
            component; a name containing a path separator or ``..`` is rejected.

    Returns:
        Path: ``.../QGIS3/profiles/<profile>/python/plugins``.

    Raises:
        ValueError: ``profile`` is not a single safe path component.
    """
    if profile in {".", ".."} or not _PROFILE_RE.fullmatch(profile):
        raise ValueError(
            f"invalid QGIS profile name {profile!r}: expected a single path component of "
            "letters, digits, '.', '_' or '-' (no path separators or '..')"
        )
    system = platform.system()
    if system == "Windows":
        base = Path(os.environ["APPDATA"]) / "QGIS" / "QGIS3"
    elif system == "Darwin":
        base = Path.home() / "Library" / "Application Support" / "QGIS" / "QGIS3"
    else:
        base = Path.home() / ".local" / "share" / "QGIS" / "QGIS3"
    return base / "profiles" / profile / "python" / "plugins"


def deploy(plugins_dir: Path, *, symlink: bool) -> Path:
    """Install the plugin into ``plugins_dir``, replacing any existing copy.

    Args:
        plugins_dir: The target QGIS plugins directory.
        symlink: Symlink the source instead of copying it.

    Returns:
        Path: The deployed plugin path.
    """
    # Resolve the destination and pin the target to the fixed plugin name directly under it, so the
    # only directory this ever creates, replaces or removes is ``<plugins_dir>/pyramids_qgis`` and
    # nothing can be redirected elsewhere (sonar S8707).
    plugins_dir = plugins_dir.resolve()
    target = plugins_dir / PLUGIN_NAME
    if target.parent != plugins_dir:  # pragma: no cover - PLUGIN_NAME is a separator-free constant
        raise ValueError(f"refusing to deploy outside {plugins_dir}")
    plugins_dir.mkdir(parents=True, exist_ok=True)

    if target.is_symlink() or target.is_file():
        target.unlink()
    elif target.is_dir():
        shutil.rmtree(target)

    if symlink:
        try:
            target.symlink_to(_PLUGIN_SRC, target_is_directory=True)
        except OSError as exc:
            # On Windows, creating a symlink needs Developer Mode or an elevated shell; without
            # it os.symlink raises OSError/WinError 1314. Turn that into a clean, actionable
            # message instead of a raw traceback (review L3).
            raise RuntimeError(
                f"could not create a symlink at {target}: {exc}. On Windows, symlinks require "
                "Developer Mode enabled or an elevated shell — re-run from an admin shell, or "
                "deploy without --symlink to copy instead."
            ) from exc
    else:
        shutil.copytree(_PLUGIN_SRC, target, ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
    return target


def main(argv: list[str] | None = None) -> int:
    """Parse arguments and deploy the plugin.

    Args:
        argv: Argument list (defaults to ``sys.argv[1:]``).

    Returns:
        int: ``0`` on success.
    """
    parser = argparse.ArgumentParser(description="Deploy pyramids_qgis into a QGIS profile.")
    parser.add_argument("--profile", default="default", help="QGIS profile name")
    parser.add_argument("--plugins-dir", help="explicit plugins directory (overrides --profile)")
    parser.add_argument(
        "--symlink", action="store_true", help="symlink instead of copying (dev workflow)"
    )
    args = parser.parse_args(argv)

    if not _PLUGIN_SRC.is_dir():
        print(f"error: plugin source not found at {_PLUGIN_SRC}", file=sys.stderr)
        return 1

    plugins_dir = Path(args.plugins_dir) if args.plugins_dir else default_plugins_dir(args.profile)
    try:
        target = deploy(plugins_dir, symlink=args.symlink)
    except (RuntimeError, OSError) as exc:
        # RuntimeError: the wrapped symlink failure. OSError: an unwrapped failure on the copy
        # path (rmtree / copytree / unlink on a locked or read-only destination). Both get a
        # one-line message and a non-zero exit instead of a raw traceback (review R2-L3).
        print(f"error: {exc}", file=sys.stderr)
        return 1
    verb = "symlinked" if args.symlink else "copied"
    print(f"{verb} {PLUGIN_NAME} -> {target}")
    print("Restart QGIS (or toggle the plugin) and enable 'Pyramids' in the Plugin Manager.")
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
