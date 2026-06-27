# This script checks ambiguity in the SNOMED-to-ICD-O map.
# It counts how many SNOMED descriptors map to the same ICD-O code.
# This helps show why mapping back from ICD-O to SNOMED can be ambiguous.

import csv
from collections import defaultdict
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_DIR = SCRIPT_DIR.parent

INPUT_FILE = PROJECT_DIR / "02_ICDO_order" / "snomed_to_icdo_map_icdo_order.tsv"
OUTPUT_FILE = SCRIPT_DIR / "icdo_to_snomed_ambiguity_summary.tsv"


def main():
    icdo_to_snomed = defaultdict(list)

    with INPUT_FILE.open("r", encoding="utf-8", newline="") as infile:
        reader = csv.DictReader(infile, delimiter="\t")

        for row in reader:
            icdo_code = row["ICD-O code"].strip()
            snomed_descriptor = row["SNOMED descriptor"].strip()
            snomed_code = row["SNOMED code"].strip()

            icdo_to_snomed[icdo_code].append((snomed_descriptor, snomed_code))

    summary_rows = []

    for icdo_code, snomed_items in icdo_to_snomed.items():
        unique_items = sorted(set(snomed_items))
        count = len(unique_items)

        examples = [
            f"{descriptor} ({code})"
            for descriptor, code in unique_items[:5]
        ]

        summary_rows.append({
            "ICD-O code": icdo_code,
            "Number of SNOMED descriptors": count,
            "Example SNOMED descriptors": "; ".join(examples),
        })

    summary_rows.sort(
        key=lambda row: row["Number of SNOMED descriptors"],
        reverse=True
    )

    with OUTPUT_FILE.open("w", encoding="utf-8", newline="") as outfile:
        fieldnames = [
            "ICD-O code",
            "Number of SNOMED descriptors",
            "Example SNOMED descriptors",
        ]

        writer = csv.DictWriter(outfile, fieldnames=fieldnames, delimiter="\t")
        writer.writeheader()
        writer.writerows(summary_rows)

    print(f"Done. Output file created: {OUTPUT_FILE}")
    print(f"ICD-O codes summarised: {len(summary_rows)}")


if __name__ == "__main__":
    main()