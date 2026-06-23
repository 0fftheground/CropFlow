ALTER TABLE cf_field
  ADD COLUMN IF NOT EXISTS external_field_id varchar(50);

DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1
    FROM pg_constraint
    WHERE conname = 'uk_cf_field_external_field_id'
  ) THEN
    ALTER TABLE cf_field
      ADD CONSTRAINT uk_cf_field_external_field_id UNIQUE (external_field_id);
  END IF;
END;
$$;
