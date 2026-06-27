import csv
import re
import sys
from pathlib import Path


csv.field_size_limit(sys.maxsize)


SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_DIR = SCRIPT_DIR.parent

MAP_FILE = PROJECT_DIR / "00_source_files" / "der2_sRefset_SimpleMapSnapshot_INT_20260501.txt"
DESCRIPTION_FILE = PROJECT_DIR / "00_source_files" / "sct2_Description_Snapshot-en_INT_20260501.txt"

OUTPUT_FILE = SCRIPT_DIR / "snomed_to_icdo_map_snomed_order.tsv"


ICDO_MAP_REFSET_ID = "446608001"
FSN_TYPE = "900000000000003001"
SYNONYM_TYPE = "900000000000013009"


def clean_fsn(term: str) -> str:
    return re.sub(r"\s*\([^)]*\)$", "", term).strip()


def load_icdo_map_rows(map_file: Path):
    rows = []
    snomed_codes = set()

    with map_file.open("r", encoding="utf-8") as f:
        reader = csv.DictReader(f, delimiter="\t")

        for row in reader:
            if row.get("active") != "1":
                continue

            if row.get("refsetId") != ICDO_MAP_REFSET_ID:
                continue

            snomed_code = row["referencedComponentId"]
            icdo_code = row["mapTarget"]

            rows.append((snomed_code, icdo_code))
            snomed_codes.add(snomed_code)

    return rows, snomed_codes


def choose_best_description(existing, term, type_id):
    if type_id == FSN_TYPE:
        term = clean_fsn(term)

    if existing is None:
        return {"term": term, "type": type_id}

    existing_type = existing["type"]
    existing_term = existing["term"]

    # Prefer synonym over FSN because it is usually cleaner
    if existing_type == FSN_TYPE and type_id == SYNONYM_TYPE:
        return {"term": term, "type": type_id}

    # If there are multiple synonyms, keep the shorter one
    if existing_type == SYNONYM_TYPE and type_id == SYNONYM_TYPE:
        if len(term) < len(existing_term):
            return {"term": term, "type": type_id}

    return existing


def load_descriptions(description_file: Path, needed_codes: set):
    descriptions = {}

    with description_file.open("r", encoding="utf-8") as f:
        reader = csv.DictReader(f, delimiter="\t")

        for row in reader:
            if row.get("active") != "1":
                continue

            if row.get("languageCode") != "en":
                continue

            concept_id = row.get("conceptId")

            if concept_id not in needed_codes:
                continue

            type_id = row.get("typeId")

            if type_id not in {FSN_TYPE, SYNONYM_TYPE}:
                continue

            term = row["term"]

            descriptions[concept_id] = choose_best_description(
                descriptions.get(concept_id),
                term,
                type_id,
            )

    return {code: value["term"] for code, value in descriptions.items()}


def write_output(rows, descriptions, output_file: Path):
    missing_descriptions = 0

    with output_file.open("w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f, delimiter="\t")
        writer.writerow(["SNOMED descriptor", "SNOMED code", "ICD-O code"])

        for snomed_code, icdo_code in rows:
            descriptor = descriptions.get(snomed_code, "")

            if descriptor == "":
                missing_descriptions += 1

            writer.writerow([descriptor, snomed_code, icdo_code])

    return missing_descriptions


def main():
    print("Reading ICD-O map file...")
    rows, needed_codes = load_icdo_map_rows(MAP_FILE)

    print(f"ICD-O map rows found: {len(rows)}")
    print(f"Unique SNOMED codes needed: {len(needed_codes)}")

    print("Reading SNOMED description file...")
    descriptions = load_descriptions(DESCRIPTION_FILE, needed_codes)

    print(f"Descriptions found: {len(descriptions)}")

    missing = write_output(rows, descriptions, OUTPUT_FILE)

    print(f"Done. Output file created: {OUTPUT_FILE}")
    print(f"Rows missing description: {missing}")


if __name__ == "__main__":
    main()