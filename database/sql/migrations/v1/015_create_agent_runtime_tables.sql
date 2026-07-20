-- V1 Migration 015
-- Purpose:
--   Add the durable CropFlow Business Agent Runtime boundary without copying
--   authoritative PlantingPlan, FarmingTask, or ReviewRequest state.

CREATE TABLE IF NOT EXISTS cf_agent_session (
  id varchar(64) PRIMARY KEY,
  planting_plan_id bigint NOT NULL REFERENCES cf_planting_plan(id) ON DELETE CASCADE,
  user_id varchar(100) NOT NULL REFERENCES cf_user(id) ON DELETE RESTRICT,
  selected_role varchar(50) NOT NULL,
  status varchar(30) NOT NULL DEFAULT 'active',
  metadata jsonb NOT NULL DEFAULT '{}'::jsonb,
  created_at timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS cf_agent_message (
  id varchar(64) PRIMARY KEY,
  session_id varchar(64) NOT NULL REFERENCES cf_agent_session(id) ON DELETE CASCADE,
  run_id varchar(64),
  role varchar(30) NOT NULL,
  content text NOT NULL,
  metadata jsonb NOT NULL DEFAULT '{}'::jsonb,
  created_at timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS cf_agent_run (
  id varchar(64) PRIMARY KEY,
  session_id varchar(64) NOT NULL REFERENCES cf_agent_session(id) ON DELETE CASCADE,
  user_message_id varchar(64) NOT NULL REFERENCES cf_agent_message(id) ON DELETE RESTRICT,
  status varchar(30) NOT NULL DEFAULT 'pending',
  iteration int4 NOT NULL DEFAULT 0,
  provider_name varchar(100) NOT NULL,
  provider_state jsonb NOT NULL DEFAULT '{}'::jsonb,
  error_code varchar(100),
  error_message text,
  started_at timestamp,
  completed_at timestamp,
  created_at timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP
);

DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1
    FROM pg_constraint
    WHERE conname = 'fk_cf_agent_message_run'
  ) THEN
    ALTER TABLE cf_agent_message
      ADD CONSTRAINT fk_cf_agent_message_run
      FOREIGN KEY (run_id) REFERENCES cf_agent_run(id) ON DELETE SET NULL;
  END IF;
END
$$;

CREATE TABLE IF NOT EXISTS cf_agent_tool_call (
  id varchar(100) PRIMARY KEY,
  run_id varchar(64) NOT NULL REFERENCES cf_agent_run(id) ON DELETE CASCADE,
  action_name varchar(100) NOT NULL,
  arguments jsonb NOT NULL DEFAULT '{}'::jsonb,
  status varchar(30) NOT NULL DEFAULT 'proposed',
  result jsonb NOT NULL DEFAULT '{}'::jsonb,
  error_code varchar(100),
  error_message text,
  approval_required boolean NOT NULL DEFAULT false,
  idempotency_key varchar(255) NOT NULL UNIQUE,
  started_at timestamp,
  completed_at timestamp,
  created_at timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS cf_agent_approval_request (
  id varchar(64) PRIMARY KEY,
  run_id varchar(64) NOT NULL REFERENCES cf_agent_run(id) ON DELETE CASCADE,
  tool_call_id varchar(100) NOT NULL UNIQUE REFERENCES cf_agent_tool_call(id) ON DELETE CASCADE,
  status varchar(30) NOT NULL DEFAULT 'pending',
  action_name varchar(100) NOT NULL,
  action_summary text NOT NULL,
  requested_by varchar(100) NOT NULL REFERENCES cf_user(id) ON DELETE RESTRICT,
  decided_by varchar(100) REFERENCES cf_user(id) ON DELETE RESTRICT,
  decision_note text,
  decided_at timestamp,
  created_at timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS cf_agent_event (
  id bigserial PRIMARY KEY,
  run_id varchar(64) NOT NULL REFERENCES cf_agent_run(id) ON DELETE CASCADE,
  sequence int4 NOT NULL,
  event_type varchar(100) NOT NULL,
  payload jsonb NOT NULL DEFAULT '{}'::jsonb,
  created_at timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
  CONSTRAINT uk_cf_agent_event_run_sequence UNIQUE (run_id, sequence)
);

CREATE TABLE IF NOT EXISTS cf_agent_audit_record (
  id bigserial PRIMARY KEY,
  run_id varchar(64) NOT NULL REFERENCES cf_agent_run(id) ON DELETE CASCADE,
  audit_type varchar(100) NOT NULL,
  actor_user_id varchar(100),
  payload jsonb NOT NULL DEFAULT '{}'::jsonb,
  created_at timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_cf_agent_session_plan
  ON cf_agent_session (planting_plan_id, updated_at DESC);
CREATE INDEX IF NOT EXISTS idx_cf_agent_message_session
  ON cf_agent_message (session_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_cf_agent_run_session
  ON cf_agent_run (session_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_cf_agent_tool_call_run
  ON cf_agent_tool_call (run_id, created_at);
CREATE INDEX IF NOT EXISTS idx_cf_agent_approval_status
  ON cf_agent_approval_request (status, created_at);
CREATE INDEX IF NOT EXISTS idx_cf_agent_event_run
  ON cf_agent_event (run_id, sequence);
CREATE INDEX IF NOT EXISTS idx_cf_agent_audit_run
  ON cf_agent_audit_record (run_id, created_at);

DROP TRIGGER IF EXISTS trg_cf_agent_session_updated_at ON cf_agent_session;
CREATE TRIGGER trg_cf_agent_session_updated_at
BEFORE UPDATE ON cf_agent_session
FOR EACH ROW EXECUTE FUNCTION cf_set_updated_at();

DROP TRIGGER IF EXISTS trg_cf_agent_run_updated_at ON cf_agent_run;
CREATE TRIGGER trg_cf_agent_run_updated_at
BEFORE UPDATE ON cf_agent_run
FOR EACH ROW EXECUTE FUNCTION cf_set_updated_at();

DROP TRIGGER IF EXISTS trg_cf_agent_tool_call_updated_at ON cf_agent_tool_call;
CREATE TRIGGER trg_cf_agent_tool_call_updated_at
BEFORE UPDATE ON cf_agent_tool_call
FOR EACH ROW EXECUTE FUNCTION cf_set_updated_at();

DROP TRIGGER IF EXISTS trg_cf_agent_approval_request_updated_at ON cf_agent_approval_request;
CREATE TRIGGER trg_cf_agent_approval_request_updated_at
BEFORE UPDATE ON cf_agent_approval_request
FOR EACH ROW EXECUTE FUNCTION cf_set_updated_at();
