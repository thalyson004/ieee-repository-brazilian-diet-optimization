# Food mapping, TBCA linkage, and environmental coefficients

## Scope

Current status (2026-09-25): after matching soybean oil to exact POF record `8400301#99`/historical C0030D and the official TBCA entry BRC0030D, the nutrition-target ledger contains 157 decisions and the active queue has 13 unresolved non-identity links (320 occurrences). The source label does not say fried; the previous BRC0048D target added that preparation qualifier. The three environmental coefficients still map to the exact POF record after rounding and were not changed. Vegan ingredient evidence applies only to this pure soybean-oil item. Other decisions remain scoped: `Feijoada vegetariana` to standardized BRC0172T; salad to POF `8511102#99`/BRC0404B; tomato sauce to `7004801#99`/BRC0100B; chocolate milk to six POF records/C0034G/BRC0034G; and cornstarch porridge to POF `6500616#99`/BRC0054G, with recipe details still uncertain. Cocoa-pulp BRC0071C remains unresolved because source does not establish pulp versus seed/bean and historical POF code is shared with a jenipapo row. The explicit vegan cow-milk exclusion is preserved. These target decisions do not prove the provenance of every generated recipe and remain distinct from ingredient, preparation, and environmental-coefficient review. Latest audits: `base-diet-audit_20260925T051018785560Z_efb30602`, `mapping-review-queue-current_20260925T051019084147Z_6781e8f1`, and `profile-ingredient-audit_20260925T051019964605Z_aae9c6c3`; all optimization outputs remain diagnostic while evidence gates are open.

Latest addendum (2026-09-24): four additional nutrition-target decisions correct unsweetened black tea (BRC0013H), unspecified whole guava (BRC0014C), raw mature pequi (BRC0173C), and unspecified raw bell pepper (BRC0031B). The index now records 45 decisions, leaving 125 of the 170 original non-identity links without a recorded target decision. Historical counts below are snapshots and are superseded by this addendum; ingredient, preparation, environmental-map, and formulation questions remain separate.

Latest queue refresh (2026-09-24): four further decisions correct the unsweetened mate/herbal tea entries, the salt status of vegetable pasta (with recipe-level uncertainty retained), and the generic orange target. The index now records 49 nutrition targets; the active review queue contains 121 unresolved links. See the dated ledger and the newest experiment addendum for run IDs and post-correction diagnostics.

Historical checkpoint (2026-09-24, 17:05 UTC): four additional high-occurrence targets were individually checked and retained (broccoli preparation, raw Brazil nut, Papaia papaya pulp, and cooked quinoa). That checkpoint recorded 53 decisions and 117 active non-identity links; it is superseded by the current 117/53 state above. These confirmations did not clear separate ingredient/environmental uncertainties.

Latest source check: raw oats by type-average, raw generic lettuce, and fluid skim cow milk by sample-average were also verified and retained. The index now has 56 recorded target decisions and the active queue has 114 pending links. The high-occurrence skim natural yogurt is deliberately still pending: the TBCA snapshot exposes two same-label records with different values, and one is identified as Vigor; source brand is unavailable.

Next verified batch (2026-09-24): melon pulp raw, scrambled egg with margarine and salt, raw unsalted cashew, and flax seed were confirmed against TBCA. The current index has 60 recorded target decisions; 110 links remain in the active queue. The decisions do not certify environmental coefficients.

The following five sources were also verified and their present targets retained: dried chia, raw avocado pulp, peeled raw carrot, unpeeled raw cucumber, and Ponkan tangerine. The current index now records 65 target decisions and 105 links remain in the active queue. `Noz, crua` remains pending because the active BRC0009U record is specifically pecan while the source does not name a species.

Previous correction: the homemade mozzarella-pizza source is now linked to TBCA BRC0225A (artisanal baked mozzarella pizza), not the previous Marguerita record BRC0685A. The closer target removes the unsupported basil and milk/egg/margarine dough assumptions, though it remains provisional because the source recipe is unavailable. A generic cereal-matinal target was also verified, retaining unresolved brand/sugar detail. At that checkpoint the index had 67 decisions and the active queue had 103 pending links.

Earlier checkpoint, 2026-09-24: the frozen initial queue has 170 non-identity links. At that checkpoint, 41 nutrition-target decisions were documented and 129 links remained without a recorded target decision. This does not establish ingredient or preparation equivalence, environmental-coefficient validity, or complete formulation matching. In particular, oil type, tofu salt, fluid-milk processing, coconut processing/maturity, pasta refinement, rice-cracker formulation, vegetable-risotto ingredients, toast brand/formulation, and couve variety remain uncertain; see the dated correction ledger below. The salted-couscous target now excludes butter and matches the stated steamed preparation, although serving/formulation details should still be checked against the original source. Later checkpoints supersede these counts.

This document describes the exact mapping path used by the archived submission and the checks required by the revised study. It distinguishes exact identity, a non-identity link with a dated target decision, and a non-identity link still awaiting a target decision. The old artifacts do not classify all links as lexical normalization versus semantic substitution. Seventy-three target decisions are indexed in [`archive/audits/adjudicated-food-map-sources.json`](../archive/audits/adjudicated-food-map-sources.json) and documented item by item in [`archive/audits/food-mapping-corrections-2026-09-24.md`](../archive/audits/food-mapping-corrections-2026-09-24.md); residual preparation, brand/variety, environmental, or ingredient uncertainty can remain even for those decisions.

The authoritative, row-level inventory for the 292 food names occurring in the 150 base diets is [`archive/audits/food-mapping-audit.csv`](../archive/audits/food-mapping-audit.csv). It is regenerated by:

```bash
python -m tests.run_experiments --experiments base-diet-audit
```

The command writes a result manifest, a full log, and an artifact workspace. It never edits a diet.

## Preserved mapping chain

For a food name `f` found in a base-diet JSON file, the archived implementation performs these joins:

1. `maps/base/mapa-sustentavel-nome.json[f]` selects a TBCA target name `t`.
2. `maps/base/mapa-nome-tbca.json[t]` supplies the TBCA code `c`.
3. `maps/derived/mapa-sustentavel-tbca.json[f]` preserves the composed map `f -> c` used by the optimizer.
4. `maps/base/mapa-tbca-completo.json[c]` supplies the nutrient record per 100 g.
5. `maps/base/mapa-sustentavel-pegadas.json[f]` supplies carbon, water, and ecological coefficients per 100 g.

The derived TBCA map can be reconstructed by joining steps 1 and 2. The historical helper recovered in the parent repository performs only that deterministic join; it does not explain how the semantic targets or environmental coefficients were originally chosen.

## Environmental source and pinned audit

The environmental source is the OSF workbook `e.book_Pegadas_alimentos_Brasil_planilhas_20231122.xlsx`, updated on 2023-11-23 from POF 2017--2018 data ([official OSF record](https://osf.io/g9d5y/)). Its `Tab_Preparacoes_100g_2018` sheet reports carbon (gCO2e), water (L), and ecological (g-m2) indicators per 100 g. The source description states that the indicators use secondary life-cycle assessment publications/reports and that multi-ingredient preparations are disaggregated using standardized TBCA-USP version 7 recipes. The workbook also retains POF item codes, source references, cooking assumptions, geographic locations, and system-boundary notes. The original 2019 book is linked in the source record for methodological background ([USP open-book record](https://doi.org/10.11606/9788588848368)).

`environmental-source-audit_20260924T205706574023Z_0d911e23` pins OSF file ID `655f914c79d42805e93e8434` and SHA-256 `988040f8e9c668d823c41b0839132a3494b9a3ad6e5a4945e18757542b16d4af`. It found all 1,170 distributed environmental map labels in the official preparation sheet and every distributed coefficient within source rounding precision. Among the 292 labels used by the preserved diets (12,670 occurrences), multiple distinct source values share one standardized preparation label for 65 carbon, 35 water, and 37 ecological entries (2,741, 1,423, and 1,412 occurrences). Thus, source identity and numeric alignment are traceable, but labels alone do not identify which original POF food row, location, production boundary, or source value is appropriate for each generated item. The audit fetches the pinned workbook to memory, verifies its hash, and does not redistribute it. Re-run with:

```bash
python -m tests.run_experiments --experiments environmental-source-audit
```

## Mapping classes

Each distinct used name receives one of the following machine-readable classes:

| Class | Definition | Interpretation |
| --- | --- | --- |
| `identity` | original name equals selected TBCA name | Exact string identity; no semantic replacement detected. |
| `non_identity_recorded_decision` | original and selected names differ; source is in the dated adjudication index | A target decision was reviewed and recorded; this does not automatically clear formulation, preparation, brand/variety, environmental, or ingredient uncertainty. |
| `non_identity_unreviewed` | original and selected names differ; no target decision is recorded | The change can range from punctuation or a TBCA qualifier to a different food. It still awaits a target decision. |
| `missing` | no target is available | The occurrence cannot be evaluated and must be excluded or resolved explicitly. |

The audit also flags a many-to-one mapping when several source names reach one selected target. This is a cardinality warning, not proof that the mapping is wrong. It is nevertheless relevant because distinct foods can receive identical nutrient targets and therefore reduce effective food diversity.

## Current audited coverage

The frozen submitted-map snapshot reports:

- 12,670 food occurrences and 292 distinct source names;
- 122 identity mappings;
- 170 non-identity links whose lexical-versus-semantic classification and selection rationale are unavailable;
- 16 selected targets reached by more than one used source name;
- zero occurrences without a TBCA record;
- zero occurrences without environmental coefficients.

The current code audit is regenerated from the active maps, diets, and dated adjudication index. The next refresh should report 155 recorded target decisions and 15 active non-identity links without a decision. The tomato-sauce adjudication corrected BRC0100B in the local nutrient snapshot to the current official values (45 kcal, 9.06 g total carbohydrate, 5.42 g available carbohydrate per 100 g). The milk map now selects current BRC0034G (fluid, 85 kcal/100 g) rather than powder BRC0035G; the POF and official TBCA evidence support this, while the source brand remains unknown. These are targeted corrections, not a complete live refresh of all TBCA codes. Earlier checkpoints are historical snapshots. The audit previously found zero unmapped TBCA/environmental occurrences and 1,597 target violations under the diagnostic calculation; the violation count is sensitive to map changes and is not a quality score.

Coverage does not establish validity. In particular, a complete join does not prove that the selected TBCA item is nutritionally equivalent to the generated item or that the footprint coefficient describes the same preparation, geography, production system, and system boundary.

For review, `archive/audits/food-mapping-review-queue.csv` and its JSON counterpart are a frozen triage artifact generated from the original audit snapshot; they list all 170 originally non-identity links, their historical targets, occurrence counts, profiles, and five ranked TBCA name suggestions. The current dated index contains 156 target decisions; the regenerated active queue has 14 original links without a recorded target decision. A normalized-name flag and similarity score help triage the preserved target: neither high similarity nor same-label duplicate codes are automatically accepted. The CSV also provides blank decision, approved-target, rationale, evidence, reviewer/date, and environmental-map adjudication fields; no row is pre-approved. Generate a fresh lexical queue with:

```bash
python -m tests.run_experiments --experiments mapping-review-queue
```

Generate a current queue from the active maps (excluding foods with a dated target decision) using:

```bash
python -m tests.run_experiments --experiments mapping-review-queue-current
```

The ranking is a string/token heuristic only. It never edits a mapping and never marks a candidate accepted; preparation, ingredients, food identity, and environmental-system boundaries require independent evidence and an explicit human decision.

The original inventory contains confirmed high-priority non-equivalences, not only spelling differences. Examples in the archived map include `Tomate, in natura -> Pitaia, in natura`, `Soja, tofu -> Óleo, soja, frito`, `Almeirão, cru -> Amendoim, grão, cru`, and `Avelã, crua -> Acarajé, s/ sal`; tomato and almeirão have since been corrected in the active nutrient map. Consequently, archived nutritional totals and feasibility decisions that depend on these links cannot support revised claims without a corrected map and sensitivity comparison.

## Required treatment in revised experiments

The revised analysis must retain three scenarios rather than silently accepting the archived map:

1. **Archived-map scenario:** reproduce the prior implementation exactly and label it historical.
2. **Identity-only scenario:** exclude or separately report all non-identity links.
3. **Reviewed-map scenario:** use only correspondences approved item by item, with reviewer, date, rationale, source food, target food, TBCA code, environmental source, units, and uncertainty recorded.

The reviewed-map scenario is mandatory for the revised primary analysis. The archived-map scenario is retained only to measure how much the corrected linkage changes the submitted results.

Primary comparative claims must be stable across these scenarios or explicitly limited to the mapping used. The sensitivity analysis must report changes in nutritional adequacy, carbon footprint, diversity, feasibility, and the ranking of optimization methods.

## Provenance limits

- The maps preserve the final links, not the human or automated procedure that selected the more sustainable variants.
- The original map preserved no confidence score, reviewer identity, or target-selection rationale. The revised dated ledger now records 156 target decisions and their sources; it is not a complete record of the remaining 14 links or of all environmental equivalence questions.
- Environmental values are keyed by the source name while nutrient values are reached through the selected TBCA target. The archived artifacts alone do not prove semantic co-identity between those two records.
- Raw LLM responses and regeneration attempts were not preserved, so mapping completeness cannot be used to infer original prompt compliance.
- The audit's 1,000 g threshold is only an anomaly screen and is not a portion recommendation.

Until item-level review and sensitivity analysis are complete, the mapping supports reproducible computation but not clinical equivalence or an unqualified environmental comparison.
