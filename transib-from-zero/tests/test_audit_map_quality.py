import unittest
from unittest.mock import patch

from scripts import audit_map_quality


class AuditMapQualityTests(unittest.TestCase):
    def test_demo_finding_has_zero_only_at_exact_count(self):
        finding_missing = audit_map_quality.AuditFinding(
            "18.9 Число demo-строк",
            39,
        )
        finding_exact = audit_map_quality.AuditFinding(
            "18.9 Число demo-строк",
            0,
        )

        self.assertNotEqual(finding_missing.count, 0)
        self.assertEqual(finding_exact.count, 0)

    def test_report_marks_archive_diff_and_manual_checks(self):
        findings = [
            audit_map_quality.AuditFinding("18.1 Радиус 2500 м", 0),
            audit_map_quality.AuditFinding("18.2 Исключённые без причины", 2),
        ]
        taxonomy = {"version": "1.0"}
        with patch.object(audit_map_quality, "_git_archive_check",
                          return_value=""):
            report = audit_map_quality.render_report(
                findings,
                taxonomy,
                ["18.3 Проверить API для zoom."],
            )

        self.assertIn("Автоматические нарушения: **1**", report)
        self.assertIn("Изменений `archive/` по git diff: нет.", report)
        self.assertIn("18.3 Проверить API для zoom.", report)

    def test_archive_check_targets_repository_paths(self):
        with patch.object(audit_map_quality.subprocess, "run") as run_mock:
            run_mock.return_value.stdout = ""
            audit_map_quality._git_archive_check()

        arguments = run_mock.call_args.args[0]
        self.assertIn("archive/", arguments)
        self.assertIn("transib-from-zero/archive/", arguments)

    def test_report_is_markdown_and_contains_manual_sections(self):
        report = audit_map_quality.render_report(
            [],
            {"version": "1.0"},
            ["18.8 Интеграционная матрица ручных решений."],
        )
        self.assertIn("# Отчёт о качестве карты", report)
        self.assertIn("## Требуют ручной проверки", report)
        self.assertIn("18.8 Интеграционная матрица", report)


if __name__ == "__main__":
    unittest.main()
