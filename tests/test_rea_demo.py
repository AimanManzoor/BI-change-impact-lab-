import json
import unittest
from unittest.mock import patch
import streamlit as st
from streamlit.testing.v1 import AppTest
from src.impact import ROOT


class ReaDemoTests(unittest.TestCase):
    def launch(self):
        return AppTest.from_file(
            str(ROOT / "app.py"), default_timeout=20
        ).run()

    def enable(self):
        return self.launch().checkbox(key="rea_enabled").check().run()

    def metrics(self, app):
        return [
            item.value for item in app.metric
            if item.label.startswith("REA:")
        ]

    def test_default_does_not_change_existing_metrics(self):
        app = self.launch()
        self.assertFalse(app.exception)
        self.assertFalse(app.checkbox(key="rea_enabled").value)
        self.assertEqual(
            [item.value for item in app.metric], ["2", "1", "1"]
        )

    def test_orders_displays_paths_and_sql(self):
        app = self.enable()
        self.assertFalse(app.exception)
        self.assertEqual(self.metrics(app), ["2", "1", "1"])
        self.assertTrue(any(
            "order_summary — 1 hop" in item.value
            for item in app.markdown
        ))
        self.assertTrue(any(
            "CREATE VIEW" in item.value for item in app.code
        ))

    def test_customers_download_matches_current_selection(self):
        with patch(
            "streamlit.download_button", wraps=st.download_button
        ) as download:
            app = self.enable()
            app.selectbox(key="rea_object").select("customers").run()
            reports = [
                json.loads(call.args[1])
                for call in download.call_args_list
                if call.args
                and call.args[0] == "Download REA demo report"
            ]

        self.assertFalse(app.exception)
        self.assertEqual(self.metrics(app), ["2", "2", "0"])
        self.assertEqual(reports[-1]["changed_object"], "customers")
        self.assertEqual(
            {
                item["object"]
                for item in reports[-1]["potentially_affected"]
            },
            {"customer_directory", "regional_sales"},
        )

    def test_leaf_clears_previous_impacts(self):
        app = self.enable()
        app.selectbox(key="rea_object").select("regional_sales").run()
        self.assertFalse(app.exception)
        self.assertEqual(self.metrics(app), ["0", "0", "0"])
        self.assertFalse(any(
            "hop(s)" in item.value for item in app.markdown
        ))
        self.assertTrue(any(
            "bundled REA fixture" in item.value for item in app.info
        ))

    def test_missing_or_invalid_evidence_shows_no_rea_metrics(self):
        errors = [
            FileNotFoundError("private path"),
            ValueError("bad schema"),
        ]
        for error in errors:
            with self.subTest(error=type(error).__name__):
                with patch(
                    "src.rea_demo.check_evidence", side_effect=error
                ):
                    app = self.enable()
                self.assertFalse(app.exception)
                self.assertFalse(self.metrics(app))
                self.assertTrue(any(
                    "REA demo verification failed" in item.value
                    for item in app.error
                ))

    def test_failed_recheck_does_not_offer_previous_download(self):
        app = self.enable()
        with patch(
            "src.rea_demo.check_evidence",
            side_effect=ValueError("changed evidence"),
        ):
            app.run()

        self.assertFalse(app.exception)
        self.assertFalse(self.metrics(app))
        self.assertFalse(any(
            item.proto.label == "Download REA demo report"
            for item in app.get("download_button")
        ))
