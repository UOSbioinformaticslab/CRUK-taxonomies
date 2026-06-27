# Extra file for clarity:
# Some ICD-O codes in the SNOMED map are topography codes starting with "C",
# while others are morphology/histology codes in the xxxx/x format.
# This script separates them into clear columns for easier review.

import csv
import re
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_DIR = SCRIPT_DIR.parent

INPUT_FILE = PROJECT_DIR / "02_ICDO_order" / "snomed_to_icdo_map_icdo_order.tsv"
OUTPUT_FILE = SCRIPT_DIR / "snomed_to_icdo_map_with_code_types.tsv"


def classify_icdo_code(code):
    code = code.strip()

    if re.match(r"^C\d{2}(\.\d)?$", code):
        return "Topography"

    if re.match(r"^\d{4}/\d$", code):
        return "Morphology / histology"

    return "Other / check"


def main():
    print("Reading ICD-O order file...")

    with INPUT_FILE.open("r", encoding="utf-8", newline="") as infile:
        reader = csv.reader(infile, delimiter="\t")
        header = next(reader)
        rows = list(reader)

    print(f"Rows read: {len(rows)}")

    with OUTPUT_FILE.open("w", encoding="utf-8", newline="") as outfile:
        writer = csv.writer(outfile, delimiter="\t")

        writer.writerow(header + ["ICD-O type", "Topography code", "Morphology code"])

        for row in rows:
            icdo_code = row[2].strip()
            icdo_type = classify_icdo_code(icdo_code)

            topography_code = icdo_code if icdo_type == "Topography" else ""
            morphology_code = icdo_code if icdo_type == "Morphology / histology" else ""

            writer.writerow(row + [icdo_type, topography_code, morphology_code])

    print(f"Done. Output file created: {OUTPUT_FILE}")


if __name__ == "__main__":
    main()