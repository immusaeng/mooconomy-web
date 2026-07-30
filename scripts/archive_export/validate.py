"""dryrun_output/*.json을 schemas/*.schema.json으로 검증한다(읽기 전용)."""
import json
import os
import jsonschema


def validate_all(out_dir, schemas_dir):
    checks = [
        ("market_snapshots.json", "market-snapshot.schema.json"),
        ("temperature_observations.json", "temperature-observation.schema.json"),
        ("question_records.json", "question-record.schema.json"),
    ]
    results = {}
    for data_file, schema_file in checks:
        data_path = os.path.join(out_dir, data_file)
        schema_path = os.path.join(schemas_dir, schema_file)
        with open(data_path, encoding="utf-8") as f:
            records = json.load(f)
        with open(schema_path, encoding="utf-8") as f:
            schema = json.load(f)
        errors = []
        for rec in records:
            try:
                jsonschema.validate(instance=rec, schema=schema)
            except jsonschema.ValidationError as e:
                errors.append(f"{rec.get('snapshot_id') or rec.get('observation_id') or rec.get('question_id')}: {e.message}")
        results[data_file] = {"count": len(records), "errors": errors, "status": "PASS" if not errors else "FAIL"}
    return results


if __name__ == "__main__":
    import sys
    out_dir = sys.argv[1] if len(sys.argv) > 1 else "scripts/archive_export/dryrun_output"
    schemas_dir = sys.argv[2] if len(sys.argv) > 2 else "schemas"
    results = validate_all(out_dir, schemas_dir)
    print(json.dumps(results, ensure_ascii=False, indent=2))
