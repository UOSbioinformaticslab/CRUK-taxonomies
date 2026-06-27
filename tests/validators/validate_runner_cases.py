import json
import subprocess
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]

TEST_CASES_FILE = PROJECT_ROOT / "tests" / "dummy_data" / "runner" / "runner_test_cases.json"
OUTPUT_DIR = PROJECT_ROOT / "tests" / "validation_outputs" / "runner"
RUNNER_PATH = PROJECT_ROOT / "python_helpers" / "runner.py"


def run_case(case):
    command = [
        "python3",
        str(RUNNER_PATH),
        "--label",
        case["label"],
        "--category",
        case.get("category", "icdOTopography")
    ]

    if case.get("histology"):
        command.extend(["--histology", case["histology"]])

    if case.get("age_range_max") is not None:
        command.extend(["--age-range-max", str(case["age_range_max"])])

    completed = subprocess.run(
        command,
        cwd=PROJECT_ROOT,
        capture_output=True,
        text=True
    )

    if completed.returncode != 0:
        return {
            "case_name": case["case_name"],
            "passed": False,
            "error": completed.stderr,
            "command": " ".join(command)
        }

    stdout = completed.stdout

    # The runner prints logs before the JSON, so we extract JSON from the first "{"
    json_start = stdout.find("{")
    if json_start == -1:
        return {
            "case_name": case["case_name"],
            "passed": False,
            "error": "No JSON output found",
            "stdout": stdout,
            "command": " ".join(command)
        }

    result = json.loads(stdout[json_start:])

    first_result = result["results"][0] if result.get("results") else {}

    actual_level = first_result.get("matched_level")
    actual_cruk = [item.get("label") for item in first_result.get("CRUK", [])]
    actual_tcga = [item.get("label") for item in first_result.get("TCGA", [])]

    expected_level = case["expected_level"]
    expected_cruk = case["expected_cruk"]
    expected_tcga = case["expected_tcga"]

    level_match = actual_level == expected_level
    cruk_match = actual_cruk == expected_cruk
    tcga_match = actual_tcga == expected_tcga

    passed = level_match and cruk_match and tcga_match and not result.get("unmatched")

    return {
        "case_name": case["case_name"],
        "passed": passed,
        "command": " ".join(command),
        "expected": {
            "matched_level": expected_level,
            "CRUK": expected_cruk,
            "TCGA": expected_tcga
        },
        "actual": {
            "matched_level": actual_level,
            "matched_schema_term": first_result.get("matched_schema_term"),
            "matched_rule": first_result.get("matched_rule"),
            "CRUK": actual_cruk,
            "TCGA": actual_tcga,
            "unmatched": result.get("unmatched", []),
            "encountered_problems": result.get("encountered_problems", [])
        },
        "checks": {
            "level_match": level_match,
            "cruk_match": cruk_match,
            "tcga_match": tcga_match
        }
    }


def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    with open(TEST_CASES_FILE, encoding="utf-8") as file:
        cases = json.load(file)

    summary = []
    passed_count = 0

    for case in cases:
        result = run_case(case)
        summary.append(result)

        if result["passed"]:
            passed_count += 1
            print(f"PASS: {result['case_name']}")
        else:
            print(f"FAIL: {result['case_name']}")

    output = {
        "number_of_cases": len(cases),
        "passed": passed_count,
        "failed": len(cases) - passed_count,
        "results": summary
    }

    output_file = OUTPUT_DIR / "runner_validation_summary.json"

    with open(output_file, "w", encoding="utf-8") as file:
        json.dump(output, file, indent=2, ensure_ascii=False)

    print(f"\nSaved validation summary to: {output_file}")


if __name__ == "__main__":
    main()