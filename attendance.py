"""SQLite-backed student attendance register."""

from __future__ import annotations

import argparse
import sqlite3
import sys
from contextlib import contextmanager
from datetime import date
from pathlib import Path
from typing import Iterator


class AttendanceError(ValueError):
    """Raised when an attendance record or query is invalid."""


def validate_date(value: str) -> str:
    try:
        parsed = date.fromisoformat(value)
    except (TypeError, ValueError) as exc:
        raise AttendanceError("Date must be a valid ISO date (YYYY-MM-DD).") from exc
    if parsed.isoformat() != value:
        raise AttendanceError("Date must use YYYY-MM-DD format.")
    return value


class AttendanceRegister:
    def __init__(self, database: str | Path = "attendance.db") -> None:
        self.database = str(database)
        with self._connect() as connection:
            connection.executescript(
                """CREATE TABLE IF NOT EXISTS students (
                       id INTEGER PRIMARY KEY, name TEXT NOT NULL
                   );
                   CREATE TABLE IF NOT EXISTS attendance (
                       id INTEGER PRIMARY KEY,
                       student_id INTEGER NOT NULL REFERENCES students(id),
                       attendance_date TEXT NOT NULL,
                       status TEXT NOT NULL CHECK (status IN ('present', 'absent')),
                       UNIQUE (student_id, attendance_date)
                   );"""
            )

    @contextmanager
    def _connect(self) -> Iterator[sqlite3.Connection]:
        connection = sqlite3.connect(self.database)
        connection.execute("PRAGMA foreign_keys = ON")
        try:
            with connection:
                yield connection
        finally:
            connection.close()

    def add_student(self, name: str) -> int:
        name = name.strip()
        if not name:
            raise AttendanceError("Student name cannot be empty.")
        with self._connect() as connection:
            cursor = connection.execute("INSERT INTO students (name) VALUES (?)", (name,))
            return int(cursor.lastrowid)

    def record(self, student_id: int, attendance_date: str, status: str) -> int:
        day = validate_date(attendance_date)
        status = status.strip().lower()
        if status not in {"present", "absent"}:
            raise AttendanceError("Status must be present or absent.")
        with self._connect() as connection:
            if connection.execute(
                "SELECT 1 FROM students WHERE id = ?", (student_id,)
            ).fetchone() is None:
                raise AttendanceError(f"Unknown student ID: {student_id}.")
            try:
                cursor = connection.execute(
                    """INSERT INTO attendance (student_id, attendance_date, status)
                       VALUES (?, ?, ?)""",
                    (student_id, day, status),
                )
            except sqlite3.IntegrityError as exc:
                if "UNIQUE constraint failed" in str(exc):
                    raise AttendanceError(
                        f"Student {student_id} already has a record for {day}."
                    ) from exc
                raise
            return int(cursor.lastrowid)

    def date_summary(self, attendance_date: str) -> dict[str, object]:
        day = validate_date(attendance_date)
        with self._connect() as connection:
            rows = connection.execute(
                """SELECT students.id, students.name, attendance.status
                   FROM attendance JOIN students ON students.id = attendance.student_id
                   WHERE attendance.attendance_date = ? ORDER BY students.name, students.id""",
                (day,),
            ).fetchall()
        present = sum(row[2] == "present" for row in rows)
        absent = len(rows) - present
        return {
            "date": day,
            "present": present,
            "absent": absent,
            "total": len(rows),
            "records": [{"student_id": row[0], "name": row[1], "status": row[2]} for row in rows],
        }

    def student_summary(self, student_id: int) -> dict[str, object]:
        with self._connect() as connection:
            student = connection.execute(
                "SELECT name FROM students WHERE id = ?", (student_id,)
            ).fetchone()
            if student is None:
                raise AttendanceError(f"Unknown student ID: {student_id}.")
            records = connection.execute(
                """SELECT attendance_date, status FROM attendance
                   WHERE student_id = ? ORDER BY attendance_date""",
                (student_id,),
            ).fetchall()
        total = len(records)
        present = sum(row[1] == "present" for row in records)
        return {
            "student_id": student_id,
            "name": student[0],
            "present": present,
            "absent": total - present,
            "total": total,
            "percentage": (present / total * 100) if total else 0.0,
            "records": [{"date": row[0], "status": row[1]} for row in records],
        }


def build_parser() -> argparse.ArgumentParser:
    root = argparse.ArgumentParser(description=__doc__)
    root.add_argument("--db", default="attendance.db", help="SQLite database path")
    commands = root.add_subparsers(dest="command", required=True)
    student = commands.add_parser("add-student")
    student.add_argument("--name", required=True)
    record = commands.add_parser("record")
    record.add_argument("--student-id", type=int, required=True)
    record.add_argument("--date", dest="attendance_date", required=True)
    record.add_argument("--status", choices=("present", "absent"), required=True)
    date_report = commands.add_parser("date-report")
    date_report.add_argument("--date", dest="attendance_date", required=True)
    student_report = commands.add_parser("student-report")
    student_report.add_argument("--student-id", type=int, required=True)
    return root


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    register = AttendanceRegister(args.db)
    try:
        if args.command == "add-student":
            print(f"Added student #{register.add_student(args.name)}.")
        elif args.command == "record":
            record_id = register.record(args.student_id, args.attendance_date, args.status)
            print(f"Recorded attendance #{record_id}.")
        elif args.command == "date-report":
            summary = register.date_summary(args.attendance_date)
            print(
                f"Attendance for {summary['date']}: {summary['present']} present, "
                f"{summary['absent']} absent ({summary['total']} recorded)."
            )
            for item in summary["records"]:
                print(f"  #{item['student_id']} {item['name']}: {item['status']}")
        else:
            summary = register.student_summary(args.student_id)
            print(
                f"{summary['name']} (#{summary['student_id']}): "
                f"{summary['present']} present, {summary['absent']} absent "
                f"out of {summary['total']} records; attendance {summary['percentage']:.1f}%."
            )
            for item in summary["records"]:
                print(f"  {item['date']}: {item['status']}")
    except (AttendanceError, OSError, sqlite3.Error) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
