-- V1 Migration 004
-- Purpose:
--   Create execution and execution-record tables.

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
