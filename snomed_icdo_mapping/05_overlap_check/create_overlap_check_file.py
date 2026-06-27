# Compare the project ICD-O labels with the SNOMED-to-ICD-O mapping.
# This helps show which ICD-O codes in our project also appear in the SNOMED map,
# and how many SNOMED descriptors map to each ICD-O code.

import csv
import json
import re
from collections import defaultdict
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_DIR = SCRIPT_DIR.parent

PROJECT_LABEL_FILE = PROJECT_DIR / "label_key_dict.json"
SNOMED_MAP_FILE = PROJECT_DIR / "02_ICDO_order" / "snomed_to_icdo_map_icdo_order.tsv"

OUTPUT_FILE = SCRIPT_DIR / "icdo_project_snomed_overlap.tsv"


def extract_icdo_code(label):
    """
    Extracts ICD-O code from the start of a project label.
    Examples:
    C49.0 Connective tissue... -> C49.0
    C50 Breast -> C50
    8200/3 Adenocystic carcinoma -> 8200/3
    """
    label = label.strip()

    match = re.match(r"^(C\d{2}(?:\.\d)?|\d{4}/\d)\b", label)
    if match:
        return match.group(1)

    return None


def load_project_icdo_labels():
    """
    Loads ICD-O labels and internal keys from label_key_dict.json.
    """
    with PROJECT_LABEL_FILE.open("r", encoding="utf-8") as f:
        label_key_dict = json.load(f)

    project_codes = {}

    for label, key in label_key_dict.items():
        icdo_code = extract_icdo_code(label)

        if icdo_code:
            project_codes[icdo_code] = {
                "project_label": label,
                "project_key": key,
            }

    return project_codes


def load_snomed_mapping_summary():
    """
    Groups SNOMED descriptors by ICD-O code.
    """
    icdo_to_snomed = defaultdict(list)

    with SNOMED_MAP_FILE.open("r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f, delimiter="\t")

        for row in reader:
            icdo_code = row["ICD-O code"].strip()
            snomed_descriptor = row["SNOMED descriptor"].strip()
            snomed_code = row["SNOMED code"].strip()

            icdo_to_snomed[icdo_code].append(
                (snomed_descriptor, snomed_code)
            )

    return icdo_to_snomed


def main():
    print("Loading project ICD-O labels...")
    project_codes = load_project_icdo_labels()

    print("Loading SNOMED-to-ICD-O map...")
    icdo_to_snomed = load_snomed_mapping_summary()

    rows = []

    for icdo_code, project_info in project_codes.items():
        if icdo_code not in icdo_to_snomed:
            continue

        unique_snomed_items = sorted(set(icdo_to_snomed[icdo_code]))

        examples = [
            f"{descriptor} ({code})"
            for descriptor, code in unique_snomed_items[:5]
        ]

        rows.append({
            "ICD-O code": icdo_code,
            "Project ICD-O label": project_info["project_label"],
            "Project key": project_info["project_key"],
            "Number of SNOMED descriptors": len(unique_snomed_items),
            "Example SNOMED descriptors": "; ".join(examples),
        })

    rows.sort(
        key=lambda row: (
            row["ICD-O code"].startswith("C") is False,
            row["ICD-O code"]
        )
    )

    with OUTPUT_FILE.open("w", encoding="utf-8", newline="") as f:
        fieldnames = [
            "ICD-O code",
            "Project ICD-O label",
            "Project key",
            "Number of SNOMED descriptors",
            "Example SNOMED descriptors",
        ]

        writer = csv.DictWriter(f, fieldnames=fieldnames, delimiter="\t")
        writer.writeheader()
        writer.writerows(rows)

    print(f"Done. Output file created: {OUTPUT_FILE}")
    print(f"Matched ICD-O codes: {len(rows)}")


if __name__ == "__main__":
    main()