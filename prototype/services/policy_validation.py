"""Draft validation & cross-form clinical alerts backed by `data/rulesets/ruleset_multi_category.json`.

Connects the standardized multi-category ruleset from `feat/policy-rules` (`POL-VALID-01`,
`POL-TRIGGER-01`) to voice draft extraction without modifying `features/policy_rules/policy.py`.
All checks are deterministic and non-blocking (advisory warnings/alerts for clinician review).
"""
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MULTI_CATEGORY_PATH = ROOT / "data" / "rulesets" / "ruleset_multi_category.json"

_RULES_CACHE = None
_BP_RE = re.compile(r"^\s*(\d{2,3})\s*/\s*(\d{2,3})")


def _load_rules():
    global _RULES_CACHE
    if _RULES_CACHE is None:
        if MULTI_CATEGORY_PATH.is_file():
            _RULES_CACHE = json.loads(MULTI_CATEGORY_PATH.read_text(encoding="utf-8"))
        else:
            _RULES_CACHE = []
    return _RULES_CACHE


def _parse_bp(value):
    if not isinstance(value, str):
        return None
    m = _BP_RE.match(value)
    if not m:
        return None
    return int(m.group(1)), int(m.group(2))


def _num(value):
    if isinstance(value, bool) or value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _eval_op(actual, op, target):
    if op == "<":
        return actual < target
    if op == "<=":
        return actual <= target
    if op == ">":
        return actual > target
    if op == ">=":
        return actual >= target
    if op == "==":
        return actual == target
    return False


def validate_draft(form_id, extracted, rules=None):
    """Evaluate `form_validation` and `cross_form_trigger` rules against extracted draft values."""
    if not form_id or not isinstance(extracted, dict) or not extracted:
        return {"validation_warnings": [], "policy_alerts": []}

    active_rules = _load_rules() if rules is None else rules
    warnings = []
    alerts = []

    for rule in active_rules:
        if rule.get("status") != "active":
            continue
        category = rule.get("category")
        clause = (rule.get("source") or {}).get("clause", "")

        if category == "form_validation" and rule.get("form_id") == form_id:
            for item in rule.get("validation_rules") or []:
                vtype = item.get("type")
                if vtype == "range":
                    field = item.get("field")
                    if field not in extracted:
                        continue
                    val = _num(extracted.get(field))
                    if val is None:
                        continue
                    lo, hi = item.get("min"), item.get("max")
                    if (lo is not None and val < lo) or (hi is not None and val > hi):
                        warnings.append({
                            "rule_id": rule["rule_id"],
                            "clause": clause,
                            "field": field,
                            "value": extracted[field],
                            "message": item.get("error_message", f"Giá trị {field} ngoài khoảng hợp lệ"),
                        })
                elif vtype == "expression" and item.get("expr") == "values.tam_thu > values.tam_truong":
                    bp = _parse_bp(extracted.get("huyet_ap"))
                    if bp is not None and bp[0] <= bp[1]:
                        warnings.append({
                            "rule_id": rule["rule_id"],
                            "clause": clause,
                            "field": "huyet_ap",
                            "value": extracted["huyet_ap"],
                            "message": item.get("error_message", "Huyết áp tâm thu phải lớn hơn tâm trương"),
                        })

        elif category == "cross_form_trigger":
            tc = rule.get("trigger_condition") or {}
            if tc.get("source_form_id") != form_id:
                continue
            conds = tc.get("conditions") or []
            matched = []
            for cond in conds:
                field = cond.get("field")
                if field not in extracted:
                    continue
                val = _num(extracted.get(field))
                if val is not None and _eval_op(val, cond.get("op"), cond.get("value")):
                    matched.append(f"{field}={extracted[field]}")
            op = (tc.get("operator") or "OR").upper()
            triggered = (len(matched) == len(conds) and bool(conds)) if op == "AND" else bool(matched)
            if triggered:
                action = rule.get("action") or {}
                alerts.append({
                    "rule_id": rule["rule_id"],
                    "clause": clause,
                    "title": rule.get("title", ""),
                    "alert_level": action.get("alert_level", "HIGH"),
                    "priority": action.get("priority", "high"),
                    "target_form_id": action.get("target_form_id"),
                    "matched": matched,
                    "message": (rule.get("source") or {}).get("evidence", rule.get("title", "")),
                })

    return {"validation_warnings": warnings, "policy_alerts": alerts}
