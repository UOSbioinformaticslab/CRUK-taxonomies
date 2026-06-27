import argparse
import copy
import json
import logging
import re
import sys
from pathlib import Path
from datetime import datetime


# ---------------------------------------------------------------------------
# Project paths
# ---------------------------------------------------------------------------

PROJECT_ROOT = Path(__file__).resolve().parents[2]
PYTHON_HELPERS = PROJECT_ROOT / "python_helpers"
sys.path.insert(0, str(PYTHON_HELPERS))

from mapping_program_intermediate import (
    get_intermediate_mapped_terms,
    topography_mappings,
)


HISTOLOGY_PATTERN = re.compile(r"^\d{4}/\d")

DUMMY_DATA_DIR = PROJECT_ROOT / "tests" / "dummy_data" / "intermediate"
DIFFICULT_DATA_DIR = PROJECT_ROOT / "tests" / "difficult_dummy_data" / "intermediate_mismatch"
OUTPUT_DIR = PROJECT_ROOT / "tests" / "validation_outputs" / "intermediate"
LOG_DIR = PROJECT_ROOT / "logs" / "intermediate"


# ---------------------------------------------------------------------------
# File helpers
# ---------------------------------------------------------------------------

def load_json_file(file_path):
    with open(file_path, encoding="utf-8") as file:
        return json.load(file)


def save_json_file(file_path, data):
    file_path = Path(file_path)
    file_path.parent.mkdir(parents=True, exist_ok=True)

    with open(file_path, "w", encoding="utf-8") as file:
        json.dump(data, file, indent=2, ensure_ascii=False)


def resolve_dataset_path(dataset_file):
    dataset_path = Path(dataset_file)

    if dataset_path.is_absolute() and dataset_path.exists():
        return dataset_path

    if dataset_path.exists():
        return dataset_path

    dummy_path = DUMMY_DATA_DIR / dataset_file
    if dummy_path.exists():
        return dummy_path

    difficult_path = DIFFICULT_DATA_DIR / dataset_file
    if difficult_path.exists():
        return difficult_path

    raise FileNotFoundError(f"Dataset file not found: {dataset_file}")


# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------

def setup_logger(dataset_path, verbose=False):
    LOG_DIR.mkdir(parents=True, exist_ok=True)

    dataset_name = dataset_path.stem
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_file = LOG_DIR / f"{dataset_name}_intermediate_{timestamp}.log"

    logger = logging.getLogger(f"intermediate_mapping_{dataset_name}_{timestamp}")
    logger.setLevel(logging.DEBUG)
    logger.propagate = False

    if logger.handlers:
        logger.handlers.clear()

    file_handler = logging.FileHandler(log_file, encoding="utf-8")
    file_handler.setLevel(logging.DEBUG)

    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.DEBUG if verbose else logging.INFO)

    formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
    file_handler.setFormatter(formatter)
    console_handler.setFormatter(formatter)

    logger.addHandler(file_handler)
    logger.addHandler(console_handler)

    return logger, str(log_file)


# ---------------------------------------------------------------------------
# Dataset parsing helpers
# ---------------------------------------------------------------------------

def is_histology_filter(filter_obj):
    if not isinstance(filter_obj, dict):
        return False

    label = filter_obj.get("label", "")
    return isinstance(label, str) and bool(HISTOLOGY_PATTERN.match(label.strip()))


def is_benign_histology(histology_label):
    if not isinstance(histology_label, str):
        return False

    histology_label = histology_label.strip()
    return bool(re.match(r"^\d{4}/0\b", histology_label))


def is_intermediate_topography_term(filter_obj):
    if not isinstance(filter_obj, dict):
        return False

    label = filter_obj.get("label", "")
    category = filter_obj.get("category", "")

    return label in topography_mappings or category in topography_mappings


def extract_histology_label(dataset_filters):
    for item in dataset_filters:
        if is_histology_filter(item):
            return item.get("label", "").strip()

    return None


def extract_intermediate_terms(dataset_filters):
    terms = []

    for item in dataset_filters:
        if is_intermediate_topography_term(item):
            terms.append({
                "id": item.get("id"),
                "label": item.get("label"),
                "category": item.get("category"),
                "primaryGroup": item.get("primaryGroup"),
                "description": item.get("description", "")
            })

    return deduplicate_filters_by_id(terms)


def extract_expected_outputs(dataset_filters):
    expected_cruk = []
    expected_tcga = []

    for item in dataset_filters:
        if not isinstance(item, dict):
            continue

        category = item.get("category")

        if category == "crukTerms":
            expected_cruk.append({
                "id": item.get("id"),
                "label": item.get("label"),
                "category": item.get("category"),
                "primaryGroup": item.get("primaryGroup"),
                "description": item.get("description", "")
            })

        elif category == "cancerTypes":
            expected_tcga.append({
                "id": item.get("id"),
                "label": item.get("label"),
                "category": item.get("category"),
                "primaryGroup": item.get("primaryGroup"),
                "description": item.get("description", "")
            })

    return (
        deduplicate_filters_by_id(expected_cruk),
        deduplicate_filters_by_id(expected_tcga),
    )


# ---------------------------------------------------------------------------
# Deduplication and output helpers
# ---------------------------------------------------------------------------

def deduplicate_filters_by_id(filters_list):
    seen = set()
    unique_filters = []

    for item in filters_list:
        item_id = item.get("id")

        if item_id:
            key = ("id", item_id)
        else:
            key = (
                "fallback",
                item.get("label"),
                item.get("category"),
                item.get("primaryGroup"),
            )

        if key not in seen:
            seen.add(key)
            unique_filters.append(item)

    return unique_filters


def deduplicate_strings(items):
    seen = set()
    unique_items = []

    for item in items:
        if item not in seen:
            seen.add(item)
            unique_items.append(item)

    return unique_items


def objects_to_label_list(objects):
    return [obj.get("label") for obj in objects]


def build_case_result(term, histology_label, term_key, cruk_objects, tcga_objects):
    return {
        "input_term": term,
        "histology": histology_label,
        "matched_schema_term": term_key,
        "CRUK": cruk_objects,
        "TCGA": tcga_objects,
    }


def remove_existing_output_filters(dataset_filters):
    cleaned_filters = []

    for item in dataset_filters:
        if not isinstance(item, dict):
            cleaned_filters.append(item)
            continue

        category = item.get("category")

        if category not in ["crukTerms", "cancerTypes"]:
            cleaned_filters.append(item)

    return cleaned_filters


def build_output_filenames(dataset_path):
    dataset_name = dataset_path.stem

    updated_dataset_output_file = (
        OUTPUT_DIR / f"{dataset_name}_intermediate_with_mapped_filters.json"
    )

    summary_output_file = (
        OUTPUT_DIR / f"{dataset_name}_intermediate_mapping_output.json"
    )

    return updated_dataset_output_file, summary_output_file


# ---------------------------------------------------------------------------
# Main validation logic
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Run intermediate mapping on a dummy dataset JSON file."
    )

    parser.add_argument(
        "dataset_file",
        help=(
            "Path to input dataset JSON file, or just the filename inside "
            "tests/dummy_data/intermediate or tests/difficult_dummy_data/intermediate_mismatch"
        )
    )

    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="Enable verbose console logging"
    )

    args = parser.parse_args()

    dataset_path = resolve_dataset_path(args.dataset_file)

    logger, log_file = setup_logger(dataset_path, verbose=args.verbose)
    logger.info("Starting intermediate dummy mapping run")
    logger.info("Resolved dataset path: %s", dataset_path)

    dataset_data = load_json_file(dataset_path)
    updated_dataset = copy.deepcopy(dataset_data)

    dataset_filters = updated_dataset.get("datasetFilters", [])

    if not isinstance(dataset_filters, list):
        logger.error("datasetFilters must be a list")
        raise ValueError("datasetFilters must be a list in this dummy-data validator.")

    histology_label = extract_histology_label(dataset_filters)
    icdo_terms = extract_intermediate_terms(dataset_filters)
    expected_cruk, expected_tcga = extract_expected_outputs(dataset_filters)

    case_results = []
    encountered_problems = []

    logger.info("Number of ICD-O input terms found: %d", len(icdo_terms))
    logger.info("Expected CRUK terms found in dataset: %d", len(expected_cruk))
    logger.info("Expected TCGA terms found in dataset: %d", len(expected_tcga))
    logger.info("Histology found: %s", histology_label)

    if histology_label is None:
        problem = (
            "No histology filter was found in datasetFilters, so override testing may be incomplete."
        )
        encountered_problems.append(problem)
        logger.warning(problem)

    if not icdo_terms:
        problem = (
            "No ICD-O/topography terms matching the intermediate schema were found in datasetFilters."
        )
        encountered_problems.append(problem)
        logger.warning(problem)

    benign_histology = is_benign_histology(histology_label)

    all_predicted_cruk = []
    all_predicted_tcga = []

    for term in icdo_terms:
        logger.info("Processing input term: %s", term.get("label"))

        term_key, cruk_objects, tcga_objects = get_intermediate_mapped_terms(
            term,
            histology_label
        )

        if benign_histology:
            tcga_objects = []

        if term_key is None:
            problem = f"No intermediate mapping found for input term: {term.get('label')}"
            encountered_problems.append(problem)
            logger.warning(problem)
        else:
            logger.info("Matched schema term: %s", term_key)

        logger.debug("CRUK results: %s", [obj.get("label") for obj in cruk_objects])
        logger.debug("TCGA results: %s", [obj.get("label") for obj in tcga_objects])

        all_predicted_cruk.extend(cruk_objects)
        all_predicted_tcga.extend(tcga_objects)

        case_results.append(
            build_case_result(
                term=term,
                histology_label=histology_label,
                term_key=term_key,
                cruk_objects=cruk_objects,
                tcga_objects=tcga_objects,
            )
        )

    all_predicted_cruk = deduplicate_filters_by_id(all_predicted_cruk)
    all_predicted_tcga = deduplicate_filters_by_id(all_predicted_tcga)

    cleaned_filters = remove_existing_output_filters(dataset_filters)
    updated_dataset_filters = cleaned_filters + all_predicted_cruk + all_predicted_tcga
    updated_dataset["datasetFilters"] = updated_dataset_filters

    predicted_cruk_labels = objects_to_label_list(all_predicted_cruk)
    predicted_tcga_labels = objects_to_label_list(all_predicted_tcga)
    expected_cruk_labels = objects_to_label_list(expected_cruk)
    expected_tcga_labels = objects_to_label_list(expected_tcga)

    cruk_label_match = predicted_cruk_labels == expected_cruk_labels
    tcga_label_match = predicted_tcga_labels == expected_tcga_labels

    passed = (
        cruk_label_match
        and tcga_label_match
        and len(encountered_problems) == 0
    )

    logger.info("Predicted CRUK labels: %s", predicted_cruk_labels)
    logger.info("Expected CRUK labels: %s", expected_cruk_labels)
    logger.info("Predicted TCGA labels: %s", predicted_tcga_labels)
    logger.info("Expected TCGA labels: %s", expected_tcga_labels)
    logger.info("CRUK label match: %s", cruk_label_match)
    logger.info("TCGA label match: %s", tcga_label_match)
    logger.info("Passed: %s", passed)

    updated_dataset_output_file, summary_output_file = build_output_filenames(dataset_path)

    summary_output = {
        "input_dataset_file": dataset_path.name,
        "histology": histology_label,
        "number_of_input_filters": len(dataset_filters),
        "number_of_output_filters": len(updated_dataset_filters),
        "number_of_icdo_terms": len(icdo_terms),
        "expected_cruk_labels": expected_cruk_labels,
        "predicted_cruk_labels": predicted_cruk_labels,
        "expected_tcga_labels": expected_tcga_labels,
        "predicted_tcga_labels": predicted_tcga_labels,
        "cruk_label_match": cruk_label_match,
        "tcga_label_match": tcga_label_match,
        "passed": passed,
        "results": case_results,
        "encountered_problems": deduplicate_strings(encountered_problems),
        "log_file": log_file,
    }

    save_json_file(updated_dataset_output_file, updated_dataset)
    save_json_file(summary_output_file, summary_output)

    logger.info("Updated dataset saved to: %s", updated_dataset_output_file)
    logger.info("Summary output saved to: %s", summary_output_file)
    logger.info("Log file saved to: %s", log_file)
    logger.info("Intermediate dummy mapping run completed successfully")


if __name__ == "__main__":
    main()