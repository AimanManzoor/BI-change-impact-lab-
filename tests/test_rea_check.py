import copy
import json
import sqlite3
import tempfile
import unittest
from pathlib import Path

from src.impact import ROOT
from src.rea_check import check_evidence, recover_sql


class ReaCheckTests(unittest.TestCase):
    def setUp(self):
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
        self.evidence = {"data": {"schema": schema}}

    def run_check(self, evidence):
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "evidence.json"
            path.write_text(json.dumps(evidence))
            before = path.read_bytes()
            try:
                return check_evidence(path)
            finally:
                self.assertEqual(path.read_bytes(), before)

    def test_recovered_dependencies_and_embedded_line_evidence(self):
        report = self.run_check(self.evidence)
        self.assertEqual(report["verified_dependencies"], 4)
        self.assertEqual(report["model_calls"], 0)
        self.assertIn("CREATE VIEW", report["recovered_sql"])
        self.assertEqual(len(report["rea_evidence_sha256"]), 64)
        for item in report["potentially_affected"]:
            for hop in item["evidence_path"]:
                line = int(hop["source_location"].removeprefix("L"))
                self.assertIn(
                    hop["dependency"],
                    report["recovered_sql"].splitlines()[line - 1],
                )

    def test_missing_and_multiple_schemas_are_rejected(self):
        for evidence in ({}, [self.evidence, self.evidence]):
            with self.subTest(evidence=evidence):
                with self.assertRaises(ValueError):
                    recover_sql(evidence)

    def test_missing_duplicate_and_wrong_kind_objects_are_rejected(self):
        for mode in ("missing", "duplicate", "wrong_kind"):
            evidence = copy.deepcopy(self.evidence)
            schema = evidence["data"]["schema"]
            if mode == "missing":
                schema["views"].pop()
            elif mode == "duplicate":
                schema["views"].append(schema["views"][0])
            else:
                schema["tables"][0], schema["views"][0] = (
                    schema["views"][0], schema["tables"][0]
                )
            with self.subTest(mode=mode):
                with self.assertRaises(ValueError):
                    recover_sql(evidence)

    def test_missing_sql_is_rejected(self):
        self.evidence["data"]["schema"]["views"][0]["sql"] = None
        with self.assertRaises(ValueError):
            recover_sql(self.evidence)

    def test_wrong_dependency_is_rejected(self):
        for view in self.evidence["data"]["schema"]["views"]:
            if view["name"] == "customer_directory":
                view["sql"] = (
                    "CREATE VIEW customer_directory AS SELECT * FROM orders"
                )
        with self.assertRaises(ValueError):
            self.run_check(self.evidence)

    def test_missing_evidence_file_is_not_created(self):
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "missing.json"
            with self.assertRaises(FileNotFoundError):
                check_evidence(path)
            self.assertFalse(path.exists())
