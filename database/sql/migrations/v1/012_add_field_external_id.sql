ALTER TABLE cf_field
  ADD COLUMN IF NOT EXISTS external_field_id varchar(50);

CREATE INDEX IF NOT EXISTS idx_cf_field_external_field_id
  ON cf_field (external_field_id);
