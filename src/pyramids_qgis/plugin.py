"""The QGIS plugin shell: register and unregister the Pyramids Processing provider.

This plugin is Processing-only (``hasProcessingProvider=yes`` in ``metadata.txt``), so enabling it
does nothing but add the provider to the Processing registry, and ``unload`` removes it. There is no
toolbar or menu action to manage. QGIS's camelCase lifecycle hooks are implemented as snake_case
methods and exposed under the names QGIS calls via ``__getattr__``: ``initGui`` (the desktop GUI
path) resolves to :meth:`PyramidsPlugin._init_gui`, and ``initProcessing`` (the headless path used
by ``qgis_process`` for ``hasProcessingProvider`` plugins) resolves to
:meth:`PyramidsPlugin.init_processing`. Both must exist: QGIS unloads the plugin if the hook for the
way it was started is absent. QGIS Server is a third path and not one this plugin serves — it loads
plugins through ``serverClassFactory``, which this package does not expose.
"""

from __future__ import annotations

import html
import traceback

from qgis.core import QgsApplication

from .provider import PyramidsProvider

#: Where a declined install offer is recorded, keyed by the state that was declined
#: (``"missing"`` or ``"outdated"``). Exported so tests assert against the same string the plugin
#: writes: a literal in both places would let a rename pass the negative tests vacuously.
INSTALL_OFFER_DISMISSED_KEY = "pyramids/install_offer_dismissed_for"


class PyramidsPlugin:
    """Thin lifecycle wrapper that owns the Processing provider.

    QGIS builds one instance per load/start cycle through the package-level ``classFactory``
    (surfaced by ``pyramids_qgis.__getattr__``), then starts it through whichever hook fits how it
    is running — ``initGui`` with a GUI, ``initProcessing`` without one — and calls :meth:`unload`
    when the plugin is disabled or QGIS shuts down. Disabling and re-enabling it builds a fresh
    instance, so there can be more than one per QGIS session. The provider is created by whichever
    start hook runs, never in the constructor, so an instance QGIS never starts holds no registry
    state.
    """

    #: QGIS-mandated camelCase start hooks, mapped to the methods implementing them. ``initGui``
    #: is the desktop path; ``initProcessing`` is the headless one QGIS requires for a
    #: ``hasProcessingProvider`` plugin. :meth:`__getattr__` resolves from this table and
    #: :meth:`__dir__` lists it, but an entry alone proves nothing: QGIS only calls a hook it has
    #: a reason to call, which for ``initProcessing`` is ``hasProcessingProvider=yes`` in
    #: ``metadata.txt``; ``test_the_metadata_flag_and_the_headless_hook_agree`` pins that pair. The
    #: targets are deliberately asymmetric: ``init_processing`` is public because :meth:`_init_gui`
    #: and the tests call it directly, while ``_init_gui`` is private because nothing but QGIS
    #: starts the GUI path.
    _QGIS_HOOKS: dict[str, str] = {"initGui": "_init_gui", "initProcessing": "init_processing"}

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
        """Create the provider and add it to the Processing registry, at most once.

        Reached directly as ``initProcessing`` (via :meth:`__getattr__`) when QGIS starts the plugin
        headlessly — ``qgis_process``, for instance — and also called first by :meth:`_init_gui` on
        the desktop path. It does no GUI work, so it is safe with no main window.

        Registering is guarded because ``QgsProcessingRegistry.addProvider`` takes ownership and
        **destroys** a provider whose id is already registered, returning ``False``. Recording that
        destroyed provider would leave a dangling wrapper whose every later use raises
        ``RuntimeError: wrapped C/C++ object ... has been deleted``, so a provider is remembered
        only once the registry has accepted it.

        **Neither failure path is silent.** A start that registers nothing still looks successful to
        QGIS — the only symptom is an empty Pyramids group in the Processing Toolbox, which is how
        this plugin's headless breakage went unnoticed in the first place. So both the
        already-registered case and an ``addProvider`` refusal log a warning to the QGIS message
        log via :meth:`_log`.

        A no-op start strands nothing: :meth:`unload` removes by id as well as by object, so the
        surviving registration still goes away when QGIS unloads the plugin it holds.
        """
        registry = QgsApplication.processingRegistry()
        existing = registry.providerById(PyramidsProvider.PROVIDER_ID)
        if existing is not None:
            self._log(
                f"a provider with id {PyramidsProvider.PROVIDER_ID!r} is already registered "
                f"({type(existing).__name__}); this start is a no-op, so the algorithms you see "
                "belong to that registration"
            )
            return
        provider = PyramidsProvider()
        if registry.addProvider(provider):
            self.provider = provider
            return
        self._log(
            "QgsProcessingRegistry.addProvider refused the Pyramids provider, so no algorithms "
            "will appear in the Processing Toolbox"
        )

    @staticmethod
    def _log(message: str) -> None:
        """Send a warning to the QGIS message log under the ``Pyramids`` tab.

        Used for the states that would otherwise be invisible: a start that registered nothing
        still looks successful to QGIS, and the only symptom is an empty Pyramids group in the
        Processing Toolbox — the exact confusion this plugin already hit once.

        Args:
            message: The text to log, without a trailing newline.
        """
        from qgis.core import Qgis, QgsMessageLog

        # MessageLevel is a plain unscoped C++ enum, so unlike the Processing enums it carries no
        # SIP_MONKEYPATCH_SCOPEENUM_UNNEST and the generated PyQt6 alias table does not cover it.
        # The scoped form is used anyway because it resolves on BOTH bindings: the qt5 CI leg
        # (conda qgis >=3.40,<4, i.e. PyQt 5.15) executes this line, with plugin.py at 100%.
        QgsMessageLog.logMessage(message, "Pyramids", level=Qgis.MessageLevel.Warning)

    def _init_gui(self) -> None:
        """Enable the plugin: register the Processing provider, then offer to install pyramids.

        QGIS reaches this through the ``initGui`` name exposed by :meth:`__getattr__`. The headless
        counterpart is :meth:`init_processing`, which registers the provider without the offer.
        """
        self.init_processing()
        # Defer the install offer with a 0-ms timer so initGui returns immediately: the dialog then
        # appears once the event loop is running and the main window is up, instead of blocking the
        # startup critical path. The install itself is still synchronous when accepted.
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

            QgsMessageLog.logMessage(
                traceback.format_exc(), "Pyramids", level=Qgis.MessageLevel.Warning
            )

    def _run_install_offer(self) -> None:
        """Prompt and, on confirmation, pip-install pyramids-core into QGIS's interpreter.

        Shows the resolved target interpreter and the exact command, warns that QGIS is unresponsive
        during the (synchronous) install, remembers a decline per state so it does not re-ask every
        start, and re-checks after a reported success that pyramids is actually importable from the
        target (pip may have installed into an interpreter QGIS does not use).

        Note:
            The install runs synchronously on the GUI thread, so QGIS is frozen for its duration; a
            background ``QgsTask`` installer with progress is the intended follow-up (needs in-QGIS
            validation, issue #3). The dialog and all three outcomes *are* covered, by
            ``tests/test_install_offer_gui.py``, which clicks the real ``QMessageBox`` offscreen —
            what is still unproven is the startup ordering, i.e. that the offer appears after the
            main window rather than blocking it (issue #46, tier B).
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
        dismissed_key = INSTALL_OFFER_DISMISSED_KEY
        if settings.value(dismissed_key, "") == state:
            return  # declined for this exact state already; re-offer only if the state changes

        parent = self.iface.mainWindow() if self.iface is not None else None
        target = _python_executable()
        # Names the interpreter, because the sentence around this hint promises an install
        # "into QGIS's Python" and a bare `pip` would hit whatever is first on PATH. Double
        # quotes because `>` redirects in cmd.exe and single quotes do not protect it there.
        manual = (
            f'<code>"{html.escape(target)}" -m pip install '
            f'"{html.escape(PYRAMIDS_REQUIREMENT)}"</code>'
        )
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

        Teardown happens in two passes, because one is not enough:

        1. **By object**, when this instance recorded a provider — the normal case, and the only
           form that reliably removes a provider this plugin registered. It is skipped when the
           C++ object has already been destroyed by someone else (checked with ``sip.isdeleted``);
           passing a dead wrapper raises ``RuntimeError: wrapped C/C++ object ... has been
           deleted``, QGIS catches that in ``unloadPlugin``, shows a dialog and returns early, and
           then never reaches ``del plugins[...]`` or ``active_plugins.remove(...)`` — leaving the
           plugin "active" with stale modules loaded.
        2. **By id**, if anything is still registered afterwards. This sweeps up a registration
           this instance never recorded, which happens when :meth:`init_processing` found the id
           already taken. QGIS keys ``qgis.utils.plugins`` by package name and refuses to start a
           second instance while one is active, so such a registration belongs to no plugin object
           QGIS can still reach: clearing it is the only way it can ever go away.

        Both passes are conditional, so a plugin QGIS merely constructed unloads without touching
        the registry.
        """
        from qgis.PyQt import sip

        provider, self.provider = self.provider, None
        registry = QgsApplication.processingRegistry()
        if provider is not None and not sip.isdeleted(provider):
            registry.removeProvider(provider)
        if registry.providerById(PyramidsProvider.PROVIDER_ID) is not None:
            registry.removeProvider(PyramidsProvider.PROVIDER_ID)

    def __getattr__(self, name: str):
        """Expose the QGIS-required camelCase lifecycle hooks dynamically.

        QGIS starts this plugin through one of two entry points, and which one depends on how QGIS
        is running:

        - **``initGui``** — used by the desktop GUI (``qgis.utils.startPlugin``). Resolves to
          :meth:`_init_gui`, which registers the provider and then offers to install pyramids.
        - **``initProcessing``** — used headlessly for plugins that declare
          ``hasProcessingProvider=yes`` (``qgis.utils.startProcessingPlugin``), i.e.
          ``qgis_process``. Resolves to :meth:`init_processing`, which only registers the
          provider: there is no GUI to show an install dialog in. **This hook is mandatory** —
          QGIS unloads the plugin outright when it is missing ("plugin has no initProcessing()
          method"), which left the algorithms unavailable to ``qgis_process``.

        Both are resolved from :attr:`_QGIS_HOOKS`, which :meth:`__dir__` also reads so the names
        show up in introspection instead of being invisible. This keeps the QGIS-mandated camelCase
        names working without declaring camelCase methods. ``__getattr__`` only runs for attributes
        normal lookup does not find, so every real attribute (``iface``, ``provider``,
        ``_init_gui``, ``unload``, …) is unaffected.

        Args:
            name: The attribute being looked up on the instance.

        Returns:
            The bound :meth:`_init_gui` for ``"initGui"``, or :meth:`init_processing` for
            ``"initProcessing"``.

        Raises:
            AttributeError: For any other attribute name.
        """
        target = self._QGIS_HOOKS.get(name)
        if target is not None:
            try:
                return getattr(self, target)
            except AttributeError:
                # A table entry pointing at a method that no longer exists: report it against the
                # hook QGIS asked for, not the private target, which would send the reader hunting
                # for the wrong name.
                raise AttributeError(
                    f"{type(self).__name__!r} maps the QGIS hook {name!r} to {target!r}, "
                    "which does not exist"
                ) from None
        raise AttributeError(f"{type(self).__name__!r} object has no attribute {name!r}")

    def __dir__(self) -> list[str]:
        """Include the dynamically resolved QGIS hook names in ``dir()``.

        Without this, ``initGui`` and ``initProcessing`` are reachable but invisible: they are
        produced by :meth:`__getattr__`, so they appear in no listing, and nothing but a test
        notices if one stops resolving.

        Returns:
            list[str]: The normal attribute listing plus the QGIS hook names.
        """
        return [*super().__dir__(), *self._QGIS_HOOKS]
