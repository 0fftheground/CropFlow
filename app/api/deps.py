from __future__ import annotations

from collections.abc import Generator

from fastapi import Depends
from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.db.session import get_db
from app.orchestrator import PlanOrchestrator, build_plan_orchestrator
from app.repositories import (
    CalendarItemRepository,
    CodeDictRepository,
    CropStageStateRepository,
    CropThermalTimeStateRepository,
    EventRecordRepository,
    ExecutionRecordRepository,
    ExecutionRepository,
    FieldRepository,
    FarmingTaskRepository,
    OperationPlanRepository,
    PlantingPlanFieldRelationRepository,
    PlantingPlanRepository,
    RiceVarietyRepository,
    ReviewRequestRepository,
    StagePredictionSnapshotRepository,
    TaskIntentRepository,
)
from app.services import (
    CodeDictQueryService,
    FarmingTaskQueryService,
    HttpPestDiseaseSurveyWindowClient,
    HttpStagePredictionClient,
    HttpWeedDiagnosisClient,
    MockPestDiseaseSurveyWindowClient,
    MockStagePredictionClient,
    MockWeatherProvider,
    MockWeedDiagnosisClient,
    PlantingPlanQueryService,
    PlantingPlanService,
    PlantProtectionPlanContextResolver,
    RiceVarietyQueryService,
    ReviewRequestQueryService,
    ReviewRequestService,
    StageManagementService,
    SurveyDateRecommendationService,
    SurveyResultService,
    TaskExecutionService,
)


def build_survey_date_recommendation_service(
    db: Session,
    settings: Settings,
) -> SurveyDateRecommendationService | None:
    diagnosis_client = (
        HttpWeedDiagnosisClient(settings.weed_diagnosis_base_url)
        if settings.weed_diagnosis_base_url
        else MockWeedDiagnosisClient()
    )
    pest_disease_client = (
        HttpPestDiseaseSurveyWindowClient(settings.pest_disease_survey_base_url)
        if settings.pest_disease_survey_base_url
        else MockPestDiseaseSurveyWindowClient()
    )

    return SurveyDateRecommendationService(
        planting_plan_repository=PlantingPlanRepository(db),
        rice_variety_repository=RiceVarietyRepository(db),
        code_dict_repository=CodeDictRepository(db),
        calendar_item_repository=CalendarItemRepository(db),
        event_record_repository=EventRecordRepository(db),
        weather_provider=MockWeatherProvider(),
        diagnosis_client=diagnosis_client,
        pest_disease_client=pest_disease_client,
        stage_prediction_snapshot_repository=StagePredictionSnapshotRepository(db),
    )


def build_stage_management_service(
    db: Session,
    settings: Settings,
) -> StageManagementService:
    stage_prediction_client = (
        HttpStagePredictionClient(settings.stage_prediction_base_url)
        if settings.stage_prediction_base_url
        else MockStagePredictionClient()
    )
    return StageManagementService(
        planting_plan_repository=PlantingPlanRepository(db),
        stage_prediction_snapshot_repository=StagePredictionSnapshotRepository(db),
        crop_stage_state_repository=CropStageStateRepository(db),
        crop_thermal_time_state_repository=CropThermalTimeStateRepository(db),
        stage_prediction_client=stage_prediction_client,
    )


def build_cropflow_plan_orchestrator(
    db: Session,
    settings: Settings,
    *,
    weather_provider: MockWeatherProvider | None = None,
    diagnosis_client: HttpWeedDiagnosisClient | MockWeedDiagnosisClient | None = None,
    pest_disease_client: HttpPestDiseaseSurveyWindowClient | MockPestDiseaseSurveyWindowClient | None = None,
) -> PlanOrchestrator:
    weather_provider = weather_provider or MockWeatherProvider()
    diagnosis_client = diagnosis_client or (
        HttpWeedDiagnosisClient(settings.weed_diagnosis_base_url)
        if settings.weed_diagnosis_base_url
        else MockWeedDiagnosisClient()
    )
    pest_disease_client = pest_disease_client or (
        HttpPestDiseaseSurveyWindowClient(settings.pest_disease_survey_base_url)
        if settings.pest_disease_survey_base_url
        else MockPestDiseaseSurveyWindowClient()
    )
    survey_date_service = SurveyDateRecommendationService(
        planting_plan_repository=PlantingPlanRepository(db),
        rice_variety_repository=RiceVarietyRepository(db),
        code_dict_repository=CodeDictRepository(db),
        calendar_item_repository=CalendarItemRepository(db),
        event_record_repository=EventRecordRepository(db),
        weather_provider=weather_provider,
        diagnosis_client=diagnosis_client,
        pest_disease_client=pest_disease_client,
        stage_prediction_snapshot_repository=StagePredictionSnapshotRepository(db),
    )
    stage_management_service = build_stage_management_service(db, settings)
    return build_plan_orchestrator(
        planting_plan_repository=PlantingPlanRepository(db),
        calendar_item_repository=CalendarItemRepository(db),
        farming_task_repository=FarmingTaskRepository(db),
        event_record_repository=EventRecordRepository(db),
        task_intent_repository=TaskIntentRepository(db),
        review_request_repository=ReviewRequestRepository(db),
        operation_plan_repository=OperationPlanRepository(db),
        stage_management_service=stage_management_service,
        survey_date_recommendation_service=survey_date_service,
        weather_provider=weather_provider,
        diagnosis_client=diagnosis_client,
        context_resolver=PlantProtectionPlanContextResolver(
            code_dict_repository=CodeDictRepository(db),
            rice_variety_repository=RiceVarietyRepository(db),
        ),
    )


def get_review_request_service(
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> Generator[ReviewRequestService, None, None]:
    yield ReviewRequestService(
        review_request_repository=ReviewRequestRepository(db),
        event_record_repository=EventRecordRepository(db),
        plan_orchestrator=build_cropflow_plan_orchestrator(db, settings),
    )


def get_planting_plan_service(
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> Generator[PlantingPlanService, None, None]:
    yield PlantingPlanService(
        planting_plan_repository=PlantingPlanRepository(db),
        field_repository=FieldRepository(db),
        planting_plan_field_relation_repository=PlantingPlanFieldRelationRepository(db),
        rice_variety_repository=RiceVarietyRepository(db),
        event_record_repository=EventRecordRepository(db),
        plan_orchestrator=build_cropflow_plan_orchestrator(db, settings),
    )


def get_planting_plan_query_service(db: Session = Depends(get_db)) -> Generator[PlantingPlanQueryService, None, None]:
    yield PlantingPlanQueryService(
        planting_plan_repository=PlantingPlanRepository(db),
        calendar_item_repository=CalendarItemRepository(db),
        farming_task_repository=FarmingTaskRepository(db),
        task_intent_repository=TaskIntentRepository(db),
        review_request_repository=ReviewRequestRepository(db),
        event_record_repository=EventRecordRepository(db),
        crop_stage_state_repository=CropStageStateRepository(db),
        crop_thermal_time_state_repository=CropThermalTimeStateRepository(db),
        stage_prediction_snapshot_repository=StagePredictionSnapshotRepository(db),
    )


def get_code_dict_query_service(db: Session = Depends(get_db)) -> Generator[CodeDictQueryService, None, None]:
    yield CodeDictQueryService(code_dict_repository=CodeDictRepository(db))


def get_rice_variety_query_service(db: Session = Depends(get_db)) -> Generator[RiceVarietyQueryService, None, None]:
    yield RiceVarietyQueryService(rice_variety_repository=RiceVarietyRepository(db))


def get_farming_task_query_service(db: Session = Depends(get_db)) -> Generator[FarmingTaskQueryService, None, None]:
    yield FarmingTaskQueryService(
        farming_task_repository=FarmingTaskRepository(db),
        operation_plan_repository=OperationPlanRepository(db),
        execution_repository=ExecutionRepository(db),
        execution_record_repository=ExecutionRecordRepository(db),
        review_request_repository=ReviewRequestRepository(db),
        task_intent_repository=TaskIntentRepository(db),
        calendar_item_repository=CalendarItemRepository(db),
        event_record_repository=EventRecordRepository(db),
    )


def get_review_request_query_service(db: Session = Depends(get_db)) -> Generator[ReviewRequestQueryService, None, None]:
    yield ReviewRequestQueryService(
        review_request_repository=ReviewRequestRepository(db),
        task_intent_repository=TaskIntentRepository(db),
        farming_task_repository=FarmingTaskRepository(db),
        operation_plan_repository=OperationPlanRepository(db),
        execution_record_repository=ExecutionRecordRepository(db),
        event_record_repository=EventRecordRepository(db),
    )


def get_survey_result_service(
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> Generator[SurveyResultService, None, None]:
    weather_provider = MockWeatherProvider()
    diagnosis_client = (
        HttpWeedDiagnosisClient(settings.weed_diagnosis_base_url)
        if settings.weed_diagnosis_base_url
        else MockWeedDiagnosisClient()
    )
    yield SurveyResultService(
        farming_task_repository=FarmingTaskRepository(db),
        execution_repository=ExecutionRepository(db),
        execution_record_repository=ExecutionRecordRepository(db),
        event_record_repository=EventRecordRepository(db),
        plan_orchestrator=build_cropflow_plan_orchestrator(
            db,
            settings,
            weather_provider=weather_provider,
            diagnosis_client=diagnosis_client,
        ),
    )


def get_task_execution_service(
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> Generator[TaskExecutionService, None, None]:
    weather_provider = MockWeatherProvider()
    diagnosis_client = (
        HttpWeedDiagnosisClient(settings.weed_diagnosis_base_url)
        if settings.weed_diagnosis_base_url
        else MockWeedDiagnosisClient()
    )
    yield TaskExecutionService(
        farming_task_repository=FarmingTaskRepository(db),
        execution_repository=ExecutionRepository(db),
        execution_record_repository=ExecutionRecordRepository(db),
        event_record_repository=EventRecordRepository(db),
        plan_orchestrator=build_cropflow_plan_orchestrator(
            db,
            settings,
            weather_provider=weather_provider,
            diagnosis_client=diagnosis_client,
        ),
    )
