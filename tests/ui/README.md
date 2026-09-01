# UI reproductions

Automated reproductions of reported UI issues, driven against a **built or
installed** DB Browser through Windows UI Automation. They are not part of the
CMake build and nothing in `src/` depends on them.

They exist to make a reported issue arguable: instead of a list of manual steps,
a maintainer can run one command and read an assertion.

## Running

```bash
pip install wintegrate pytest
set DB4S_EXE=C:\Program Files\DB Browser for SQLite\DB Browser for SQLite.exe
pytest tests/ui -v
```

`DB4S_EXE` is optional if DB Browser is installed in the default location. The
tests skip on non-Windows.

## A failing test is the point

Each file targets one **open** issue, so the reproduction test is expected to
fail on a build that still has the bug. Each also carries **controls** that must
pass — they prove the harness reached the right window and read the right
widget, so a red reproduction cannot be dismissed as a broken test.

Expected on 3.13.1 for `test_issue_3893_leading_spaces.py`:

```
test_the_tables_reached_the_tree                        PASSED   <- control
test_a_name_without_leading_spaces_is_unchanged         PASSED   <- control
test_leading_spaces_are_preserved[  two_leading]        FAILED   <- the issue
test_leading_spaces_are_preserved[    four_leading]     FAILED   <- the issue
```

## Current reproductions

| file | issue |
|---|---|
| `test_issue_3893_leading_spaces.py` | [#3893](https://github.com/sqlitebrowser/sqlitebrowser/issues/3893) — leading spaces collapsed in the Database Structure tree |
