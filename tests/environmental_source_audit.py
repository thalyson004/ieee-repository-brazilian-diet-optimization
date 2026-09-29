"""Audit distributed footprint coefficients against the pinned official OSF workbook."""

from __future__ import annotations

import argparse
import hashlib
import json
import urllib.request
import xml.etree.ElementTree as ET
import zipfile
from collections import defaultdict
from io import BytesIO
from pathlib import Path
from typing import Any

from diet_optimization.experiments.runner import source_provenance
from diet_optimization.optimization.utils import load_json_file


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SOURCE_URL = "https://osf.io/download/fv3tx/"
SOURCE_FILE_ID = "655f914c79d42805e93e8434"
SOURCE_SHA256 = "988040f8e9c668d823c41b0839132a3494b9a3ad6e5a4945e18757542b16d4af"
SOURCE_TITLE = (
    "Atualização das tabelas das pegadas ambientais de alimentos e preparações "
    "culinárias consumidos no Brasil conforme a POF de 2018"
)
METRICS = (
    ("carbon_footprint", 0, "gCO2e per 100 g"),
    ("water_footprint", 1, "liters per 100 g"),
    ("ecological_footprint", 2, "g-m2 per 100 g"),
)
NS = {
    "m": "http://schemas.openxmlformats.org/spreadsheetml/2006/main",
    "r": "http://schemas.openxmlformats.org/officeDocument/2006/relationships",
    "p": "http://schemas.openxmlformats.org/package/2006/relationships",
}


def fetch_pinned_workbook() -> bytes:
    request = urllib.request.Request(
        SOURCE_URL,
        headers={"User-Agent": "ieee2026-1-environmental-source-audit/1.0"},
    )
    with urllib.request.urlopen(request, timeout=60) as response:
        content = response.read()
    digest = hashlib.sha256(content).hexdigest()
    if digest != SOURCE_SHA256:
        raise ValueError(
            "Downloaded OSF workbook SHA-256 does not match the pinned source: "
            f"expected {SOURCE_SHA256}, got {digest}"
        )
    return content


def _cell_value(cell: ET.Element, shared_strings: list[str]) -> str | None:
    value = cell.find("m:v", NS)
    if value is None or value.text is None:
        return None
    if cell.attrib.get("t") == "s":
        return shared_strings[int(value.text)]
    return value.text


def parse_official_preparation_sheet(workbook_bytes: bytes) -> dict[str, list[tuple[float, float, float]]]:
    """Read prep labels and CF/WF/EF cells from the source's 100-g worksheet."""
    with zipfile.ZipFile(BytesIO(workbook_bytes)) as workbook:
        workbook_xml = ET.fromstring(workbook.read("xl/workbook.xml"))
        rels_xml = ET.fromstring(workbook.read("xl/_rels/workbook.xml.rels"))
        relations = {
            item.attrib["Id"]: item.attrib["Target"]
            for item in rels_xml.findall("p:Relationship", NS)
        }
        sheet_target = None
        for sheet in workbook_xml.findall(".//m:sheet", NS):
            if sheet.attrib.get("name") == "Tab_Preparacoes_100g_2018":
                sheet_target = relations[sheet.attrib[f"{{{NS['r']}}}id"]]
                break
        if sheet_target is None:
            raise ValueError("Pinned workbook lacks Tab_Preparacoes_100g_2018")
        sheet_path = sheet_target.lstrip("/")
        if not sheet_path.startswith("xl/"):
            sheet_path = f"xl/{sheet_path}"
        shared_root = ET.fromstring(workbook.read("xl/sharedStrings.xml"))
        shared = [
            "".join(text.text or "" for text in item.findall(".//m:t", NS))
            for item in shared_root.findall("m:si", NS)
        ]
        sheet_xml = ET.fromstring(workbook.read(sheet_path))
        values_by_name: defaultdict[str, list[tuple[float, float, float]]] = defaultdict(list)
        for row in sheet_xml.findall(".//m:sheetData/m:row", NS):
            cells = {
                "".join(char for char in cell.attrib["r"] if char.isalpha()): _cell_value(cell, shared)
                for cell in row.findall("m:c", NS)
            }
            name = cells.get("D")
            if not name:
                continue
            try:
                footprints = tuple(float(cells[column]) for column in ("E", "F", "G"))
            except (KeyError, TypeError, ValueError):
                continue
            values_by_name[name].append(footprints)  # type: ignore[arg-type]
        return dict(values_by_name)


def compare_rounded_values(
    map_values: dict[str, Any],
    source_values: dict[str, list[tuple[float, float, float]]],
) -> dict[str, Any]:
    matched_names = set(map_values) & set(source_values)
    unmatched_map_names = sorted(set(map_values) - set(source_values))
    unmatched_source_names = sorted(set(source_values) - set(map_values))
    metrics: dict[str, Any] = {}
    for metric_name, index, unit in METRICS:
        precision = 1 if metric_name == "ecological_footprint" else 0
        half_unit = 0.5 * (10 ** -precision)
        matched = mismatched = 0
        ambiguous_names = 0
        maximum_rounding_residual = 0.0
        ambiguous_ranges: list[dict[str, Any]] = []
        for food_name in matched_names:
            official = [row[index] for row in source_values[food_name]]
            unique = sorted(set(official))
            ambiguous_names += len(unique) > 1
            current = float(map_values[food_name][metric_name])
            residual = min(abs(current - value) for value in official)
            maximum_rounding_residual = max(maximum_rounding_residual, residual)
            if residual <= half_unit + 1e-8:
                matched += 1
            else:
                mismatched += 1
            if len(unique) > 1:
                ambiguous_ranges.append({
                    "food_name": food_name,
                    "official_min": min(unique),
                    "official_max": max(unique),
                    "distributed_value": current,
                    "source_rows": len(official),
                })
        metrics[metric_name] = {
            "unit": unit,
            "distributed_value_within_rounding_tolerance_of_any_official_row": matched,
            "distributed_value_outside_rounding_tolerance": mismatched,
            "official_prep_labels_with_multiple_values": ambiguous_names,
            "maximum_distance_to_nearest_official_value": maximum_rounding_residual,
            "ambiguous_value_ranges": sorted(
                ambiguous_ranges,
                key=lambda row: (
                    -(row["official_max"] - row["official_min"]),
                    row["food_name"],
                ),
            )[:50],
        }
    return {
        "distributed_map_entry_count": len(map_values),
        "official_prep_label_count": len(source_values),
        "exact_prep_label_matches": len(matched_names),
        "distributed_names_without_official_exact_label": unmatched_map_names,
        "official_prep_labels_not_in_distributed_map": unmatched_source_names,
        "metrics": metrics,
    }


def count_preserved_diet_food_occurrences() -> tuple[dict[str, int], dict[str, int]]:
    """Count original unique food labels and occurrences separately by profile."""
    all_counts: defaultdict[str, int] = defaultdict(int)
    profile_counts: dict[str, int] = {}
    for profile in ("regular", "vegetariana", "vegana"):
        plans = load_json_file(PROJECT_ROOT / "diets-base" / f"dietas-{profile}.json")
        profile_occurrences = 0
        for plan in plans:
            for day in plan.values():
                if not isinstance(day, dict):
                    continue
                for items in day.values():
                    if not isinstance(items, list):
                        continue
                    for item in items:
                        if isinstance(item, dict) and isinstance(item.get("alimento"), str):
                            all_counts[item["alimento"]] += 1
                            profile_occurrences += 1
        profile_counts[profile] = profile_occurrences
    return dict(all_counts), profile_counts


def run(output_dir: Path) -> dict[str, Any]:
    output_dir.mkdir(parents=True, exist_ok=False)
    workbook_bytes = fetch_pinned_workbook()
    source_values = parse_official_preparation_sheet(workbook_bytes)
    distributed = load_json_file(PROJECT_ROOT / "maps" / "base" / "mapa-sustentavel-pegadas.json")
    comparison = compare_rounded_values(distributed, source_values)
    source_food_occurrences, profile_occurrences = count_preserved_diet_food_occurrences()
    active_food_coefficients = {
        name: distributed[name] for name in source_food_occurrences if name in distributed
    }
    active_comparison = compare_rounded_values(active_food_coefficients, source_values)
    for metric, summary in active_comparison["metrics"].items():
        # Count all ambiguous labels, not only the 50 detail rows retained for output.
        source_index = next(index for name, index, _unit in METRICS if name == metric)
        summary["ambiguous_occurrence_count"] = sum(
            source_food_occurrences[name]
            for name, rows in source_values.items()
            if name in source_food_occurrences
            and len({row[source_index] for row in rows}) > 1
        )
        summary["ambiguous_active_food_names"] = sum(
            name in source_values
            and len({row[source_index] for row in source_values[name]}) > 1
            for name in source_food_occurrences
        )
    report = {
        "schema_version": "1.0",
        "status": "source_alignment_audit_not_food_equivalence_adjudication",
        "official_source": {
            "title": SOURCE_TITLE,
            "osf_node": "https://osf.io/g9d5y/",
            "osf_file_id": SOURCE_FILE_ID,
            "file_name": "e.book_Pegadas_alimentos_Brasil_planilhas_20231122.xlsx",
            "download_url": SOURCE_URL,
            "sha256": hashlib.sha256(workbook_bytes).hexdigest(),
            "sheet": "Tab_Preparacoes_100g_2018",
            "source_update": "2023-11-23",
        },
        "source_provenance": source_provenance(),
        "rounding_tolerance": {
            "carbon_footprint": "0.5 gCO2e/100 g",
            "water_footprint": "0.5 L/100 g",
            "ecological_footprint": "0.05 g-m2/100 g",
        },
        "interpretation_warning": (
            "Exact-label and numeric source alignment do not determine which POF source row "
            "is appropriate for a generated food, confirm ingredients/preparation equivalence, "
            "or resolve geographic/system-boundary uncertainty. The distributed map may collapse "
            "multiple official POF rows into one TBCA preparation label."
        ),
        "comparison": comparison,
        "preserved_diet_usage": {
            "profile_occurrence_counts": profile_occurrences,
            "distinct_food_names": len(source_food_occurrences),
            "total_food_occurrences": sum(source_food_occurrences.values()),
            "food_names_without_exact_distributed_coefficient": sorted(
                set(source_food_occurrences) - set(distributed)
            ),
            "active_food_comparison": active_comparison,
        },
    }
    path = output_dir / "environmental-source-audit.json"
    path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({
        "status": report["status"],
        "source_sha256": report["official_source"]["sha256"],
        "map_entries": comparison["distributed_map_entry_count"],
        "exact_label_matches": comparison["exact_prep_label_matches"],
        "unmatched_map_names": len(comparison["distributed_names_without_official_exact_label"]),
        "active_distinct_food_names": len(source_food_occurrences),
        "active_occurrences": sum(source_food_occurrences.values()),
        "metrics": {
            metric: {
                "aligned_after_rounding": result[
                    "distributed_value_within_rounding_tolerance_of_any_official_row"
                ],
                "outside_tolerance": result["distributed_value_outside_rounding_tolerance"],
                "ambiguous_source_labels": result["official_prep_labels_with_multiple_values"],
            }
            for metric, result in comparison["metrics"].items()
        },
        "output": str(path),
    }, ensure_ascii=False, indent=2))
    return report


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, required=True)
    return parser.parse_args()


def main() -> None:
    run(parse_args().output_dir)


if __name__ == "__main__":
    main()
