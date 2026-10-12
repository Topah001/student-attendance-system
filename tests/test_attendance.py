import unittest
from pathlib import Path

from attendance import AttendanceError, AttendanceRegister


class AttendanceTests(unittest.TestCase):
    def setUp(self):
        self.database = Path(__file__).with_name(".test_attendance.db")
        self.database.unlink(missing_ok=True)
        self.addCleanup(self.database.unlink, missing_ok=True)
        self.register = AttendanceRegister(self.database)
        self.student = self.register.add_student("Taylor Student")

    def test_records_attendance_and_reports_student_percentage(self):
        self.register.record(self.student, "2026-10-01", "present")
        self.register.record(self.student, "2026-10-02", "absent")
        self.register.record(self.student, "2026-10-03", "present")
        summary = self.register.student_summary(self.student)
        self.assertEqual(summary["present"], 2)
        self.assertEqual(summary["absent"], 1)
        self.assertEqual(summary["total"], 3)
        self.assertAlmostEqual(summary["percentage"], 200 / 3)
        self.assertEqual(len(summary["records"]), 3)

    def test_date_summary_counts_records_and_lists_students(self):
        other = self.register.add_student("Another Student")
        self.register.record(self.student, "2026-10-01", "present")
        self.register.record(other, "2026-10-01", "absent")
        summary = self.register.date_summary("2026-10-01")
        self.assertEqual((summary["present"], summary["absent"], summary["total"]), (1, 1, 2))
        self.assertEqual({r["status"] for r in summary["records"]}, {"present", "absent"})

    def test_duplicate_date_and_invalid_fields_are_rejected(self):
        self.register.record(self.student, "2026-10-01", "present")
        with self.assertRaisesRegex(AttendanceError, "already has a record"):
            self.register.record(self.student, "2026-10-01", "absent")
        with self.assertRaisesRegex(AttendanceError, "Status must"):
            self.register.record(self.student, "2026-10-02", "late")
        with self.assertRaisesRegex(AttendanceError, "valid ISO date"):
            self.register.record(self.student, "2026-02-30", "present")

    def test_unknown_student_and_empty_summary(self):
        with self.assertRaisesRegex(AttendanceError, "Unknown student"):
            self.register.record(999, "2026-10-01", "present")
        summary = self.register.student_summary(self.student)
        self.assertEqual(summary["total"], 0)
        self.assertEqual(summary["percentage"], 0.0)


if __name__ == "__main__":
    unittest.main()
