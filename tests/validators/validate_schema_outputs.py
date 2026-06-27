import json
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]

SCHEMAS_DIR = PROJECT_ROOT / "schemas"
LABEL_KEY_DICT_PATH = PROJECT_ROOT / "label_key_dict.json"
FILTER_DATA_PATH = PROJECT_ROOT / "longer_filter_data.json"
OUTPUT_DIR = PROJECT_ROOT / "tests" / "validation_outputs" / "schema"


SCHEMA_FILES = [
    "schema_simple_1.1.2.json",
    "schema_intermediate_1.1.2.json",
    "schema_complex_1.1.2.json",
    "schema_special_1.1.2.json",
    "schema_rare_1.1.2.json",
]


OUTPUT_KEYS = {
    "cruk",
    "tcga",
    "CRUK",
    "TCGA",
    "default_cruk",
    "default_tcga",
    "default_CRUK",
    "default_TCGA",
    "return_cruk",
    "return_tcga",
    "return_CRUK",
    "return_TCGA",
    "cruk_terms",
    "tcga_terms",
}


def load_json(path):
    with open(path, encoding="utf-8") as file:
        return json.load(file)


def save_json(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)

    with open(path, "w", encoding="utf-8") as file:
        json.dump(data, file, indent=2, ensure_ascii=False)


def collect_filter_labels(filter_data):
    labels = set()

    def search_node(node):
        if isinstance(node, dict):
            label = node.get("label")
            if isinstance(label, str):
                labels.add(label)

            for value in node.values():
                search_node(value)

        elif isinstance(node, list):
            for item in node:
                search_node(item)

    search_node(filter_data)
    return labels


def collect_schema_output_labels(schema_data):
    found = []

    def search_node(node, path="root"):
        if isinstance(node, dict):
            for key, value in node.items():
                current_path = f"{path}.{key}"

                if key in OUTPUT_KEYS:
                    if isinstance(value, list):
                        for label in value:
                            if isinstance(label, str):
                                found.append({
                                    "label": label,
                                    "key": key,
                                    "path": current_path
                                })

                    elif isinstance(value, str):
                        found.append({
                            "label": value,
                            "key": key,
                            "path": current_path
                        })

                search_node(value, current_path)

        elif isinstance(node, list):
            for index, item in enumerate(node):
                search_node(item, f"{path}[{index}]")

    search_node(schema_data)
    return found


def main():
    label_key_dict = load_json(LABEL_KEY_DICT_PATH)
    filter_data = load_json(FILTER_DATA_PATH)

    label_key_labels = set(label_key_dict.keys())
    filter_data_labels = collect_filter_labels(filter_data)

    all_results = []
    total_labels_checked = 0
    total_missing_label_key_dict = 0
    total_missing_filter_data = 0

    for schema_file in SCHEMA_FILES:
        schema_path = SCHEMAS_DIR / schema_file

        if not schema_path.exists():
            all_results.append({
                "schema_file": schema_file,
                "schema_exists": False,
                "problem": "Schema file not found."
            })
            continue

        schema_data = load_json(schema_path)
        output_labels = collect_schema_output_labels(schema_data)

        checked = []
        missing_label_key_dict = []
        missing_filter_data = []

        for item in output_labels:
            label = item["label"]

            in_label_key_dict = label in label_key_labels
            in_filter_data = label in filter_data_labels

            result = {
                "label": label,
                "key": item["key"],
                "path": item["path"],
                "in_label_key_dict": in_label_key_dict,
                "in_filter_data": in_filter_data
            }

            checked.append(result)

            if not in_label_key_dict:
                missing_label_key_dict.append(result)

            if not in_filter_data:
                missing_filter_data.append(result)

        total_labels_checked += len(checked)
        total_missing_label_key_dict += len(missing_label_key_dict)
        total_missing_filter_data += len(missing_filter_data)

        all_results.append({
            "schema_file": schema_file,
            "schema_exists": True,
            "number_of_output_labels_checked": len(checked),
            "number_missing_from_label_key_dict": len(missing_label_key_dict),
            "number_missing_from_filter_data": len(missing_filter_data),
            "missing_from_label_key_dict": missing_label_key_dict,
            "missing_from_filter_data": missing_filter_data,
            "checked_labels": checked
        })

    summary = {
        "number_of_schema_files": len(SCHEMA_FILES),
        "total_output_labels_checked": total_labels_checked,
        "total_missing_from_label_key_dict": total_missing_label_key_dict,
        "total_missing_from_filter_data": total_missing_filter_data,
        "passed": (
            total_missing_label_key_dict == 0
            and total_missing_filter_data == 0
        ),
        "results": all_results
    }

    output_file = OUTPUT_DIR / "schema_output_label_validation_summary.json"
    save_json(output_file, summary)

    print("Schema output label validation completed.")
    print(f"Total labels checked: {total_labels_checked}")
    print(f"Missing from label_key_dict: {total_missing_label_key_dict}")
    print(f"Missing from filter_data: {total_missing_filter_data}")
    print(f"Passed: {summary['passed']}")
    print(f"Saved summary to: {output_file}")


if __name__ == "__main__":
    main()
