# Base-diet audit summary

- Scope: archived normalized diet files; raw API responses were not preserved.
- Plans: 150 (150 with the expected 5-day/6-meal schema).
- Food occurrences: 12670 across 292 unique names.
- Exact TBCA names: 122; names requiring the explicit preserved mapping: 170.
- Identity mappings: 122; non-identity mappings without a preserved lexical-versus-semantic classification: 170.
- Used TBCA targets reached by multiple generated names: 16.
- Invalid quantities: 0.
- Quantities above the 1000 g screening threshold: 0.
- Duplicate foods within the same meal: 0.
- TBCA-unmapped occurrences: 0.
- Environmental-unmapped occurrences: 0.
- Plans with at least one implemented nutritional-target violation: 150.
- Total implemented nutritional-target violations: 1418.

The machine-readable item, plan, nutrient, mapping, and summary files in this directory are the authoritative audit output. `food_mapping_audit.csv` links every distinct food name to its selected TBCA record, environmental coefficients, occurrence count, mapping type, and ambiguity flags. Raw API failure and regeneration counts cannot be inferred from these normalized JSON files.
