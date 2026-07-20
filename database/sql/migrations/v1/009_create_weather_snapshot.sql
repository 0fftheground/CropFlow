CREATE TABLE IF NOT EXISTS cf_weather_snapshot (
    id BIGSERIAL PRIMARY KEY,
    farm_id BIGINT NOT NULL REFERENCES cf_farm(id) ON DELETE CASCADE,
    weather_year INTEGER NOT NULL,
    weather_date DATE NOT NULL,
    source_type VARCHAR(50) NOT NULL,
    data_version VARCHAR(100) NOT NULL,
    data_hash VARCHAR(64) NOT NULL,
    payload JSONB NOT NULL DEFAULT '{}'::jsonb,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    superseded_at TIMESTAMP,
    superseded_by_snapshot_id BIGINT REFERENCES cf_weather_snapshot(id) ON DELETE SET NULL,
    source_event_id BIGINT REFERENCES cf_event_record(id) ON DELETE SET NULL,
    created_by_type VARCHAR(20) NOT NULL DEFAULT 'system',
    created_by_id VARCHAR(100),
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uq_weather_snapshot_identity UNIQUE (
        farm_id,
        weather_year,
        weather_date,
        source_type,
        data_version,
        data_hash
    )
);

CREATE INDEX IF NOT EXISTS idx_weather_snapshot_farm_year_date
    ON cf_weather_snapshot (farm_id, weather_year, weather_date DESC, id DESC);

CREATE INDEX IF NOT EXISTS idx_weather_snapshot_active_lookup
    ON cf_weather_snapshot (farm_id, weather_year, weather_date, source_type, is_active);
