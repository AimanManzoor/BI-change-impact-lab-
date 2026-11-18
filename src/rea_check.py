"""Verify REA-recovered SQL against our synthetic retail reference."""
import argparse
import hashlib
import json
import tempfile
from pathlib import Path

from src.impact import downstream, verify_fixture

EXPECTED = {
    "tables": {"customers", "orders"},
    "views": {
        "order_summary", "regional_sales", "customer_directory"
    },
}


def recover_sql(evidence):
    schemas = []

    def visit(value):
        if isinstance(value, dict):
            schema = value.get("schema")
            if isinstance(schema, dict) and all(
                isinstance(schema.get(kind), list)
                for kind in EXPECTED
            ):
                schemas.append(schema)
            for item in value.values():
                visit(item)
        elif isinstance(value, list):
            for item in value:
                visit(item)

    visit(evidence)

    if len(schemas) != 1:
        raise ValueError("Expected exactly one complete schema object")

    statements = []
    for kind, names in EXPECTED.items():
        objects = schemas[0][kind]
        if not all(
            isinstance(item, dict)
            and isinstance(item.get("name"), str)
            for item in objects
        ):
            raise ValueError("Malformed schema object")

        if (
            len(objects) != len(names)
            or {item["name"] for item in objects} != names
        ):
            raise ValueError(
                "Schema objects differ from the retail reference"
            )

        for item in sorted(objects, key=lambda item: item["name"]):
            sql = item.get("sql")
            if not isinstance(sql, str) or not sql.strip():
                raise ValueError("Missing SQL declaration")
            statements.append(sql.strip().rstrip(";") + ";")

    return "\n\n".join(statements) + "\n"


def check_evidence(path):
    from graphify.extract import extract

    raw = Path(path).read_bytes()
    sql = recover_sql(json.loads(raw))

    with tempfile.TemporaryDirectory(prefix="bi-rea-") as temporary:
        directory = Path(temporary)
        recovered = directory / "recovered.sql"
        recovered.write_text(sql, encoding="utf-8")

        result = extract([recovered], root=directory)
        if (
            result.get("failed_sources")
            or not result.get("extracted_sources")
        ):
            raise ValueError("SQL extraction was incomplete")

        _, edges = verify_fixture(result)
        if len(edges) != 4 or any(
            edge.get("confidence") != "EXTRACTED"
            for edge in edges
        ):
            raise ValueError("Expected four extracted dependencies")

        impacts = downstream(result, "orders")
        observed = [
            (item["object"], item["depth"]) for item in impacts
        ]
        if observed != [
            ("order_summary", 1), ("regional_sales", 2)
        ]:
            raise ValueError("Downstream impacts differ from reference")

        for item in impacts:
            for hop in item["evidence_path"]:
                hop["source_file"] = "recovered.sql"

    return {
        "status": "reference_verified",
        "scope": "synthetic retail fixture only",
        "rea_evidence_sha256": hashlib.sha256(raw).hexdigest(),
        "recovered_sql": sql,
        "recovered_sql_sha256": hashlib.sha256(
            sql.encode()
        ).hexdigest(),
        "verified_objects": 5,
        "verified_dependencies": 4,
        "changed_object": "orders",
        "potentially_affected": impacts,
        "human_review_required": True,
        "model_calls": 0,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--evidence", type=Path, required=True)
    args = parser.parse_args()

    try:
        report = check_evidence(args.evidence)
    except (ValueError, OSError) as error:
        parser.exit(1, f"Stopped: {error}\n")

    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
