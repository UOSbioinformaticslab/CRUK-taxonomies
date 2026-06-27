import argparse
import copy
import json
import logging
import sys
from pathlib import Path
from datetime import datetime


# ---------------------------------------------------------------------------
# Project paths
# ---------------------------------------------------------------------------

PROJECT_ROOT = Path(__file__).resolve().parents[2]
PYTHON_HELPERS = PROJECT_ROOT / "python_helpers"
sys.path.insert(0, str(PYTHON_HELPERS))

from mapping_program_special import map_special_cruk_terms


DUMMY_DATA_DIR = PROJECT_ROOT / "tests" / "dummy_data" / "special"
DIFFICULT_DUMMY_DATA_DIR = PROJECT_ROOT / "tests" / "difficult_dummy_data" / "special"
OUTPUT_DIR = PROJECT_ROOT / "tests" / "validation_outputs" / "special"
LOG_DIR = PROJECT_ROOT / "logs" / "special"


# ---------------------------------------------------------------------------
# File helpers
# ---------------------------------------------------------------------------

def load_json_file(file_path):
    file_path = Path(file_path)

    with open(file_path, encoding="utf-8") as file:
        return json.load(file)


def save_json_file(data, file_path):
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

    difficult_path = DIFFICULT_DUMMY_DATA_DIR / dataset_file
    if difficult_path.exists():
        return difficult_path

    raise FileNotFoundError(f"Dataset file not found: {dataset_file}")


# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------

def setup_logging(dataset_path, verbose=False):
    LOG_DIR.mkdir(parents=True, exist_ok=True)

    dataset_path = Path(dataset_path)
    dataset_name = dataset_path.stem
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    log_file = LOG_DIR / f"{dataset_name}_special_{timestamp}.log"

    logger = logging.getLogger(f"special_mapping_{dataset_name}_{timestamp}")
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

    logger.info("Logging started")
    logger.info("Log file: %s", log_file)

    return logger, str(log_file)


# ---------------------------------------------------------------------------
# Deduplication helpers
# ---------------------------------------------------------------------------

def deduplicate_by_id(items):
    seen = set()
    unique_items = []

    for item in items:
        if not isinstance(item, dict):
            continue

        item_id = item.get("id")

        if item_id is not None:
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


def objects_to_label_list(objects):
    return [obj.get("label") for obj in objects if isinstance(obj, dict)]


# ---------------------------------------------------------------------------
# Dataset parsing helpers
# ---------------------------------------------------------------------------

def extract_expected_outputs(dataset):
    """
    Extract CRUK and TCGA filters already present in the dummy dataset.

    These are treated as the expected outputs for validation.
    """
    expected_cruk = []
    expected_tcga = []
    dataset_filters = dataset.get("datasetFilters", [])

    def search_node(node):
        if isinstance(node, dict):
            category = node.get("category")

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


def remove_existing_output_filters(dataset_filters):
    """
    Remove existing CRUK and TCGA output filters before adding newly predicted
    special-mapped results.

    For CRUK-label-driven special rules, the first CRUK term is kept as the
    input term. Additional CRUK/TCGA outputs are removed and regenerated.
    """
    cleaned_filters = []
    kept_input_cruk = False

    for item in dataset_filters:
        if not isinstance(item, dict):
            cleaned_filters.append(item)
            continue

        category = item.get("category")

        if category == "crukTerms":
            if not kept_input_cruk:
                cleaned_filters.append(item)
                kept_input_cruk = True

        elif category == "cancerTypes":
            continue

        else:
            cleaned_filters.append(item)

    return cleaned_filters


def extract_existing_cruk_from_cleaned_filters(cleaned_filters):
    existing_cruk = []

    for item in cleaned_filters:
        if isinstance(item, dict) and item.get("category") == "crukTerms":
            existing_cruk.append({
                "id": item.get("id"),
                "label": item.get("label"),
                "category": item.get("category"),
                "primaryGroup": item.get("primaryGroup"),
                "description": item.get("description", "")
            })

    return deduplicate_by_id(existing_cruk)


# ---------------------------------------------------------------------------
# Special mapping logic
# ---------------------------------------------------------------------------

def apply_special_mapping_to_dataset(dataset):
    """
    Apply special mapping to one dataset and append resolved CRUK/TCGA objects.

    This validates schema_special_1.1.2.json behaviour using dummy datasets.
    """
    updated_dataset = copy.deepcopy(dataset)

    dataset_filters = updated_dataset.get("datasetFilters", [])

    if not isinstance(dataset_filters, list):
        raise ValueError("datasetFilters must be a list in this dummy-data validator.")

    expected_cruk, expected_tcga = extract_expected_outputs(dataset)

    cleaned_filters = remove_existing_output_filters(dataset_filters)

    special_result = map_special_cruk_terms(cleaned_filters)

    resolved_cruk_objects = special_result.get("resolved_cruk_objects", []) or []
    resolved_tcga_objects = special_result.get("resolved_tcga_objects", []) or []

    existing_cruk_objects = extract_existing_cruk_from_cleaned_filters(cleaned_filters)

    existing_ids = {
        item.get("id")
        for item in cleaned_filters
        if isinstance(item, dict) and item.get("id") is not None
    }

    added_cruk_objects = []
    for obj in resolved_cruk_objects:
        obj_id = obj.get("id")

        if obj_id not in existing_ids:
            added_cruk_objects.append(obj)
            existing_ids.add(obj_id)

    added_tcga_objects = []
    for obj in resolved_tcga_objects:
        obj_id = obj.get("id")

        if obj_id not in existing_ids:
            added_tcga_objects.append(obj)
            existing_ids.add(obj_id)

    predicted_cruk_objects = deduplicate_by_id(existing_cruk_objects + added_cruk_objects)
    predicted_tcga_objects = deduplicate_by_id(added_tcga_objects)

    updated_dataset["datasetFilters"] = (
        cleaned_filters
        + added_cruk_objects
        + added_tcga_objects
    )

    expected_cruk_labels = objects_to_label_list(expected_cruk)
    predicted_cruk_labels = objects_to_label_list(predicted_cruk_objects)

    expected_tcga_labels = objects_to_label_list(expected_tcga)
    predicted_tcga_labels = objects_to_label_list(predicted_tcga_objects)

    cruk_label_match = predicted_cruk_labels == expected_cruk_labels
    tcga_label_match = predicted_tcga_labels == expected_tcga_labels

    missing_labels_in_label_key_dict = special_result.get(
        "missing_labels_in_label_key_dict", []
    ) or []

    missing_labels_in_filter_data = special_result.get(
        "missing_labels_in_filter_data", []
    ) or []

    encountered_problems = []

    if missing_labels_in_label_key_dict:
        encountered_problems.append(
            "Some returned labels were missing from label_key_dict."
        )

    if missing_labels_in_filter_data:
        encountered_problems.append(
            "Some returned labels were missing from filter_data."
        )

    passed = (
        cruk_label_match
        and tcga_label_match
        and not encountered_problems
    )

    summary = {
        "input": special_result.get("input"),
        "matched_rule_names": special_result.get("matched_rule_names", []),
        "return_cruk_labels": special_result.get("return_cruk_labels", []),
        "return_tcga_labels": special_result.get("return_tcga_labels", []),
        "expected_cruk_labels": expected_cruk_labels,
        "predicted_cruk_labels": predicted_cruk_labels,
        "expected_tcga_labels": expected_tcga_labels,
        "predicted_tcga_labels": predicted_tcga_labels,
        "cruk_label_match": cruk_label_match,
        "tcga_label_match": tcga_label_match,
        "passed": passed,
        "missing_labels_in_label_key_dict": missing_labels_in_label_key_dict,
        "missing_labels_in_filter_data": missing_labels_in_filter_data,
        "added_cruk_filters": added_cruk_objects,
        "added_tcga_filters": added_tcga_objects,
        "number_of_added_cruk_filters": len(added_cruk_objects),
        "number_of_added_tcga_filters": len(added_tcga_objects),
        "encountered_problems": deduplicate_strings(encountered_problems)
    }

    return updated_dataset, summary


# ---------------------------------------------------------------------------
# Output paths
# ---------------------------------------------------------------------------

def build_output_filename(input_path):
    input_path = Path(input_path)
    return OUTPUT_DIR / f"{input_path.stem}_special_with_mapped_filters.json"


def build_summary_filename(input_path):
    input_path = Path(input_path)
    return OUTPUT_DIR / f"{input_path.stem}_special_mapping_output.json"


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Apply schema_special_1.1.2.json mapping to a dummy dataset."
    )

    parser.add_argument(
        "dataset_file",
        help=(
            "Name or path of the dummy dataset JSON file inside "
            "tests/dummy_data/special or tests/difficult_dummy_data/special"
        )
    )

    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="Enable verbose logging"
    )

    args = parser.parse_args()

    input_path = resolve_dataset_path(args.dataset_file)

    logger, log_file = setup_logging(input_path, verbose=args.verbose)

    logger.info("Starting special dummy mapping run")
    logger.info("Resolved dataset path: %s", input_path)

    dataset = load_json_file(input_path)

    updated_dataset, summary = apply_special_mapping_to_dataset(dataset)
    summary["log_file"] = log_file
    summary["input_dataset_file"] = input_path.name

    output_path = build_output_filename(input_path)
    summary_path = build_summary_filename(input_path)

    save_json_file(updated_dataset, output_path)
    save_json_file(summary, summary_path)

    logger.info("Special mapping completed")
    logger.info("Matched rules: %s", summary["matched_rule_names"])
    logger.info("Returned CRUK labels: %s", summary["return_cruk_labels"])
    logger.info("Returned TCGA labels: %s", summary["return_tcga_labels"])
    logger.info("Predicted CRUK labels: %s", summary["predicted_cruk_labels"])
    logger.info("Expected CRUK labels: %s", summary["expected_cruk_labels"])
    logger.info("Predicted TCGA labels: %s", summary["predicted_tcga_labels"])
    logger.info("Expected TCGA labels: %s", summary["expected_tcga_labels"])
    logger.info("CRUK label match: %s", summary["cruk_label_match"])
    logger.info("TCGA label match: %s", summary["tcga_label_match"])
    logger.info("Passed: %s", summary["passed"])
    logger.info("Missing labels in label_key_dict: %s", summary["missing_labels_in_label_key_dict"])
    logger.info("Missing labels in filter_data: %s", summary["missing_labels_in_filter_data"])
    logger.info("Added CRUK filters: %s", summary["added_cruk_filters"])
    logger.info("Added TCGA filters: %s", summary["added_tcga_filters"])
    logger.info("Saved output to: %s", output_path)
    logger.info("Saved summary to: %s", summary_path)


if __name__ == "__main__":
    main()

