-- V1 Migration 005
-- Purpose:
--   Create evaluation, feedback, and notification tables.

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
