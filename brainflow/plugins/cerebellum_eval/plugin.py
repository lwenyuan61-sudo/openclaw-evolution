"""Cerebellum Evaluator (prediction/error-correction) - MVP.

Given raw forage text, estimates:
- evidence_strength (0-10)
- novelty (0-10)
- actionability (0-10)
- risk (0-10)

Heuristic only; does not decide final actions.
"""

from __future__ import annotations

import re
from typing import Any, Dict


def run(raw: str) -> Dict[str, Any]:
    t = (raw or "").lower()

    def has(p: str) -> bool:
        return re.search(p, t) is not None

    evidence = 0
    if has(r"randomi[sz]ed|\brct\b"): evidence += 5
    if has(r"double[- ]blind|placebo"): evidence += 3
    if has(r"meta[- ]analysis|systematic review"): evidence += 2
    evidence = min(evidence, 10)

    novelty = 0
    if has(r"2026"): novelty += 5
    elif has(r"2025"): novelty += 4
    elif has(r"2024"): novelty += 3
    if has(r"preprint|medrxiv|biorxiv|doi:"): novelty += 2
    novelty = min(novelty, 10)

    actionability = 0
    if has(r"trial|nct\d+|dose|mg|week|weeks"): actionability += 4
    if has(r"safety|adverse|ae\b|contraind"): actionability += 2
    if has(r"protocol|methods"): actionability += 1
    actionability = min(actionability, 10)

    risk = 0
    if has(r"immunosuppress|infection|cancer"): risk += 4
    if has(r"rapamycin|sirolimus"): risk += 2
    if has(r"gene therapy|viral vector|oskm|reprogram"): risk += 3
    risk = min(risk, 10)

    return {
        "ok": True,
        "evidence_strength": evidence,
        "novelty": novelty,
        "actionability": actionability,
        "risk": risk,
    }
