SURVEY_DATE_RECOMMENDATION_JOB = "SurveyDateRecommendationJob"
TASK_DUE_CHECK_JOB = "TaskDueCheckJob"
DAILY_WEATHER_CHECK_JOB = "DailyWeatherCheckJob"

EVENT_TYPE_CALENDAR_ITEM_UPDATED = "CalendarItemUpdated"
EVENT_TYPE_CALENDAR_ITEM_REFRESH_FAILED = "CalendarItemRefreshFailed"
EVENT_TYPE_PLAN_CREATED = "PlanCreated"
EVENT_TYPE_PLAN_UPDATED = "PlanUpdated"
EVENT_TYPE_PLAN_KEY_INFO_CHANGED = "PlanKeyInfoChanged"
EVENT_TYPE_WEATHER_UPDATED = "WeatherUpdated"
EVENT_TYPE_ACTUAL_STAGE_RECORDED = "ActualStageRecorded"
EVENT_TYPE_STAGE_CHANGED = "StageChanged"
EVENT_TYPE_SURVEY_RESULT_RECORDED = "SurveyResultRecorded"
EVENT_TYPE_REVIEW_REQUEST_RESOLVED = "ReviewRequestResolved"
EVENT_TYPE_EXECUTION_COMPLETED = "ExecutionCompleted"
EVENT_TYPE_EXECUTION_RECORD_UPDATED = "ExecutionRecordUpdated"
EVENT_TYPE_TASK_INTENT_CREATED = "TaskIntentCreated"
EVENT_TYPE_REVIEW_REQUEST_CREATED = "ReviewRequestCreated"
EVENT_TYPE_TASK_DUE_CHECK_TRIGGERED = "TaskDueCheckTriggered"
EVENT_TYPE_FARMING_TASK_CREATED = "FarmingTaskCreated"
EVENT_TYPE_OPERATION_PLAN_CREATED = "OperationPlanCreated"

EVENT_PROCESSING_STATUS_RECEIVED = "received"
EVENT_PROCESSING_STATUS_PROCESSING = "processing"
EVENT_PROCESSING_STATUS_PROCESSED = "processed"
EVENT_PROCESSING_STATUS_FAILED = "failed"

TASK_CATEGORY_PLANT_PROTECTION = "plant_protection"

TASK_SUBTYPE_SOIL_SEALING_WEED_CONTROL = "plant_protection.soil_sealing_weed_control"
TASK_SUBTYPE_STEM_LEAF_WEED_PRE_SURVEY = "plant_protection.stem_leaf_weed_pre_survey"
TASK_SUBTYPE_STEM_LEAF_WEED_RECONTROL_PRE_SURVEY = "plant_protection.stem_leaf_weed_recontrol_pre_survey"
TASK_SUBTYPE_STEM_LEAF_WEED_CONTROL = "plant_protection.stem_leaf_weed_control"
TASK_SUBTYPE_INJURY_MITIGATION = "plant_protection.injury_mitigation"
TASK_SUBTYPE_RICE_SAFETY_SURVEY = "plant_protection.rice_safety_survey"
TASK_SUBTYPE_CONTROL_EFFECT_SURVEY = "plant_protection.control_effect_survey"
TASK_SUBTYPE_SERVICE_EFFECT_EVALUATION = "plant_protection.service_effect_evaluation"
TASK_SUBTYPE_SERVICE_EFFECT_SURVEY = "plant_protection.service_effect_survey"
TASK_SUBTYPE_REGULAR_DISEASE_PEST_SURVEY = "plant_protection.regular_disease_pest_survey"
TASK_SUBTYPE_SUDDEN_DISEASE_PEST_SURVEY = "plant_protection.sudden_disease_pest_survey"
TASK_SUBTYPE_DISEASE_PEST_CONTROL = "plant_protection.disease_pest_control"
PEST_DISEASE_CONTROL_AVAILABLE_TARGETS = (
    "二化螟",
    "稻纵卷叶螟",
    "稻飞虱",
    "稻瘟病",
    "纹枯病",
)
PEST_DISEASE_TARGET_LABELS = {
    "ErHuaMing": "二化螟",
    "DaoZongJuanYeMing": "稻纵卷叶螟",
    "DaoFeiShi": "稻飞虱",
    "DaoWenBing": "稻瘟病",
    "WenKuBing": "纹枯病",
}

CALENDAR_STATUS_ACTIVE = "active"
CALENDAR_STATUS_GENERATED = "generated"
CALENDAR_STATUS_INVALIDATED = "invalidated"

TASK_INTENT_STATUS_PENDING = "pending"
TASK_INTENT_STATUS_NO_ACTION = "no_action"
TASK_INTENT_STATUS_CONVERTED = "converted"
TASK_INTENT_STATUS_REJECTED = "rejected"
TASK_INTENT_STATUS_PENDING_MORE_INFO = "pending_more_info"
REVIEW_REQUEST_STATUS_OPEN = "open"
REVIEW_REQUEST_STATUS_RESOLVED = "resolved"

FARMING_TASK_STATUS_PENDING = "pending"
FARMING_TASK_STATUS_COMPLETED = "completed"
EXECUTION_MODE_MANUAL = "manual"
EXECUTION_STATUS_COMPLETED = "completed"
EXECUTION_RECORD_TYPE_SURVEY_RESULT = "survey_result"
EXECUTION_RECORD_TYPE_OPERATION_RESULT = "operation_result"

OPERATION_PLAN_STATUS_ACTIVE = "active"
