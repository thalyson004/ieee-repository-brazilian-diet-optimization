"""Load and validate an explicit nutritional constraint protocol."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def load_protocol(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    protocol_id = payload.get("protocol_id")
    if not protocol_id:
        raise ValueError("Nutrition protocol must define protocol_id")

    minima: dict[str, float] = {}
    maxima: dict[str, dict[str, float]] = {}
    for target in payload.get("core_targets", []):
        field = target.get("tbca_field")
        if not field or not target.get("unit") or not target.get("source"):
            raise ValueError(f"Incomplete core nutrition target: {target}")
        lower, upper = target.get("lower"), target.get("upper")
        if lower is None and upper is None:
            raise ValueError(f"Target has no active bound: {field}")
        if lower is not None:
            minima[field] = float(lower)
        if upper is not None:
            maxima[field] = {"meta": float(upper), "tolerancia": 1.0}

    secondary: list[dict[str, Any]] = []
    descriptive: list[dict[str, Any]] = []
    for target in payload.get("additional_rules", []):
        field = target.get("tbca_field")
        if not field:
            raise ValueError(f"Additional nutrition rule lacks tbca_field: {target}")
        rule = str(target.get("model_rule", "")).lower()
        if "secondary adequacy outcome" in rule:
            secondary.append(target)
            continue
        lower, upper = target.get("lower"), target.get("upper")
        if lower is None and upper is None:
            descriptive.append(target)
            continue
        if lower is not None:
            minima[field] = float(lower)
        if upper is not None:
            maxima[field] = {"meta": float(upper), "tolerancia": 1.0}

    if "Energia" not in minima or "Energia" not in maxima:
        raise ValueError("Protocol must specify both lower and upper energy bounds")
    if minima["Energia"] > maxima["Energia"]["meta"]:
        raise ValueError("Energy lower bound exceeds its upper bound")
    return {
        "protocol_id": protocol_id,
        "minimum_goals": minima,
        "maximum_goals": maxima,
        "secondary_targets": secondary,
        "descriptive_targets": descriptive,
        "meal_energy_share_limits": {},
        "meal_energy_share_penalty_weight": 0.0,
        "source_status": payload.get("status"),
    }
