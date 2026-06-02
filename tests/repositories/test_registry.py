import pytest
from sqlalchemy.exc import SAWarning

from app.db.base import Base
from app.repositories import ReviewRequestRepository


def test_core_models_registered_in_metadata() -> None:
    expected_tables = {
        "cf_code_dict",
        "cf_crop_stage_dict",
        "cf_field",
        "cf_farm",
        "cf_planting_plan",
        "cf_planting_plan_field_relation",
        "cf_event_record",
        "cf_calendar_item",
        "cf_task_intent",
        "cf_review_request",
        "cf_farming_task",
        "cf_operation_plan",
        "cf_execution",
        "cf_execution_record",
        "cf_crop_stage_state",
        "cf_crop_thermal_time_state",
        "cf_rice_variety",
        "cf_stage_prediction_snapshot",
        "cf_user",
    }

    assert expected_tables.issubset(Base.metadata.tables.keys())


def test_metadata_can_sort_tables() -> None:
    with pytest.warns(SAWarning, match="unresolvable cycles"):
        sorted_tables = Base.metadata.sorted_tables

    assert len(sorted_tables) >= 19


def test_review_request_source_entity_mapping_covers_core_entities() -> None:
    for entity_type in ("task_intent", "calendar_item", "farming_task", "execution_record"):
        assert entity_type in ReviewRequestRepository.SOURCE_ENTITY_MODELS
