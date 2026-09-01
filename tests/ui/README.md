# UI reproductions

Automated reproductions of reported UI issues, driven against a **built or
installed** DB Browser through Windows UI Automation. They are not part of the
CMake build and nothing in `src/` depends on them.

They exist to make a reported issue arguable: instead of a list of manual steps,
a maintainer can run one command and read an assertion.

## Running

```bash
pip install "wintegrate>=0.5.1" pytest
set DB4S_EXE=C:\Program Files\DB Browser for SQLite\DB Browser for SQLite.exe
pytest tests/ui -v
```

`DB4S_EXE` is optional if DB Browser is installed in the default location. The
tests skip on non-Windows.

## Green means the issue still reproduces

Each file targets one **open** issue, so the reproduction is marked
`xfail(strict=True)`. That makes the result meaningful in both directions:

| result | means |
|---|---|
| **xfail** | the issue still reproduces on this build |
| **XPASS** (a failure, because `strict`) | the behaviour changed — fixed, or the build is different |
| **a control fails** | the harness did not measure what it claims to; ignore the rest |

Expected on 3.13.1:

```
test_the_tables_reached_the_tree                        PASSED   <- control
test_a_name_without_leading_spaces_is_unchanged         PASSED   <- control
test_leading_spaces_are_preserved[  two_leading]        XFAIL    <- the issue
test_leading_spaces_are_preserved[    four_leading]     XFAIL    <- the issue
```

The measured mapping is printed on every run regardless of outcome, because an
xfail swallows the assertion output and the measurement is the point:

```
  created as            -> tree publishes
  '  two_leading'       -> 'two_leading'
  '    four_leading'    -> 'four_leading'
  'no_leading'          -> 'no_leading'
```

## In CI

`.github/workflows/wintegrate-repro-3893.yml` runs this against the released
3.13.1 msi on **both** architectures — `win64` carries Qt 5 and `arm64` carries
Qt 6 — so the run also answers "does this depend on the Qt version".

## Current reproductions

| file | issue |
|---|---|
| `test_issue_3893_leading_spaces.py` | [#3893](https://github.com/sqlitebrowser/sqlitebrowser/issues/3893) — leading spaces collapsed in the Database Structure tree |
