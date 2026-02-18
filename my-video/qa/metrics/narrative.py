from __future__ import annotations

from typing import Any, Dict, List


_REQUIRED_SECTIONS = ["hook", "problem", "how", "example", "recap", "outro"]


def evaluate_narrative(manifest: Dict[str, Any]) -> Dict[str, Any]:
    narrative = manifest.get("narrative", {}) if isinstance(manifest, dict) else {}
    section_coverage = narrative.get("sectionCoverage") if isinstance(narrative, dict) else {}
    section_coverage = section_coverage if isinstance(section_coverage, dict) else {}

    missing: List[str] = []
    for section in _REQUIRED_SECTIONS:
        if not bool(section_coverage.get(section, False)):
            missing.append(section)

    covered = len(_REQUIRED_SECTIONS) - len(missing)
    score = (covered / len(_REQUIRED_SECTIONS)) * 100.0

    fail_reasons: List[str] = []
    if missing:
        fail_reasons.append("missing sections: " + ", ".join(missing))

    return {
        "score": score,
        "covered_count": covered,
        "required_count": len(_REQUIRED_SECTIONS),
        "missing_sections": missing,
        "hasHook": bool(narrative.get("hasHook", False)),
        "hasExample": bool(narrative.get("hasExample", False)),
        "hasRecap": bool(narrative.get("hasRecap", False)),
        "fail_reasons": fail_reasons,
    }
