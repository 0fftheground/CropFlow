-- V1 Migration 002
-- Purpose:
--   Create plan, event, and stage-related tables.

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
