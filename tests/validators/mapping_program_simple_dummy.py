import argparse
import copy
import json
import logging
import os
import sys
from pathlib import Path
from datetime import datetime


# ---------------------------------------------------------------------------
# Project paths
# ---------------------------------------------------------------------------

PROJECT_ROOT = Path(__file__).resolve().parents[2]
PYTHON_HELPERS = PROJECT_ROOT / "python_helpers"
sys.path.insert(0, str(PYTHON_HELPERS))

from mapping_program_simple import get_mapped_terms


DUMMY_DATA_DIR = PROJECT_ROOT / "tests" / "dummy_data" / "simple"
DIFFICULT_DATA_DIR = PROJECT_ROOT / "tests" / "difficult_dummy_data" / "simple_no_mapping"
OUTPUT_DIR = PROJECT_ROOT / "tests" / "validation_outputs" / "simple"
LOG_DIR = PROJECT_ROOT / "logs" / "simple"


# ---------------------------------------------------------------------------
# File helpers
# ---------------------------------------------------------------------------

def load_json_file(filepath):
    with open(filepath, encoding="utf-8") as file:
        return json.load(file)


def save_json_file(filepath, data):
    filepath = Path(filepath)
    filepath.parent.mkdir(parents=True, exist_ok=True)

    with open(filepath, "w", encoding="utf-8") as file:
        json.dump(data, file, indent=2, ensure_ascii=False)


def resolve_dataset_path(dataset_file):
    dataset_path = Path(dataset_file)

    if dataset_path.is_absolute() and dataset_path.exists():
        return dataset_path

    if dataset_path.exists():
        return dataset_path

    simple_path = DUMMY_DATA_DIR / dataset_file
    if simple_path.exists():
        return simple_path

    difficult_path = DIFFICULT_DATA_DIR / dataset_file
    if difficult_path.exists():
        return difficult_path

    raise FileNotFoundError(f"Dataset file not found: {dataset_file}")


# ---------------------------------------------------------------------------
# Deduplication helpers
# ---------------------------------------------------------------------------

def deduplicate_by_id(items):
    seen = set()
    unique_items = []

    for item in items:
        item_id = item.get("id")

        if item_id not in seen:
            seen.add(item_id)
            unique_items.append(item)

    return unique_items


def deduplicate_strings(items):
    seen = set()
    unique_items = []

    for item in items:
        if item not in seen:
            seen.add(item)
            unique_items.append(item)

    return unique_items


# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------

def setup_logger(dataset_path, verbose=False):
    LOG_DIR.mkdir(parents=True, exist_ok=True)

    dataset_name = dataset_path.stem
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_file = LOG_DIR / f"{dataset_name}_simple_{timestamp}.log"

    logger = logging.getLogger(f"simple_mapping_{dataset_name}_{timestamp}")
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
# Dataset parsing
# ---------------------------------------------------------------------------

def collect_icdo_terms_from_dataset(dataset):
    """
    Collect ICD-O topography filters from datasetFilters.

    This validator is for simple mapping only, so it looks for topography-like
    cancer-type terms with labels starting with C.
    """
    dataset_filters = dataset.get("datasetFilters", [])
    collected_terms = []

    def search_node(node):
        if isinstance(node, dict):
            label = node.get("label", "")
            category = node.get("category", "")
            primary_group = node.get("primaryGroup", "")

            if (
                primary_group == "cancer-type"
                and isinstance(label, str)
                and label.startswith("C")
                and category not in ["crukTerms", "cancerTypes"]
            ):
                collected_terms.append({
                    "id": node.get("id"),
                    "label": node.get("label"),
                    "category": node.get("category"),
                    "primaryGroup": node.get("primaryGroup"),
                    "description": node.get("description", "")
                })

            for value in node.values():
                search_node(value)

        elif isinstance(node, list):
            for item in node:
                search_node(item)

    search_node(dataset_filters)
    return deduplicate_by_id(collected_terms)


def extract_expected_outputs(dataset):
    """
    Extract existing CRUK and TCGA filters from the dummy dataset.

    These are treated as expected outputs and compared against the predicted
    simple mapping outputs.
    """
    dataset_filters = dataset.get("datasetFilters", [])
    expected_cruk = []
    expected_tcga = []

    def search_node(node):
        if isinstance(node, dict):
            category = node.get("category", "")

            if category == "crukTerms":
                expected_cruk.append({
                    "id": node.get("id"),
                    "label": node.get("label"),
                    "category": node.get("category"),
                    "primaryGroup": node.get("primaryGroup"),
                    "description": node.get("description", "")
                })

            elif category == "cancerTypes":
                expected_tcga.append({
                    "id": node.get("id"),
                    "label": node.get("label"),
                    "category": node.get("category"),
                    "primaryGroup": node.get("primaryGroup"),
                    "description": node.get("description", "")
                })

            for value in node.values():
                search_node(value)

        elif isinstance(node, list):
            for item in node:
                search_node(item)

    search_node(dataset_filters)
    return deduplicate_by_id(expected_cruk), deduplicate_by_id(expected_tcga)


def objects_to_label_list(objects):
    return [obj.get("label") for obj in objects]


def remove_existing_output_filters(dataset_filters):
    """
    Remove existing CRUK and TCGA output filters from datasetFilters before
    adding newly predicted outputs.
    """
    cleaned_filters = []

    for item in dataset_filters:
        if not isinstance(item, dict):
            cleaned_filters.append(item)
            continue

        category = item.get("category")

        if category not in ["crukTerms", "cancerTypes"]:
            cleaned_filters.append(item)

    return cleaned_filters


# ---------------------------------------------------------------------------
# Output paths
# ---------------------------------------------------------------------------

def build_output_filenames(dataset_path):
    dataset_name = dataset_path.stem

    updated_dataset_output_file = (
        OUTPUT_DIR / f"{dataset_name}_simple_with_mapped_filters.json"
    )

    summary_output_file = (
        OUTPUT_DIR / f"{dataset_name}_simple_mapping_output.json"
    )

    return updated_dataset_output_file, summary_output_file


# ---------------------------------------------------------------------------
# Main validation logic
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Run simple mapping on a dummy dataset and save validation outputs."
    )

    parser.add_argument(
        "dataset_file",
        help=(
            "Path to the dummy dataset JSON file, or just the filename inside "
            "tests/dummy_data/simple or tests/difficult_dummy_data/simple_no_mapping"
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
    logger.info("Starting simple dummy mapping run")
    logger.info("Resolved dataset path: %s", dataset_path)

    dataset = load_json_file(dataset_path)
    updated_dataset = copy.deepcopy(dataset)

    dataset_filters = updated_dataset.get("datasetFilters", [])

    if not isinstance(dataset_filters, list):
        logger.error("datasetFilters must be a list")
        raise ValueError("datasetFilters must be a list in this dummy-data validator.")

    icdo_terms = collect_icdo_terms_from_dataset(dataset)
    expected_cruk, expected_tcga = extract_expected_outputs(dataset)

    encountered_problems = []
    case_results = []
    all_predicted_cruk = []
    all_predicted_tcga = []

    logger.info("Number of ICD-O input terms found: %d", len(icdo_terms))
    logger.info("Expected CRUK terms found in dataset: %d", len(expected_cruk))
    logger.info("Expected TCGA terms found in dataset: %d", len(expected_tcga))

    if not icdo_terms:
        problem = "No ICD-O cancer-type terms found in datasetFilters."
        encountered_problems.append(problem)
        logger.warning(problem)

    for term in icdo_terms:
        logger.info("Processing input term: %s", term.get("label"))

        matched_term, cruk_objects, tcga_objects = get_mapped_terms(term)

        if matched_term is None:
            problem = f"No simple mapping found for input term: {term.get('label')}"
            encountered_problems.append(problem)
            logger.warning(problem)
        else:
            logger.info("Matched schema term: %s", matched_term)

        logger.debug("CRUK results: %s", [obj.get("label") for obj in cruk_objects])
        logger.debug("TCGA results: %s", [obj.get("label") for obj in tcga_objects])

        all_predicted_cruk.extend(cruk_objects)
        all_predicted_tcga.extend(tcga_objects)

        case_results.append({
            "input_term": term,
            "matched_schema_term": matched_term,
            "cruk_results": cruk_objects,
            "tcga_results": tcga_objects
        })

    all_predicted_cruk = deduplicate_by_id(all_predicted_cruk)
    all_predicted_tcga = deduplicate_by_id(all_predicted_tcga)

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
        "log_file": log_file
    }

    save_json_file(updated_dataset_output_file, updated_dataset)
    save_json_file(summary_output_file, summary_output)

    logger.info("Updated dataset saved to: %s", updated_dataset_output_file)
    logger.info("Summary output saved to: %s", summary_output_file)
    logger.info("Log file saved to: %s", log_file)
    logger.info("Simple dummy mapping run completed successfully")


if __name__ == "__main__":
    main()
