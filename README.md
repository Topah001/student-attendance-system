# Student Attendance System

A Python 3.13 command-line attendance register using a local SQLite database. It records one present/absent status per student per date and reports date summaries and student attendance percentages.

## Requirements

- Python 3.13 (standard library only)

## Run

```powershell
python attendance.py add-student --name "Jordan Lee"
python attendance.py record --student-id 1 --date 2026-10-12 --status present
python attendance.py record --student-id 1 --date 2026-10-13 --status absent
python attendance.py date-report --date 2026-10-12
python attendance.py student-report --student-id 1
```

The database defaults to `attendance.db` in the current directory. Use `--db path\to\file.db` before a command for another local database. Dates use `YYYY-MM-DD`; recording the same student twice on a date is rejected. The student report counts only dates with a recorded status.

## Tests

```powershell
python -m unittest discover -s tests -v
```

The app is offline, and generated databases are excluded from version control.
