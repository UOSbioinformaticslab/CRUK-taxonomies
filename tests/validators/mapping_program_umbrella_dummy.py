import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

INPUT_DIR = ROOT / "tests" / "dummy_data" / "umbrella"
OUTPUT_DIR = ROOT / "tests" / "validation_outputs" / "umbrella"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

TESTS = [
    {
        "input_file": "umbrella_C69_C72.json",
        "expected_matched_level": "umbrella",
        "expected_cruk": ["Eye cancer", "Brain tumours", "Spinal cord tumours"],
    },
    {
        "input_file": "child_C71_brain.json",
        "expected_matched_level": "intermediate",
        "expected_cruk": ["Brain tumours"],
    },
    {
        "input_file": "umbrella_C40_C41.json",
        "expected_matched_level": "umbrella",
        "expected_cruk": ["Bone cancer"],
    },
    {
        "input_file": "child_C40_0_bone.json",
        "expected_matched_level": "complex",
        "expected_cruk": ["Bone cancer"],
    },
]


def get_first_topography_label(dataset_path):
    with open(dataset_path, encoding="utf-8") as f:
        data = json.load(f)

    for item in data.get("datasetFilters", []):
        if item.get("category") == "icdOTopography":
            return item.get("label")

    raise ValueError(f"No icdOTopography label found in {dataset_path}")


def run_runner(label):
    command = [
        "python3",
        str(ROOT / "python_helpers" / "runner.py"),
        "--label",
        label,
    ]

    completed = subprocess.run(
        command,
        cwd=ROOT,
        capture_output=True,
        text=True,
    )

    if completed.returncode != 0:
        print("Runner command failed:")
        print(" ".join(command))
        print("\nSTDOUT:")
        print(completed.stdout)
        print("\nSTDERR:")
        print(completed.stderr)
        raise RuntimeError("Runner failed")

    json_start = completed.stdout.find("{")
    if json_start == -1:
        print("No JSON output found.")
        print(completed.stdout)
        raise RuntimeError("No JSON output found")

    return json.loads(completed.stdout[json_start:])


def cruk_labels(output):
    labels = []
    for result in output.get("results", []):
        for item in result.get("CRUK", []):
            labels.append(item.get("label"))
    return labels


def main():
    summary = []

    for test in TESTS:
        dataset_path = INPUT_DIR / test["input_file"]
        label = get_first_topography_label(dataset_path)

        output = run_runner(label)

        output_file = OUTPUT_DIR / test["input_file"].replace(".json", "_output.json")
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(output, f, indent=2, ensure_ascii=False)

        actual_level = output["results"][0]["matched_level"] if output.get("results") else None
        actual_cruk = cruk_labels(output)

        passed = (
            actual_level == test["expected_matched_level"]
            and sorted(actual_cruk) == sorted(test["expected_cruk"])
        )

        summary.append({
            "input_file": test["input_file"],
            "label": label,
            "expected_matched_level": test["expected_matched_level"],
            "actual_matched_level": actual_level,
            "expected_cruk": test["expected_cruk"],
            "actual_cruk": actual_cruk,
            "status": "PASS" if passed else "FAIL",
            "output_file": str(output_file.relative_to(ROOT)),
        })

    summary_file = OUTPUT_DIR / "umbrella_validation_summary.json"
    with open(summary_file, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2, ensure_ascii=False)

    for item in summary:
        print(f"{item['status']}: {item['input_file']} -> {item['actual_matched_level']} -> {item['actual_cruk']}")

    print(f"\nSaved summary to: {summary_file.relative_to(ROOT)}")


if __name__ == "__main__":
    main()