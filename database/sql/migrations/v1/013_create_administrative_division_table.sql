-- V1 Migration 013
-- Purpose:
--   Create administrative division reference table for province/city/county lookup.

CREATE TABLE IF NOT EXISTS cf_administrative_division (
  id bigserial PRIMARY KEY,
  code varchar(12) NOT NULL,
  adcode varchar(6) NOT NULL,
  name varchar(100) NOT NULL,
  division_type varchar(50) NOT NULL,
  level int4 NOT NULL,
  parent_code varchar(12),
  sort_order int4 NOT NULL,
  created_by_type varchar(20) NOT NULL DEFAULT 'system',
  created_by_id varchar(100),
  created_at timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
  CONSTRAINT uk_cf_administrative_division_code UNIQUE (code)
);

CREATE INDEX IF NOT EXISTS idx_cf_administrative_division_parent_code
  ON cf_administrative_division(parent_code);

CREATE INDEX IF NOT EXISTS idx_cf_administrative_division_level
  ON cf_administrative_division(level);

CREATE INDEX IF NOT EXISTS idx_cf_administrative_division_sort_order
  ON cf_administrative_division(sort_order);

DROP TRIGGER IF EXISTS trg_cf_administrative_division_updated_at ON cf_administrative_division;
CREATE TRIGGER trg_cf_administrative_division_updated_at
BEFORE UPDATE ON cf_administrative_division
FOR EACH ROW
EXECUTE FUNCTION cf_set_updated_at();
