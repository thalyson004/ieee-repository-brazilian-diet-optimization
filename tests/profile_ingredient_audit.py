"""Lexically flag animal-derived ingredient risks for manual profile review."""

from __future__ import annotations

import argparse
import csv
import json
import re
import unicodedata
from collections import defaultdict
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
EXCLUSIONS_PATH = PROJECT_ROOT / "configs" / "profile-exclusions.json"
ANIMAL_TERMS = {
    "meat_or_fish": (
        "carne", "boi", "bovina", "suina", "porco", "frango", "galinha", "peru",
        "peixe", "sardinha", "atum", "bacalhau", "camarao", "bode", "linguica",
        "presunto", "bacon", "costela", "mignon", "alcatra", "patinho", "lagarto",
        "musculo", "picanha", "charque", "carne seca", "salsicha", "salame",
        "mortadela", "calabresa", "frios", "anchova", "marisco", "frutos do mar",
        "cordeiro", "carneiro", "caldo de galinha", "caldo de frango",
    ),
    "dairy": (
        "leite", "queijo", "iogurte", "manteiga", "requeijao", "coalho", "ricota",
        "mussarela", "parmesao", "cream cheese", "creme de leite", "caseina", "lactose",
    ),
    "egg": ("ovo", "ovos", "clara", "gema", "omelete"),
    "other_animal_derived": ("mel", "gelatina", "colageno", "caldo de carne", "caldo de peixe"),
}


def normalize(value: str) -> str:
    ascii_text = "".join(
        char for char in unicodedata.normalize("NFKD", value.casefold())
        if not unicodedata.combining(char)
    )
    return " ".join(re.findall(r"[a-z0-9]+", ascii_text))


def risk_hits(food_name: str, profile: str) -> dict[str, list[str]]:
    normalized = normalize(food_name)
    words = set(normalized.split())
    hits = {}
    for risk_class, terms in ANIMAL_TERMS.items():
        matched = [
            term for term in terms
            if (" " in normalize(term) and normalize(term) in normalized)
            or (" " not in normalize(term) and normalize(term) in words)
        ]
        # Handle a plant-milk label without hiding explicit cow-milk wording.
        tokens = normalized.split()
        coconut_milk_label = "leite de coco" in normalized or any(
            tokens[index:index + 2] in (["leite", "coco"], ["coco", "leite"])
            for index in range(len(tokens) - 1)
        )
        explicitly_animal_milk = any(
            marker in words for marker in {"vaca", "condensado", "caseina", "lactose"}
        )
        if (risk_class == "dairy" and coconut_milk_label and tokens.count("leite") == 1
                and not explicitly_animal_milk):
            matched = [term for term in matched if term != "leite"]
        if risk_class == "dairy" and "couve" in words and "manteiga" in words:
            tokens = normalized.split()
            if any(tokens[index:index + 2] == ["couve", "manteiga"] for index in range(len(tokens) - 1)):
                matched = [term for term in matched if term != "manteiga"]
        if risk_class == "dairy" and "sem" in words:
            tokens = normalized.split()
            matched = [
                term for term in matched
                if not any(tokens[index] == "sem" and tokens[index + 1] == normalize(term)
                           for index in range(len(tokens) - 1))
            ]
        if profile == "vegetariana" and risk_class == "meat_or_fish" and ("ovo" in words or "ovos" in words or "omelete" in words):
            matched = [term for term in matched if term != "galinha"]
        if not matched:
            continue
        if profile == "vegetariana" and risk_class in {"dairy", "egg"}:
            continue
        hits[risk_class] = matched
    return hits


def collect_profile(profile: str) -> list[dict]:
    path = PROJECT_ROOT / "diets-base" / f"dietas-{profile}.json"
    plans = json.loads(path.read_text(encoding="utf-8"))
    exclusion_config = json.loads(EXCLUSIONS_PATH.read_text(encoding="utf-8"))
    exclusions = {
        item["food_name"]: item["reason"]
        for item in exclusion_config["profiles"].get(profile, [])
    }
    counts: dict[str, dict] = defaultdict(lambda: {"occurrences": 0, "diet_ids": set()})
    for diet_id, plan in enumerate(plans, start=1):
        for meals in plan.values():
            if not isinstance(meals, dict):
                continue
            for items in meals.values():
                if not isinstance(items, list):
                    continue
                for item in items:
                    if not isinstance(item, dict):
                        continue
                    name = str(item.get("alimento", ""))
                    if name:
                        counts[name]["occurrences"] += 1
                        counts[name]["diet_ids"].add(diet_id)
    return [
        {
            "profile": profile,
            "food_name": name,
            "occurrence_count": values["occurrences"],
            "source_diet_count": len(values["diet_ids"]),
            "lexical_risk_hits": risk_hits(name, profile),
            "review_status": (
                "EXCLUDED_FROM_DERIVED_PROFILE_POOL"
                if name in exclusions else "PENDING_INGREDIENT_VERIFICATION"
            ),
            "decision": exclusions.get(name, ""),
            "ingredient_evidence": (
                "configs/profile-exclusions.json; exact source name is removed only from derived optimizer input"
                if name in exclusions else ""
            ),
            "reviewer": "",
            "review_date": "",
        }
        for name, values in sorted(counts.items())
    ]


def build_queue() -> list[dict]:
    return collect_profile("vegetariana") + collect_profile("vegana")


def write_queue(output_dir: Path) -> tuple[Path, Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    rows = build_queue()
    json_path = output_dir / "profile-ingredient-review-queue.json"
    csv_path = output_dir / "profile-ingredient-review-queue.csv"
    json_path.write_text(json.dumps({
        "schema_version": "1.0",
        "status": "lexical_screen_only_no_ingredient_claims_verified",
        "scope": ["vegetariana", "vegana"],
        "rows": rows,
    }, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    columns = ["profile", "food_name", "occurrence_count", "source_diet_count", "lexical_risk_hits", "review_status", "decision", "ingredient_evidence", "reviewer", "review_date"]
    with csv_path.open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=columns)
        writer.writeheader()
        for row in rows:
            writer.writerow({**row, "lexical_risk_hits": json.dumps(row["lexical_risk_hits"], ensure_ascii=False)})
    return json_path, csv_path


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    json_path, csv_path = write_queue(args.output_dir.resolve())
    print(f"Profile-food rows to review: {len(build_queue())}")
    print(f"JSON: {json_path}")
    print(f"CSV: {csv_path}")


if __name__ == "__main__":
    main()
