ALTER TABLE cf_farm ADD COLUMN IF NOT EXISTS province varchar(100);
ALTER TABLE cf_farm ADD COLUMN IF NOT EXISTS city varchar(100);
ALTER TABLE cf_farm ADD COLUMN IF NOT EXISTS district_county varchar(100);
ALTER TABLE cf_farm ADD COLUMN IF NOT EXISTS adcode varchar(20);
