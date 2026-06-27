import csv
import re
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_DIR = SCRIPT_DIR.parent

INPUT_FILE = PROJECT_DIR / "01_SNOMED_order" / "snomed_to_icdo_map_snomed_order.tsv"
OUTPUT_FILE = SCRIPT_DIR / "snomed_to_icdo_map_icdo_order.tsv"


def sort_key(row):
    icdo_code = row[2].strip()

    # Topography codes, e.g. C00.0, C47.5
    match = re.match(r"^C(\d{2})(?:\.(\d))?$", icdo_code)
    if match:
        main_code = int(match.group(1))
        sub_code = int(match.group(2)) if match.group(2) is not None else -1
        return (0, main_code, sub_code, row[0])

    # Morphology / histology codes, e.g. 8200/3, 9450/3
    match = re.match(r"^(\d{4})/(\d)$", icdo_code)
    if match:
        morphology_code = int(match.group(1))
        behaviour_code = int(match.group(2))
        return (1, morphology_code, behaviour_code, row[0])

    # Any unexpected format goes last
    return (2, icdo_code, row[0])


def main():
    print("Reading SNOMED-order file...")

    with INPUT_FILE.open("r", encoding="utf-8", newline="") as infile:
        reader = csv.reader(infile, delimiter="\t")
        header = next(reader)
        rows = list(reader)

    print(f"Rows read: {len(rows)}")

    rows_sorted = sorted(rows, key=sort_key)

    with OUTPUT_FILE.open("w", encoding="utf-8", newline="") as outfile:
        writer = csv.writer(outfile, delimiter="\t")
        writer.writerow(header)
        writer.writerows(rows_sorted)

    print(f"Done. Output file created: {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
    