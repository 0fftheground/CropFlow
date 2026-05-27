from __future__ import annotations

import json
import logging
import socket
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from typing import Any, Protocol
from urllib import error, request
from urllib.parse import urlsplit

from app.core.logging import LogTimer, summarize_for_log
from app.models import CropStageState, CropThermalTimeState, PlantingPlan, StagePredictionSnapshot
from app.repositories import (
    CropStageStateRepository,
    CropThermalTimeStateRepository,
    PlantingPlanRepository,
    StagePredictionSnapshotRepository,
)

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class StageTimelineNode:
    stage_code: str
    stage_name: str
    start_date: date
    end_date: date | None
    key_date: date | None
    metadata: dict[str, Any]


@dataclass(slots=True)
class StagePredictionResult:
    algorithm_code: str
    algorithm_version: str | None
    stage_timeline: dict[str, Any]
    thermal_thresholds: dict[str, Any]
    raw_response: dict[str, Any]


@dataclass(slots=True)
class StageRefreshResult:
    snapshot: StagePredictionSnapshot
    crop_stage_state: CropStageState
    crop_thermal_time_state: CropThermalTimeState
    previous_stage_code: str | None
    stage_changed: bool


@dataclass(slots=True)
class StageStateSnapshot:
    crop_stage_state: CropStageState | None
    crop_thermal_time_state: CropThermalTimeState | None
    latest_prediction_snapshot: StagePredictionSnapshot | None


class StagePredictionClient(Protocol):
    def predict_stage(
        self,
        *,
        planting_plan: PlantingPlan,
        as_of_date: date,
    ) -> StagePredictionResult: ...


class HttpStagePredictionClient:
    def __init__(self, base_url: str, timeout_seconds: float = 10.0) -> None:
        self.base_url = base_url.rstrip("/")
        self.timeout_seconds = timeout_seconds

    def predict_stage(
        self,
        *,
        planting_plan: PlantingPlan,
        as_of_date: date,
    ) -> StagePredictionResult:
        payload = _build_stage_prediction_request_payload(planting_plan, as_of_date=as_of_date)
        response = self._post_json("/stage/predict", payload)
        data = response.get("data")
        if not isinstance(data, dict):
            raise ValueError("stage prediction API did not return a valid data object.")
        stage_timeline = dict(data.get("stage_timeline") or {})
        if not stage_timeline:
            raise ValueError("stage prediction API did not return stage_timeline.")
        thermal_thresholds = dict(data.get("thermal_thresholds") or {})
        return StagePredictionResult(
            algorithm_code=str(data.get("algorithm_code") or "stage_prediction_algorithm"),
            algorithm_version=str(data["algorithm_version"]) if data.get("algorithm_version") is not None else None,
            stage_timeline=stage_timeline,
            thermal_thresholds=thermal_thresholds,
            raw_response=response,
        )

    def _post_json(self, path: str, payload: dict[str, Any]) -> dict[str, Any]:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        url = f"{self.base_url}{path}"
        http_request = request.Request(
            url,
            data=body,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        timer = LogTimer()
        logger.info(
            "Calling stage prediction API path=%s host=%s payload=%s",
            path,
            urlsplit(url).netloc,
            summarize_for_log(payload),
        )
        try:
            with request.urlopen(http_request, timeout=self.timeout_seconds) as response:
                response_payload = json.loads(response.read().decode("utf-8"))
                logger.info(
                    "Stage prediction API succeeded path=%s status=%s duration_ms=%.2f response=%s",
                    path,
                    getattr(response, "status", 200),
                    timer.elapsed_ms,
                    summarize_for_log(response_payload),
                )
                return response_payload
        except error.HTTPError as exc:
            raw_response = exc.read().decode("utf-8", errors="replace")
            logger.warning(
                "Stage prediction API returned HTTP error path=%s status=%s duration_ms=%.2f payload=%s response=%s",
                path,
                exc.code,
                timer.elapsed_ms,
                summarize_for_log(payload),
                summarize_for_log(raw_response),
            )
            message = f"Stage prediction API {path} returned HTTP {exc.code}"
            if raw_response:
                message = f"{message}: {raw_response}"
            raise ValueError(message) from exc
        except error.URLError as exc:
            logger.error(
                "Stage prediction API is unreachable path=%s duration_ms=%.2f payload=%s reason=%s",
                path,
                timer.elapsed_ms,
                summarize_for_log(payload),
                exc.reason,
            )
            raise RuntimeError(f"Stage prediction API {path} is unreachable: {exc.reason}") from exc
        except (TimeoutError, socket.timeout) as exc:
            logger.error(
                "Stage prediction API timed out path=%s duration_ms=%.2f payload=%s",
                path,
                timer.elapsed_ms,
                summarize_for_log(payload),
            )
            raise RuntimeError(f"Stage prediction API {path} timed out.") from exc


class MockStagePredictionClient:
    def predict_stage(
        self,
        *,
        planting_plan: PlantingPlan,
        as_of_date: date,
    ) -> StagePredictionResult:
        tillering_date = planting_plan.sowing_date + timedelta(days=10)
        pokou_date = tillering_date + timedelta(days=50)
        heading_date = pokou_date + timedelta(days=8)
        maturity_date = heading_date + timedelta(days=32)
        stage_timeline = {
            "stages": [
                {
                    "stage_code": "seedling",
                    "stage_name": "苗期",
                    "start_date": planting_plan.sowing_date.isoformat(),
                    "end_date": (tillering_date - timedelta(days=1)).isoformat(),
                    "key_date": planting_plan.sowing_date.isoformat(),
                },
                {
                    "stage_code": "tillering",
                    "stage_name": "分蘖期",
                    "start_date": tillering_date.isoformat(),
                    "end_date": (pokou_date - timedelta(days=1)).isoformat(),
                    "key_date": tillering_date.isoformat(),
                },
                {
                    "stage_code": "pokou",
                    "stage_name": "破口期",
                    "start_date": pokou_date.isoformat(),
                    "end_date": (heading_date - timedelta(days=1)).isoformat(),
                    "key_date": pokou_date.isoformat(),
                },
                {
                    "stage_code": "heading",
                    "stage_name": "齐穗期",
                    "start_date": heading_date.isoformat(),
                    "end_date": (maturity_date - timedelta(days=1)).isoformat(),
                    "key_date": heading_date.isoformat(),
                },
                {
                    "stage_code": "maturity",
                    "stage_name": "成熟期",
                    "start_date": maturity_date.isoformat(),
                    "end_date": maturity_date.isoformat(),
                    "key_date": maturity_date.isoformat(),
                },
            ],
        }
        thermal_thresholds = {
            "base_temperature": 10,
            "accumulated_thermal_time": 780,
            "thermal_time_unit": "degree_day",
            "last_calculated_date": as_of_date.isoformat(),
            "data_version": "mock-weather-v1",
        }
        return StagePredictionResult(
            algorithm_code="stage_prediction_algorithm",
            algorithm_version="mock-v1",
            stage_timeline=stage_timeline,
            thermal_thresholds=thermal_thresholds,
            raw_response={
                "mock": True,
                "code": 200,
                "data": {
                    "algorithm_code": "stage_prediction_algorithm",
                    "algorithm_version": "mock-v1",
                    "stage_timeline": stage_timeline,
                    "thermal_thresholds": thermal_thresholds,
                },
            },
        )


class StageManagementService:
    def __init__(
        self,
        planting_plan_repository: PlantingPlanRepository,
        stage_prediction_snapshot_repository: StagePredictionSnapshotRepository,
        crop_stage_state_repository: CropStageStateRepository,
        crop_thermal_time_state_repository: CropThermalTimeStateRepository,
        stage_prediction_client: StagePredictionClient,
    ) -> None:
        self.planting_plan_repository = planting_plan_repository
        self.stage_prediction_snapshot_repository = stage_prediction_snapshot_repository
        self.crop_stage_state_repository = crop_stage_state_repository
        self.crop_thermal_time_state_repository = crop_thermal_time_state_repository
        self.stage_prediction_client = stage_prediction_client

    def refresh_prediction(
        self,
        planting_plan_id: int,
        *,
        prediction_source: str,
        source_event_id: int | None = None,
        as_of_date: date | None = None,
    ) -> StageRefreshResult:
        planting_plan = self._get_plan(planting_plan_id)
        effective_as_of_date = as_of_date or date.today()
        prediction = self.stage_prediction_client.predict_stage(
            planting_plan=planting_plan,
            as_of_date=effective_as_of_date,
        )
        latest_snapshot = self.stage_prediction_snapshot_repository.get_latest_by_plan(planting_plan_id)
        snapshot = StagePredictionSnapshot(
            planting_plan_id=planting_plan_id,
            prediction_version=(latest_snapshot.prediction_version if latest_snapshot is not None else 0) + 1,
            prediction_source=prediction_source,
            algorithm_code=prediction.algorithm_code,
            algorithm_version=prediction.algorithm_version,
            generated_at=_utcnow(),
            input_payload=_build_stage_prediction_request_payload(planting_plan, as_of_date=effective_as_of_date),
            stage_timeline=prediction.stage_timeline,
            thermal_thresholds=prediction.thermal_thresholds,
            source_event_id=source_event_id,
            created_by_type="system",
            created_by_id="StageManagementService",
        )
        self.stage_prediction_snapshot_repository.add(snapshot)
        self.stage_prediction_snapshot_repository.flush()

        current_node = resolve_current_stage_node(prediction.stage_timeline, effective_as_of_date)
        existing_stage_state = self.crop_stage_state_repository.get_by_plan(planting_plan_id)
        previous_stage_code = existing_stage_state.current_stage_code if existing_stage_state is not None else None
        if existing_stage_state is None:
            stage_state = CropStageState(
                planting_plan_id=planting_plan_id,
                current_stage_code=current_node.stage_code,
                current_stage_name=current_node.stage_name,
                stage_source="predicted",
                effective_date=current_node.start_date,
                source_snapshot_id=snapshot.id,
                last_updated_at=_utcnow(),
                version=1,
                created_by_type="system",
                created_by_id="StageManagementService",
            )
            self.crop_stage_state_repository.add(stage_state)
        else:
            stage_state = existing_stage_state
            stage_state.current_stage_code = current_node.stage_code
            stage_state.current_stage_name = current_node.stage_name
            stage_state.stage_source = "predicted"
            stage_state.effective_date = current_node.start_date
            stage_state.source_snapshot_id = snapshot.id
            stage_state.last_updated_at = _utcnow()
            stage_state.version = int(stage_state.version or 0) + 1
            stage_state.updated_at = _utcnow()

        thermal_payload = prediction.thermal_thresholds
        existing_thermal_state = self.crop_thermal_time_state_repository.get_by_plan(planting_plan_id)
        accumulated_thermal_time = Decimal(str(thermal_payload.get("accumulated_thermal_time") or 0))
        base_temperature_raw = thermal_payload.get("base_temperature")
        base_temperature = Decimal(str(base_temperature_raw)) if base_temperature_raw is not None else None
        last_calculated_date = _parse_optional_iso_date(thermal_payload.get("last_calculated_date")) or effective_as_of_date
        if existing_thermal_state is None:
            thermal_state = CropThermalTimeState(
                planting_plan_id=planting_plan_id,
                accumulated_thermal_time=accumulated_thermal_time,
                thermal_time_unit=str(thermal_payload.get("thermal_time_unit") or "degree_day"),
                base_temperature=base_temperature,
                start_date=planting_plan.sowing_date,
                last_calculated_date=last_calculated_date,
                threshold_snapshot_id=snapshot.id,
                data_version=str(thermal_payload["data_version"]) if thermal_payload.get("data_version") is not None else None,
                created_by_type="system",
                created_by_id="StageManagementService",
            )
            self.crop_thermal_time_state_repository.add(thermal_state)
        else:
            thermal_state = existing_thermal_state
            thermal_state.accumulated_thermal_time = accumulated_thermal_time
            thermal_state.thermal_time_unit = str(thermal_payload.get("thermal_time_unit") or "degree_day")
            thermal_state.base_temperature = base_temperature
            thermal_state.start_date = planting_plan.sowing_date
            thermal_state.last_calculated_date = last_calculated_date
            thermal_state.threshold_snapshot_id = snapshot.id
            thermal_state.data_version = (
                str(thermal_payload["data_version"]) if thermal_payload.get("data_version") is not None else None
            )
            thermal_state.updated_at = _utcnow()

        return StageRefreshResult(
            snapshot=snapshot,
            crop_stage_state=stage_state,
            crop_thermal_time_state=thermal_state,
            previous_stage_code=previous_stage_code,
            stage_changed=previous_stage_code is not None and previous_stage_code != current_node.stage_code,
        )

    def get_stage_snapshot(self, planting_plan_id: int) -> StageStateSnapshot:
        self._get_plan(planting_plan_id)
        return StageStateSnapshot(
            crop_stage_state=self.crop_stage_state_repository.get_by_plan(planting_plan_id),
            crop_thermal_time_state=self.crop_thermal_time_state_repository.get_by_plan(planting_plan_id),
            latest_prediction_snapshot=self.stage_prediction_snapshot_repository.get_latest_by_plan(planting_plan_id),
        )

    def _get_plan(self, planting_plan_id: int) -> PlantingPlan:
        planting_plan = self.planting_plan_repository.get(planting_plan_id)
        if planting_plan is None:
            raise LookupError(f"Planting plan {planting_plan_id} does not exist.")
        return planting_plan


def resolve_current_stage_node(stage_timeline: dict[str, Any], as_of_date: date) -> StageTimelineNode:
    nodes = parse_stage_timeline_nodes(stage_timeline)
    effective_nodes = [node for node in nodes if node.start_date <= as_of_date]
    if effective_nodes:
        return effective_nodes[-1]
    return nodes[0]


def parse_stage_timeline_nodes(stage_timeline: dict[str, Any]) -> list[StageTimelineNode]:
    raw_stages = stage_timeline.get("stages")
    if not isinstance(raw_stages, list) or not raw_stages:
        raise ValueError("stage_timeline.stages must be a non-empty array.")
    nodes: list[StageTimelineNode] = []
    for item in raw_stages:
        if not isinstance(item, dict):
            raise ValueError("stage_timeline.stages items must be objects.")
        stage_code = str(item.get("stage_code") or item.get("stageCode") or "").strip()
        if not stage_code:
            raise ValueError("stage_timeline.stages item is missing stage_code.")
        stage_name = str(item.get("stage_name") or item.get("stageName") or stage_code).strip()
        raw_start_date = item.get("start_date") or item.get("startDate") or item.get("key_date") or item.get("keyDate")
        if raw_start_date is None:
            raise ValueError(f"stage_timeline stage {stage_code} is missing start_date.")
        raw_end_date = item.get("end_date") or item.get("endDate")
        raw_key_date = item.get("key_date") or item.get("keyDate")
        metadata = {
            key: value
            for key, value in item.items()
            if key
            not in {
                "stage_code",
                "stageCode",
                "stage_name",
                "stageName",
                "start_date",
                "startDate",
                "end_date",
                "endDate",
                "key_date",
                "keyDate",
            }
        }
        nodes.append(
            StageTimelineNode(
                stage_code=stage_code,
                stage_name=stage_name,
                start_date=_parse_required_iso_date(raw_start_date, f"{stage_code}.start_date"),
                end_date=_parse_optional_iso_date(raw_end_date),
                key_date=_parse_optional_iso_date(raw_key_date),
                metadata=metadata,
            ),
        )
    nodes.sort(key=lambda item: (item.start_date, item.stage_code))
    return nodes


def extract_pest_disease_growth_stage(stage_timeline: dict[str, Any]) -> dict[str, str]:
    nodes = parse_stage_timeline_nodes(stage_timeline)
    code_to_date = {node.stage_code: node.start_date.isoformat() for node in nodes}
    required_mapping = {
        "tillering_date": "tillering",
        "pokou_date": "pokou",
        "heading_date": "heading",
        "maturity_date": "maturity",
    }
    missing = [stage_code for stage_code in required_mapping.values() if stage_code not in code_to_date]
    if missing:
        raise ValueError(f"stage_timeline does not contain required pest-disease stage codes: {missing}.")
    return {
        field_name: code_to_date[stage_code]
        for field_name, stage_code in required_mapping.items()
    }


def _build_stage_prediction_request_payload(
    planting_plan: PlantingPlan,
    *,
    as_of_date: date,
) -> dict[str, Any]:
    metadata_payload = dict(planting_plan.metadata_payload or {})
    return {
        "planting_plan_id": planting_plan.id,
        "plan_code": planting_plan.plan_code,
        "crop_name": planting_plan.crop_name,
        "culti_type_code": planting_plan.culti_type_code,
        "planting_method_code": planting_plan.planting_method_code,
        "variety_id": planting_plan.variety_id,
        "variety_name": planting_plan.variety_name,
        "sowing_date": planting_plan.sowing_date.isoformat(),
        "transplant_date": planting_plan.transplant_date.isoformat() if planting_plan.transplant_date else None,
        "transplant_leaf_age": str(planting_plan.transplant_leaf_age) if planting_plan.transplant_leaf_age is not None else None,
        "expected_harvest_date": (
            planting_plan.expected_harvest_date.isoformat() if planting_plan.expected_harvest_date else None
        ),
        "previous_harvest_date": (
            planting_plan.previous_harvest_date.isoformat() if planting_plan.previous_harvest_date else None
        ),
        "ratoon_first_season_harvest_date": (
            planting_plan.ratoon_first_season_harvest_date.isoformat()
            if planting_plan.ratoon_first_season_harvest_date
            else None
        ),
        "as_of_date": as_of_date.isoformat(),
        "metadata": metadata_payload,
    }


def _parse_required_iso_date(raw_value: Any, field_name: str) -> date:
    parsed = _parse_optional_iso_date(raw_value)
    if parsed is None:
        raise ValueError(f"{field_name} must be a valid ISO date.")
    return parsed


def _parse_optional_iso_date(raw_value: Any) -> date | None:
    if raw_value is None:
        return None
    if isinstance(raw_value, date):
        return raw_value
    if not isinstance(raw_value, str):
        raise ValueError(f"Unsupported date value: {raw_value!r}.")
    return date.fromisoformat(raw_value)


def _utcnow() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)
