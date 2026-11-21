"""The QGIS plugin shell: register and unregister the Pyramids Processing provider.

This plugin is Processing-only (``hasProcessingProvider=yes`` in ``metadata.txt``), so enabling it
does nothing but add the provider to the Processing registry, and ``unload`` removes it. There is no
toolbar or menu action to manage. QGIS's ``initGui`` lifecycle hook is implemented as the snake_case
:meth:`PyramidsPlugin._init_gui` and exposed under the ``initGui`` name via ``__getattr__``, so the
method QGIS calls exists without a camelCase declaration.
"""

from __future__ import annotations

from qgis.core import QgsApplication

from .provider import PyramidsProvider


class PyramidsPlugin:
    """Thin lifecycle wrapper that owns the Processing provider."""

    def __init__(self, iface):
        """Store the QGIS interface handle and defer provider creation to ``initGui``.

        Args:
            iface: The ``QgisInterface`` passed by QGIS.
        """
        self.iface = iface
        self.provider: PyramidsProvider | None = None

    def init_processing(self) -> None:
        """Create the provider and add it to the Processing registry."""
        self.provider = PyramidsProvider()
        QgsApplication.processingRegistry().addProvider(self.provider)

    def _init_gui(self) -> None:
        """Enable the plugin: register the Processing provider, then offer to install pyramids.

        QGIS reaches this through the ``initGui`` name exposed by :meth:`__getattr__`.
        """
        self.init_processing()
        self._offer_pyramids_install()

    def _offer_pyramids_install(self) -> None:
        """Offer to install/upgrade ``pyramids-core`` when it is missing or too old.

        The plugin is useless without ``pyramids-core``, and only ``>= MIN_PYRAMIDS_VERSION`` is
        safe inside QGIS (it honours the ``PYRAMIDS_MANAGE_GDAL_ENV`` opt-out set in ``__init__``).
        On load, if it is absent or outdated, pop a prompt and — on the user's confirmation — pip
        install it into QGIS's interpreter, then suggest a restart. Everything is wrapped so a
        failure in the offer never blocks the plugin from loading; a user who declines still gets
        the actionable error from ``ensure_pyramids`` when they run an algorithm.
        """
        try:
            from qgis.PyQt.QtWidgets import QMessageBox

            from .dependencies import (
                PYRAMIDS_REQUIREMENT,
                install_pyramids,
                pyramids_installed,
                pyramids_outdated,
            )

            missing = not pyramids_installed()
            outdated = (not missing) and pyramids_outdated()
            if not missing and not outdated:
                return

            parent = self.iface.mainWindow() if self.iface is not None else None
            verb = "is not installed" if missing else "is older than the supported version"
            question = (
                f"The Pyramids plugin needs <b>{PYRAMIDS_REQUIREMENT}</b>, which {verb} in QGIS's "
                "Python.<br><br>Install it now with pip into QGIS's interpreter?"
            )
            if (
                QMessageBox.question(parent, "Pyramids: install pyramids-core", question)
                != QMessageBox.StandardButton.Yes
            ):
                return

            ok, output = install_pyramids(upgrade=outdated)
            tail = output[-1500:] if output else ""
            if ok:
                QMessageBox.information(
                    parent,
                    "Pyramids",
                    "pyramids-core installed. Restart QGIS for the algorithms to pick it up.",
                )
            else:
                QMessageBox.warning(
                    parent,
                    "Pyramids: install failed",
                    "Could not install pyramids-core automatically. Install it by hand into QGIS's "
                    f"Python:<br><br><code>pip install '{PYRAMIDS_REQUIREMENT}'</code>"
                    + (f"<br><br><pre>{tail}</pre>" if tail else ""),
                )
        except Exception:
            return

    def unload(self) -> None:
        """Remove the provider when the plugin is disabled or QGIS shuts down."""
        if self.provider is not None:
            QgsApplication.processingRegistry().removeProvider(self.provider)
            self.provider = None

    def __getattr__(self, name: str):
        """Expose the QGIS-required ``initGui`` lifecycle method dynamically.

        QGIS enables the plugin by calling ``initGui``; resolve that to the snake_case
        :meth:`_init_gui` on demand so the method QGIS needs exists without declaring a camelCase
        method. ``__getattr__`` only runs for attributes normal lookup does not find, so every real
        attribute (``iface``, ``provider``, ``_init_gui``, ``unload``, …) is unaffected.

        Args:
            name: The attribute being looked up on the instance.

        Returns:
            The bound ``_init_gui`` method when ``name`` is ``"initGui"``.

        Raises:
            AttributeError: For any other attribute name.
        """
        if name == "initGui":
            return self._init_gui
        raise AttributeError(f"{type(self).__name__!r} object has no attribute {name!r}")
