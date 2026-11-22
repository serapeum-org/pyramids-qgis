"""The QGIS plugin shell: register and unregister the Pyramids Processing provider.

This plugin is Processing-only (``hasProcessingProvider=yes`` in ``metadata.txt``), so enabling it
does nothing but add the provider to the Processing registry, and ``unload`` removes it. There is no
toolbar or menu action to manage. QGIS's camelCase lifecycle hooks are implemented as snake_case
methods and exposed under the names QGIS calls via ``__getattr__``: ``initGui`` (the desktop GUI
path) resolves to :meth:`PyramidsPlugin._init_gui`, and ``initProcessing`` (the headless path used
by ``qgis_process`` and QGIS Server for ``hasProcessingProvider`` plugins) resolves to
:meth:`PyramidsPlugin.init_processing`. Both must exist: QGIS unloads the plugin if the hook for the
way it was started is absent.
"""

from __future__ import annotations

import html
import traceback

from qgis.core import QgsApplication

from .provider import PyramidsProvider


class PyramidsPlugin:
    """Thin lifecycle wrapper that owns the Processing provider.

    QGIS builds one instance per session through :func:`pyramids_qgis.classFactory`, then starts it
    through whichever hook fits how it is running — ``initGui`` with a GUI, ``initProcessing``
    without one — and calls :meth:`unload` when the plugin is disabled or QGIS shuts down. The
    provider is created by whichever start hook runs, never in the constructor, so an instance that
    QGIS never starts holds no registry state.
    """

    def __init__(self, iface):
        """Store the QGIS interface handle and leave the provider to the start hook.

        The provider is built by :meth:`init_processing` (headless) or :meth:`_init_gui` (GUI), not
        here, so constructing the plugin touches no QGIS global state.

        Args:
            iface: The ``QgisInterface`` passed by QGIS. It is ``None`` in headless runs such as
                ``qgis_process``, so anything that needs a parent window must tolerate that.
        """
        self.iface = iface
        self.provider: PyramidsProvider | None = None

    def init_processing(self) -> None:
        """Create the provider and add it to the Processing registry.

        Reached directly as ``initProcessing`` (via :meth:`__getattr__`) when QGIS starts the plugin
        headlessly — ``qgis_process`` and QGIS Server — and also called first by
        :meth:`_init_gui` on the desktop path. It does no GUI work, so it is safe with no
        main window.
        """
        self.provider = PyramidsProvider()
        QgsApplication.processingRegistry().addProvider(self.provider)

    def _init_gui(self) -> None:
        """Enable the plugin: register the Processing provider, then offer to install pyramids.

        QGIS reaches this through the ``initGui`` name exposed by :meth:`__getattr__`. The headless
        counterpart is :meth:`init_processing`, which registers the provider without the offer.
        """
        self.init_processing()
        # Defer the install offer with a 0-ms timer so initGui returns immediately: the dialog then
        # appears once the event loop is running and the main window is up, instead of blocking the
        # startup critical path (M1). The install itself is still synchronous when accepted.
        from qgis.PyQt.QtCore import QTimer

        QTimer.singleShot(0, self._offer_pyramids_install)

    def _offer_pyramids_install(self) -> None:
        """Offer to install/upgrade ``pyramids-core`` when it is missing or too old.

        The plugin is useless without ``pyramids-core``, and only ``>= MIN_PYRAMIDS_VERSION`` is
        safe inside QGIS (it honours the ``PYRAMIDS_MANAGE_GDAL_ENV`` opt-out set in ``__init__``).
        The work is delegated to :meth:`_run_install_offer`; any failure there is logged to the QGIS
        message log (never silently swallowed) and never blocks plugin load. A user who declines
        still gets the actionable error from ``ensure_pyramids`` when they run an algorithm.
        """
        try:
            self._run_install_offer()
        except Exception:  # plugin load must never fail because of the offer
            from qgis.core import Qgis, QgsMessageLog

            QgsMessageLog.logMessage(traceback.format_exc(), "Pyramids", level=Qgis.Warning)

    def _run_install_offer(self) -> None:
        """Prompt and, on confirmation, pip-install pyramids-core into QGIS's interpreter.

        Shows the resolved target interpreter and the exact command, warns that QGIS is unresponsive
        during the (synchronous) install, remembers a decline per state so it does not re-ask every
        start, and re-checks after a reported success that pyramids is actually importable from the
        target (pip may have installed into an interpreter QGIS does not use).

        Note:
            The install runs synchronously on the GUI thread, so QGIS is frozen for its duration; a
            background ``QgsTask`` installer with progress is the intended follow-up (needs in-QGIS
            validation, issue #3). This whole method is only reachable in a running QGIS and is not
            exercised by the (QGIS-free) unit tests.
        """
        import importlib

        from qgis.core import QgsSettings
        from qgis.PyQt.QtCore import Qt
        from qgis.PyQt.QtWidgets import QApplication, QMessageBox

        from .dependencies import (
            PYRAMIDS_REQUIREMENT,
            _python_executable,
            install_pyramids,
            pyramids_installed,
            pyramids_outdated,
        )

        missing = not pyramids_installed()
        outdated = (not missing) and pyramids_outdated()
        if not missing and not outdated:
            return

        state = "missing" if missing else "outdated"
        settings = QgsSettings()
        dismissed_key = "pyramids/install_offer_dismissed_for"
        if settings.value(dismissed_key, "") == state:
            return  # declined for this exact state already; re-offer only if the state changes (M3)

        parent = self.iface.mainWindow() if self.iface is not None else None
        target = _python_executable()
        manual = f"<code>pip install '{html.escape(PYRAMIDS_REQUIREMENT)}'</code>"
        verb = "is not installed" if missing else "is older than the supported version"
        req = html.escape(PYRAMIDS_REQUIREMENT)
        question = (
            f"The Pyramids plugin needs <b>{req}</b>, which {verb} in QGIS's Python."
            f"<br><br>Install it into:<br><code>{html.escape(target)}</code>"
            "<br><br><b>QGIS will be unresponsive for a few minutes</b> while it downloads and "
            "installs — there is no progress indicator."
        )
        box = QMessageBox(parent)
        box.setWindowTitle("Pyramids: install pyramids-core")
        box.setTextFormat(Qt.TextFormat.RichText)
        box.setText(question)
        yes = box.addButton(QMessageBox.StandardButton.Yes)
        box.addButton("Not now", QMessageBox.ButtonRole.RejectRole)
        never = box.addButton("Don't ask again", QMessageBox.ButtonRole.DestructiveRole)
        box.exec()
        clicked = box.clickedButton()
        if clicked is never:
            settings.setValue(dismissed_key, state)  # persist only on an explicit "Don't ask again"
            return
        if clicked is not yes:
            return  # "Not now" / closed: re-offer next start, do not persist

        QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
        try:
            ok, output = install_pyramids(upgrade=outdated)
        finally:
            QApplication.restoreOverrideCursor()

        importlib.invalidate_caches()  # so the re-check below can see a freshly installed package
        if self._report_install_result(parent, ok=ok, output=output, target=target, manual=manual):
            settings.remove(dismissed_key)  # succeeded and importable: clear any stale dismissal

    def _report_install_result(
        self, parent, *, ok: bool, output: str, target: str, manual: str
    ) -> bool:
        """Show the post-install outcome dialog and report whether pyramids is now usable.

        Args:
            parent: The dialog parent widget (the QGIS main window, or ``None``).
            ok: Whether ``install_pyramids`` reported success (pip exit code 0).
            output: The captured pip stdout/stderr, whose tail is shown on a non-success.
            target: The interpreter path the install targeted, shown in the incomplete message.
            manual: Pre-rendered HTML with the manual ``pip install`` fallback command.

        Returns:
            bool: ``True`` only when pip succeeded and pyramids-core is now importable at a
            supported version (the caller then clears the dismissal key); ``False`` otherwise.
        """
        from qgis.PyQt.QtWidgets import QMessageBox

        from .dependencies import pyramids_installed, pyramids_outdated

        tail = html.escape(output[-1500:]) if output else ""
        extra = f"<br><br><pre>{tail}</pre>" if tail else ""
        if ok and pyramids_installed() and not pyramids_outdated():
            QMessageBox.information(
                parent,
                "Pyramids",
                "pyramids-core installed. Restart QGIS for the algorithms to pick it up.",
            )
            return True
        if ok:
            QMessageBox.warning(
                parent,
                "Pyramids: install incomplete",
                "pip reported success, but pyramids-core is still not importable from "
                f"<code>{html.escape(target)}</code> — it may not be the interpreter QGIS uses. "
                f"Install it into QGIS's Python by hand:<br><br>{manual}" + extra,
            )
            return False
        QMessageBox.warning(
            parent,
            "Pyramids: install failed",
            "Could not install pyramids-core automatically. Install it by hand into QGIS's "
            f"Python:<br><br>{manual}" + extra,
        )
        return False

    def unload(self) -> None:
        """Remove the provider when the plugin is disabled or QGIS shuts down.

        Serves both start paths, and is a no-op when no start hook ever ran: without the guard,
        unloading a plugin QGIS had only constructed would pass ``None`` to the registry. Removing
        the provider hands it back to QGIS, which destroys it, so ``provider`` is cleared to avoid
        holding a stale wrapper.
        """
        if self.provider is not None:
            QgsApplication.processingRegistry().removeProvider(self.provider)
            self.provider = None

    def __getattr__(self, name: str):
        """Expose the QGIS-required camelCase lifecycle hooks dynamically.

        QGIS starts this plugin through one of two entry points, and which one depends on how QGIS
        is running:

        - **``initGui``** — used by the desktop GUI (``qgis.utils.startPlugin``). Resolves to
          :meth:`_init_gui`, which registers the provider and then offers to install pyramids.
        - **``initProcessing``** — used headlessly for plugins that declare
          ``hasProcessingProvider=yes`` (``qgis.utils.startProcessingPlugin``), i.e.
          ``qgis_process`` and QGIS Server. Resolves to :meth:`init_processing`, which only
          registers the provider: there is no GUI to show an install dialog in. **This hook is
          mandatory** — QGIS unloads the plugin outright when it is missing ("plugin has no
          initProcessing() method"), which left the algorithms unavailable to ``qgis_process``.

        Resolving both on demand keeps the QGIS-mandated camelCase names working without declaring
        camelCase methods. ``__getattr__`` only runs for attributes normal lookup does not find, so
        every real attribute (``iface``, ``provider``, ``_init_gui``, ``unload``, …) is unaffected.

        Args:
            name: The attribute being looked up on the instance.

        Returns:
            The bound :meth:`_init_gui` for ``"initGui"``, or :meth:`init_processing` for
            ``"initProcessing"``.

        Raises:
            AttributeError: For any other attribute name.
        """
        if name == "initGui":
            return self._init_gui
        if name == "initProcessing":
            return self.init_processing
        raise AttributeError(f"{type(self).__name__!r} object has no attribute {name!r}")
