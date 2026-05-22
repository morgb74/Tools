# Python Filename Hyphen-to-Underscore Renamer

## Overview

This script scans the current Windows folder, including all subfolders, for Python files ending in `.py`.

For each Python file whose filename contains a hyphen `-`, the script offers to rename the file by replacing hyphens with underscores `_`.

Example:

```text
OLD: EVA-Schedule.py
NEW: EVA_Schedule.py
```

The file extension is preserved. Only the filename is changed. The script does not edit file contents, imports, references, or any other files.

---

## What the Script Does

The script:

1. Starts scanning from the folder where it is run.
2. Recursively searches all subfolders for `*.py` files.
3. Finds Python filenames containing `-`.
4. Shows the old filename and proposed new filename.
5. Prompts you one file at a time.
6. Renames the file only if you approve.
7. Shows a summary at the end.

---

## What the Script Does Not Do

The script does **not**:

- Modify Python code inside files.
- Update imports or references.
- Rename folders.
- Rename non-Python files.
- Overwrite existing files.
- Rename files without asking first.

If the target filename already exists, the script skips that file to avoid overwriting anything.

---

## Requirements

You need:

- Windows
- Python 3.8 or newer

No third-party Python packages are required.

---

## Recommended File Name

Save the script as:

```text
rename_py_files.py
```

---

## Where to Put the Script

Place `rename_py_files.py` in the top-level folder you want to scan.

For example:

```text
C:\devops\EVA_Tools\rename_py_files.py
```

When run from `C:\devops\EVA_Tools`, the script scans:

```text
C:\devops\EVA_Tools
C:\devops\EVA_Tools\AIS
C:\devops\EVA_Tools\EVA_Schedule
C:\devops\EVA_Tools\EVA_Schedule\src
...
```

and all other subfolders.

---

## How to Run the Script

Open PowerShell or Command Prompt.

Change into the folder where the script is saved:

```powershell
cd C:\devops\EVA_Tools
```

Run the script:

```powershell
python rename_py_files.py
```

---

## Prompt Options

For each matching file, the script displays:

```text
Rename?
OLD: C:\devops\EVA_Tools\EVA_Schedule\src\EVA-Schedule.py
NEW: C:\devops\EVA_Tools\EVA_Schedule\src\EVA_Schedule.py
Proceed? [y]es / [n]o / [q]uit:
```

You can enter:

| Input | Meaning |
|---|---|
| `y` or `yes` | Rename this file |
| `n`, `no`, or Enter | Skip this file |
| `q` or `quit` | Stop processing immediately |

---

## Example Run

```text
Scanning for Python files under: C:\devops\EVA_Tools

Rename?
OLD: C:\devops\EVA_Tools\EVA_Schedule\src\EVA-Schedule.py
NEW: C:\devops\EVA_Tools\EVA_Schedule\src\EVA_Schedule.py
Proceed? [y]es / [n]o / [q]uit: y
Renamed.

Rename?
OLD: C:\devops\EVA_Tools\Router_Check\src\Router-Check.py
NEW: C:\devops\EVA_Tools\Router_Check\src\Router_Check.py
Proceed? [y]es / [n]o / [q]uit: n
```

---

## End Summary

At the end, the script prints a summary like this:

```text
Summary
-------
Files found: 5
Renamed:     3
Skipped:     2
Failed:      0
```

It also lists:

- Renamed files
- Skipped files
- Failed files, if any

---

## Safety Notes

Before running the script on an important repo, make sure your work is committed or backed up.

Recommended Git workflow:

```powershell
git status
git add .
git commit -m "Backup before filename cleanup"
python rename_py_files.py
git status
```

After reviewing the renamed files:

```powershell
git add .
git commit -m "Rename Python files to use underscores"
```

---

## Troubleshooting

### `python` is not recognized

Python may not be installed or may not be on your PATH.

Try:

```powershell
py rename_py_files.py
```

### Permission denied

Close any editor, terminal, or process that may be using the file, then run the script again.

### Target already exists

The script will skip a rename if the destination filename already exists.

Example:

```text
OLD: Router-Check.py
NEW: Router_Check.py
```

If `Router_Check.py` already exists, the script will not overwrite it.

Resolve the duplicate manually before retrying.

---

## Notes for Python Naming

Python module filenames should generally use lowercase letters and underscores.

Preferred:

```text
eva_schedule.py
router_check.py
excel_column_updater.py
```

Acceptable for this script’s purpose:

```text
EVA_Schedule.py
Router_Check.py
excel_column_updater.py
```

Avoid:

```text
EVA-Schedule.py
Router-Check.py
excel-column-updater.py
```

Hyphens are not valid in normal Python import module names.
