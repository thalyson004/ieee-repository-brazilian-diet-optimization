"""Aggregate TBCA missingness markers for foods used in the study.

The report intentionally excludes per-food compositions and numeric values.
It stores only aggregate status counts, source identifiers, and fetch failures.
"""

from __future__ import annotations

import argparse
import json
import time
import unicodedata
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from html.parser import HTMLParser
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DIET_FILES = {
    "regular": PROJECT_ROOT / "diets-base" / "dietas-regular.json",
    "vegetarian": PROJECT_ROOT / "diets-base" / "dietas-vegetariana.json",
    "vegan": PROJECT_ROOT / "diets-base" / "dietas-vegana.json",
}
MAPPING_PATH = PROJECT_ROOT / "maps" / "derived" / "mapa-sustentavel-tbca.json"
TBCA_PATH = PROJECT_ROOT / "maps" / "base" / "mapa-tbca-completo.json"
PROTOCOL_PATH = PROJECT_ROOT / "configs" / "revised-nutrition-protocol.json"
SOURCE_HOME = "https://www.tbca.net.br/"


def normalize_label(value: str) -> str:
    decomposed = unicodedata.normalize("NFKD", value)
    return " ".join("".join(ch for ch in decomposed if not unicodedata.combining(ch)).casefold().split())


class StatisticsTableParser(HTMLParser):
    """Read table text into rows, without retaining the page or values on disk."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.rows: list[list[str]] = []
        self._row: list[str] | None = None
        self._cell: list[str] | None = None

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag == "tr":
            self._row = []
        elif tag in {"td", "th"} and self._row is not None:
            self._cell = []

    def handle_data(self, data: str) -> None:
        if self._cell is not None:
            self._cell.append(data)

    def handle_endtag(self, tag: str) -> None:
        if tag in {"td", "th"} and self._cell is not None and self._row is not None:
            self._row.append(" ".join("".join(self._cell).split()))
            self._cell = None
        elif tag == "tr" and self._row is not None:
            if self._row:
                self.rows.append(self._row)
            self._row = None


def value_status(value: str, data_type: str) -> str:
    marker = value.strip().casefold().replace(".", "")
    if marker == "na":
        return "not_analyzed"
    if marker in {"tr", "traço", "traco"}:
        return "trace"
    if marker in {"nd", "n.d."}:
        return "not_detected"
    if marker in {"", "-", "—", "–"}:
        return "blank_or_dash"
    try:
        float(marker.replace(",", "."))
    except ValueError:
        return "other_marker"
    return "numeric_" + (normalize_label(data_type).replace(" ", "_") or "unspecified")


def local_map_status(entry: dict[str, Any], field: str) -> str:
    nutrients = entry.get("nutrientes", {})
    values = {normalize_label(str(key)): value for key, value in nutrients.items()} if isinstance(nutrients, dict) else {}
    value = values.get(normalize_label(field))
    try:
        number = float(value)
    except (TypeError, ValueError):
        return "missing_or_nonnumeric"
    return "numeric_zero" if number == 0 else "numeric_nonzero"


def parse_statistics(html: str) -> list[dict[str, str]]:
    parser = StatisticsTableParser()
    parser.feed(html)
    # The official statistical table has component, tag, unit, mean, SD, min,
    # max, n, references, and data-type columns.
    result = []
    for row in parser.rows:
        if len(row) >= 10 and normalize_label(row[0]) not in {"componente", "component", "nutriente"}:
            result.append({"component": row[0], "value": row[3], "data_type": row[9]})
    return result


def _walk_foods(value: Any):
    if isinstance(value, dict):
        if isinstance(value.get("alimento"), str):
            try:
                grams = float(str(value.get("quantidade", "0")).replace(",", "."))
            except (TypeError, ValueError):
                grams = 0.0
            if grams > 0:
                yield value["alimento"], grams
        else:
            for nested in value.values():
                yield from _walk_foods(nested)
    elif isinstance(value, list):
        for nested in value:
            yield from _walk_foods(nested)


def collect_scope() -> tuple[dict[str, dict[str, float]], dict[str, Any], list[str]]:
    name_to_code = json.loads(MAPPING_PATH.read_text(encoding="utf-8"))
    tbca = json.loads(TBCA_PATH.read_text(encoding="utf-8"))
    scope: dict[str, dict[str, float]] = {}
    unknown_names: list[str] = []
    for profile, path in DIET_FILES.items():
        stats: defaultdict[str, float] = defaultdict(float)
        plans = json.loads(path.read_text(encoding="utf-8"))
        for plan in plans:
            for name, grams in _walk_foods(plan):
                code = name_to_code.get(name)
                if not code or code not in tbca:
                    unknown_names.append(name)
                    continue
                stats[code + "|occurrences"] += 1
                stats[code + "|grams"] += grams
        scope[profile] = dict(stats)
    return scope, tbca, sorted(set(unknown_names))


def fetch_page(code: str, url: str, attempts: int = 4) -> tuple[str, str | None, str | None]:
    stats_url = url.replace("int_composicao_alimentos.php", "int_composicao_estatistica.php")
    if stats_url == url:
        return code, None, "unrecognized_detail_url"
    for attempt in range(attempts):
        try:
            request = Request(
                stats_url,
                headers={"User-Agent": "Mozilla/5.0 (academic TBCA marker audit; contact via repository)"},
            )
            with urlopen(request, timeout=25) as response:
                return code, response.read().decode("utf-8", "replace"), None
        except (HTTPError, URLError, TimeoutError, OSError) as exc:
            if attempt + 1 == attempts:
                return code, None, type(exc).__name__
            time.sleep(1.0 * (attempt + 1))
    return code, None, "exhausted_retries"


def audit(output_dir: Path, workers: int = 3, request_pause: float = 0.25) -> dict[str, Any]:
    scope, tbca, unknown_names = collect_scope()
    codes = sorted({key.split("|", 1)[0] for profile in scope.values() for key in profile})
    protocol = json.loads(PROTOCOL_PATH.read_text(encoding="utf-8"))
    rules = list(protocol.get("core_targets", []))
    rules.extend(
        r for r in protocol.get("additional_rules", [])
        if (r.get("lower") is not None or r.get("upper") is not None)
        and str(r.get("model_rule", "")).lower().startswith("hard")
    )
    wanted: dict[str, str] = {}
    for rule in rules:
        field = str(rule.get("tbca_field", ""))
        if field:
            wanted[normalize_label(field)] = field

    totals: defaultdict[str, Counter[str]] = defaultdict(Counter)
    crosscheck: defaultdict[str, Counter[str]] = defaultdict(Counter)
    profile_totals: defaultdict[str, defaultdict[str, Counter[str]]] = defaultdict(lambda: defaultdict(Counter))
    errors: list[dict[str, str]] = []
    completed = 0
    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures = []
        for code in codes:
            entry = tbca.get(code, {})
            url = entry.get("link") if isinstance(entry, dict) else None
            if not url:
                errors.append({"code": code, "error": "missing_source_link"})
                continue
            futures.append(pool.submit(fetch_page, code, url))
            time.sleep(request_pause)
        for future in as_completed(futures):
            code, html, error = future.result()
            if error or html is None:
                errors.append({"code": code, "error": error or "empty_response"})
                continue
            page_rows = parse_statistics(html)
            by_component = {normalize_label(row["component"]): row for row in page_rows}
            if not by_component:
                errors.append({"code": code, "error": "statistics_table_not_parsed"})
                continue
            completed += 1
            for normalized, field in wanted.items():
                row = by_component.get(normalized)
                status = "component_not_listed" if row is None else value_status(row["value"], row["data_type"])
                totals[field][status] += 1
                local_status = local_map_status(tbca[code], field)
                crosscheck[field][f"official_{status}|local_{local_status}"] += 1
                for profile, stat in scope.items():
                    occurrences = int(stat.get(code + "|occurrences", 0))
                    grams = float(stat.get(code + "|grams", 0.0))
                    if occurrences:
                        profile_totals[profile][field][status + "|foods"] += 1
                        profile_totals[profile][field][status + "|occurrences"] += occurrences
                        profile_totals[profile][field][status + "|grams"] += grams

    output_dir.mkdir(parents=True, exist_ok=True)
    payload = {
        "schema_version": "1.0",
        "audit": "tbca-official-marker-aggregate",
        "status": "complete" if completed == len(codes) and not errors else "incomplete",
        "source": SOURCE_HOME,
        "source_accessed_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "reporting_policy": "Aggregated statuses only; no per-food nutrient values or source pages are persisted.",
        "candidate_codes": len(codes),
        "pages_parsed": completed,
        "fetch_errors": errors,
        "unmapped_or_missing_source_names_count": len(unknown_names),
        "nutrient_status_counts_across_codes": {k: dict(v) for k, v in sorted(totals.items())},
        "official_marker_vs_local_snapshot_counts": {k: dict(v) for k, v in sorted(crosscheck.items())},
        "profile_status_exposure": {
            profile: {
                nutrient: {
                    status: {
                        "foods": values[status + "|foods"],
                        "occurrences": values[status + "|occurrences"],
                        "grams": round(values[status + "|grams"], 3),
                    }
                    for status in sorted({key.split("|", 1)[0] for key in values})
                }
                for nutrient, values in sorted(nutrients.items())
            }
            for profile, nutrients in sorted(profile_totals.items())
        },
        "interpretation_guardrails": [
            "Numeric values marked Assumido are not missingness markers and do not establish analytical measurement.",
            "The TBCA documentation describes NA as not analyzed but states it is treated as zero for dietary-intake assessment; the audit reports the source marker separately and does not alter the local map.",
            "Trace markers are reported separately; the TBCA defines nutrient-specific trace thresholds, so the audit does not impose a universal numeric substitute.",
            "Aggregate exposure is descriptive of the preserved source plans, not a validation of food mappings or diets.",
        ],
    }
    path = output_dir / "tbca-marker-audit.json"
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Codes in scope: {len(codes)}; parsed official pages: {completed}; errors: {len(errors)}")
    print(f"Aggregated result (no per-food compositions): {path}")
    return payload


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--workers", type=int, choices=range(1, 5), default=3)
    parser.add_argument("--request-pause", type=float, default=0.25)
    args = parser.parse_args()
    payload = audit(args.output_dir, args.workers, args.request_pause)
    if payload["status"] != "complete":
        raise SystemExit("TBCA marker audit is incomplete; inspect the saved result and fetch_errors.")


if __name__ == "__main__":
    main()
