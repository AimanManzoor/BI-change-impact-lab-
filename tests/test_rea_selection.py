import json
import sqlite3
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from src.impact import ROOT
from src.rea_check import check_evidence


class ReaSelectionTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.path = Path(temporary.name) / "evidence.json"

        with sqlite3.connect(":memory:") as connection:
            connection.executescript(
                (ROOT / "examples/retail.sql").read_text()
            )
            schema = {"tables": [], "views": []}
            for kind, name, sql in connection.execute(
                "SELECT type, name, sql FROM sqlite_schema "
                "WHERE type IN ('table','view')"
            ):
                schema[kind + "s"].append({"name": name, "sql": sql})

        self.path.write_text(json.dumps({"data": {"schema": schema}}))

    def test_all_five_objects_match_independent_expectations(self):
        cases = {
            "orders": (
                {"order_summary": 1, "regional_sales": 2}, 1, 1
            ),
            "customers": (
                {"customer_directory": 1, "regional_sales": 1}, 2, 0
            ),
            "order_summary": ({"regional_sales": 1}, 1, 0),
            "regional_sales": ({}, 0, 0),
            "customer_directory": ({}, 0, 0),
        }

        for name, (expected, direct, indirect) in cases.items():
            with self.subTest(name=name):
                report = check_evidence(self.path, object_name=name)
                self.assertEqual(report["changed_object"], name)
                self.assertEqual(
                    {
                        item["object"]: item["depth"]
                        for item in report["potentially_affected"]
                    },
                    expected,
                )
                self.assertEqual(
                    (report["direct_count"], report["indirect_count"]),
                    (direct, indirect),
                )

    def test_invalid_object_is_rejected_before_file_access(self):
        for name in (
            "unknown", "Orders", "", None, 123,
            "orders; DROP TABLE orders",
        ):
            with self.subTest(name=name):
                with self.assertRaises(ValueError):
                    check_evidence(
                        self.path.parent / "missing.json",
                        object_name=name,
                    )

    def test_cli_selection_default_and_invalid_name(self):
        for name, expected_code in (
            (None, 0), ("customers", 0), ("unknown", 1)
        ):
            command = [
                sys.executable, "-m", "src.rea_check",
                "--evidence", str(self.path),
            ]
            if name is not None:
                command += ["--object", name]

            process = subprocess.run(
                command, cwd=ROOT, capture_output=True,
                text=True, timeout=30,
            )
            self.assertEqual(
                process.returncode, expected_code, process.stderr
            )
            if expected_code == 0:
                self.assertEqual(
                    json.loads(process.stdout)["changed_object"],
                    name or "orders",
                )
            else:
                self.assertEqual(process.stdout, "")
