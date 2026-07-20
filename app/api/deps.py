from __future__ import annotations

import asyncio
from collections.abc import AsyncGenerator, Generator

from fastapi import Depends
from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.agent_runtime.actions import ActionInvocation, CropFlowActionExecutor
from app.agent_runtime.ontology import CropFlowOntology
from app.agent_runtime.projection import CropFlowContextBuilder
from app.agent_runtime.providers import build_agent_model_provider
from app.agent_runtime.resilience import build_run_budget_policy
from app.agent_runtime.runtime import AgentRuntime
from app.db.session import get_db, get_session_factory
from app.orchestrator import PlanOrchestrator, build_plan_orchestrator
from app.repositories import (
    AgentRuntimeRepository,
    AdministrativeDivisionRepository,
    CalendarItemRepository,
    CodeDictRepository,
    CropStageDictRepository,
    CropStageStateRepository,
    CropThermalTimeStateRepository,
    EventRecordRepository,
    ExecutionRecordRepository,
    ExecutionRepository,
    FarmRepository,
    FarmFieldRelationRepository,
    FieldRepository,
    FarmingTaskRepository,
    OperationPlanRepository,
    PlantingPlanFieldRelationRepository,
    PlantingPlanRepository,
    RiceControlWindowLevel1Repository,
    RiceVarietyRepository,
    ReviewRequestRepository,
    StagePredictionSnapshotRepository,
    TaskIntentRepository,
)
from app.services import (
    AdministrativeDivisionQueryService,
    CodeDictQueryService,
    FarmFieldQueryService,
    FarmFieldService,
    FarmQueryService,
    FarmService,
    FarmingTaskQueryService,
    HttpPestDiseaseControlClient,
    HttpPestDiseaseSurveyWindowClient,
    HttpStagePredictionClient,
    HttpWeatherProvider,
    HttpWeedDiagnosisClient,
    MockPestDiseaseControlClient,
    MockPestDiseaseSurveyWindowClient,
    MockStagePredictionClient,
    MockWeatherProvider,
    MockWeedDiagnosisClient,
    PestDiseaseControlPlanningService,
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
    WeatherProvider,
)


def _require_setting(settings: Settings, value: str | None, env_name: str, capability: str) -> str:
    normalized = value.strip() if isinstance(value, str) else ""
    if normalized:
        return normalized
    if settings.require_real_integrations:
        raise RuntimeError(
            f"{capability} requires {env_name} when CROPFLOW_REQUIRE_REAL_INTEGRATIONS=true.",
        )
    return ""


def build_weed_diagnosis_client(
    settings: Settings,
) -> HttpWeedDiagnosisClient | MockWeedDiagnosisClient:
    base_url = _require_setting(
        settings,
        settings.weed_diagnosis_base_url,
        "CROPFLOW_WEED_DIAGNOSIS_BASE_URL",
        "Weed diagnosis integration",
    )
    if base_url:
        return HttpWeedDiagnosisClient(base_url)
    return MockWeedDiagnosisClient()


def build_pest_disease_survey_window_client(
    settings: Settings,
) -> HttpPestDiseaseSurveyWindowClient | MockPestDiseaseSurveyWindowClient:
    base_url = _require_setting(
        settings,
        settings.pest_disease_survey_base_url,
        "CROPFLOW_PEST_DISEASE_SURVEY_BASE_URL",
        "Pest disease survey integration",
    )
    if base_url:
        return HttpPestDiseaseSurveyWindowClient(base_url)
    return MockPestDiseaseSurveyWindowClient()


def build_pest_disease_control_client(
    settings: Settings,
) -> HttpPestDiseaseControlClient | MockPestDiseaseControlClient:
    base_url = settings.pest_disease_control_base_url or settings.pest_disease_survey_base_url
    base_url = _require_setting(
        settings,
        base_url,
        "CROPFLOW_PEST_DISEASE_CONTROL_BASE_URL",
        "Pest disease control integration",
    )
    if base_url:
        return HttpPestDiseaseControlClient(base_url)
    return MockPestDiseaseControlClient()


def build_weather_provider(
    db: Session,
    settings: Settings,
) -> WeatherProvider:
    weather_api_base_url = _require_setting(
        settings,
        settings.weather_api_base_url,
        "CROPFLOW_WEATHER_API_BASE_URL",
        "Weather integration",
    )
    weather_api_token = _require_setting(
        settings,
        settings.weather_api_token,
        "CROPFLOW_WEATHER_API_TOKEN",
        "Weather integration",
    )
    if weather_api_base_url and weather_api_token:
        return HttpWeatherProvider(
            farm_repository=FarmRepository(db),
            base_url=weather_api_base_url,
            auth_token=weather_api_token,
            alert_base_url=settings.weather_alert_api_base_url,
            alert_auth_token=settings.weather_alert_api_token,
            timeout_seconds=settings.weather_api_timeout_seconds,
            climatology_reference_years=settings.weather_climatology_reference_years,
        )
    return MockWeatherProvider()


def build_survey_date_recommendation_service(
    db: Session,
    settings: Settings,
) -> SurveyDateRecommendationService | None:
    diagnosis_client = build_weed_diagnosis_client(settings)
    pest_disease_client = build_pest_disease_survey_window_client(settings)

    return SurveyDateRecommendationService(
        planting_plan_repository=PlantingPlanRepository(db),
        farm_repository=FarmRepository(db),
        rice_variety_repository=RiceVarietyRepository(db),
        code_dict_repository=CodeDictRepository(db),
        rice_control_window_level1_repository=RiceControlWindowLevel1Repository(db),
        calendar_item_repository=CalendarItemRepository(db),
        event_record_repository=EventRecordRepository(db),
        weather_provider=build_weather_provider(db, settings),
        diagnosis_client=diagnosis_client,
        pest_disease_client=pest_disease_client,
        stage_prediction_snapshot_repository=StagePredictionSnapshotRepository(db),
        farming_task_repository=FarmingTaskRepository(db),
    )


def build_stage_management_service(
    db: Session,
    settings: Settings,
    *,
    weather_provider: WeatherProvider | None = None,
) -> StageManagementService:
    weather_provider = weather_provider or build_weather_provider(db, settings)
    stage_prediction_base_url = _require_setting(
        settings,
        settings.stage_prediction_base_url,
        "CROPFLOW_STAGE_PREDICTION_BASE_URL",
        "Stage prediction integration",
    )
    stage_prediction_client = (
        HttpStagePredictionClient(stage_prediction_base_url)
        if stage_prediction_base_url
        else MockStagePredictionClient()
    )
    return StageManagementService(
        planting_plan_repository=PlantingPlanRepository(db),
        farm_repository=FarmRepository(db),
        rice_variety_repository=RiceVarietyRepository(db),
        stage_prediction_snapshot_repository=StagePredictionSnapshotRepository(db),
        crop_stage_state_repository=CropStageStateRepository(db),
        crop_thermal_time_state_repository=CropThermalTimeStateRepository(db),
        stage_prediction_client=stage_prediction_client,
        weather_provider=weather_provider,
        crop_stage_dict_repository=CropStageDictRepository(db),
    )


def build_cropflow_plan_orchestrator(
    db: Session,
    settings: Settings,
    *,
    weather_provider: WeatherProvider | None = None,
    diagnosis_client: HttpWeedDiagnosisClient | MockWeedDiagnosisClient | None = None,
    pest_disease_client: HttpPestDiseaseSurveyWindowClient | MockPestDiseaseSurveyWindowClient | None = None,
) -> PlanOrchestrator:
    weather_provider = weather_provider or build_weather_provider(db, settings)
    diagnosis_client = diagnosis_client or build_weed_diagnosis_client(settings)
    pest_disease_client = pest_disease_client or build_pest_disease_survey_window_client(settings)
    pest_disease_control_client = build_pest_disease_control_client(settings)
    context_resolver = PlantProtectionPlanContextResolver(
        code_dict_repository=CodeDictRepository(db),
        rice_variety_repository=RiceVarietyRepository(db),
    )
    survey_date_service = SurveyDateRecommendationService(
        planting_plan_repository=PlantingPlanRepository(db),
        farm_repository=FarmRepository(db),
        rice_variety_repository=RiceVarietyRepository(db),
        code_dict_repository=CodeDictRepository(db),
        rice_control_window_level1_repository=RiceControlWindowLevel1Repository(db),
        calendar_item_repository=CalendarItemRepository(db),
        event_record_repository=EventRecordRepository(db),
        weather_provider=weather_provider,
        diagnosis_client=diagnosis_client,
        pest_disease_client=pest_disease_client,
        stage_prediction_snapshot_repository=StagePredictionSnapshotRepository(db),
        farming_task_repository=FarmingTaskRepository(db),
    )
    stage_management_service = build_stage_management_service(db, settings, weather_provider=weather_provider)
    pest_disease_control_planning_service = PestDiseaseControlPlanningService(
        planting_plan_repository=PlantingPlanRepository(db),
        farm_repository=FarmRepository(db),
        rice_control_window_level1_repository=RiceControlWindowLevel1Repository(db),
        stage_prediction_snapshot_repository=StagePredictionSnapshotRepository(db),
        calendar_item_repository=CalendarItemRepository(db),
        operation_plan_repository=OperationPlanRepository(db),
        context_resolver=context_resolver,
        weather_provider=weather_provider,
        control_client=pest_disease_control_client,
    )
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
        context_resolver=context_resolver,
        pest_disease_control_planning_service=pest_disease_control_planning_service,
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
        farm_field_relation_repository=FarmFieldRelationRepository(db),
        planting_plan_field_relation_repository=PlantingPlanFieldRelationRepository(db),
        rice_variety_repository=RiceVarietyRepository(db),
        farm_repository=FarmRepository(db),
        event_record_repository=EventRecordRepository(db),
        plan_orchestrator=build_cropflow_plan_orchestrator(db, settings),
    )


def get_planting_plan_query_service(db: Session = Depends(get_db)) -> Generator[PlantingPlanQueryService, None, None]:
    yield PlantingPlanQueryService(
        planting_plan_repository=PlantingPlanRepository(db),
        planting_plan_field_relation_repository=PlantingPlanFieldRelationRepository(db),
        calendar_item_repository=CalendarItemRepository(db),
        farming_task_repository=FarmingTaskRepository(db),
        task_intent_repository=TaskIntentRepository(db),
        review_request_repository=ReviewRequestRepository(db),
        operation_plan_repository=OperationPlanRepository(db),
        event_record_repository=EventRecordRepository(db),
        crop_stage_state_repository=CropStageStateRepository(db),
        crop_thermal_time_state_repository=CropThermalTimeStateRepository(db),
        stage_prediction_snapshot_repository=StagePredictionSnapshotRepository(db),
        farm_repository=FarmRepository(db),
    )


def get_code_dict_query_service(db: Session = Depends(get_db)) -> Generator[CodeDictQueryService, None, None]:
    yield CodeDictQueryService(code_dict_repository=CodeDictRepository(db))


def get_administrative_division_query_service(
    db: Session = Depends(get_db),
) -> Generator[AdministrativeDivisionQueryService, None, None]:
    yield AdministrativeDivisionQueryService(
        administrative_division_repository=AdministrativeDivisionRepository(db),
    )


def get_farm_service(db: Session = Depends(get_db)) -> Generator[FarmService, None, None]:
    yield FarmService(
        farm_repository=FarmRepository(db),
        field_repository=FieldRepository(db),
        farm_field_relation_repository=FarmFieldRelationRepository(db),
        planting_plan_repository=PlantingPlanRepository(db),
        planting_plan_field_relation_repository=PlantingPlanFieldRelationRepository(db),
    )


def get_farm_query_service(db: Session = Depends(get_db)) -> Generator[FarmQueryService, None, None]:
    yield FarmQueryService(farm_repository=FarmRepository(db))


def get_farm_field_service(db: Session = Depends(get_db)) -> Generator[FarmFieldService, None, None]:
    yield FarmFieldService(
        field_repository=FieldRepository(db),
        farm_repository=FarmRepository(db),
        farm_field_relation_repository=FarmFieldRelationRepository(db),
        planting_plan_field_relation_repository=PlantingPlanFieldRelationRepository(db),
    )


def get_farm_field_query_service(db: Session = Depends(get_db)) -> Generator[FarmFieldQueryService, None, None]:
    yield FarmFieldQueryService(
        field_repository=FieldRepository(db),
        farm_repository=FarmRepository(db),
        farm_field_relation_repository=FarmFieldRelationRepository(db),
    )


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
    weather_provider = build_weather_provider(db, settings)
    diagnosis_client = build_weed_diagnosis_client(settings)
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
    weather_provider = build_weather_provider(db, settings)
    diagnosis_client = build_weed_diagnosis_client(settings)
    yield TaskExecutionService(
        farming_task_repository=FarmingTaskRepository(db),
        operation_plan_repository=OperationPlanRepository(db),
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


async def get_agent_runtime(
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> AsyncGenerator[AgentRuntime, None]:
    ontology = CropFlowOntology()
    context_builder, farming_task_query_service, review_request_query_service = _build_agent_query_components(
        db,
        settings,
        ontology,
    )
    runtime_repository = context_builder.runtime_repository
    plan_orchestrator = build_cropflow_plan_orchestrator(db, settings)
    task_execution_service = TaskExecutionService(
        farming_task_repository=FarmingTaskRepository(db),
        operation_plan_repository=OperationPlanRepository(db),
        execution_repository=ExecutionRepository(db),
        execution_record_repository=ExecutionRecordRepository(db),
        event_record_repository=EventRecordRepository(db),
        plan_orchestrator=plan_orchestrator,
    )
    review_request_service = ReviewRequestService(
        review_request_repository=ReviewRequestRepository(db),
        event_record_repository=EventRecordRepository(db),
        plan_orchestrator=plan_orchestrator,
    )
    action_executor = CropFlowActionExecutor(
        ontology=ontology,
        farming_task_query_service=farming_task_query_service,
        review_request_query_service=review_request_query_service,
        task_execution_service=task_execution_service,
        review_request_service=review_request_service,
        plan_context_loader=context_builder.load_snapshot,
    )

    async def execute_parallel_query(invocation: ActionInvocation) -> dict:
        return await asyncio.to_thread(
            _execute_agent_query_in_isolated_session,
            invocation,
            settings,
            ontology,
        )

    model_provider = build_agent_model_provider(settings)
    runtime = AgentRuntime(
        repository=runtime_repository,
        context_builder=context_builder,
        action_executor=action_executor,
        model_provider=model_provider,
        max_iterations=settings.agent_max_iterations,
        parallel_query_executor=execute_parallel_query,
        max_parallel_queries=settings.agent_max_parallel_queries,
        budget_policy=build_run_budget_policy(settings),
    )
    try:
        yield runtime
    finally:
        close = getattr(model_provider, "aclose", None)
        if close is not None:
            await close()


def _build_agent_query_components(
    db: Session,
    settings: Settings,
    ontology: CropFlowOntology,
) -> tuple[CropFlowContextBuilder, FarmingTaskQueryService, ReviewRequestQueryService]:
    context_builder = CropFlowContextBuilder(
        runtime_repository=AgentRuntimeRepository(db),
        planting_plan_repository=PlantingPlanRepository(db),
        planting_plan_field_repository=PlantingPlanFieldRelationRepository(db),
        farm_repository=FarmRepository(db),
        crop_stage_repository=CropStageStateRepository(db),
        crop_thermal_repository=CropThermalTimeStateRepository(db),
        farming_task_repository=FarmingTaskRepository(db),
        review_request_repository=ReviewRequestRepository(db),
        ontology=ontology,
        default_role=settings.agent_default_role,
        task_limit=settings.agent_context_task_limit,
        review_limit=settings.agent_context_review_limit,
    )
    farming_task_query_service = FarmingTaskQueryService(
        farming_task_repository=FarmingTaskRepository(db),
        operation_plan_repository=OperationPlanRepository(db),
        execution_repository=ExecutionRepository(db),
        execution_record_repository=ExecutionRecordRepository(db),
        review_request_repository=ReviewRequestRepository(db),
        task_intent_repository=TaskIntentRepository(db),
        calendar_item_repository=CalendarItemRepository(db),
        event_record_repository=EventRecordRepository(db),
    )
    review_request_query_service = ReviewRequestQueryService(
        review_request_repository=ReviewRequestRepository(db),
        task_intent_repository=TaskIntentRepository(db),
        farming_task_repository=FarmingTaskRepository(db),
        operation_plan_repository=OperationPlanRepository(db),
        execution_record_repository=ExecutionRecordRepository(db),
        event_record_repository=EventRecordRepository(db),
    )
    return context_builder, farming_task_query_service, review_request_query_service


def _execute_agent_query_in_isolated_session(
    invocation: ActionInvocation,
    settings: Settings,
    ontology: CropFlowOntology,
) -> dict:
    with get_session_factory()() as query_db:
        context_builder, farming_task_query_service, review_request_query_service = _build_agent_query_components(
            query_db,
            settings,
            ontology,
        )
        query_executor = CropFlowActionExecutor(
            ontology=ontology,
            farming_task_query_service=farming_task_query_service,
            review_request_query_service=review_request_query_service,
            task_execution_service=None,
            review_request_service=None,
            plan_context_loader=context_builder.load_snapshot,
        )
        return query_executor.execute(invocation)
