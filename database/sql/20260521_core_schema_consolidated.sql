-- CropFlow consolidated core schema DDL
-- Scope:
--   - farm / field / variety / planting-plan base tables
--   - stage, calendar, task, execution, feedback, review, notification, event tables
--   - user/account and audit fields
--   - runtime traceability fields: parent_task_id / source_execution_id / source_execution_record_id
-- Excludes:
--   - inventory tables
--   - device callback / command tables
--
-- This file is the current authoritative design-time SQL draft.
-- It consolidates:
--   - 20260518_weed_protection_closed_loop.sql
--   - 20260518_user_audit_patch.sql
-- The older files are retained only as historical references and should not
-- receive new schema changes.
--
-- This file targets PostgreSQL.

CREATE OR REPLACE FUNCTION cf_set_updated_at()
RETURNS trigger
LANGUAGE plpgsql
AS $$
BEGIN
  NEW.updated_at = CURRENT_TIMESTAMP;
  RETURN NEW;
END;
$$;

CREATE TABLE IF NOT EXISTS cf_farm (
  id bigserial PRIMARY KEY,
  farm_name varchar(100) NOT NULL,
  external_farm_id varchar(50) UNIQUE,
  province varchar(100),
  city varchar(100),
  district_county varchar(100),
  adcode varchar(20),
  boundary_wkt text,
  centroid_lat numeric(9, 6),
  centroid_lon numeric(9, 6),
  created_by_type varchar(20) NOT NULL DEFAULT 'system',
  created_by_id varchar(100),
  created_at timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS cf_field (
  id bigserial PRIMARY KEY,
  field_name varchar(100) NOT NULL,
  boundary_wkt text,
  centroid_lat numeric(9, 6),
  centroid_lon numeric(9, 6),
  area_ha numeric(10, 4),
  created_by_type varchar(20) NOT NULL DEFAULT 'system',
  created_by_id varchar(100),
  created_at timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS cf_farm_field_relation (
  id bigserial PRIMARY KEY,
  farm_id bigint NOT NULL REFERENCES cf_farm(id) ON DELETE CASCADE,
  field_id bigint NOT NULL REFERENCES cf_field(id) ON DELETE CASCADE,
  created_by_type varchar(20) NOT NULL DEFAULT 'system',
  created_by_id varchar(100),
  created_at timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
  CONSTRAINT uk_cf_farm_field_relation UNIQUE (farm_id, field_id)
);

CREATE TABLE IF NOT EXISTS cf_code_dict (
  id bigserial PRIMARY KEY,
  code int8 NOT NULL,
  code_name varchar(100) NOT NULL,
  category varchar(50) NOT NULL,
  is_active boolean NOT NULL DEFAULT true,
  created_by_type varchar(20) NOT NULL DEFAULT 'system',
  created_by_id varchar(100),
  created_at timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
  CONSTRAINT uk_cf_code_dict_code UNIQUE (code),
  CONSTRAINT uk_cf_code_dict_category_name UNIQUE (category, code_name)
);

CREATE TABLE IF NOT EXISTS cf_user (
  id varchar(100) PRIMARY KEY,
  user_code varchar(100) UNIQUE,
  username varchar(100) NOT NULL,
  display_name varchar(100),
  mobile varchar(50),
  email varchar(255),
  status varchar(20) NOT NULL DEFAULT 'active',
  metadata jsonb NOT NULL DEFAULT '{}'::jsonb,
  created_by_type varchar(20) NOT NULL DEFAULT 'system',
  created_by_id varchar(100),
  created_at timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS cf_user_account (
  id bigserial PRIMARY KEY,
  user_id varchar(100) NOT NULL REFERENCES cf_user(id) ON DELETE CASCADE,
  account_type varchar(50) NOT NULL DEFAULT 'password',
  login_name varchar(100) NOT NULL,
  password_hash varchar(255),
  status varchar(20) NOT NULL DEFAULT 'active',
  last_login_at timestamp,
  last_login_ip varchar(64),
  password_changed_at timestamp,
  failed_login_count int4 NOT NULL DEFAULT 0,
  locked_until timestamp,
  metadata jsonb NOT NULL DEFAULT '{}'::jsonb,
  created_by_type varchar(20) NOT NULL DEFAULT 'system',
  created_by_id varchar(100),
  created_at timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
  CONSTRAINT uk_cf_user_account_user_type UNIQUE (user_id, account_type),
  CONSTRAINT uk_cf_user_account_login_name UNIQUE (login_name)
);

CREATE TABLE IF NOT EXISTS cf_rice_variety (
  id bigserial PRIMARY KEY,
  name varchar(255) NOT NULL,
  approve_year int4,
  approve_no varchar(64),
  approve_region varchar(255),
  suitable_region varchar(255),
  culti_type_code int8 REFERENCES cf_code_dict(code) ON DELETE RESTRICT,
  sub_type_code int8 REFERENCES cf_code_dict(code) ON DELETE RESTRICT,
  maturity_code int8 REFERENCES cf_code_dict(code) ON DELETE RESTRICT,
  control_variety varchar(255),
  growth_days numeric(6, 2),
  compare_days numeric(6, 2),
  rice_code varchar(64),
  created_by_type varchar(20) NOT NULL DEFAULT 'system',
  created_by_id varchar(100),
  created_at timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS cf_planting_plan (
  id bigserial PRIMARY KEY,
  plan_code varchar(100) NOT NULL,
  plan_name varchar(255) NOT NULL,
  farm_id bigint NOT NULL REFERENCES cf_farm(id) ON DELETE RESTRICT,
  year int4,
  culti_type_code int8 NOT NULL REFERENCES cf_code_dict(code) ON DELETE RESTRICT,
  planting_method_code int8 NOT NULL REFERENCES cf_code_dict(code) ON DELETE RESTRICT,
  crop_name varchar(50) NOT NULL,
  variety_id bigint NOT NULL REFERENCES cf_rice_variety(id) ON DELETE RESTRICT,
  variety_name varchar(255) NOT NULL,
  sowing_date date NOT NULL,
  transplant_date date,
  harvest_date date,
  transplant_leaf_age numeric(6, 2),
  previous_harvest_date date,
  ratoon_first_season_harvest_date date,
  expected_harvest_date date,
  status varchar(50) NOT NULL DEFAULT 'draft',
  task_generation_window_days int4 NOT NULL DEFAULT 14,
  metadata jsonb NOT NULL DEFAULT '{}'::jsonb,
  created_by_type varchar(20) NOT NULL DEFAULT 'system',
  created_by_id varchar(100),
  created_at timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
  CONSTRAINT uk_cf_planting_plan_plan_code UNIQUE (plan_code)
);

CREATE TABLE IF NOT EXISTS cf_planting_plan_field_relation (
  id bigserial PRIMARY KEY,
  planting_plan_id bigint NOT NULL REFERENCES cf_planting_plan(id) ON DELETE CASCADE,
  field_id bigint NOT NULL REFERENCES cf_field(id) ON DELETE RESTRICT,
  created_by_type varchar(20) NOT NULL DEFAULT 'system',
  created_by_id varchar(100),
  created_at timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
  CONSTRAINT uk_cf_plan_field_relation UNIQUE (planting_plan_id, field_id)
);

CREATE TABLE IF NOT EXISTS cf_event_record (
  id bigserial PRIMARY KEY,
  planting_plan_id bigint REFERENCES cf_planting_plan(id) ON DELETE SET NULL,
  event_type varchar(100) NOT NULL,
  event_category varchar(50) NOT NULL,
  event_source varchar(50) NOT NULL,
  source_system varchar(100),
  source_record_id varchar(100),
  payload jsonb NOT NULL DEFAULT '{}'::jsonb,
  occurred_at timestamp NOT NULL,
  received_at timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
  processed_at timestamp,
  processing_status varchar(50) NOT NULL DEFAULT 'received',
  idempotency_key varchar(255) NOT NULL,
  error_message text,
  created_by_type varchar(20) NOT NULL DEFAULT 'system',
  created_by_id varchar(100),
  created_at timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
  CONSTRAINT uk_cf_event_record_idempotency_key UNIQUE (idempotency_key)
);

CREATE TABLE IF NOT EXISTS cf_stage_prediction_snapshot (
  id bigserial PRIMARY KEY,
  planting_plan_id bigint NOT NULL REFERENCES cf_planting_plan(id) ON DELETE CASCADE,
  prediction_version int4 NOT NULL,
  prediction_source varchar(50) NOT NULL,
  algorithm_code varchar(100) NOT NULL,
  algorithm_version varchar(100),
  generated_at timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
  input_payload jsonb NOT NULL DEFAULT '{}'::jsonb,
  stage_timeline jsonb NOT NULL DEFAULT '{}'::jsonb,
  thermal_thresholds jsonb NOT NULL DEFAULT '{}'::jsonb,
  source_event_id bigint REFERENCES cf_event_record(id) ON DELETE SET NULL,
  created_by_type varchar(20) NOT NULL DEFAULT 'system',
  created_by_id varchar(100),
  created_at timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS cf_crop_stage_state (
  id bigserial PRIMARY KEY,
  planting_plan_id bigint NOT NULL REFERENCES cf_planting_plan(id) ON DELETE CASCADE,
  current_stage_code varchar(50) NOT NULL,
  current_stage_name varchar(100) NOT NULL,
  stage_source varchar(50) NOT NULL,
  effective_date date NOT NULL,
  source_snapshot_id bigint REFERENCES cf_stage_prediction_snapshot(id) ON DELETE SET NULL,
  last_updated_at timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
  version int4 NOT NULL DEFAULT 1,
  created_by_type varchar(20) NOT NULL DEFAULT 'system',
  created_by_id varchar(100),
  created_at timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
  CONSTRAINT uk_cf_crop_stage_state_plan UNIQUE (planting_plan_id)
);

CREATE TABLE IF NOT EXISTS cf_crop_thermal_time_state (
  id bigserial PRIMARY KEY,
  planting_plan_id bigint NOT NULL REFERENCES cf_planting_plan(id) ON DELETE CASCADE,
  accumulated_thermal_time numeric(10, 2) NOT NULL DEFAULT 0,
  thermal_time_unit varchar(20) NOT NULL DEFAULT 'degree_day',
  base_temperature numeric(6, 2),
  start_date date,
  last_calculated_date date,
  threshold_snapshot_id bigint REFERENCES cf_stage_prediction_snapshot(id) ON DELETE SET NULL,
  data_version varchar(100),
  created_by_type varchar(20) NOT NULL DEFAULT 'system',
  created_by_id varchar(100),
  created_at timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
  CONSTRAINT uk_cf_crop_thermal_time_state_plan UNIQUE (planting_plan_id)
);

CREATE TABLE IF NOT EXISTS cf_calendar_item (
  id bigserial PRIMARY KEY,
  planting_plan_id bigint NOT NULL REFERENCES cf_planting_plan(id) ON DELETE CASCADE,
  stage_code varchar(50),
  task_category varchar(50) NOT NULL,
  task_subtype varchar(100) NOT NULL,
  title varchar(255) NOT NULL,
  description text,
  suggested_start_date date NOT NULL,
  suggested_end_date date NOT NULL,
  status varchar(50) NOT NULL DEFAULT 'active',
  calendar_version int4 NOT NULL DEFAULT 1,
  source_snapshot_id bigint REFERENCES cf_stage_prediction_snapshot(id) ON DELETE SET NULL,
  parent_task_id bigint,
  source_execution_id bigint,
  source_execution_record_id bigint,
  generation_condition jsonb NOT NULL DEFAULT '{}'::jsonb,
  generated_task_id bigint,
  last_generation_checked_at timestamp,
  invalidated_reason text,
  idempotency_key varchar(255) NOT NULL,
  created_by_type varchar(20) NOT NULL DEFAULT 'system',
  created_by_id varchar(100),
  created_at timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
  CONSTRAINT uk_cf_calendar_item_idempotency_key UNIQUE (idempotency_key)
);

CREATE TABLE IF NOT EXISTS cf_task_intent (
  id bigserial PRIMARY KEY,
  planting_plan_id bigint NOT NULL REFERENCES cf_planting_plan(id) ON DELETE CASCADE,
  task_category varchar(50) NOT NULL,
  task_subtype varchar(100) NOT NULL,
  priority varchar(20) NOT NULL DEFAULT 'normal',
  status varchar(50) NOT NULL DEFAULT 'pending',
  trigger_type varchar(50) NOT NULL,
  trigger_summary text,
  rule_result jsonb NOT NULL DEFAULT '{}'::jsonb,
  suggested_action text,
  need_more_info_fields jsonb NOT NULL DEFAULT '{}'::jsonb,
  no_action_reason text,
  parent_task_id bigint,
  source_execution_id bigint,
  source_execution_record_id bigint,
  converted_task_id bigint,
  source_event_id bigint REFERENCES cf_event_record(id) ON DELETE SET NULL,
  idempotency_key varchar(255) NOT NULL,
  created_by_type varchar(20) NOT NULL DEFAULT 'system',
  created_by_id varchar(100),
  created_at timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
  CONSTRAINT uk_cf_task_intent_idempotency_key UNIQUE (idempotency_key)
);

CREATE TABLE IF NOT EXISTS cf_review_request (
  id bigserial PRIMARY KEY,
  planting_plan_id bigint NOT NULL REFERENCES cf_planting_plan(id) ON DELETE CASCADE,
  review_type varchar(50) NOT NULL,
  status varchar(50) NOT NULL DEFAULT 'open',
  priority varchar(20) NOT NULL DEFAULT 'normal',
  assigned_user_id varchar(100) REFERENCES cf_user(id) ON DELETE SET NULL,
  source_entity_type varchar(100) NOT NULL,
  source_entity_id bigint NOT NULL,
  title varchar(255) NOT NULL,
  description text,
  decision varchar(50),
  decision_payload jsonb NOT NULL DEFAULT '{}'::jsonb,
  resolved_by varchar(100) REFERENCES cf_user(id) ON DELETE SET NULL,
  resolved_at timestamp,
  idempotency_key varchar(255) NOT NULL,
  created_by_type varchar(20) NOT NULL DEFAULT 'system',
  created_by_id varchar(100),
  created_at timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
  CONSTRAINT uk_cf_review_request_idempotency_key UNIQUE (idempotency_key)
);

COMMENT ON COLUMN cf_review_request.decision_payload IS
  'Structured review payload. Suggested keys: contextRefs, adjustments, reason.';

COMMENT ON COLUMN cf_calendar_item.parent_task_id IS
  'Upstream business task being continued or revisited by this calendar item, not the direct trigger record owner.';

COMMENT ON COLUMN cf_calendar_item.source_execution_id IS
  'Execution that contains the direct runtime result used to create this calendar item.';

COMMENT ON COLUMN cf_calendar_item.source_execution_record_id IS
  'Direct execution or survey record that triggered this calendar item.';

COMMENT ON COLUMN cf_calendar_item.generation_condition IS
  'Structured calendar generation context such as stage window, algorithm branch, and prerequisite checks.';

COMMENT ON COLUMN cf_task_intent.parent_task_id IS
  'Upstream business task being extended, remediated, or reviewed by this task intent.';

COMMENT ON COLUMN cf_task_intent.source_execution_id IS
  'Execution that contains the direct runtime result used to create this task intent.';

COMMENT ON COLUMN cf_task_intent.source_execution_record_id IS
  'Direct execution or survey record that triggered this task intent.';

COMMENT ON COLUMN cf_task_intent.rule_result IS
  'Structured runtime decision result. Suggested keys include algorithmCode, branchType, proposedTask, proposedPlan, and inputRefs.';

COMMENT ON COLUMN cf_farming_task.parent_task_id IS
  'Upstream business task being continued or remediated by this formal farming task.';

COMMENT ON COLUMN cf_farming_task.source_execution_id IS
  'Execution that contains the direct runtime result or approved review basis used to generate this farming task.';

COMMENT ON COLUMN cf_farming_task.source_execution_record_id IS
  'Direct execution or survey record that triggered this farming task generation.';

COMMENT ON COLUMN cf_execution_record.result_payload IS
  'Structured execution or survey result payload. May become the direct input for follow-up orchestration.';

CREATE TABLE IF NOT EXISTS cf_farming_task (
  id bigserial PRIMARY KEY,
  planting_plan_id bigint NOT NULL REFERENCES cf_planting_plan(id) ON DELETE CASCADE,
  calendar_item_id bigint REFERENCES cf_calendar_item(id) ON DELETE SET NULL,
  task_intent_id bigint REFERENCES cf_task_intent(id) ON DELETE SET NULL,
  review_request_id bigint REFERENCES cf_review_request(id) ON DELETE SET NULL,
  task_category varchar(50) NOT NULL,
  task_subtype varchar(100) NOT NULL,
  title varchar(255) NOT NULL,
  description text,
  target_stage_code varchar(50),
  planned_start_at timestamp,
  planned_end_at timestamp,
  priority varchar(20) NOT NULL DEFAULT 'normal',
  status varchar(50) NOT NULL DEFAULT 'pending',
  execution_mode varchar(50) NOT NULL DEFAULT 'manual',
  generation_reason text,
  parent_task_id bigint,
  source_execution_id bigint,
  source_execution_record_id bigint,
  idempotency_key varchar(255) NOT NULL,
  created_by_type varchar(20) NOT NULL DEFAULT 'system',
  created_by_id varchar(100),
  created_at timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
  CONSTRAINT uk_cf_farming_task_idempotency_key UNIQUE (idempotency_key)
);

DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1
    FROM pg_constraint
    WHERE conname = 'fk_cf_calendar_item_generated_task'
  ) THEN
    ALTER TABLE cf_calendar_item
      ADD CONSTRAINT fk_cf_calendar_item_generated_task
      FOREIGN KEY (generated_task_id) REFERENCES cf_farming_task(id) ON DELETE SET NULL;
  END IF;
END;
$$;

DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1
    FROM pg_constraint
    WHERE conname = 'fk_cf_task_intent_converted_task'
  ) THEN
    ALTER TABLE cf_task_intent
      ADD CONSTRAINT fk_cf_task_intent_converted_task
      FOREIGN KEY (converted_task_id) REFERENCES cf_farming_task(id) ON DELETE SET NULL;
  END IF;
END;
$$;

DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1
    FROM pg_constraint
    WHERE conname = 'fk_cf_calendar_item_parent_task'
  ) THEN
    ALTER TABLE cf_calendar_item
      ADD CONSTRAINT fk_cf_calendar_item_parent_task
      FOREIGN KEY (parent_task_id) REFERENCES cf_farming_task(id) ON DELETE SET NULL;
  END IF;
END;
$$;

DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1
    FROM pg_constraint
    WHERE conname = 'fk_cf_task_intent_parent_task'
  ) THEN
    ALTER TABLE cf_task_intent
      ADD CONSTRAINT fk_cf_task_intent_parent_task
      FOREIGN KEY (parent_task_id) REFERENCES cf_farming_task(id) ON DELETE SET NULL;
  END IF;
END;
$$;

DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1
    FROM pg_constraint
    WHERE conname = 'fk_cf_farming_task_parent_task'
  ) THEN
    ALTER TABLE cf_farming_task
      ADD CONSTRAINT fk_cf_farming_task_parent_task
      FOREIGN KEY (parent_task_id) REFERENCES cf_farming_task(id) ON DELETE SET NULL;
  END IF;
END;
$$;

CREATE TABLE IF NOT EXISTS cf_operation_plan (
  id bigserial PRIMARY KEY,
  planting_plan_id bigint NOT NULL REFERENCES cf_planting_plan(id) ON DELETE CASCADE,
  farming_task_id bigint NOT NULL REFERENCES cf_farming_task(id) ON DELETE CASCADE,
  plan_type varchar(50) NOT NULL,
  status varchar(50) NOT NULL DEFAULT 'draft',
  version int4 NOT NULL DEFAULT 1,
  algorithm_code varchar(100),
  algorithm_version varchar(100),
  operation_area jsonb NOT NULL DEFAULT '{}'::jsonb,
  operation_window_start timestamp,
  operation_window_end timestamp,
  execution_mode varchar(50) NOT NULL DEFAULT 'manual',
  parameters jsonb NOT NULL DEFAULT '{}'::jsonb,
  prescription_map jsonb NOT NULL DEFAULT '{}'::jsonb,
  acceptance_criteria jsonb NOT NULL DEFAULT '{}'::jsonb,
  basis text,
  source_event_id bigint REFERENCES cf_event_record(id) ON DELETE SET NULL,
  idempotency_key varchar(255) NOT NULL,
  created_by_type varchar(20) NOT NULL DEFAULT 'system',
  created_by_id varchar(100),
  created_at timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
  CONSTRAINT uk_cf_operation_plan_idempotency_key UNIQUE (idempotency_key)
);

CREATE TABLE IF NOT EXISTS cf_execution (
  id bigserial PRIMARY KEY,
  planting_plan_id bigint NOT NULL REFERENCES cf_planting_plan(id) ON DELETE CASCADE,
  farming_task_id bigint NOT NULL REFERENCES cf_farming_task(id) ON DELETE CASCADE,
  operation_plan_id bigint REFERENCES cf_operation_plan(id) ON DELETE SET NULL,
  execution_mode varchar(50) NOT NULL DEFAULT 'manual',
  status varchar(50) NOT NULL DEFAULT 'pending',
  assigned_to_type varchar(50),
  assigned_to_id varchar(100),
  external_system_code varchar(100),
  external_execution_id varchar(100),
  started_at timestamp,
  completed_at timestamp,
  failure_reason text,
  created_by_type varchar(20) NOT NULL DEFAULT 'system',
  created_by_id varchar(100),
  created_at timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS cf_execution_record (
  id bigserial PRIMARY KEY,
  planting_plan_id bigint NOT NULL REFERENCES cf_planting_plan(id) ON DELETE CASCADE,
  execution_id bigint NOT NULL REFERENCES cf_execution(id) ON DELETE CASCADE,
  record_type varchar(50) NOT NULL,
  record_time timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
  actual_start_at timestamp,
  actual_end_at timestamp,
  actual_area numeric(12, 4),
  actual_amount numeric(12, 4),
  amount_unit varchar(50),
  result_payload jsonb NOT NULL DEFAULT '{}'::jsonb,
  attachments jsonb NOT NULL DEFAULT '[]'::jsonb,
  created_by_type varchar(20) NOT NULL DEFAULT 'system',
  created_by_id varchar(100),
  created_at timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP
);

DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1
    FROM pg_constraint
    WHERE conname = 'fk_cf_calendar_item_source_execution'
  ) THEN
    ALTER TABLE cf_calendar_item
      ADD CONSTRAINT fk_cf_calendar_item_source_execution
      FOREIGN KEY (source_execution_id) REFERENCES cf_execution(id) ON DELETE SET NULL;
  END IF;
END;
$$;

DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1
    FROM pg_constraint
    WHERE conname = 'fk_cf_calendar_item_source_execution_record'
  ) THEN
    ALTER TABLE cf_calendar_item
      ADD CONSTRAINT fk_cf_calendar_item_source_execution_record
      FOREIGN KEY (source_execution_record_id) REFERENCES cf_execution_record(id) ON DELETE SET NULL;
  END IF;
END;
$$;

DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1
    FROM pg_constraint
    WHERE conname = 'fk_cf_task_intent_source_execution'
  ) THEN
    ALTER TABLE cf_task_intent
      ADD CONSTRAINT fk_cf_task_intent_source_execution
      FOREIGN KEY (source_execution_id) REFERENCES cf_execution(id) ON DELETE SET NULL;
  END IF;
END;
$$;

DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1
    FROM pg_constraint
    WHERE conname = 'fk_cf_task_intent_source_execution_record'
  ) THEN
    ALTER TABLE cf_task_intent
      ADD CONSTRAINT fk_cf_task_intent_source_execution_record
      FOREIGN KEY (source_execution_record_id) REFERENCES cf_execution_record(id) ON DELETE SET NULL;
  END IF;
END;
$$;

DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1
    FROM pg_constraint
    WHERE conname = 'fk_cf_farming_task_source_execution'
  ) THEN
    ALTER TABLE cf_farming_task
      ADD CONSTRAINT fk_cf_farming_task_source_execution
      FOREIGN KEY (source_execution_id) REFERENCES cf_execution(id) ON DELETE SET NULL;
  END IF;
END;
$$;

DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1
    FROM pg_constraint
    WHERE conname = 'fk_cf_farming_task_source_execution_record'
  ) THEN
    ALTER TABLE cf_farming_task
      ADD CONSTRAINT fk_cf_farming_task_source_execution_record
      FOREIGN KEY (source_execution_record_id) REFERENCES cf_execution_record(id) ON DELETE SET NULL;
  END IF;
END;
$$;

CREATE TABLE IF NOT EXISTS cf_evaluation (
  id bigserial PRIMARY KEY,
  planting_plan_id bigint NOT NULL REFERENCES cf_planting_plan(id) ON DELETE CASCADE,
  execution_id bigint NOT NULL REFERENCES cf_execution(id) ON DELETE CASCADE,
  operation_plan_id bigint REFERENCES cf_operation_plan(id) ON DELETE SET NULL,
  source_type varchar(50) NOT NULL DEFAULT 'system',
  source_id varchar(100),
  result varchar(50) NOT NULL DEFAULT 'unknown',
  score numeric(6, 2),
  metrics jsonb NOT NULL DEFAULT '{}'::jsonb,
  conclusion text,
  evaluated_at timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
  created_by_type varchar(20) NOT NULL DEFAULT 'system',
  created_by_id varchar(100),
  created_at timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS cf_feedback (
  id bigserial PRIMARY KEY,
  planting_plan_id bigint NOT NULL REFERENCES cf_planting_plan(id) ON DELETE CASCADE,
  evaluation_id bigint NOT NULL REFERENCES cf_evaluation(id) ON DELETE CASCADE,
  execution_id bigint NOT NULL REFERENCES cf_execution(id) ON DELETE CASCADE,
  source_type varchar(50) NOT NULL DEFAULT 'system',
  source_id varchar(100),
  feedback_type varchar(50) NOT NULL,
  severity varchar(20) NOT NULL DEFAULT 'info',
  status varchar(50) NOT NULL DEFAULT 'open',
  summary text NOT NULL,
  details jsonb NOT NULL DEFAULT '{}'::jsonb,
  requires_review boolean NOT NULL DEFAULT false,
  feedback_version int4 NOT NULL DEFAULT 1,
  idempotency_key varchar(255) NOT NULL,
  created_by_type varchar(20) NOT NULL DEFAULT 'system',
  created_by_id varchar(100),
  created_at timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
  CONSTRAINT uk_cf_feedback_idempotency_key UNIQUE (idempotency_key)
);

CREATE TABLE IF NOT EXISTS cf_system_notification (
  id bigserial PRIMARY KEY,
  planting_plan_id bigint NOT NULL REFERENCES cf_planting_plan(id) ON DELETE CASCADE,
  notification_type varchar(50) NOT NULL,
  target_user_id varchar(100) REFERENCES cf_user(id) ON DELETE SET NULL,
  title varchar(255) NOT NULL,
  content text NOT NULL,
  status varchar(50) NOT NULL DEFAULT 'unread',
  source_entity_type varchar(100),
  source_entity_id bigint,
  created_by_type varchar(20) NOT NULL DEFAULT 'system',
  created_by_id varchar(100),
  created_at timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
  read_at timestamp,
  updated_at timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP
);

COMMENT ON TABLE cf_farm IS
  'Farm master data.';

COMMENT ON TABLE cf_field IS
  'Field master data.';

COMMENT ON TABLE cf_farm_field_relation IS
  'Relation between farms and fields.';

COMMENT ON TABLE cf_code_dict IS
  'Shared code dictionary table used by plan and variety reference fields.';

COMMENT ON TABLE cf_user IS
  'Minimal user table used by review and notification modules.';

COMMENT ON TABLE cf_user_account IS
  'User account and authentication profile table.';

COMMENT ON TABLE cf_rice_variety IS
  'Rice variety reference table.';

COMMENT ON TABLE cf_planting_plan IS
  'Top-level planting plan aggregate root for MVP orchestration.';

COMMENT ON TABLE cf_planting_plan_field_relation IS
  'Relation between a planting plan and its fields.';

COMMENT ON TABLE cf_event_record IS
  'Normalized inbound and internal event log consumed by orchestrators.';

COMMENT ON TABLE cf_stage_prediction_snapshot IS
  'Stage prediction snapshot emitted by stage prediction algorithms.';

COMMENT ON TABLE cf_crop_stage_state IS
  'Current crop stage state for a planting plan.';

COMMENT ON TABLE cf_crop_thermal_time_state IS
  'Accumulated thermal time state for a planting plan.';

COMMENT ON TABLE cf_calendar_item IS
  'Preparatory calendar item used for future survey, evaluation, or stage-driven task generation.';

COMMENT ON TABLE cf_task_intent IS
  'Runtime task suggestion awaiting review or later conversion into a formal farming task.';

COMMENT ON TABLE cf_review_request IS
  'Human review work item created from task intents, feedback, or runtime exceptions.';

COMMENT ON TABLE cf_farming_task IS
  'Formal executable farming task and entry object for the execution module.';

COMMENT ON TABLE cf_operation_plan IS
  'Concrete operation plan or prescription attached to a formal farming task.';

COMMENT ON TABLE cf_execution IS
  'Execution instance of a farming task.';

COMMENT ON TABLE cf_execution_record IS
  'Execution or survey result record captured during an execution.';

COMMENT ON TABLE cf_evaluation IS
  'Evaluation result derived from execution outcome.';

COMMENT ON TABLE cf_feedback IS
  'Operational feedback derived from evaluation or runtime signals.';

COMMENT ON TABLE cf_system_notification IS
  'User-facing notification generated by review, task, or execution flows.';

COMMENT ON COLUMN cf_user.status IS
  'Suggested values: active, disabled.';

COMMENT ON COLUMN cf_user_account.account_type IS
  'Suggested values: password, sso, external.';

COMMENT ON COLUMN cf_user_account.status IS
  'Suggested values: active, locked, disabled.';

COMMENT ON COLUMN cf_planting_plan.status IS
  'Suggested values: draft, active, completed, cancelled.';

COMMENT ON COLUMN cf_event_record.event_category IS
  'Suggested values: input, domain.';

COMMENT ON COLUMN cf_event_record.event_source IS
  'Suggested values: user, job, external, module.';

COMMENT ON COLUMN cf_event_record.payload IS
  'Normalized event payload consumed by orchestrators and handlers.';

COMMENT ON COLUMN cf_event_record.processing_status IS
  'Suggested values: received, processing, processed, failed, ignored.';

COMMENT ON COLUMN cf_stage_prediction_snapshot.input_payload IS
  'Input snapshot sent to the stage prediction algorithm.';

COMMENT ON COLUMN cf_stage_prediction_snapshot.stage_timeline IS
  'Predicted stage timeline returned by the stage prediction algorithm.';

COMMENT ON COLUMN cf_stage_prediction_snapshot.thermal_thresholds IS
  'Thermal threshold snapshot used by stage prediction and later audits.';

COMMENT ON COLUMN cf_crop_stage_state.stage_source IS
  'Suggested values: prediction, manual.';

COMMENT ON COLUMN cf_calendar_item.status IS
  'Suggested values: active, generated, invalidated.';

COMMENT ON COLUMN cf_task_intent.priority IS
  'Suggested values: low, normal, high, urgent.';

COMMENT ON COLUMN cf_task_intent.status IS
  'Suggested values: pending, in_review, converted, rejected, no_action.';

COMMENT ON COLUMN cf_task_intent.trigger_type IS
  'Suggested values: field_condition, sensor, device, feedback, review, manual, survey_result.';

COMMENT ON COLUMN cf_task_intent.need_more_info_fields IS
  'Structured list of missing fields or evidences required before a decision can be made.';

COMMENT ON COLUMN cf_review_request.review_type IS
  'Suggested values: task_intent, feedback, execution_exception, plan_change, stage_change.';

COMMENT ON COLUMN cf_review_request.status IS
  'Suggested values: open, in_progress, resolved, cancelled.';

COMMENT ON COLUMN cf_review_request.priority IS
  'Suggested values: low, normal, high, urgent.';

COMMENT ON COLUMN cf_review_request.decision IS
  'Suggested values: approve, reject, need_more_info, no_action, adjust.';

COMMENT ON COLUMN cf_farming_task.priority IS
  'Suggested values: low, normal, high, urgent.';

COMMENT ON COLUMN cf_farming_task.status IS
  'Suggested values: pending, ready, running, completed, failed, cancelled.';

COMMENT ON COLUMN cf_farming_task.execution_mode IS
  'Suggested values: manual, device, drone, third_party.';

COMMENT ON COLUMN cf_operation_plan.plan_type IS
  'Suggested values align with task categories such as irrigation, fertilization, plant_protection.';

COMMENT ON COLUMN cf_operation_plan.status IS
  'Suggested values: draft, active, superseded, invalidated.';

COMMENT ON COLUMN cf_operation_plan.execution_mode IS
  'Suggested values: manual, device, drone, third_party.';

COMMENT ON COLUMN cf_operation_plan.parameters IS
  'Structured operation parameters such as dosage, water volume, prescriptions, and control targets.';

COMMENT ON COLUMN cf_operation_plan.prescription_map IS
  'Structured prescription map or area-based differentiated parameters.';

COMMENT ON COLUMN cf_operation_plan.acceptance_criteria IS
  'Structured acceptance and verification criteria for execution outcome.';

COMMENT ON COLUMN cf_execution.execution_mode IS
  'Suggested values: manual, device, drone, third_party.';

COMMENT ON COLUMN cf_execution.status IS
  'Suggested values: pending, running, completed, failed, cancelled.';

COMMENT ON COLUMN cf_execution_record.record_type IS
  'Suggested values: status_update, result, manual_upload, device_callback, survey_result.';

COMMENT ON COLUMN cf_execution_record.attachments IS
  'Structured attachment metadata such as images, files, or trajectories.';

COMMENT ON COLUMN cf_evaluation.source_type IS
  'Suggested values: system, algorithm, user, external.';

COMMENT ON COLUMN cf_evaluation.result IS
  'Suggested values: pass, warning, fail, unknown.';

COMMENT ON COLUMN cf_evaluation.metrics IS
  'Structured evaluation metrics and indicator values.';

COMMENT ON COLUMN cf_feedback.source_type IS
  'Suggested values: system, algorithm, user, external.';

COMMENT ON COLUMN cf_feedback.feedback_type IS
  'Suggested values: completed, incomplete, abnormal, remedial_needed, adjust_future.';

COMMENT ON COLUMN cf_feedback.severity IS
  'Suggested values: info, warning, critical.';

COMMENT ON COLUMN cf_feedback.status IS
  'Suggested values: open, processing, closed.';

COMMENT ON COLUMN cf_feedback.details IS
  'Structured feedback details, including runtime anomalies or follow-up recommendations.';

COMMENT ON COLUMN cf_system_notification.notification_type IS
  'Suggested values: review_required, task_due, task_updated, execution_alert, info.';

COMMENT ON COLUMN cf_system_notification.status IS
  'Suggested values: unread, read, dismissed.';

CREATE INDEX IF NOT EXISTS idx_cf_farm_field_relation_farm_id
  ON cf_farm_field_relation (farm_id);

CREATE INDEX IF NOT EXISTS idx_cf_farm_field_relation_field_id
  ON cf_farm_field_relation (field_id);

CREATE INDEX IF NOT EXISTS idx_cf_code_dict_category_active
  ON cf_code_dict (category, is_active);

CREATE INDEX IF NOT EXISTS idx_cf_user_status
  ON cf_user (status);

CREATE INDEX IF NOT EXISTS idx_cf_user_account_user_id
  ON cf_user_account (user_id);

CREATE INDEX IF NOT EXISTS idx_cf_user_account_status
  ON cf_user_account (status);

CREATE INDEX IF NOT EXISTS idx_cf_planting_plan_farm_id
  ON cf_planting_plan (farm_id);

CREATE INDEX IF NOT EXISTS idx_cf_planting_plan_variety_id
  ON cf_planting_plan (variety_id);

CREATE INDEX IF NOT EXISTS idx_cf_planting_plan_culti_type_code
  ON cf_planting_plan (culti_type_code);

CREATE INDEX IF NOT EXISTS idx_cf_planting_plan_planting_method_code
  ON cf_planting_plan (planting_method_code);

CREATE INDEX IF NOT EXISTS idx_cf_plan_field_relation_plan_id
  ON cf_planting_plan_field_relation (planting_plan_id);

CREATE INDEX IF NOT EXISTS idx_cf_plan_field_relation_field_id
  ON cf_planting_plan_field_relation (field_id);

CREATE INDEX IF NOT EXISTS idx_cf_event_record_plan_id
  ON cf_event_record (planting_plan_id);

CREATE INDEX IF NOT EXISTS idx_cf_event_record_type_status
  ON cf_event_record (event_type, processing_status);

CREATE INDEX IF NOT EXISTS idx_cf_stage_prediction_snapshot_plan_id
  ON cf_stage_prediction_snapshot (planting_plan_id);

CREATE INDEX IF NOT EXISTS idx_cf_calendar_item_plan_status
  ON cf_calendar_item (planting_plan_id, status);

CREATE INDEX IF NOT EXISTS idx_cf_calendar_item_task_subtype
  ON cf_calendar_item (task_subtype);

CREATE INDEX IF NOT EXISTS idx_cf_calendar_item_parent_task_id
  ON cf_calendar_item (parent_task_id);

CREATE INDEX IF NOT EXISTS idx_cf_calendar_item_source_execution_id
  ON cf_calendar_item (source_execution_id);

CREATE INDEX IF NOT EXISTS idx_cf_calendar_item_source_execution_record_id
  ON cf_calendar_item (source_execution_record_id);

CREATE INDEX IF NOT EXISTS idx_cf_task_intent_plan_status
  ON cf_task_intent (planting_plan_id, status);

CREATE INDEX IF NOT EXISTS idx_cf_task_intent_parent_task_id
  ON cf_task_intent (parent_task_id);

CREATE INDEX IF NOT EXISTS idx_cf_task_intent_source_execution_id
  ON cf_task_intent (source_execution_id);

CREATE INDEX IF NOT EXISTS idx_cf_task_intent_source_execution_record_id
  ON cf_task_intent (source_execution_record_id);

CREATE INDEX IF NOT EXISTS idx_cf_review_request_plan_status
  ON cf_review_request (planting_plan_id, status);

CREATE INDEX IF NOT EXISTS idx_cf_review_request_assigned_user_id
  ON cf_review_request (assigned_user_id);

CREATE INDEX IF NOT EXISTS idx_cf_review_request_source_entity
  ON cf_review_request (source_entity_type, source_entity_id);

CREATE INDEX IF NOT EXISTS idx_cf_farming_task_plan_status
  ON cf_farming_task (planting_plan_id, status);

CREATE INDEX IF NOT EXISTS idx_cf_farming_task_task_subtype
  ON cf_farming_task (task_subtype);

CREATE INDEX IF NOT EXISTS idx_cf_farming_task_review_request_id
  ON cf_farming_task (review_request_id);

CREATE INDEX IF NOT EXISTS idx_cf_farming_task_parent_task_id
  ON cf_farming_task (parent_task_id);

CREATE INDEX IF NOT EXISTS idx_cf_farming_task_source_execution_id
  ON cf_farming_task (source_execution_id);

CREATE INDEX IF NOT EXISTS idx_cf_farming_task_source_execution_record_id
  ON cf_farming_task (source_execution_record_id);

CREATE UNIQUE INDEX IF NOT EXISTS uk_cf_operation_plan_active_task
  ON cf_operation_plan (farming_task_id)
  WHERE status = 'active';

CREATE INDEX IF NOT EXISTS idx_cf_execution_task_id
  ON cf_execution (farming_task_id);

CREATE INDEX IF NOT EXISTS idx_cf_execution_operation_plan_id
  ON cf_execution (operation_plan_id);

CREATE INDEX IF NOT EXISTS idx_cf_execution_status
  ON cf_execution (status);

CREATE INDEX IF NOT EXISTS idx_cf_execution_record_execution_id
  ON cf_execution_record (execution_id);

CREATE INDEX IF NOT EXISTS idx_cf_evaluation_execution_id
  ON cf_evaluation (execution_id);

CREATE INDEX IF NOT EXISTS idx_cf_feedback_execution_id
  ON cf_feedback (execution_id);

CREATE INDEX IF NOT EXISTS idx_cf_feedback_requires_review
  ON cf_feedback (requires_review);

CREATE INDEX IF NOT EXISTS idx_cf_system_notification_plan_status
  ON cf_system_notification (planting_plan_id, status);

DROP TRIGGER IF EXISTS trg_cf_farm_updated_at ON cf_farm;
CREATE TRIGGER trg_cf_farm_updated_at
BEFORE UPDATE ON cf_farm
FOR EACH ROW
EXECUTE FUNCTION cf_set_updated_at();

DROP TRIGGER IF EXISTS trg_cf_field_updated_at ON cf_field;
CREATE TRIGGER trg_cf_field_updated_at
BEFORE UPDATE ON cf_field
FOR EACH ROW
EXECUTE FUNCTION cf_set_updated_at();

DROP TRIGGER IF EXISTS trg_cf_farm_field_relation_updated_at ON cf_farm_field_relation;
CREATE TRIGGER trg_cf_farm_field_relation_updated_at
BEFORE UPDATE ON cf_farm_field_relation
FOR EACH ROW
EXECUTE FUNCTION cf_set_updated_at();

DROP TRIGGER IF EXISTS trg_cf_code_dict_updated_at ON cf_code_dict;
CREATE TRIGGER trg_cf_code_dict_updated_at
BEFORE UPDATE ON cf_code_dict
FOR EACH ROW
EXECUTE FUNCTION cf_set_updated_at();

DROP TRIGGER IF EXISTS trg_cf_user_updated_at ON cf_user;
CREATE TRIGGER trg_cf_user_updated_at
BEFORE UPDATE ON cf_user
FOR EACH ROW
EXECUTE FUNCTION cf_set_updated_at();

DROP TRIGGER IF EXISTS trg_cf_user_account_updated_at ON cf_user_account;
CREATE TRIGGER trg_cf_user_account_updated_at
BEFORE UPDATE ON cf_user_account
FOR EACH ROW
EXECUTE FUNCTION cf_set_updated_at();

DROP TRIGGER IF EXISTS trg_cf_rice_variety_updated_at ON cf_rice_variety;
CREATE TRIGGER trg_cf_rice_variety_updated_at
BEFORE UPDATE ON cf_rice_variety
FOR EACH ROW
EXECUTE FUNCTION cf_set_updated_at();

DROP TRIGGER IF EXISTS trg_cf_planting_plan_updated_at ON cf_planting_plan;
CREATE TRIGGER trg_cf_planting_plan_updated_at
BEFORE UPDATE ON cf_planting_plan
FOR EACH ROW
EXECUTE FUNCTION cf_set_updated_at();

DROP TRIGGER IF EXISTS trg_cf_plan_field_relation_updated_at ON cf_planting_plan_field_relation;
CREATE TRIGGER trg_cf_plan_field_relation_updated_at
BEFORE UPDATE ON cf_planting_plan_field_relation
FOR EACH ROW
EXECUTE FUNCTION cf_set_updated_at();

DROP TRIGGER IF EXISTS trg_cf_event_record_updated_at ON cf_event_record;
CREATE TRIGGER trg_cf_event_record_updated_at
BEFORE UPDATE ON cf_event_record
FOR EACH ROW
EXECUTE FUNCTION cf_set_updated_at();

DROP TRIGGER IF EXISTS trg_cf_stage_prediction_snapshot_updated_at ON cf_stage_prediction_snapshot;
CREATE TRIGGER trg_cf_stage_prediction_snapshot_updated_at
BEFORE UPDATE ON cf_stage_prediction_snapshot
FOR EACH ROW
EXECUTE FUNCTION cf_set_updated_at();

DROP TRIGGER IF EXISTS trg_cf_crop_stage_state_updated_at ON cf_crop_stage_state;
CREATE TRIGGER trg_cf_crop_stage_state_updated_at
BEFORE UPDATE ON cf_crop_stage_state
FOR EACH ROW
EXECUTE FUNCTION cf_set_updated_at();

DROP TRIGGER IF EXISTS trg_cf_crop_thermal_time_state_updated_at ON cf_crop_thermal_time_state;
CREATE TRIGGER trg_cf_crop_thermal_time_state_updated_at
BEFORE UPDATE ON cf_crop_thermal_time_state
FOR EACH ROW
EXECUTE FUNCTION cf_set_updated_at();

DROP TRIGGER IF EXISTS trg_cf_calendar_item_updated_at ON cf_calendar_item;
CREATE TRIGGER trg_cf_calendar_item_updated_at
BEFORE UPDATE ON cf_calendar_item
FOR EACH ROW
EXECUTE FUNCTION cf_set_updated_at();

DROP TRIGGER IF EXISTS trg_cf_task_intent_updated_at ON cf_task_intent;
CREATE TRIGGER trg_cf_task_intent_updated_at
BEFORE UPDATE ON cf_task_intent
FOR EACH ROW
EXECUTE FUNCTION cf_set_updated_at();

DROP TRIGGER IF EXISTS trg_cf_review_request_updated_at ON cf_review_request;
CREATE TRIGGER trg_cf_review_request_updated_at
BEFORE UPDATE ON cf_review_request
FOR EACH ROW
EXECUTE FUNCTION cf_set_updated_at();

DROP TRIGGER IF EXISTS trg_cf_farming_task_updated_at ON cf_farming_task;
CREATE TRIGGER trg_cf_farming_task_updated_at
BEFORE UPDATE ON cf_farming_task
FOR EACH ROW
EXECUTE FUNCTION cf_set_updated_at();

DROP TRIGGER IF EXISTS trg_cf_operation_plan_updated_at ON cf_operation_plan;
CREATE TRIGGER trg_cf_operation_plan_updated_at
BEFORE UPDATE ON cf_operation_plan
FOR EACH ROW
EXECUTE FUNCTION cf_set_updated_at();

DROP TRIGGER IF EXISTS trg_cf_execution_updated_at ON cf_execution;
CREATE TRIGGER trg_cf_execution_updated_at
BEFORE UPDATE ON cf_execution
FOR EACH ROW
EXECUTE FUNCTION cf_set_updated_at();

DROP TRIGGER IF EXISTS trg_cf_execution_record_updated_at ON cf_execution_record;
CREATE TRIGGER trg_cf_execution_record_updated_at
BEFORE UPDATE ON cf_execution_record
FOR EACH ROW
EXECUTE FUNCTION cf_set_updated_at();

DROP TRIGGER IF EXISTS trg_cf_evaluation_updated_at ON cf_evaluation;
CREATE TRIGGER trg_cf_evaluation_updated_at
BEFORE UPDATE ON cf_evaluation
FOR EACH ROW
EXECUTE FUNCTION cf_set_updated_at();

DROP TRIGGER IF EXISTS trg_cf_feedback_updated_at ON cf_feedback;
CREATE TRIGGER trg_cf_feedback_updated_at
BEFORE UPDATE ON cf_feedback
FOR EACH ROW
EXECUTE FUNCTION cf_set_updated_at();

DROP TRIGGER IF EXISTS trg_cf_system_notification_updated_at ON cf_system_notification;
CREATE TRIGGER trg_cf_system_notification_updated_at
BEFORE UPDATE ON cf_system_notification
FOR EACH ROW
EXECUTE FUNCTION cf_set_updated_at();

-- Expected task_subtype values for the current weed-protection loop include:
--   WF_SOIL_SEAL_WEED
--   WF_STEM_LEAF_WEED_SURVEY
--   WF_STEM_LEAF_WEED
--   WF_STEM_LEAF_WEED_POST_SURVEY
--   WF_STEM_LEAF_WEED_ADDITIONAL_CONTROL
--   WF_PLANT_PROTECTION_SERVICE_EVALUATION
--   WF_PLANT_PROTECTION_SERVICE_EFFECT_SURVEY
