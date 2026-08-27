import re
from difflib import SequenceMatcher
from typing import Any

from app.services.multimodal import flatten_artifact

NUMBER_RE = re.compile(r"(?<![A-Za-z])(?:\$|₹|€|£)?\d+(?:[,.]\d+)*(?:\s*%|\s*[A-Za-z]{1,8})?")
DATE_RE = re.compile(r"\b(?:\d{1,4}[/-]){1,2}\d{1,4}\b|\b(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+\d{1,2},?\s+\d{4}\b", re.I)
RISK_TERMS = {"terminate", "termination", "penalty", "liability", "indemnity", "confidential", "renewal", "notice", "warranty", "payment", "obligation", "shall", "must"}


def _norm(text: str) -> str:
    return " ".join(text.lower().split())


def _risk(text: str) -> list[str]:
    normalized = _norm(text)
    return sorted(term for term in RISK_TERMS if re.search(rf"\b{re.escape(term)}\b", normalized))


def _change_kind(old: str, new: str) -> str:
    if NUMBER_RE.findall(old) != NUMBER_RE.findall(new):
        return "numeric_change"
    if DATE_RE.findall(old) != DATE_RE.findall(new):
        return "date_change"
    if _risk(old) != _risk(new):
        return "risk_term_change"
    return "text_change"


def semantic_diff(old_artifact: dict[str, Any], new_artifact: dict[str, Any]) -> dict[str, Any]:
    old_rows = flatten_artifact(old_artifact)
    new_rows = flatten_artifact(new_artifact)
    old_text = [_norm(row["text"]) for row in old_rows]
    new_text = [_norm(row["text"]) for row in new_rows]
    matcher = SequenceMatcher(a=old_text, b=new_text, autojunk=False)
    changes: list[dict[str, Any]] = []

    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        if tag == "equal":
            continue
        old_slice = old_rows[i1:i2]
        new_slice = new_rows[j1:j2]
        if tag == "replace":
            for old_row, new_row in zip(old_slice, new_slice):
                changes.append({
                    "type": _change_kind(old_row["text"], new_row["text"]),
                    "status": "modified",
                    "old": old_row,
                    "new": new_row,
                    "risk_terms_added": sorted(set(_risk(new_row["text"])) - set(_risk(old_row["text"]))),
                    "risk_terms_removed": sorted(set(_risk(old_row["text"])) - set(_risk(new_row["text"]))),
                })
            for row in old_slice[len(new_slice):]:
                changes.append({"type": "removed", "status": "removed", "old": row, "new": None})
            for row in new_slice[len(old_slice):]:
                changes.append({"type": "added", "status": "added", "old": None, "new": row})
        elif tag == "delete":
            changes.extend({"type": "removed", "status": "removed", "old": row, "new": None} for row in old_slice)
        elif tag == "insert":
            changes.extend({"type": "added", "status": "added", "old": None, "new": row} for row in new_slice)

    return {
        "summary": {
            "old_units": len(old_rows),
            "new_units": len(new_rows),
            "changes": len(changes),
            "added": sum(c["status"] == "added" for c in changes),
            "removed": sum(c["status"] == "removed" for c in changes),
            "modified": sum(c["status"] == "modified" for c in changes),
            "risk_changes": sum(bool(c.get("risk_terms_added") or c.get("risk_terms_removed")) for c in changes),
        },
        "changes": changes,
        "method": "provenance-aware sequence alignment with numeric/date/risk classification",
    }
