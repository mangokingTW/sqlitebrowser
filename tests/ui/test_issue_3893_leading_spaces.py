"""Issue #3893 — leading spaces in a name are collapsed in the Database Structure tree.

    https://github.com/sqlitebrowser/sqlitebrowser/issues/3893

This is an automated reproduction. It drives a real DB Browser build through
Windows UI Automation and reads the names the application publishes for its
Database Structure tree items.

Run it with::

    pip install wintegrate pytest
    set DB4S_EXE=C:\\Program Files\\DB Browser for SQLite\\DB Browser for SQLite.exe
    pytest tests/ui/test_issue_3893_leading_spaces.py -v

Measured on 3.13.1 (win64, Qt 5.15.2), Windows 11 26100 ARM64:

    name in the SQL                          tree item         leading spaces
    '  this_name_starts_with_2_spaces'       (2 spaces gone)   2 -> 0
    '<20 spaces>this_name_starts_with_20...' (20 spaces gone)  20 -> 0
    'this_name_starts_with_no_spaces'        unchanged         0 -> 0   (control)

`test_leading_spaces_are_preserved` is the one that reproduces the issue: it
asserts what the tree *should* show. It is marked `xfail(strict=True)` because
the issue is open, which gives the run a useful meaning in both directions:

* **xfail** — the issue still reproduces on this build.
* **XPASS → failure** — the tree now reports the name correctly, so either the
  issue was fixed or the build changed. Worth knowing either way.

The other two tests are controls, and they must pass — without them a red
reproduction could equally mean the harness never found the right tree, or that
the tables were never created.

Why read the accessible name rather than compare screenshots: whitespace is
invisible. A screenshot cannot distinguish two leading spaces from none, and
neither can a human scrolling the tree. It is also the name a screen reader
announces, so if it is wrong here it is wrong there too.

The window is maximised so the **Schema** column is on screen beside the Name
column, which is the one thing a reader can see: the schema keeps a space after
the opening quote where the name has none.

What the recording does **not** show is *how many* spaces were dropped. Measured
on 3.13.1, the Schema column collapses a run of whitespace to a single space, so
20 and 2 render identically there, and the Name column drops both entirely. That
is a wider finding than the issue describes — the collapsing is not confined to
the Name column — and it is precisely why the count has to be asserted rather
than looked at.
"""

from __future__ import annotations

import os
import sqlite3
import sys
import time
import uuid
from pathlib import Path

import pytest

pytest.importorskip("wintegrate", reason="pip install wintegrate")

from wintegrate import Window  # noqa: E402
from wintegrate.apps import sweep_processes_verified  # noqa: E402

from conftest import maximize  # noqa: E402

pytestmark = pytest.mark.skipif(
    sys.platform != "win32", reason="drives the Windows build through UI Automation"
)

PROCESS = "DB Browser for SQLite.exe"

# UIA control type ids. The structure tree publishes its rows as tree items on
# Qt 6 and as list items on Qt 5, so both are collected.
CONTROL_TYPE_LIST_ITEM = 50007
CONTROL_TYPE_TREE_ITEM = 50024

# The names describe what should be on screen, so a screenshot or a recording of
# this run is readable without a caption: three rows that all start at the same
# column, two of which say they should not.
#
# One uses **20** spaces, the width the issue's own example used, and it turns
# out to matter for a reason that was not obvious: measured on 3.13.1, the
# Database Structure view renders 20 and 2 identically. The Name column drops
# them entirely and the Schema column beside it collapses the run to a single
# space, so `CREATE TABLE " this_name` looks the same either way.
#
# The whitespace collapsing therefore is not limited to leading spaces in the
# Name column, which is all the issue describes. Keeping both widths is what
# demonstrates that the count is not preserved anywhere in this view — and it
# is also why the recording cannot show the magnitude, only the assertions can.
TWO_LEADING = "  this_name_starts_with_2_spaces"
MANY_LEADING = " " * 20 + "this_name_starts_with_20_spaces"
NO_LEADING = "this_name_starts_with_no_spaces"
TABLES = (TWO_LEADING, MANY_LEADING, NO_LEADING)

# How long to leave the populated tree on screen at the end. Nothing waits on
# this — it exists so a recording of the run contains several seconds of the
# evidence rather than a single frame at the moment everything shuts down.
HOLD_FOR_THE_RECORDING = float(os.environ.get("DB4S_HOLD", "6"))

# The tree is populated asynchronously after the file opens.
TREE_TIMEOUT = float(os.environ.get("DB4S_TREE_TIMEOUT", "30"))


def _executable() -> str:
    configured = os.environ.get("DB4S_EXE")
    if configured:
        if not Path(configured).exists():
            pytest.fail(f"DB4S_EXE is set to {configured!r}, which does not exist")
        return configured
    for candidate in (
        r"C:\Program Files\DB Browser for SQLite\DB Browser for SQLite.exe",
        r"C:\Program Files (x86)\DB Browser for SQLite\DB Browser for SQLite.exe",
    ):
        if Path(candidate).exists():
            return candidate
    pytest.skip("DB Browser for SQLite not found; set DB4S_EXE to its full path")


@pytest.fixture(scope="module")
def structure_tree_names(recording) -> list[str]:
    """Every name the Database Structure tree publishes, for a known database."""
    database = Path(os.environ.get("TEMP", ".")) / f"issue3893-{uuid.uuid4().hex[:8]}.db"
    connection = sqlite3.connect(database)
    try:
        for table in TABLES:
            connection.execute(f'CREATE TABLE "{table}" ("Field1" INTEGER)')
        connection.commit()
    finally:
        connection.close()

    # An old build otherwise opens a modal announcing a newer version, and the
    # window behind it never becomes reachable.
    os.system(
        r'reg add "HKCU\Software\sqlitebrowser\sqlitebrowser\checkversion" '
        r"/v enabled /t REG_SZ /d false /f >nul 2>&1"
    )

    sweep_processes_verified((PROCESS,), ("DB Browser",))
    time.sleep(1.0)
    process, window = Window.launch_and_discover(
        [_executable(), str(database)], timeout=120.0, process_names=(PROCESS,)
    )
    try:
        # Maximised *before* recording starts, so the Schema column is on
        # screen next to the Name column and the video has no dead time at the
        # front. Nothing is asserted from the Schema column — UIA does not
        # publish it — but a reader of the recording needs it.
        maximize(window.hwnd)
        time.sleep(2.0)
        recording.begin()

        deadline = time.monotonic() + TREE_TIMEOUT
        names: list[str] = []
        while time.monotonic() < deadline:
            time.sleep(1.0)
            root = window.re_resolve_element()
            found = root.find_all(control_type_id=CONTROL_TYPE_TREE_ITEM)
            found += root.find_all(control_type_id=CONTROL_TYPE_LIST_ITEM)
            names = [element.name for element in found if element.name]
            if any(NO_LEADING in name for name in names):
                break
        assert names, (
            f"the Database Structure tree published no names within {TREE_TIMEOUT}s, so "
            "nothing below is measuring what it claims to"
        )
        # Printed unconditionally: an xfail swallows the assertion output, and the
        # measurement is the whole point of running this.
        print("\n  created as            -> tree publishes")
        for table in TABLES:
            published = [n for n in names if n.strip() == table.strip()]
            print(f"  {table!r:<38} -> {published[0]!r}" if published else
                  f"  {table!r:<38} -> (not found)")
        time.sleep(HOLD_FOR_THE_RECORDING)
        return names
    finally:
        process.terminate()
        sweep_processes_verified((PROCESS,), ("DB Browser",))
        database.unlink(missing_ok=True)


def _matching(names: list[str], table: str) -> list[str]:
    """Distinct names the tree publishes for this table, in the order seen.

    De-duplicated because the same row is reachable as both a tree item and a
    list item depending on the Qt version, and a repeated name would make the
    assertion below fail for two reasons at once — the interesting one being
    the whitespace.
    """
    seen: list[str] = []
    for name in names:
        if name.strip() == table.strip() and name not in seen:
            seen.append(name)
    return seen


def test_the_tables_reached_the_tree(structure_tree_names):
    """Control: without this a failure below could just mean nothing was found."""
    for table in TABLES:
        assert _matching(structure_tree_names, table), (
            f"no tree item matched {table.strip()!r}; the tree published "
            f"{structure_tree_names!r}"
        )


def test_a_name_without_leading_spaces_is_unchanged(structure_tree_names):
    """Control: the tree does report names accurately when there is no whitespace."""
    assert _matching(structure_tree_names, NO_LEADING) == [NO_LEADING]


@pytest.mark.xfail(
    strict=True,
    reason="issue #3893 is open: the Database Structure tree collapses leading spaces",
)
@pytest.mark.parametrize("table", [TWO_LEADING, MANY_LEADING])
def test_leading_spaces_are_preserved(structure_tree_names, table):
    """Reproduces #3893. Expected to fail while the issue is open."""
    published = _matching(structure_tree_names, table)
    assert published == [table], (
        f"the Database Structure tree shows {published!r} for a table created as "
        f"{table!r} — {len(table) - len(table.lstrip())} leading spaces were collapsed. "
        "The name is what identifies the table, so a name that cannot be read back "
        "accurately cannot be matched against the schema either."
    )
