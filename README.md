# CRUK Taxonomies ICD-O Mapping

This repository contains a rule-based mapping workflow for classifying ICD-O topography and histology inputs into CRUK cancer terms and, where appropriate, TCGA project labels.

## Overview

The workflow takes ICD-O topography and histology filter objects as input, applies a sequence of schema-based mapping rules, and returns generated CRUK and TCGA filter objects in the structure expected by the CRUK Data Hub website.

It was developed to support consistent cancer-type filtering in the CRUK Data Hub and reduce the need for manual lookup when ICD-O code combinations are used.

This repository also includes supplementary SNOMED CT to ICD-O mapping work, located in `snomed_icdo_mapping/`. This work is separate from the main ICD-O to CRUK/TCGA mapping pipeline. See [Supplementary SNOMED CT to ICD-O workflow](#supplementary-snomed-ct-to-icd-o-workflow) for details, including source material and licensing.

## Reproducibility and running the code

No external Python dependencies are required to run the core mapping scripts in `programs/`, including `runner.py` and `generate_results_dictionary.py`. These scripts use only Python standard library modules.

The main mapping pipeline is run using:

```text
programs/runner.py
```

To check how to run the mapping pipeline, use:

```bash
python3 programs/runner.py --help
```

See [Running the mapper](#running-the-mapper) below for a worked example.

### Generating `results_dictionary.json`

The script used to generate `results_dictionary.json` is:

```text
programs/generate_results_dictionary.py
```

This script extracts ICD-O topography and histology labels from `label_key_dict.json`, runs the mapping pipeline across each topography–histology combination, and saves the generated outputs as `results_dictionary.json`.

The `results_dictionary.json` file is included. To generate a new version, run:

```bash
python3 programs/generate_results_dictionary.py --output results_dictionary.json
```

The full dictionary generation may take some time, as it iterates across all extracted ICD-O topography and histology combinations.

## Repository structure

```text
.
├── README.md
├── programs/
│   ├── runner.py
│   ├── generate_results_dictionary.py
│   ├── mapping_utils.py
│   ├── mapping_program_umbrella.py
│   ├── mapping_program_simple.py
│   ├── mapping_program_intermediate.py
│   ├── mapping_program_complex.py
│   ├── mapping_program_special.py
│   └── mapping_program_rare.py
│
├── schemas/
│   ├── schema_umbrella_1.1.2.json
│   ├── schema_simple_1.1.2.json
│   ├── schema_intermediate_1.1.2.json
│   ├── schema_complex_1.1.2.json
│   ├── schema_special_1.1.2.json
│   └── schema_rare_1.1.2.json
│
├── tests/
│   ├── dummy_data/
│   ├── validators/
│   ├── validation_outputs/
│   └── website_validation_workbook/
│
├── snomed_icdo_mapping/
│   ├── 01_SNOMED_order/
│   ├── 02_ICDO_order/
│   ├── 03_annotated/
│   ├── 04_ambiguity_check/
│   ├── 05_overlap_check/
│   └── README.md
│
├── label_key_dict.json
├── longer_filter_data.json
└── results_dictionary.json
```

## How the schemas and programs work together

The JSON schema files define the mapping rules. Each `mapping_program_*.py` file implements the matching logic for its corresponding schema.

For example, `schemas/schema_complex_1.1.2.json` contains complex site-histology rules, and `programs/mapping_program_complex.py` applies those rules during the mapping workflow.

The `programs/runner.py` script coordinates the mapping programs and applies them in sequence.

The `programs/generate_results_dictionary.py` script runs the mapping pipeline repeatedly across extracted ICD-O topography and histology labels to produce `results_dictionary.json`.

## Main input files

### `label_key_dict.json`

Maps filter labels to their corresponding CRUK Data Hub filter IDs.

### `longer_filter_data.json`

Contains the full filter objects used by the CRUK Data Hub, including:

* `id`
* `label`
* `category`
* `primaryGroup`
* `description`

These files allow the mapper to return full Data Hub filter objects, including CRUK and TCGA outputs where applicable, rather than label text only.

## Mapping schemas

The workflow is split into several schema levels. Each schema handles a different type of mapping case.

### Umbrella schema

Handles broad ICD-O topography ranges and umbrella cancer site groupings. These rules are only used when the input matches an umbrella-level term directly, rather than a more specific child topography term.

### Simple schema

Handles direct topography-to-CRUK mappings where histology is not needed.

Example:

```text
C77.9 Lymph node, NOS
→ Secondary cancer
```

### Intermediate schema

Handles mappings where the topography gives a broad cancer site, but histology is needed to refine the output or assign a more specific TCGA label.

Example:

```text
C64 Kidney + 8310/3 Clear cell renal cell carcinoma
→ Kidney cancer
→ KIRC
```

### Complex schema

Handles site-histology combinations where the correct output depends on both anatomical site and tumour type.

Example:

```text
Melanoma histology + eye topography
→ UVM

Melanoma histology + skin topography
→ SKCM
```

### Special schema

Handles special CRUK hierarchy, one-to-many outputs, parent-child return logic, and metadata-related labels.

Examples include returning both a specific child cancer term and its broader parent category where appropriate, or adding metadata-related CRUK terms such as children's cancers, men's cancers, or breast cancer in men.

Example:

```text
Breast cancer in men
→ Breast cancer in men
→ Men's cancer
```

### Rare schema

Handles rare cancer mappings based on topography, histology, direct CRUK label rules, and fallback logic.

These rules are used for rare primary sites, rare histology-driven cancers, and cases where no more specific umbrella, intermediate, complex, special, or simple schema rule applies.

Example:

```text
9540/3 Malignant schwannoma
→ Malignant schwannoma
```

## Mapping order

The runner applies the mapping programs in the following order:

```text
umbrella → intermediate → complex → special → simple → rare
```

The workflow stops once a suitable match is found. The umbrella rules are only used for direct umbrella-level inputs, while more specific site-histology rules are checked before broader simple and rare fallback mappings.

## Output format

The runner response can include:

* `topography_labels`
* `histology_label`
* `existing_cruk_labels`
* `age_range_max`
* `childhood_case_detected`
* `male_case_detected`
* `results`
* `unmatched`
* `encountered_problems`

Each mapped CRUK or TCGA output is returned as a full filter object containing:

* `id`
* `label`
* `category`
* `primaryGroup`
* `description`

Generated filter objects may also include:

```json
{
  "isGenerated": true
}
```

This indicates that the filter was added automatically by the mapping workflow rather than manually selected by the user on the website.

### Example output

```text
Input:
C77.9 Lymph node, NOS
9724/3 Systemic EBV positive T-cell lymphoproliferative disease of childhood
age_range_max: 15

CRUK: Secondary cancer
TCGA: none
childhood_case_detected: true
existing_cruk_labels: Children's cancers
```
## Running the mapper

Run the mapper from the repository root folder.

To see the available command-line options, run:

```bash
python3 programs/runner.py --help
```

The only required command-line argument is `--label`. Optional arguments include `--category`, `--histology`, `--existing-cruk-label`, `--age-range-max`, and `--output`.

The mapper can be run using an input label alone, or using an input label together with a histology label. The runner then applies the relevant schema rules automatically.

### Running with an input label only

Use `--label` when the input is a single ICD-O topography label:

```bash
python3 programs/runner.py \
  --label "C50 Breast"
```

### Running with an input label and histology

Use `--label` together with `--histology` when both ICD-O topography and histology information are available:

```bash
python3 programs/runner.py \
  --label "C64 Kidney" \
  --histology "8310/3 Clear cell adenocarcinoma, NOS"
```

Optional arguments, such as `--category`, `--existing-cruk-label`, `--age-range-max`, and `--output`, can be added when required.

The runner response records the matched schema level, generated CRUK terms, generated TCGA labels, unmatched terms, encountered problems, and any metadata flags detected during mapping.

## Validation

Validation files are stored in the `tests/` folder.

```text
tests/
├── dummy_data/
├── validators/
├── validation_outputs/
└── website_validation_workbook/
```

### `tests/dummy_data/`

Contains JSON test cases used to check the mapping programs.

### `tests/validators/`

Contains Python scripts used to run validation checks against the mapping programs and schemas.

### `tests/validation_outputs/`

Contains outputs generated by local validation scripts.

### `tests/website_validation_workbook/`

Contains website-based validation evidence, including the validation table, notes, column guide, and saved JSON outputs produced through the CRUK Data Hub website interface.

Validation covers:

* standard positive mapping checks
* false-positive TCGA checks
* topography-only validation
* rare cancer validation
* childhood age-range validation
* website output checks using saved JSON files

## Supplementary SNOMED CT to ICD-O workflow

The `snomed_icdo_mapping/` folder contains supplementary exploratory work linking SNOMED CT descriptors and concept codes to ICD-O codes. This work is separate from the main ICD-O to CRUK/TCGA mapping pipeline.

The SNOMED CT to ICD-O work was generated from SNOMED CT RF2 release files obtained via NHS TRUD. The main source file was the RF2 Simple Map Snapshot file, which contains SNOMED CT concept-to-ICD-O map entries. The RF2 English Description Snapshot file was then used to attach readable SNOMED CT descriptors to the mapped SNOMED concept codes.

The files included in `snomed_icdo_mapping/` are processed outputs derived from these source files. The main annotated output is stored in `snomed_icdo_mapping/03_annotated/` and includes:

* SNOMED descriptors
* SNOMED concept codes
* ICD-O codes
* ICD-O code type classification

The ICD-O codes are classified as either topography codes or morphology/histology codes.

Raw SNOMED CT release files are not included in this repository because SNOMED CT is subject to licensing restrictions. Users should obtain the original SNOMED CT release files directly from the official TRUD source if they need to reproduce this part of the work.

Further details are provided in `snomed_icdo_mapping/README.md`.

## Website integration

The mapping workflow is used by the CRUK Data Hub website to generate additional CRUK and TCGA filter objects from ICD-O inputs.

The website sends selected ICD-O topography and histology filters to the backend mapping endpoint, and the mapper returns CRUK and TCGA filters in the same structure used by the Data Hub filter system.

## Generated outputs

The repository includes `results_dictionary.json`, a large generated output file stored using Git LFS. It contains generated mapping outputs across ICD-O topography and histology combinations and is included for review rather than manual editing.

Because this file is large, GitHub may not display its contents directly in the browser. It can be downloaded through GitHub or pulled using Git LFS.

To generate a new version of this file, see [Generating `results_dictionary.json`](#generating-results_dictionaryjson).

## Notes and limitations

The runner order is based on the testing completed so far. It changed during development, for example when intermediate rules were placed before simple rules. Future validation may show if the order needs further changes.

In some cases, the workflow returns a CRUK term without a TCGA label when the correct TCGA project is not clear.

Validation notes are used to document expected behaviour, edge cases, and cases that may need future review.