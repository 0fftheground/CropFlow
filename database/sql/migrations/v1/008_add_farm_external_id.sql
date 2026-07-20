ALTER TABLE cf_farm
  ADD COLUMN IF NOT EXISTS external_farm_id varchar(50);

DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1
    FROM pg_constraint
    WHERE conname = 'uk_cf_farm_external_farm_id'
  ) THEN
    ALTER TABLE cf_farm
      ADD CONSTRAINT uk_cf_farm_external_farm_id UNIQUE (external_farm_id);
  END IF;
END;
$$;
