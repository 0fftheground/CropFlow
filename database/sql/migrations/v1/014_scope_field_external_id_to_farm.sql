ALTER TABLE cf_field
  DROP CONSTRAINT IF EXISTS uk_cf_field_external_field_id;

CREATE INDEX IF NOT EXISTS idx_cf_field_external_field_id
  ON cf_field (external_field_id);
