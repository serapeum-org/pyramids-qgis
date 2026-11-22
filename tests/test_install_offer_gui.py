"""Tests that drive the real ``pyramids-core`` install dialog, offscreen.

The offer is the plugin's most user-visible code and was previously untestable: it opens a **modal**
``QMessageBox`` (``plugin.py``, ``box.exec()``), and ``exec()`` does not return until something
clicks a button, so a test could never reach them from its own body.

The way in is to schedule the interaction *before* triggering the modal. A zero-delay ``QTimer``
fires inside ``exec()``'s own nested event loop, where ``QApplication.activeModalWidget()`` is the
dialog; the handler clicks a button by its visible text and ``exec()`` returns normally. That needs
no extra test dependency — only the session ``QgsApplication`` the suite already builds and the
``QT_QPA_PLATFORM=offscreen`` platform ``conftest`` already sets, so these run headless on both Qt5
and Qt6.

Two details are load-bearing:

- ``_run_install_offer`` imports ``install_pyramids`` from :mod:`pyramids_qgis.dependencies` *as it
  runs*, so a stub must replace the attribute on that module. Patching it on
  :mod:`pyramids_qgis.plugin` has no effect, and the real installer would run ``pip``.
- Accepting the offer opens a **second** modal — the outcome dialog — so a clicker has to answer a
  sequence of dialogs, not one.

Every dialog interaction is backed by a rescue timer that rejects whatever is open, so a mismatched
label can only fail the test, never hang the suite.
"""

from __future__ import annotations

import pytest
from qgis.core import QgsSettings
from qgis.PyQt.QtCore import QTimer
from qgis.PyQt.QtWidgets import QApplication

from pyramids_qgis import dependencies as deps
from pyramids_qgis.plugin import PyramidsPlugin

pytestmark = pytest.mark.gui

#: Where the plugin records a declined offer, keyed by the state that was declined.
DISMISSED_KEY = "pyramids/install_offer_dismissed_for"

#: How long to wait before giving up on an expected dialog, in milliseconds.
RESCUE_MS = 4000

#: How often to look for an open dialog while a queue is outstanding, in milliseconds.
POLL_MS = 25


class DialogDriver:
    """Clicks a scripted sequence of modal dialogs and records what it saw.

    Attributes:
        seen: One dict per dialog answered, each holding its ``title``, visible ``buttons``, the
            full ``text`` and which label was ``clicked``.
        errors: Messages for dialogs that could not be answered as scripted, including rescues.
    """

    def __init__(self) -> None:
        """Start with no dialogs seen, no errors and nothing queued."""
        self.seen: list[dict] = []
        self.errors: list[str] = []
        self._queue: list[str] = []
        self._timer: QTimer | None = None
        self._elapsed = 0

    def expect(self, *labels: str) -> None:
        """Queue one label per dialog, to be clicked as each dialog appears.

        A repeating timer polls for the open dialog rather than scheduling one handler per dialog
        at a guessed delay: the outcome dialog only exists once the first one has been answered, so
        fixed offsets race against it. Polling also means the queue is answered in order however
        long each step takes.

        Args:
            labels: One label per expected dialog, in order. Matching ignores ``&`` accelerators,
                so ``"Yes"`` matches a standard ``&Yes`` button.
        """
        self._queue = list(labels)
        self._elapsed = 0
        self._timer = QTimer()
        self._timer.setInterval(POLL_MS)
        self._timer.timeout.connect(self._tick)
        self._timer.start()

    def stop(self) -> None:
        """Stop polling. Called at teardown so no timer of this test can fire during the next."""
        if self._timer is not None:
            self._timer.stop()
            self._timer = None

    def _tick(self) -> None:
        """Answer the open dialog, if any, then stop once the queue is empty or time runs out."""
        self._elapsed += POLL_MS
        box = QApplication.activeModalWidget()
        if box is not None and self._queue:
            self._answer(box, self._queue.pop(0))
        if not self._queue:
            self.stop()
            return
        if self._elapsed >= RESCUE_MS:
            self.errors.append(f"timed out waiting for dialogs; still expecting {self._queue}")
            self.stop()
            if box is not None:
                box.reject()

    def _answer(self, box, label: str) -> None:
        """Click the button of ``box`` whose text starts with ``label``.

        Args:
            box: The modal dialog currently open.
            label: The visible button text to match, without accelerators.
        """
        buttons = {button.text().replace("&", ""): button for button in box.buttons()}
        self.seen.append(
            {
                "title": box.windowTitle(),
                "buttons": sorted(buttons),
                "text": box.text(),
                "clicked": label,
            }
        )
        for text, button in buttons.items():
            if text.startswith(label):
                button.click()
                return
        self.errors.append(f"no button {label!r} among {sorted(buttons)}")
        box.reject()

    @property
    def titles(self) -> list[str]:
        """Return the window titles of the dialogs answered, in order."""
        return [dialog["title"] for dialog in self.seen]


@pytest.fixture
def driver():
    """Yield a fresh :class:`DialogDriver`, and stop its timer however the test ends.

    Without the teardown a timer from a failed test keeps polling and rejects the *next* test's
    dialog, which turns one real failure into a cascade of misleading ones.
    """
    helper = DialogDriver()
    yield helper
    helper.stop()


@pytest.fixture
def clean_dismissal():
    """Remove the recorded decline before and after a test, so runs cannot influence each other."""
    QgsSettings().remove(DISMISSED_KEY)
    yield
    QgsSettings().remove(DISMISSED_KEY)


@pytest.fixture
def installs(monkeypatch):
    """Stub the installer on the module the offer imports it from, and record its calls.

    Returns:
        list[dict]: The keyword arguments of each ``install_pyramids`` call the offer made. Empty
        while nothing has accepted the offer.
    """
    calls: list[dict] = []

    def fake_install(**kwargs):
        calls.append(kwargs)
        return True, "stubbed installer: no pip ran"

    monkeypatch.setattr(deps, "install_pyramids", fake_install)
    return calls


@pytest.fixture
def missing_pyramids(monkeypatch):
    """Make the plugin see ``pyramids-core`` as absent, the state that offers a fresh install."""
    monkeypatch.setattr(deps, "pyramids_installed", lambda: False)
    monkeypatch.setattr(deps, "pyramids_outdated", lambda: False)


@pytest.fixture
def outdated_pyramids(monkeypatch):
    """Make the plugin see ``pyramids-core`` as present but too old, the upgrade state."""
    monkeypatch.setattr(deps, "pyramids_installed", lambda: True)
    monkeypatch.setattr(deps, "pyramids_outdated", lambda: True)


def test_the_offer_shows_three_buttons_and_names_the_version_floor(
    driver, clean_dismissal, installs, missing_pyramids
):
    """The dialog offers exactly Yes / Not now / Don't ask again and states what is required."""
    driver.expect("Not now")
    PyramidsPlugin(None)._run_install_offer()

    assert not driver.errors, driver.errors
    assert driver.titles == ["Pyramids: install pyramids-core"]
    dialog = driver.seen[0]
    assert dialog["buttons"] == ["Don't ask again", "Not now", "Yes"]
    assert deps.MIN_PYRAMIDS_VERSION_STR in dialog["text"], "the dialog must state the floor"
    assert "pyramids-core" in dialog["text"]


def test_dont_ask_again_records_the_decline(driver, clean_dismissal, installs, missing_pyramids):
    """ "Don't ask again" persists the decline for this state, and installs nothing."""
    driver.expect("Don't ask again")
    PyramidsPlugin(None)._run_install_offer()

    assert not driver.errors, driver.errors
    assert QgsSettings().value(DISMISSED_KEY) == "missing"
    assert installs == [], "declining must not run the installer"


def test_not_now_declines_without_recording_it(driver, clean_dismissal, installs, missing_pyramids):
    """ "Not now" installs nothing and records nothing, so the offer returns on the next start."""
    driver.expect("Not now")
    PyramidsPlugin(None)._run_install_offer()

    assert not driver.errors, driver.errors
    assert QgsSettings().value(DISMISSED_KEY, "") == "", "'Not now' must not be remembered"
    assert installs == []


def test_a_recorded_decline_shows_no_dialog(driver, clean_dismissal, installs, missing_pyramids):
    """With the decline already recorded for this state, the offer is silent."""
    QgsSettings().setValue(DISMISSED_KEY, "missing")
    driver.expect("Not now")
    PyramidsPlugin(None)._run_install_offer()

    assert driver.seen == [], "a dialog appeared despite the recorded decline"
    assert installs == []


def test_accepting_runs_the_installer_and_reports_success(
    driver, clean_dismissal, installs, missing_pyramids, monkeypatch
):
    """Yes installs, then a second dialog reports the result and the decline is cleared."""
    QgsSettings().setValue(DISMISSED_KEY, "outdated")  # a decline recorded for the OTHER state
    driver.expect("Yes", "OK")

    plugin = PyramidsPlugin(None)
    monkeypatch.setattr(plugin, "_report_install_result", lambda *a, **k: True)
    plugin._run_install_offer()

    assert not driver.errors, driver.errors
    assert installs == [{"upgrade": False}], f"installer calls were {installs}"
    assert QgsSettings().value(DISMISSED_KEY, "") == "", (
        "a successful install must clear the decline, including one recorded for the other state"
    )


def test_an_outdated_install_is_offered_as_an_upgrade(
    driver, clean_dismissal, installs, outdated_pyramids, monkeypatch
):
    """An installed-but-old pyramids is offered as an upgrade, and recorded under its own state."""
    driver.expect("Don't ask again")
    PyramidsPlugin(None)._run_install_offer()

    assert not driver.errors, driver.errors
    assert "older than the supported version" in driver.seen[0]["text"]
    assert QgsSettings().value(DISMISSED_KEY) == "outdated", (
        "the decline is per state, so declining an upgrade must not silence a missing install"
    )


def test_accepting_an_upgrade_passes_upgrade_true(
    driver, clean_dismissal, installs, outdated_pyramids, monkeypatch
):
    """Accepting in the outdated state asks the installer to upgrade, not to install fresh."""
    driver.expect("Yes", "OK")
    plugin = PyramidsPlugin(None)
    monkeypatch.setattr(plugin, "_report_install_result", lambda *a, **k: False)
    plugin._run_install_offer()

    assert not driver.errors, driver.errors
    assert installs == [{"upgrade": True}], f"installer calls were {installs}"


def test_a_failed_install_reports_the_manual_command(
    driver, clean_dismissal, missing_pyramids, monkeypatch
):
    """When the installer fails, the outcome dialog hands the user the command to run by hand."""
    monkeypatch.setattr(deps, "install_pyramids", lambda **kw: (False, "pip exploded"))
    driver.expect("Yes", "OK")
    PyramidsPlugin(None)._run_install_offer()

    assert not driver.errors, driver.errors
    assert len(driver.seen) == 2, f"expected the offer and an outcome dialog, got {driver.titles}"
    outcome = driver.seen[1]
    assert "failed" in outcome["title"].lower()
    assert "pip install" in outcome["text"], "the outcome must name the manual command"
    assert QgsSettings().value(DISMISSED_KEY, "") == "", "a failed install must not be remembered"
