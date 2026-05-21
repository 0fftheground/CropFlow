-- V1 Migration 001
-- Purpose:
--   Create base reference tables and the shared updated_at trigger function.

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
