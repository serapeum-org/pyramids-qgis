"""Shared base class and helpers for the pyramids Processing algorithms.

Every algorithm here is file-in / file-out and delegates to the ``pyramids`` command-line
interface, which is called *in-process* via :func:`pyramids.cli.main`. That CLI maps 1:1
onto library calls and is the library's stable, documented contract, so the plugin never
re-implements raster logic and never drifts from the library's behaviour: an algorithm's
whole job is to translate QGIS parameters into a ``pyramids <command> ...`` argument list.
"""

from __future__ import annotations

import contextlib
import io
import threading
from pathlib import Path

from qgis.core import (
    QgsCoordinateReferenceSystem,
    QgsProcessingAlgorithm,
    QgsProcessingException,
)

from ..dependencies import ensure_pyramids, vendored_gdal_warning

#: Serializes the process-global ``sys.stdout`` / ``sys.stderr`` capture in
#: :meth:`PyramidsAlgorithm.run_pyramids`. QGIS runs ``processAlgorithm`` in a background
#: ``QgsTask`` thread, and batch mode / the graphical modeler can run algorithms concurrently;
#: ``contextlib.redirect_stdout`` replaces the streams process-wide, so without this lock two
#: concurrent runs would corrupt each other's captured buffers. The lock makes the capture
#: windows mutually exclusive. The residual caveat (unavoidable with global streams) is that
#: unrelated main-thread output, e.g. the QGIS Python console, printed during a capture window is
#: still absorbed into that run's buffer — acceptable because the window is a single fast CLI call.
_CLI_CAPTURE_LOCK = threading.Lock()


class PyramidsAlgorithm(QgsProcessingAlgorithm):
    """Base class: name/group boilerplate plus the shared pyramids CLI runner."""

    #: Processing group this algorithm appears under; overridden per subclass.
    GROUP = "Raster"
    #: Lowercase, stable group id; overridden per subclass.
    GROUP_ID = "raster"

    def createInstance(self):  # noqa: N802  (QGIS-mandated method name)
        """Return a fresh instance (QGIS clones the algorithm per run)."""
        return type(self)()

    def group(self) -> str:
        """Return the display name of the algorithm's group."""
        return self.GROUP

    def groupId(self) -> str:  # noqa: N802  (QGIS-mandated method name)
        """Return the stable id of the algorithm's group."""
        return self.GROUP_ID

    def tr(self, text: str) -> str:
        """Translate ``text`` (no-op passthrough until translations are added)."""
        return text

    def check_pyramids(self, feedback) -> None:
        """Ensure pyramids is importable and warn on a vendored-GDAL build.

        Shared by the CLI runner and the mesh algorithms (which call the pyramids library
        directly rather than through the CLI), so every algorithm applies the same import
        guard and GDAL-conflict warning before touching pyramids.

        Args:
            feedback: The Processing feedback object for log messages.

        Raises:
            QgsProcessingException: pyramids is not importable from QGIS's Python.
        """
        ensure_pyramids()
        warning = vendored_gdal_warning()
        if warning:
            feedback.pushWarning(warning)

    def run_pyramids(self, argv: list[str], feedback) -> None:
        """Run ``pyramids <argv>`` in-process and surface its output through ``feedback``.

        The pyramids CLI returns ``0`` on success and prints a one-line ``error: ...`` to
        stderr on an expected failure (bad CRS, missing file, ...). Both stdout and stderr
        are captured: stdout is echoed to the Processing log, and a non-zero exit is turned
        into a :class:`QgsProcessingException` carrying the captured message. The capture
        replaces the process-global streams, so it is serialized with :data:`_CLI_CAPTURE_LOCK`
        to keep concurrent runs (batch mode / the modeler) from corrupting each other's
        buffers; see that lock's note for the residual single-process-stream caveat.

        Args:
            argv: The CLI arguments, e.g. ``["warp", src, dst, "--crs", "EPSG:3857"]``.
            feedback: The Processing feedback object for log messages.

        Raises:
            QgsProcessingException: pyramids is missing, or the command exited non-zero.
        """
        self.check_pyramids(feedback)

        from pyramids import cli

        feedback.pushInfo("pyramids " + " ".join(argv))
        stdout, stderr = io.StringIO(), io.StringIO()
        exit_message: str | None = None
        try:
            # Nested (not parenthesized) with-items: the parenthesized form is Python 3.10+,
            # but the compile matrix includes 3.9 (QGIS 3.22 LTR).
            with _CLI_CAPTURE_LOCK:
                with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
                    code = cli.main(argv)
        except SystemExit as exc:  # defensive: main() returns an int, but guard anyway
            # exc.code is None (-> 0), an int (-> that code), or any other object such as the
            # string from sys.exit("message") -- which int() would turn into a ValueError that
            # bypasses the clean failure path below. Treat a non-int, non-None code as a failure
            # and carry its text as the error message.
            raw = exc.code
            if raw is None or isinstance(raw, int):
                code = raw or 0
            else:
                code = 1
                exit_message = str(raw)
        except QgsProcessingException:
            raise
        except Exception as exc:  # noqa: BLE001  (report any library error cleanly)
            raise QgsProcessingException(f"pyramids {argv[0]} failed: {exc}") from exc

        out_text = stdout.getvalue().strip()
        err_text = stderr.getvalue().strip()
        if out_text:
            feedback.pushInfo(out_text)
        if code != 0:
            raise QgsProcessingException(
                err_text or exit_message or f"pyramids {argv[0]} exited with code {code}"
            )
        if err_text:
            feedback.pushInfo(err_text)


def crs_to_pyramids(crs: QgsCoordinateReferenceSystem) -> str | None:
    """Convert a QGIS CRS to a string the pyramids CLI accepts (``--crs``).

    pyramids accepts an authority code (``EPSG:3857``), WKT, or PROJ4. Prefer the compact
    authority id when present; fall back to full WKT for custom/unregistered CRSes.

    Args:
        crs: The QGIS CRS.

    Returns:
        str | None: ``"EPSG:<code>"`` or a WKT string, or ``None`` for an invalid CRS.
    """
    if crs is None or not crs.isValid():
        return None
    auth_id = crs.authid()
    if auth_id and auth_id.upper().startswith("EPSG:"):
        return auth_id
    return crs.toWkt()


def layer_source_path(layer) -> str:
    """Return the on-disk path of a QGIS layer, stripping any OGR sublayer suffix.

    Vector sources can carry a ``|layername=...`` / ``|layerid=...`` suffix; the file path
    is the part before the first ``|``.

    Args:
        layer: A ``QgsRasterLayer`` or ``QgsVectorLayer``.

    Returns:
        str: The source file path.
    """
    return str(layer.source()).split("|", 1)[0]


def validate_input_path(path: str, feedback) -> None:
    """Warn (do not fail) when a layer source does not look like a readable local file.

    pyramids can read remote / VSI paths too, so a non-file source is not necessarily an
    error — but it is the common cause of a confusing downstream failure, so flag it.

    Args:
        path: The resolved source path.
        feedback: The Processing feedback object.
    """
    if not Path(path).exists():
        feedback.pushWarning(
            f"Input source {path!r} is not a local file; pyramids will try to read it as a "
            "GDAL/OGR path (remote or VSI). If this is an in-memory or database layer, "
            "export it to a file first."
        )
