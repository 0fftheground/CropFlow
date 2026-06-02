CREATE TABLE IF NOT EXISTS pp_rice_control_window_level_1 (
    id BIGSERIAL PRIMARY KEY,
    province VARCHAR(100) NOT NULL,
    city VARCHAR(100) NOT NULL,
    county VARCHAR(100) NOT NULL,
    data_year INTEGER NOT NULL,
    detail JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_rice_control_window_level_1_region_year
    ON pp_rice_control_window_level_1 (province, city, county, data_year, id DESC);
