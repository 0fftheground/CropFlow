CREATE TABLE IF NOT EXISTS cf_crop_stage_dict (
    id BIGSERIAL PRIMARY KEY,
    stage_code VARCHAR(50) NOT NULL,
    stage_name VARCHAR(100) NOT NULL,
    season_scope VARCHAR(20) NOT NULL,
    business_stage_code VARCHAR(50),
    display_order INTEGER NOT NULL,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_by_type VARCHAR(20) NOT NULL DEFAULT 'system',
    created_by_id VARCHAR(100),
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uk_cf_crop_stage_dict_stage_code UNIQUE (stage_code)
);

CREATE INDEX IF NOT EXISTS idx_cf_crop_stage_dict_active_order
    ON cf_crop_stage_dict (is_active, display_order, id);
