# SNOMED CT to ICD-O Mapping
This folder contains supplementary exploratory SNOMED CT to ICD-O mapping work.

The workflow uses SNOMED CT mapping and description source files locally to generate reviewed outputs linking SNOMED descriptors and concept codes to ICD-O codes. The main annotated output classifies ICD-O codes as either topography codes or morphology/histology codes.

Raw SNOMED CT source files are not included in this repository.

## Folder structure

```text
snomed_icdo_mapping/
├── 01_SNOMED_order/
├── 02_ICDO_order/
├── 03_annotated/
├── 04_ambiguity_check/
├── 05_overlap_check/
└── README.md
```

## Local source files
The original SNOMED CT source files are required to reproduce the workflow, but they are not included in this repository because they may be large and may be subject to access or licensing restrictions.


## `01_SNOMED_order`

Creates a three-column SNOMED CT to ICD-O mapping file in the original SNOMED file order.

Main output:

```text
snomed_to_icdo_map_snomed_order.tsv
```

The output contains:

* `SNOMED descriptor`
* `SNOMED code`
* `ICD-O code`

## `02_ICDO_order`

Creates the same three-column mapping file, but sorted by ICD-O code to make review easier.

Main output:

```text
snomed_to_icdo_map_icdo_order.tsv
```

## `03_annotated`

Contains the main annotated SNOMED CT to ICD-O mapping output.

Main output:

```text
snomed_to_icdo_map_with_code_types.tsv
```

This file links:

* SNOMED descriptors
* SNOMED concept codes
* ICD-O codes
* ICD-O code type

The ICD-O code type separates codes into:

* topography codes
* morphology/histology codes

## `04_ambiguity_check`

Contains a summary showing how many SNOMED descriptors map to the same ICD-O code.

Main output:

```text
icdo_to_snomed_ambiguity_summary.tsv
```

This helps illustrate why reverse mapping from ICD-O back to SNOMED CT can be ambiguous. A single ICD-O code may correspond to many different SNOMED descriptors or concepts, so the reverse direction does not always identify one clear SNOMED concept.

Example:

* ICD-O code: `C49.0`
* Number of SNOMED descriptors: `1341`
* Example SNOMED descriptors:

  * Accessory vertebral vein
  * Alar part of nasalis muscle
  * Angular artery
  * Angular vein

This means that starting from `C49.0` alone may not be enough to select one definitive SNOMED CT descriptor.

## `05_overlap_check`

Contains a project-specific comparison between ICD-O labels used in the CRUK/TCGA mapping project and the SNOMED CT to ICD-O map.

Main output:

```text
icdo_project_snomed_overlap.tsv
```

This output shows which project ICD-O codes also appear in the SNOMED-derived map, and how many SNOMED descriptors map to each project ICD-O code.

Example:

* ICD-O code: `C49.0`
* Project ICD-O label: `C49.0 Connective, subcutaneous and other soft tissues of head, face, and neck`
* Project key: `0_0_8_0`
* Number of SNOMED descriptors: `1341`
* Example SNOMED descriptors:

  * Accessory vertebral vein
  * Alar part of nasalis muscle
  * Angular artery
  * Angular vein

In the project file, `C49.0` appears as one ICD-O label with one project key. In the SNOMED-derived map, many different SNOMED descriptors map to the same ICD-O code. This helps show the difference between broader ICD-O project labels and more detailed SNOMED CT descriptors.


## Note on ICD-O code types
Topography codes usually start with `C` and describe the tumour site or anatomical location.

Morphology/histology codes usually use the `xxxx/x` format and describe the tumour type or microscopic appearance.

The annotated output keeps these code types separate for easier review.


## DataHub review
Processed SNOMED-to-ICD-O outputs were reviewed through the CRUK Data Hub environment during project testing. This helped assess how SNOMED-derived links could be surfaced and compared with ICD-O-related project outputs.


## Notes and limitations
This workflow is exploratory and supplementary. It supports review of SNOMED CT to ICD-O links, but it is separate from the main ICD-O to CRUK/TCGA mapping pipeline.

Reverse mapping from ICD-O to SNOMED CT is more ambiguous because a single ICD-O code may correspond to many SNOMED CT descriptors or concepts.

Raw SNOMED CT source files are not included in this repository.


