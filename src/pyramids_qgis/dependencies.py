"""Runtime checks — and optional installation — of pyramids in the QGIS Python environment.

The plugin is a thin adapter: all real work is done by ``pyramids-core``, which must be importable
from the interpreter QGIS runs. This module both reports problems with a clear, actionable message
(instead of a stack trace deep inside an algorithm) and can install the package on request.

Why a GDAL-vendoring wheel is safe now (it was not before): the PyPI ``pyramids-core`` wheel ships a
private ``osgeo`` and, left to its defaults, exports process-global GDAL env vars
(``GDAL_DRIVER_PATH`` / ``GDAL_DATA`` / ``PROJ_LIB`` / ``PATH``) that QGIS's own GDAL would read
— clobbering it. pyramids-core **>= 0.81.0** honours ``PYRAMIDS_MANAGE_GDAL_ENV=0`` (pyramids-core
#1588), which the plugin sets in ``__init__`` before pyramids is imported: pyramids then leaves the
GDAL environment to QGIS and does not activate its vendored build. On >= 0.81.0 that wheel
is fine inside QGIS; only an **older** vendored build is dangerous — hence the version floor below.
"""

from __future__ import annotations

import importlib.metadata
import importlib.util
import os
import sys
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:  # pragma: no cover - for the annotation only; never imported at runtime
    from qgis.PyQt.QtCore import QByteArray

#: Lowest pyramids-core that honours ``PYRAMIDS_MANAGE_GDAL_ENV`` (#1588) — the opt-out that makes
#: the GDAL-vendoring wheel safe inside QGIS. The plugin requires at least this.
MIN_PYRAMIDS_VERSION = (0, 81, 0)
MIN_PYRAMIDS_VERSION_STR = "0.81.0"

#: The pip requirement string the installer uses.
PYRAMIDS_REQUIREMENT = f"pyramids-core>={MIN_PYRAMIDS_VERSION_STR}"

# pip install budget, in milliseconds (QProcess works in ms, unlike subprocess's seconds).
# 10 minutes: a cold pyramids-core install pulls GDAL-adjacent wheels over a slow link.
PIP_TIMEOUT_MS = 600_000
# Covers only the fork/exec, not the install, and matches Qt's own waitForStarted default of
# 30s. Shortening it buys nothing: a wrong interpreter path fails in milliseconds anyway, while
# a cold, antivirus-scanned CreateProcess on Windows can take seconds - and a spurious
# 'could not run pip' would send the user chasing an error that does not exist.
PIP_START_TIMEOUT_MS = 30_000
# Reaped synchronously after kill() so the exit code and the buffered output are readable
# below; a survivor would be killed and reaped by the QProcess destructor regardless.
PIP_KILL_TIMEOUT_MS = 5_000

#: Distribution names `pyramids` is published under (PyPI vs conda-forge).
_PYRAMIDS_DISTRIBUTIONS = ("pyramids-core", "pyramids")

_INSTALL_HINT = (
    "The 'pyramids-core' package is not importable from the QGIS Python environment.\n"
    f"Install it (>= {MIN_PYRAMIDS_VERSION_STR}) into the interpreter QGIS runs:\n"
    f'  - any QGIS (from PyPI):  <qgis-python> -m pip install "{PYRAMIDS_REQUIREMENT}"\n'
    "  - conda-based QGIS: conda install -c conda-forge pyramids (must satisfy the floor;\n"
    "    conda-forge can lag PyPI, so prefer the pip line until it catches up)\n"
    "When QGIS starts with a window, the plugin offers to install it for you; running headlessly "
    "(qgis_process) there is no dialog, so install it yourself."
)


def _locatable(name: str) -> bool:
    """Return whether ``name`` can be located without importing it; ``False`` on a broken install.

    A partial/broken install can make :func:`importlib.util.find_spec` raise ``ImportError`` or
    ``ValueError``; swallow those to ``False`` so the probes never leak a bare error (L3).

    Args:
        name: The import name to look up.

    Returns:
        bool: ``True`` when a spec is found, ``False`` when absent or the lookup errored.
    """
    try:
        return importlib.util.find_spec(name) is not None
    except (ImportError, ValueError):
        return False


def pyramids_installed() -> bool:
    """Return whether the ``pyramids`` package can be located (without importing it)."""
    return _locatable("pyramids")


def _version_tuple(version: str) -> tuple[int, ...]:
    """Parse the leading numeric ``x.y.z`` of a version string into a comparable tuple.

    Each dotted chunk contributes its leading digits; a chunk that does not start with a digit stops
    the parse. So ``"1.2.dev0"`` becomes ``(1, 2)``, and ``"0.81.0rc1"`` becomes ``(0, 81, 0)``
    (the ``0rc1`` chunk still starts with a digit) — adequate for a ``>=`` floor comparison. PEP 440
    epochs (``"1!2.3"``) and local segments are NOT understood (the epoch is dropped); pyramids-core
    uses plain ``N.N.N[pre]`` releases, so this is sufficient here.

    Args:
        version: A distribution version string.

    Returns:
        tuple[int, ...]: The leading dotted integers; empty if none parse.
    """
    parts: list[int] = []
    for chunk in version.split("."):
        digits = ""
        for char in chunk:
            if char.isdigit():
                digits += char
            else:
                break
        if not digits:
            break
        parts.append(int(digits))
    return tuple(parts)


def pyramids_version() -> tuple[int, ...] | None:
    """Return the installed pyramids version as a comparable tuple, or ``None`` if unknown.

    Tries each distribution name pyramids is published under (``pyramids-core`` on PyPI,
    ``pyramids`` on conda-forge). A version string that parses to no digits (e.g. ``"unknown"``)
    is reported as ``None`` so callers take the unknown-version path rather than treating it as
    below the floor (N2).

    Returns:
        tuple[int, ...] | None: e.g. ``(0, 81, 0)``, or ``None`` when neither distribution's
        metadata is found (or its version string yields no digits).
    """
    for name in _PYRAMIDS_DISTRIBUTIONS:
        try:
            parsed = _version_tuple(importlib.metadata.version(name))
        except importlib.metadata.PackageNotFoundError:
            continue
        return parsed or None
    return None


def _meets_floor(version: tuple[int, ...]) -> bool:
    """Return whether ``version`` is at least :data:`MIN_PYRAMIDS_VERSION`, length-padded.

    Tuple comparison makes a shorter prefix sort below a longer one (``(0, 81) < (0, 81, 0)``), so a
    bare ``"0.81"`` would be wrongly judged below a ``(0, 81, 0)`` floor. Pad both to equal length
    with zeros before comparing (L1).

    Args:
        version: A parsed version tuple from :func:`_version_tuple`.

    Returns:
        bool: ``True`` when ``version`` is greater than or equal to the floor.
    """
    width = max(len(version), len(MIN_PYRAMIDS_VERSION))
    padded = version + (0,) * (width - len(version))
    floor = MIN_PYRAMIDS_VERSION + (0,) * (width - len(MIN_PYRAMIDS_VERSION))
    return padded >= floor


def pyramids_outdated() -> bool:
    """Return whether an installed pyramids is older than :data:`MIN_PYRAMIDS_VERSION`.

    A ``None`` version (installed but metadata unreadable) is treated as **not** outdated here —
    :func:`vendored_gdal_warning` handles the unknown-version case conservatively instead.

    Returns:
        bool: ``True`` only when a version is known and below the floor.
    """
    version = pyramids_version()
    return version is not None and not _meets_floor(version)


def ensure_pyramids() -> None:
    """Raise a Processing-friendly error when ``pyramids`` is not importable.

    Raises:
        QgsProcessingException: ``pyramids`` cannot be found in QGIS's Python.
    """
    # Imported lazily so this module is importable (for unit reasoning) without QGIS.
    from qgis.core import QgsProcessingException

    if not pyramids_installed():
        raise QgsProcessingException(_INSTALL_HINT)


_EO_HINT = (
    "pyramids-eo is not installed, so the Earth-observation algorithms are unavailable.\n"
    "Install it into the QGIS Python environment:\n"
    "  <qgis-python> -m pip install pyramids-eo"
)


def pyramids_eo_installed() -> bool:
    """Return whether the ``pyramids_eo`` package can be located."""
    return _locatable("pyramids_eo")


def ensure_pyramids_eo() -> None:
    """Raise a Processing-friendly error when ``pyramids_eo`` is not importable.

    Unlike pyramids-mesh (optional, soft warning), pyramids-eo is a hard requirement for the
    Earth-observation algorithms — without it there is nothing to run.

    Raises:
        QgsProcessingException: ``pyramids_eo`` cannot be found in QGIS's Python.
    """
    from qgis.core import QgsProcessingException

    if not pyramids_eo_installed():
        raise QgsProcessingException(_EO_HINT)


_MESH_DRIVERS_HINT = (
    "pyramids-mesh is not installed, so only UGRID NetCDF meshes can be read or written.\n"
    "Install it into the QGIS Python environment to enable the other mesh formats "
    "(2DM, Selafin, DFSU, XMDF, PLY, ...):\n"
    "  <qgis-python> -m pip install pyramids-mesh"
)


def pyramids_mesh_installed() -> bool:
    """Return whether the ``pyramids_mesh`` driver package can be located."""
    return _locatable("pyramids_mesh")


def mesh_drivers_warning() -> str | None:
    """Return a hint when pyramids-mesh is absent, else ``None``.

    pyramids-mesh is optional: the built-in UGRID NetCDF read/write works without it, but every
    other mesh format (2DM, Selafin, DFSU, ...) is provided by a pyramids-mesh driver. This is a
    soft warning, not an error — a NetCDF-only workflow is fine without it.

    Returns:
        str | None: The install hint when pyramids-mesh is missing, otherwise ``None``.
    """
    if not pyramids_mesh_installed():
        return _MESH_DRIVERS_HINT
    return None


def _vendors_gdal() -> bool:
    """Return whether the installed pyramids ships a private ``_vendor/osgeo`` GDAL on disk.

    Detection is by **filesystem** (via :func:`importlib.util.find_spec`, which does not import the
    package): inspecting an already-imported ``osgeo.__file__`` would return QGIS's module and hide
    a genuinely vendored pyramids build.

    Returns:
        bool: ``True`` when a ``_vendor/osgeo`` directory exists under the package.
    """
    try:
        spec = importlib.util.find_spec("pyramids")
    except (ImportError, ValueError):  # a broken/partial install can raise from find_spec
        return False
    if spec is None or not spec.submodule_search_locations:
        return False
    # `_vendor/osgeo` is the exact location pyramids' runtime bootstrap ships and activates the
    # vendored SWIG bindings from — see pyramids/base/_bootstrap.py. If pyramids changes that
    # layout, update this path to match.
    return any(
        (Path(location) / "_vendor" / "osgeo").is_dir()
        for location in spec.submodule_search_locations
    )


def vendored_gdal_warning() -> str | None:
    """Return a warning when a GDAL-vendoring pyramids build is unsafe inside QGIS, else ``None``.

    A vendored build is only dangerous on versions that predate the ``PYRAMIDS_MANAGE_GDAL_ENV``
    opt-out (pyramids-core #1588, >= :data:`MIN_PYRAMIDS_VERSION`). On a new-enough build the plugin
    sets ``PYRAMIDS_MANAGE_GDAL_ENV=0`` in ``__init__`` and pyramids leaves QGIS's GDAL untouched,
    so no warning is needed. Only an **older** (or version-unknown) vendored build can clobber
    QGIS's GDAL — that is what this reports, pointing at the fix: upgrade to >= the floor.

    Returns:
        str | None: A warning when a too-old vendored build is detected, otherwise ``None`` (also
        when pyramids is absent, not vendored, or a broken install — those are not this one's to
        report; absence is :func:`ensure_pyramids`'s).
    """
    if not _vendors_gdal():
        # Not vendored, not installed, or broken (find_spec raised): nothing to warn about.
        return None
    version = pyramids_version()
    if version is not None and _meets_floor(version):
        # Honours the env opt-out this plugin sets, so the vendored GDAL is never activated.
        return None
    return (
        "The installed pyramids build vendors its own GDAL and is older than "
        f"{MIN_PYRAMIDS_VERSION_STR} (or its version could not be read), so it does not honour the "
        "PYRAMIDS_MANAGE_GDAL_ENV opt-out and can conflict with QGIS's GDAL. Upgrade it: "
        f'<qgis-python> -m pip install --upgrade "{PYRAMIDS_REQUIREMENT}"'
    )


def _python_executable() -> str:
    """Best-effort path to the interpreter QGIS runs, for invoking ``-m pip``.

    ``sys.executable`` is the Python binary on Linux/macOS but is often the QGIS application binary
    on Windows (e.g. ``qgis-bin.exe``), which cannot run ``-m pip``. When it does not look like a
    Python executable, probe the standard locations under the interpreter's prefixes.

    Returns:
        str: A Python executable path if one is found, else ``sys.executable`` (or ``"python"``).
    """
    exe = sys.executable or ""
    if exe and Path(exe).stem.lower().startswith("python"):
        return exe
    names = ("python3.exe", "python.exe") if os.name == "nt" else ("python3", "python")
    for base in (sys.exec_prefix, sys.base_prefix, os.path.dirname(exe)):
        found = _find_python_in(base, names) if base else None
        if found:
            return found
    return exe or "python"


def _find_python_in(base: str, names: tuple[str, ...]) -> str | None:
    """Return the first ``names`` file that exists under ``base`` (or its ``bin``/``Scripts``).

    Args:
        base: A prefix directory to probe (e.g. ``sys.exec_prefix``).
        names: Candidate executable basenames to look for, in priority order.

    Returns:
        str | None: The path of the first matching file, or ``None`` when none exists.
    """
    for subdir in ("", "bin", "Scripts"):
        directory = Path(base, subdir) if subdir else Path(base)
        for name in names:
            candidate = directory / name
            if candidate.is_file():
                return str(candidate)
    return None


def _read_all(data: "QByteArray") -> str:
    """Decode a ``QByteArray`` of process output into text.

    Args:
        data: The ``QByteArray`` returned by ``QProcess.readAllStandardOutput``/``...Error``.

    Returns:
        str: The decoded text; undecodable bytes are replaced rather than raising, because pip's
            output encoding varies by platform and console code page.
    """
    return bytes(data).decode("utf-8", errors="replace")


def _drain(process) -> str:
    """Read and decode both of a process's output channels.

    Args:
        process: The ``QProcess`` to drain. Both channels are consumed, so call this once.

    Returns:
        str: stdout followed by stderr, decoded with replacement.
    """
    return _read_all(process.readAllStandardOutput()) + _read_all(process.readAllStandardError())


def _failure(reason: str, manual: str, captured: str = "") -> str:
    """Build a failure message carrying the manual command and any output pip produced.

    Takes the captured text rather than the ``QProcess`` so each caller decides what to
    read: the launch-failure path has nothing to read (measured - a never-started process
    returns 0 bytes on both channels), while the other paths have already drained them.

    Args:
        reason: The one-line cause, e.g. a launch error, a timeout, or a non-zero exit.
        manual: The shell command the user can run by hand.
        captured: Whatever pip wrote, if anything.

    Returns:
        str: ``reason``, the manual-install hint, and the captured output when there is any.
    """
    message = f"{reason}\n  install manually: {manual}"
    return f"{message}\n{captured}" if captured.strip() else message


def install_pyramids(*, upgrade: bool = False) -> tuple[bool, str]:
    """Install (or upgrade) ``pyramids-core`` into the QGIS interpreter with pip.

    Runs ``<qgis-python> -m pip install --no-input [--upgrade] "pyramids-core>=<floor>"`` in a child
    process via Qt's ``QProcess``, with the child's stdin redirected from the null device. Both are
    deliberate: pip prompts through its keyring and proxy-authentication paths, and this call blocks
    the GUI thread, so a prompt must become an error rather than a wait.

    Never raises. All four failure modes — a launch failure (wrong interpreter, no pip), a timeout
    (the process is killed), a crash, and a non-zero exit — are returned as a failure carrying
    whatever output pip produced and a manual command the user can paste, so the caller can show
    both.

    ``QProcess`` rather than ``subprocess``: this is a Qt application, so the Qt API is the native
    one here, and it keeps the module free of the ``subprocess`` import that bandit blacklists
    (B404/B603) — plugins.qgis.org blocks a submitted version on any bandit finding, so the plugin
    cannot ship that import. The process is still a child process: the Qt API is a different
    interface to the same work, chosen because it is the idiomatic one, not to assert that running
    pip is risk-free or that it changed anything about the security of running it.

    Args:
        upgrade: Pass ``--upgrade`` (use when an older pyramids is already installed).

    Returns:
        tuple[bool, str]: ``(succeeded, combined_output)``.
    """
    # Imported lazily, through the qgis.PyQt shim for Qt5/Qt6 portability, so importing this
    # module stays free of PyQGIS — `ensure_pyramids()` and the version helpers must work while
    # QGIS is still starting up.
    from qgis.PyQt.QtCore import QProcess

    executable = _python_executable()
    # --no-input makes pip fail with a message instead of waiting on a prompt; its keyring
    # and proxy-authentication paths both prompt, and this runs on the GUI thread.
    arguments = ["-m", "pip", "install", "--no-input"]
    if upgrade:
        arguments.append("--upgrade")
    arguments.append(PYRAMIDS_REQUIREMENT)
    # Built for a human to paste, which is why it is not just " ".join(arguments): --no-input
    # is dropped, since a prompt pip could not answer automatically (keyring, proxy auth) may be
    # exactly why this failed, and by hand the user can answer it.
    #
    # Quoting: `>` is a redirection operator in cmd.exe, and single quotes are not quoting
    # characters there at all - measured, the bare form created a file named 0.81.0 and the
    # single-quoted form one named 0.81.0', both installing with no version floor. Double quotes
    # are correct for cmd.exe and for POSIX shells. They are NOT sufficient for PowerShell,
    # which needs a leading `&` before a quoted executable path (measured on pwsh 7.6.10:
    # ParserError, "Unexpected token '-m'"), so the message says so rather than pretending one
    # string serves every shell.
    upgrade_flag = "--upgrade " if upgrade else ""
    manual = (
        f'"{executable}" -m pip install {upgrade_flag}"{PYRAMIDS_REQUIREMENT}"'
        "   (in PowerShell, prefix the line with & )"
    )

    process = QProcess()
    process.setProgram(executable)
    process.setArguments(arguments)
    # QProcess.start() opens a pipe to the child's stdin and holds it open until the QProcess is
    # destroyed, where subprocess left stdin inherited - and QGIS is a console-less GUI process, so
    # a child's read returned EOF at once. Without this redirect a pip that prompts never finishes:
    # measured on real Qt6, a stdin-reading child is still Running after 3s (so it would block for
    # the whole PIP_TIMEOUT_MS with the GUI thread and a wait cursor held), against 0.08s with it.
    process.setStandardInputFile(QProcess.nullDevice())
    process.start()

    if not process.waitForStarted(PIP_START_TIMEOUT_MS):
        # Nothing to capture: a process that never started has written nothing (measured).
        return False, _failure(f"Could not run pip ({executable}): {process.errorString()}", manual)
    if not process.waitForFinished(PIP_TIMEOUT_MS):
        process.kill()
        process.waitForFinished(PIP_KILL_TIMEOUT_MS)
        # Read the channels after the kill: whatever pip managed to write is still buffered and is
        # the only diagnostic a wedged install leaves. Measured on real Qt6 - a child that prints
        # and then outlives the budget still yields its text here.
        return False, _failure(
            f"pip did not finish within {PIP_TIMEOUT_MS // 1000}s and was stopped.",
            manual,
            _drain(process),
        )

    output = _drain(process)
    # Qt documents exitCode() as meaningless unless exitStatus() is NormalExit, so both are
    # checked. The enum is resolved with getattr so the lookup works whichever shape the
    # binding uses: measured on Qt 6.11.0, QProcess.ExitStatus exists and QProcess.NormalExit
    # does not, and this plugin spans QGIS 3.22 through 4.x. Comparing int(exitStatus()) does
    # NOT work - int() on that enum raises TypeError - so the members are compared directly.
    normal_exit = getattr(QProcess, "ExitStatus", QProcess).NormalExit
    if process.exitStatus() == normal_exit and process.exitCode() == 0:
        return True, output
    reason = (
        f"pip exited with code {process.exitCode()}."
        if process.exitStatus() == normal_exit
        else f"pip crashed (exit code {process.exitCode()})."
    )
    return False, _failure(reason, manual, output)
