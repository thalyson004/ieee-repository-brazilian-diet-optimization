"""Build a non-accepting, ranked TBCA candidate queue for manual food-map review."""

from __future__ import annotations

import argparse
import csv
import json
import re
import unicodedata
from difflib import SequenceMatcher
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
AUDIT_SOURCE = PROJECT_ROOT / "archive" / "audits" / "food-mapping-audit.csv"
TBCA_SOURCE = PROJECT_ROOT / "maps" / "base" / "mapa-tbca-completo.json"
GENERIC_QUALIFIERS = {
    "a", "as", "ao", "aos", "com", "c", "da", "das", "de", "do", "dos",
    "em", "in", "natura", "o", "os", "para", "por", "sem", "s", "brasil",
    "cru", "crua", "cruas", "crus", "media", "medias", "diferente", "diferentes",
    "amostra", "amostras", "tipo", "tipos",
}


def normalize_name(value: str) -> str:
    decomposed = unicodedata.normalize("NFKD", value.casefold())
    ascii_text = "".join(char for char in decomposed if not unicodedata.combining(char))
    tokens = re.findall(r"[a-z0-9]+", ascii_text)
    return " ".join(token for token in tokens if token not in GENERIC_QUALIFIERS)


def similarity(source: str, candidate: str) -> float:
    source_norm, candidate_norm = normalize_name(source), normalize_name(candidate)
    sequence = SequenceMatcher(None, source_norm, candidate_norm).ratio()
    source_tokens, candidate_tokens = set(source_norm.split()), set(candidate_norm.split())
    overlap = len(source_tokens & candidate_tokens) / max(1, len(source_tokens | candidate_tokens))
    return 0.55 * sequence + 0.45 * overlap


def build_queue() -> list[dict]:
    with AUDIT_SOURCE.open(encoding="utf-8-sig", newline="") as stream:
        mappings = list(csv.DictReader(stream))
    tbca = json.loads(TBCA_SOURCE.read_text(encoding="utf-8"))
    records = [
        (code, item["nome"], normalize_name(item["nome"]))
        for code, item in tbca.items()
    ]
    queue = []
    for mapping in mappings:
        if mapping["mapping_kind"] != "non_identity_unreviewed":
            continue
        source = mapping["food_original"]
        current = mapping["tbca_record_name"]
        source_tokens = set(normalize_name(source).split())
        overlap_ranked = []
        for code, name, normalized in records:
            if name == current:
                continue
            candidate_tokens = set(normalized.split())
            overlap = len(source_tokens & candidate_tokens) / max(
                1, len(source_tokens | candidate_tokens)
            )
            overlap_ranked.append((overlap, code, name))
        shortlist = sorted(overlap_ranked, key=lambda row: (-row[0], row[2]))[:120]
        ranked = sorted(
            ({"tbca_code": code, "candidate_name": name,
              "heuristic_similarity": round(similarity(source, name), 5)}
             for _, code, name in shortlist),
            key=lambda item: (-item["heuristic_similarity"], item["candidate_name"]),
        )[:5]
        queue.append({
            "food_original": source,
            "current_tbca_name": current,
            "current_tbca_code": mapping["tbca_code"],
            "occurrence_count": int(mapping["occurrence_count"]),
            "profiles": mapping["profiles"],
            "review_status": "PENDING_MANUAL_REVIEW",
            "automatic_acceptance": False,
            "decision": "",
            "approved_tbca_name": "",
            "approved_tbca_code": "",
            "decision_rationale": "",
            "evidence_url_or_reference": "",
            "reviewer": "",
            "review_date": "",
            "environmental_mapping_decision": "",
            "ranking_method": "normalized character similarity plus token Jaccard; suggestions are not equivalence evidence",
            "suggestions": ranked,
        })
    return sorted(queue, key=lambda item: (-item["occurrence_count"], item["food_original"]))


def write_queue(output_dir: Path) -> tuple[Path, Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    rows = build_queue()
    json_path = output_dir / "food-mapping-review-queue.json"
    csv_path = output_dir / "food-mapping-review-queue.csv"
    json_path.write_text(json.dumps({
        "schema_version": "1.0",
        "status": "suggestions_only_no_mapping_was_changed",
        "unreviewed_mapping_count": len(rows),
        "rows": rows,
    }, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    columns = [
        "food_original", "current_tbca_name", "current_tbca_code", "occurrence_count",
        "profiles", "review_status", "decision", "approved_tbca_name", "approved_tbca_code",
        "decision_rationale", "evidence_url_or_reference", "reviewer", "review_date",
        "environmental_mapping_decision",
    ]
    for index in range(1, 6):
        columns.extend((f"candidate_{index}", f"candidate_{index}_code", f"candidate_{index}_score"))
    with csv_path.open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=columns)
        writer.writeheader()
        for row in rows:
            output = {key: row[key] for key in columns[:14]}
            for index, candidate in enumerate(row["suggestions"], start=1):
                output[f"candidate_{index}"] = candidate["candidate_name"]
                output[f"candidate_{index}_code"] = candidate["tbca_code"]
                output[f"candidate_{index}_score"] = candidate["heuristic_similarity"]
            writer.writerow(output)
    return json_path, csv_path


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    json_path, csv_path = write_queue(args.output_dir.resolve())
    print(f"Unreviewed mappings: {len(build_queue())}")
    print(f"JSON queue: {json_path}")
    print(f"CSV queue: {csv_path}")


if __name__ == "__main__":
    main()
