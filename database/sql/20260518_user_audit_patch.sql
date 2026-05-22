-- Patch existing weed-protection closed-loop tables with:
--   - minimal user/auth tables
--   - cf_code_dict structure/data aligned with agri_code_dict
--   - created_by_type / created_by_id audit columns
--   - review assignee / resolver and notification target user references
--   - evaluation / feedback source fields
--
-- Note:
--   Load cf_code_dict from agri_code_dict_202605181653.csv or from the existing agri_code_dict source table
--   before enforcing downstream foreign keys.

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

ALTER TABLE cf_farm ADD COLUMN IF NOT EXISTS created_by_type varchar(20) NOT NULL DEFAULT 'system';
ALTER TABLE cf_farm ADD COLUMN IF NOT EXISTS created_by_id varchar(100);

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

ALTER TABLE cf_field ADD COLUMN IF NOT EXISTS created_by_type varchar(20) NOT NULL DEFAULT 'system';
ALTER TABLE cf_field ADD COLUMN IF NOT EXISTS created_by_id varchar(100);

ALTER TABLE cf_farm_field_relation ADD COLUMN IF NOT EXISTS created_by_type varchar(20) NOT NULL DEFAULT 'system';
ALTER TABLE cf_farm_field_relation ADD COLUMN IF NOT EXISTS created_by_id varchar(100);

ALTER TABLE cf_rice_variety ADD COLUMN IF NOT EXISTS culti_type_code int8;
ALTER TABLE cf_rice_variety ADD COLUMN IF NOT EXISTS sub_type_code int8;
ALTER TABLE cf_rice_variety ADD COLUMN IF NOT EXISTS maturity_code int8;
ALTER TABLE cf_rice_variety ADD COLUMN IF NOT EXISTS created_by_type varchar(20) NOT NULL DEFAULT 'system';
ALTER TABLE cf_rice_variety ADD COLUMN IF NOT EXISTS created_by_id varchar(100);
ALTER TABLE cf_rice_variety ADD COLUMN IF NOT EXISTS created_at timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP;
ALTER TABLE cf_rice_variety ADD COLUMN IF NOT EXISTS updated_at timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP;

ALTER TABLE cf_planting_plan ADD COLUMN IF NOT EXISTS culti_type_code int8;
ALTER TABLE cf_planting_plan ADD COLUMN IF NOT EXISTS planting_method_code int8;
ALTER TABLE cf_planting_plan ADD COLUMN IF NOT EXISTS created_by_type varchar(20) NOT NULL DEFAULT 'system';
ALTER TABLE cf_planting_plan ADD COLUMN IF NOT EXISTS created_by_id varchar(100);

ALTER TABLE cf_planting_plan_field_relation ADD COLUMN IF NOT EXISTS created_by_type varchar(20) NOT NULL DEFAULT 'system';
ALTER TABLE cf_planting_plan_field_relation ADD COLUMN IF NOT EXISTS created_by_id varchar(100);

ALTER TABLE cf_event_record ADD COLUMN IF NOT EXISTS created_by_type varchar(20) NOT NULL DEFAULT 'system';
ALTER TABLE cf_event_record ADD COLUMN IF NOT EXISTS created_by_id varchar(100);

ALTER TABLE cf_stage_prediction_snapshot ADD COLUMN IF NOT EXISTS created_by_type varchar(20) NOT NULL DEFAULT 'system';
ALTER TABLE cf_stage_prediction_snapshot ADD COLUMN IF NOT EXISTS created_by_id varchar(100);

ALTER TABLE cf_crop_stage_state ADD COLUMN IF NOT EXISTS created_by_type varchar(20) NOT NULL DEFAULT 'system';
ALTER TABLE cf_crop_stage_state ADD COLUMN IF NOT EXISTS created_by_id varchar(100);

ALTER TABLE cf_crop_thermal_time_state ADD COLUMN IF NOT EXISTS created_by_type varchar(20) NOT NULL DEFAULT 'system';
ALTER TABLE cf_crop_thermal_time_state ADD COLUMN IF NOT EXISTS created_by_id varchar(100);

ALTER TABLE cf_calendar_item ADD COLUMN IF NOT EXISTS created_by_type varchar(20) NOT NULL DEFAULT 'system';
ALTER TABLE cf_calendar_item ADD COLUMN IF NOT EXISTS created_by_id varchar(100);

ALTER TABLE cf_task_intent ADD COLUMN IF NOT EXISTS created_by_type varchar(20) NOT NULL DEFAULT 'system';
ALTER TABLE cf_task_intent ADD COLUMN IF NOT EXISTS created_by_id varchar(100);

ALTER TABLE cf_review_request ADD COLUMN IF NOT EXISTS assigned_user_id varchar(100);
ALTER TABLE cf_review_request ADD COLUMN IF NOT EXISTS created_by_type varchar(20) NOT NULL DEFAULT 'system';
ALTER TABLE cf_review_request ADD COLUMN IF NOT EXISTS created_by_id varchar(100);

ALTER TABLE cf_farming_task ADD COLUMN IF NOT EXISTS created_by_type varchar(20) NOT NULL DEFAULT 'system';
ALTER TABLE cf_farming_task ADD COLUMN IF NOT EXISTS created_by_id varchar(100);

ALTER TABLE cf_operation_plan ADD COLUMN IF NOT EXISTS created_by_type varchar(20) NOT NULL DEFAULT 'system';
ALTER TABLE cf_operation_plan ADD COLUMN IF NOT EXISTS created_by_id varchar(100);

ALTER TABLE cf_execution ADD COLUMN IF NOT EXISTS created_by_type varchar(20) NOT NULL DEFAULT 'system';
ALTER TABLE cf_execution ADD COLUMN IF NOT EXISTS created_by_id varchar(100);

ALTER TABLE cf_execution_record ADD COLUMN IF NOT EXISTS created_by_type varchar(20) NOT NULL DEFAULT 'system';
ALTER TABLE cf_execution_record ADD COLUMN IF NOT EXISTS created_by_id varchar(100);

ALTER TABLE cf_evaluation ADD COLUMN IF NOT EXISTS source_type varchar(50) NOT NULL DEFAULT 'system';
ALTER TABLE cf_evaluation ADD COLUMN IF NOT EXISTS source_id varchar(100);
ALTER TABLE cf_evaluation ADD COLUMN IF NOT EXISTS created_by_type varchar(20) NOT NULL DEFAULT 'system';
ALTER TABLE cf_evaluation ADD COLUMN IF NOT EXISTS created_by_id varchar(100);

ALTER TABLE cf_feedback ADD COLUMN IF NOT EXISTS source_type varchar(50) NOT NULL DEFAULT 'system';
ALTER TABLE cf_feedback ADD COLUMN IF NOT EXISTS source_id varchar(100);
ALTER TABLE cf_feedback ADD COLUMN IF NOT EXISTS created_by_type varchar(20) NOT NULL DEFAULT 'system';
ALTER TABLE cf_feedback ADD COLUMN IF NOT EXISTS created_by_id varchar(100);

ALTER TABLE cf_system_notification ADD COLUMN IF NOT EXISTS created_by_type varchar(20) NOT NULL DEFAULT 'system';
ALTER TABLE cf_system_notification ADD COLUMN IF NOT EXISTS created_by_id varchar(100);

UPDATE cf_planting_plan
SET culti_type_code = CASE culti_type
  WHEN '双季晚稻' THEN 4
  WHEN '早稻' THEN 5
  WHEN '一季晚稻' THEN 6
  WHEN '中稻' THEN 7
  WHEN '再生稻' THEN 8
  ELSE culti_type_code
END
WHERE culti_type_code IS NULL AND culti_type IS NOT NULL;

UPDATE cf_planting_plan
SET planting_method_code = CASE planting_method
  WHEN '直播' THEN 1
  WHEN '抛秧' THEN 2
  WHEN '插秧' THEN 3
  ELSE planting_method_code
END
WHERE planting_method_code IS NULL AND planting_method IS NOT NULL;

UPDATE cf_rice_variety
SET sub_type_code = CASE sub_type
  WHEN '籼' THEN 9
  WHEN '粳' THEN 10
  WHEN '籼粳交' THEN 11
  ELSE sub_type_code
END
WHERE sub_type_code IS NULL AND sub_type IS NOT NULL;

UPDATE cf_rice_variety
SET culti_type_code = culti_type
WHERE culti_type_code IS NULL AND culti_type IS NOT NULL;

UPDATE cf_rice_variety
SET maturity_code = maturity
WHERE maturity_code IS NULL AND maturity IS NOT NULL;

ALTER TABLE cf_planting_plan ALTER COLUMN culti_type_code SET NOT NULL;
ALTER TABLE cf_planting_plan ALTER COLUMN planting_method_code SET NOT NULL;

ALTER TABLE cf_planting_plan DROP COLUMN IF EXISTS crop_season;
ALTER TABLE cf_planting_plan DROP COLUMN IF EXISTS rice_cropping_type;
ALTER TABLE cf_planting_plan DROP COLUMN IF EXISTS culti_type;
ALTER TABLE cf_planting_plan DROP COLUMN IF EXISTS planting_method;

ALTER TABLE cf_rice_variety DROP COLUMN IF EXISTS culti_type;
ALTER TABLE cf_rice_variety DROP COLUMN IF EXISTS sub_type;
ALTER TABLE cf_rice_variety DROP COLUMN IF EXISTS maturity;

ALTER TABLE cf_rice_variety DROP CONSTRAINT IF EXISTS fk_cf_rice_variety_culti_type_code;
ALTER TABLE cf_rice_variety DROP CONSTRAINT IF EXISTS fk_cf_rice_variety_sub_type_code;
ALTER TABLE cf_rice_variety DROP CONSTRAINT IF EXISTS fk_cf_rice_variety_maturity_code;
ALTER TABLE cf_planting_plan DROP CONSTRAINT IF EXISTS fk_cf_planting_plan_culti_type_code;
ALTER TABLE cf_planting_plan DROP CONSTRAINT IF EXISTS fk_cf_planting_plan_planting_method_code;

DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM pg_constraint WHERE conname = 'fk_cf_rice_variety_culti_type_code'
  ) THEN
    ALTER TABLE cf_rice_variety
      ADD CONSTRAINT fk_cf_rice_variety_culti_type_code
      FOREIGN KEY (culti_type_code) REFERENCES cf_code_dict(code) ON DELETE RESTRICT;
  END IF;
END;
$$;

DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM pg_constraint WHERE conname = 'fk_cf_rice_variety_sub_type_code'
  ) THEN
    ALTER TABLE cf_rice_variety
      ADD CONSTRAINT fk_cf_rice_variety_sub_type_code
      FOREIGN KEY (sub_type_code) REFERENCES cf_code_dict(code) ON DELETE RESTRICT;
  END IF;
END;
$$;

DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM pg_constraint WHERE conname = 'fk_cf_rice_variety_maturity_code'
  ) THEN
    ALTER TABLE cf_rice_variety
      ADD CONSTRAINT fk_cf_rice_variety_maturity_code
      FOREIGN KEY (maturity_code) REFERENCES cf_code_dict(code) ON DELETE RESTRICT;
  END IF;
END;
$$;

DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM pg_constraint WHERE conname = 'fk_cf_planting_plan_culti_type_code'
  ) THEN
    ALTER TABLE cf_planting_plan
      ADD CONSTRAINT fk_cf_planting_plan_culti_type_code
      FOREIGN KEY (culti_type_code) REFERENCES cf_code_dict(code) ON DELETE RESTRICT;
  END IF;
END;
$$;

DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM pg_constraint WHERE conname = 'fk_cf_planting_plan_planting_method_code'
  ) THEN
    ALTER TABLE cf_planting_plan
      ADD CONSTRAINT fk_cf_planting_plan_planting_method_code
      FOREIGN KEY (planting_method_code) REFERENCES cf_code_dict(code) ON DELETE RESTRICT;
  END IF;
END;
$$;

DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM pg_constraint WHERE conname = 'fk_cf_review_request_assigned_user'
  ) THEN
    ALTER TABLE cf_review_request
      ADD CONSTRAINT fk_cf_review_request_assigned_user
      FOREIGN KEY (assigned_user_id) REFERENCES cf_user(id) ON DELETE SET NULL;
  END IF;
END;
$$;

DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM pg_constraint WHERE conname = 'fk_cf_review_request_resolved_by_user'
  ) THEN
    ALTER TABLE cf_review_request
      DROP CONSTRAINT IF EXISTS cf_review_request_resolved_by_fkey;
    ALTER TABLE cf_review_request
      ADD CONSTRAINT fk_cf_review_request_resolved_by_user
      FOREIGN KEY (resolved_by) REFERENCES cf_user(id) ON DELETE SET NULL;
  END IF;
END;
$$;

DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM pg_constraint WHERE conname = 'fk_cf_system_notification_target_user'
  ) THEN
    ALTER TABLE cf_system_notification
      DROP CONSTRAINT IF EXISTS cf_system_notification_target_user_id_fkey;
    ALTER TABLE cf_system_notification
      ADD CONSTRAINT fk_cf_system_notification_target_user
      FOREIGN KEY (target_user_id) REFERENCES cf_user(id) ON DELETE SET NULL;
  END IF;
END;
$$;

CREATE INDEX IF NOT EXISTS idx_cf_user_status
  ON cf_user (status);

CREATE INDEX IF NOT EXISTS idx_cf_user_account_user_id
  ON cf_user_account (user_id);

CREATE INDEX IF NOT EXISTS idx_cf_user_account_status
  ON cf_user_account (status);

CREATE INDEX IF NOT EXISTS idx_cf_code_dict_category_active
  ON cf_code_dict (category, is_active);

CREATE INDEX IF NOT EXISTS idx_cf_planting_plan_culti_type_code
  ON cf_planting_plan (culti_type_code);

CREATE INDEX IF NOT EXISTS idx_cf_planting_plan_planting_method_code
  ON cf_planting_plan (planting_method_code);

CREATE INDEX IF NOT EXISTS idx_cf_review_request_assigned_user_id
  ON cf_review_request (assigned_user_id);

CREATE INDEX IF NOT EXISTS idx_cf_system_notification_target_user_id
  ON cf_system_notification (target_user_id);

CREATE OR REPLACE FUNCTION cf_set_updated_at()
RETURNS trigger
LANGUAGE plpgsql
AS $$
BEGIN
  NEW.updated_at = CURRENT_TIMESTAMP;
  RETURN NEW;
END;
$$;

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

DROP TRIGGER IF EXISTS trg_cf_code_dict_updated_at ON cf_code_dict;
CREATE TRIGGER trg_cf_code_dict_updated_at
BEFORE UPDATE ON cf_code_dict
FOR EACH ROW
EXECUTE FUNCTION cf_set_updated_at();

DROP TRIGGER IF EXISTS trg_cf_rice_variety_updated_at ON cf_rice_variety;
CREATE TRIGGER trg_cf_rice_variety_updated_at
BEFORE UPDATE ON cf_rice_variety
FOR EACH ROW
EXECUTE FUNCTION cf_set_updated_at();
