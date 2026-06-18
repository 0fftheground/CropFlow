from __future__ import annotations

from typing import Any

from app.core.constants import PEST_DISEASE_TARGET_LABELS


def localize_disease_pest_plan_payload(payload: dict[str, Any]) -> dict[str, Any]:
    localized = dict(payload)
    if isinstance(localized.get("targets"), dict):
        localized["targets"] = _localize_target_map(localized["targets"])
    if isinstance(localized.get("rounds"), list):
        localized["rounds"] = [_localize_target_round_payload(item) for item in localized["rounds"]]

    control_plan = localized.get("controlPlan")
    if isinstance(control_plan, dict):
        localized_control_plan = dict(control_plan)
        if isinstance(localized_control_plan.get("targets"), dict):
            localized_control_plan["targets"] = _localize_target_map(localized_control_plan["targets"])
        if isinstance(localized_control_plan.get("rounds"), list):
            localized_control_plan["rounds"] = [
                _localize_target_round_payload(item) for item in localized_control_plan["rounds"]
            ]
        localized["controlPlan"] = localized_control_plan

    theory_plan = localized.get("theoryPlan")
    if isinstance(theory_plan, dict):
        localized_theory_plan = dict(theory_plan)
        if isinstance(localized_theory_plan.get("targets"), dict):
            localized_theory_plan["targets"] = _localize_target_map(localized_theory_plan["targets"])
        if isinstance(localized_theory_plan.get("rounds"), list):
            localized_theory_plan["rounds"] = [
                _localize_target_round_payload(item) for item in localized_theory_plan["rounds"]
            ]
        localized["theoryPlan"] = localized_theory_plan

    adjusted_plan = localized.get("adjustedPlan")
    if isinstance(adjusted_plan, dict) and isinstance(adjusted_plan.get("rounds"), list):
        localized_adjusted_plan = dict(adjusted_plan)
        localized_adjusted_plan["rounds"] = [
            _localize_target_round_payload(item) for item in localized_adjusted_plan["rounds"]
        ]
        localized["adjustedPlan"] = localized_adjusted_plan
    return localized


def _localize_target_round_payload(item: Any) -> Any:
    if not isinstance(item, dict):
        return item
    localized_item = dict(item)
    if isinstance(localized_item.get("targets"), dict):
        localized_item["targets"] = _localize_target_map(localized_item["targets"])
    return localized_item


def _localize_target_map(targets: dict[str, Any]) -> dict[str, Any]:
    return {
        str(PEST_DISEASE_TARGET_LABELS.get(str(key), key)): value
        for key, value in targets.items()
    }
