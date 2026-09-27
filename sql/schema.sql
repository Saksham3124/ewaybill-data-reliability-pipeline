-- ============================================================================
-- DGCI&S Road E-Way Bill Data Reliability & Reconciliation Pipeline Schema
-- Database: PostgreSQL 14+
-- Governance Phase 3: Data Foundation
-- ============================================================================

-- Enable UUID extension for run identifiers
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- ============================================================================
-- 1. CONTROL & METADATA LAYER
-- ============================================================================

CREATE TABLE IF NOT EXISTS pipeline_runs (
    run_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    source_filename VARCHAR(255) NOT NULL,
    source_filepath TEXT NOT NULL,
    ingestion_timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    status VARCHAR(50) NOT NULL DEFAULT 'STARTED',
    row_counts JSONB,
    validation_summary JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    completed_at TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_pipeline_runs_timestamp ON pipeline_runs(ingestion_timestamp);
CREATE INDEX IF NOT EXISTS idx_pipeline_runs_status ON pipeline_runs(status);

-- ============================================================================
-- 2. RAW DATA LAYER (Audit & Exact Source Preservation)
-- ============================================================================

-- Raw Table I: State-to-State Matrix
CREATE TABLE IF NOT EXISTS raw_state_to_state_matrix (
    id BIGSERIAL PRIMARY KEY,
    run_id UUID NOT NULL REFERENCES pipeline_runs(run_id) ON DELETE CASCADE,
    from_state VARCHAR(100) NOT NULL,
    to_state VARCHAR(100) NOT NULL,
    movement_value NUMERIC(24, 12), -- NULL preserved
    source_row_index INT NOT NULL,
    source_col_index INT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_raw_s2s_run ON raw_state_to_state_matrix(run_id);
CREATE INDEX IF NOT EXISTS idx_raw_s2s_states ON raw_state_to_state_matrix(from_state, to_state);

-- Raw Table II: Chapter Summary
CREATE TABLE IF NOT EXISTS raw_chapter_summary (
    id BIGSERIAL PRIMARY KEY,
    run_id UUID NOT NULL REFERENCES pipeline_runs(run_id) ON DELETE CASCADE,
    chapter_code VARCHAR(10) NOT NULL,
    chapter_description TEXT NOT NULL,
    movement_value NUMERIC(24, 12), -- NULL preserved
    source_row_index INT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_raw_chap_sum_run ON raw_chapter_summary(run_id);
CREATE INDEX IF NOT EXISTS idx_raw_chap_sum_code ON raw_chapter_summary(chapter_code);

-- Raw Table III: Chapter Outward Matrix
CREATE TABLE IF NOT EXISTS raw_chapter_outward_matrix (
    id BIGSERIAL PRIMARY KEY,
    run_id UUID NOT NULL REFERENCES pipeline_runs(run_id) ON DELETE CASCADE,
    chapter_code VARCHAR(10) NOT NULL,
    chapter_description TEXT NOT NULL,
    state VARCHAR(100) NOT NULL,
    movement_value NUMERIC(24, 12), -- NULL preserved
    source_row_index INT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_raw_chap_out_run ON raw_chapter_outward_matrix(run_id);
CREATE INDEX IF NOT EXISTS idx_raw_chap_out_code_state ON raw_chapter_outward_matrix(chapter_code, state);

-- Raw Table IV: Chapter Inward Matrix
CREATE TABLE IF NOT EXISTS raw_chapter_inward_matrix (
    id BIGSERIAL PRIMARY KEY,
    run_id UUID NOT NULL REFERENCES pipeline_runs(run_id) ON DELETE CASCADE,
    chapter_code VARCHAR(10) NOT NULL,
    chapter_description TEXT NOT NULL,
    state VARCHAR(100) NOT NULL,
    movement_value NUMERIC(24, 12), -- NULL preserved
    is_summary_column BOOLEAN NOT NULL DEFAULT FALSE,
    source_row_index INT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_raw_chap_in_run ON raw_chapter_inward_matrix(run_id);
CREATE INDEX IF NOT EXISTS idx_raw_chap_in_code_state ON raw_chapter_inward_matrix(chapter_code, state);

-- Raw Table V: Chapter Internal Matrix
CREATE TABLE IF NOT EXISTS raw_chapter_internal_matrix (
    id BIGSERIAL PRIMARY KEY,
    run_id UUID NOT NULL REFERENCES pipeline_runs(run_id) ON DELETE CASCADE,
    chapter_code VARCHAR(10) NOT NULL,
    chapter_description TEXT NOT NULL,
    state VARCHAR(100) NOT NULL,
    movement_value NUMERIC(24, 12), -- NULL preserved
    is_summary_column BOOLEAN NOT NULL DEFAULT FALSE,
    source_row_index INT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_raw_chap_int_run ON raw_chapter_internal_matrix(run_id);
CREATE INDEX IF NOT EXISTS idx_raw_chap_int_code_state ON raw_chapter_internal_matrix(chapter_code, state);

-- Raw Worksheet Metadata & Published Totals
CREATE TABLE IF NOT EXISTS raw_worksheet_metadata (
    id BIGSERIAL PRIMARY KEY,
    run_id UUID NOT NULL REFERENCES pipeline_runs(run_id) ON DELETE CASCADE,
    worksheet_name VARCHAR(100) NOT NULL,
    title_text TEXT,
    data_start_row INT NOT NULL,
    data_end_row INT NOT NULL,
    row_count INT NOT NULL,
    column_count INT NOT NULL,
    null_cells_count INT NOT NULL,
    reported_total NUMERIC(24, 12),
    reported_state_totals JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_raw_meta_run ON raw_worksheet_metadata(run_id);

-- ============================================================================
-- 3. NORMALIZED / TRUSTED LAYER
-- ============================================================================

-- Normalized 1: state_movement
CREATE TABLE IF NOT EXISTS trusted_state_movement (
    id BIGSERIAL PRIMARY KEY,
    run_id UUID NOT NULL REFERENCES pipeline_runs(run_id) ON DELETE CASCADE,
    origin_state VARCHAR(100) NOT NULL,
    destination_state VARCHAR(100) NOT NULL,
    movement_value_inr_crore NUMERIC(24, 12), -- NULL preserved
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_trusted_state_movement UNIQUE (run_id, origin_state, destination_state)
);

CREATE INDEX IF NOT EXISTS idx_trusted_sm_run ON trusted_state_movement(run_id);
CREATE INDEX IF NOT EXISTS idx_trusted_sm_origin ON trusted_state_movement(origin_state);
CREATE INDEX IF NOT EXISTS idx_trusted_sm_dest ON trusted_state_movement(destination_state);

-- Normalized 2: chapter_movement
CREATE TABLE IF NOT EXISTS trusted_chapter_movement (
    id BIGSERIAL PRIMARY KEY,
    run_id UUID NOT NULL REFERENCES pipeline_runs(run_id) ON DELETE CASCADE,
    chapter_code VARCHAR(10) NOT NULL,
    chapter_description TEXT NOT NULL,
    movement_value_inr_crore NUMERIC(24, 12), -- NULL preserved
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_trusted_chapter_movement UNIQUE (run_id, chapter_code)
);

CREATE INDEX IF NOT EXISTS idx_trusted_cm_run ON trusted_chapter_movement(run_id);
CREATE INDEX IF NOT EXISTS idx_trusted_cm_code ON trusted_chapter_movement(chapter_code);

-- Normalized 3: state_chapter_outward
CREATE TABLE IF NOT EXISTS trusted_state_chapter_outward (
    id BIGSERIAL PRIMARY KEY,
    run_id UUID NOT NULL REFERENCES pipeline_runs(run_id) ON DELETE CASCADE,
    chapter_code VARCHAR(10) NOT NULL,
    chapter_description TEXT NOT NULL,
    state VARCHAR(100) NOT NULL,
    movement_value_inr_crore NUMERIC(24, 12), -- NULL preserved
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_trusted_state_chapter_outward UNIQUE (run_id, chapter_code, state)
);

CREATE INDEX IF NOT EXISTS idx_trusted_sco_run ON trusted_state_chapter_outward(run_id);
CREATE INDEX IF NOT EXISTS idx_trusted_sco_code_state ON trusted_state_chapter_outward(chapter_code, state);

-- Normalized 4: state_chapter_inward
CREATE TABLE IF NOT EXISTS trusted_state_chapter_inward (
    id BIGSERIAL PRIMARY KEY,
    run_id UUID NOT NULL REFERENCES pipeline_runs(run_id) ON DELETE CASCADE,
    chapter_code VARCHAR(10) NOT NULL,
    chapter_description TEXT NOT NULL,
    state VARCHAR(100) NOT NULL,
    movement_value_inr_crore NUMERIC(24, 12), -- NULL preserved
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_trusted_state_chapter_inward UNIQUE (run_id, chapter_code, state)
);

CREATE INDEX IF NOT EXISTS idx_trusted_sci_run ON trusted_state_chapter_inward(run_id);
CREATE INDEX IF NOT EXISTS idx_trusted_sci_code_state ON trusted_state_chapter_inward(chapter_code, state);

-- Normalized 5: state_chapter_internal
CREATE TABLE IF NOT EXISTS trusted_state_chapter_internal (
    id BIGSERIAL PRIMARY KEY,
    run_id UUID NOT NULL REFERENCES pipeline_runs(run_id) ON DELETE CASCADE,
    chapter_code VARCHAR(10) NOT NULL,
    chapter_description TEXT NOT NULL,
    state VARCHAR(100) NOT NULL,
    movement_value_inr_crore NUMERIC(24, 12), -- NULL preserved
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_trusted_state_chapter_internal UNIQUE (run_id, chapter_code, state)
);

CREATE INDEX IF NOT EXISTS idx_trusted_scint_run ON trusted_state_chapter_internal(run_id);
CREATE INDEX IF NOT EXISTS idx_trusted_scint_code_state ON trusted_state_chapter_internal(chapter_code, state);

-- ============================================================================
-- 4. VALIDATION RESULTS LAYER
-- ============================================================================

CREATE TABLE IF NOT EXISTS validation_results (
    validation_id BIGSERIAL PRIMARY KEY,
    run_id UUID REFERENCES pipeline_runs(run_id) ON DELETE CASCADE,
    check_id VARCHAR(50) NOT NULL,
    check_category VARCHAR(50) NOT NULL,
    check_name VARCHAR(255) NOT NULL,
    table_name VARCHAR(100) NOT NULL,
    status VARCHAR(20) NOT NULL, -- 'PASS', 'WARNING', 'FAIL'
    severity VARCHAR(20) NOT NULL, -- 'INFO', 'WARNING', 'ERROR', 'CRITICAL'
    expected_value TEXT,
    observed_value TEXT,
    difference NUMERIC(24, 12),
    affected_records INT NOT NULL DEFAULT 0,
    message TEXT NOT NULL,
    executed_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_val_results_run ON validation_results(run_id);
CREATE INDEX IF NOT EXISTS idx_val_results_status ON validation_results(status);
CREATE INDEX IF NOT EXISTS idx_val_results_category ON validation_results(check_category);

-- ============================================================================
-- 5. RECONCILIATION RESULTS LAYER (CROSS-TABLE ADVISORY AUDITS)
-- ============================================================================

CREATE TABLE IF NOT EXISTS reconciliation_results (
    reconciliation_id BIGSERIAL PRIMARY KEY,
    run_id UUID NOT NULL REFERENCES pipeline_runs(run_id) ON DELETE CASCADE,
    rule_code VARCHAR(50) NOT NULL,
    rule_category VARCHAR(50) NOT NULL DEFAULT 'DATA-OBSERVED',
    source_tables VARCHAR(255) NOT NULL,
    dimension VARCHAR(50) NOT NULL,
    entity VARCHAR(100) NOT NULL,
    expected_value NUMERIC(24, 12),
    observed_value NUMERIC(24, 12),
    absolute_difference NUMERIC(24, 12),
    relative_difference NUMERIC(24, 12),
    absolute_tolerance NUMERIC(24, 12),
    relative_tolerance NUMERIC(24, 12),
    status VARCHAR(20) NOT NULL, -- 'PASS', 'WARNING', 'UNRESOLVED', 'FAIL'
    severity VARCHAR(20) NOT NULL, -- 'INFO', 'WARNING', 'ERROR', 'CRITICAL'
    message TEXT NOT NULL,
    executed_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_rec_results_run ON reconciliation_results(run_id);
CREATE INDEX IF NOT EXISTS idx_rec_results_rule ON reconciliation_results(rule_code);
CREATE INDEX IF NOT EXISTS idx_rec_results_status ON reconciliation_results(status);
CREATE INDEX IF NOT EXISTS idx_rec_results_entity ON reconciliation_results(entity);

-- ============================================================================
-- 6. STATISTICAL ANALYSIS RESULTS LAYER (YEAR-OVER-YEAR COMPARISON)
-- ============================================================================

CREATE TABLE IF NOT EXISTS statistical_results (
    statistical_id BIGSERIAL PRIMARY KEY,
    run_id UUID NOT NULL REFERENCES pipeline_runs(run_id) ON DELETE CASCADE,
    comparison_year VARCHAR(20) NOT NULL DEFAULT '2023-24',
    reference_year VARCHAR(20) NOT NULL DEFAULT '2022-23',
    dimension VARCHAR(100) NOT NULL,
    metric VARCHAR(100) NOT NULL,
    test_method VARCHAR(50) NOT NULL, -- 'YOY_CHANGE', 'KS_TEST', 'PSI', 'CROSS_YEAR_OBSERVATION'
    sample_size_reference INT,
    sample_size_comparison INT,
    statistic NUMERIC(24, 12),
    p_value NUMERIC(24, 12),
    alpha NUMERIC(10, 6),
    psi_value NUMERIC(24, 12),
    psi_threshold NUMERIC(10, 6),
    status VARCHAR(50) NOT NULL, -- 'NO_MATERIAL_STATISTICAL_CHANGE', 'STATISTICALLY_DIFFERENT', 'INSUFFICIENT_DATA', 'NOT_APPLICABLE'
    interpretation TEXT NOT NULL,
    executed_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_stat_results_run ON statistical_results(run_id);
CREATE INDEX IF NOT EXISTS idx_stat_results_dim ON statistical_results(dimension);
CREATE INDEX IF NOT EXISTS idx_stat_results_method ON statistical_results(test_method);
CREATE INDEX IF NOT EXISTS idx_stat_results_status ON statistical_results(status);

-- ============================================================================
-- 7. INCIDENTS LAYER
-- ============================================================================

CREATE TABLE IF NOT EXISTS incidents (
    incident_id BIGSERIAL PRIMARY KEY,
    run_id UUID NOT NULL REFERENCES pipeline_runs(run_id) ON DELETE CASCADE,
    incident_type VARCHAR(100) NOT NULL,
    failure_type VARCHAR(100) NOT NULL DEFAULT 'DATA_INTEGRITY_FAILURE',
    severity VARCHAR(50) NOT NULL,
    status VARCHAR(50) NOT NULL DEFAULT 'OPEN',
    source_table VARCHAR(100),
    check_id VARCHAR(50),
    check_name VARCHAR(255),
    expected_value TEXT,
    observed_value TEXT,
    difference NUMERIC(24, 12),
    affected_record_count INT DEFAULT 0,
    title VARCHAR(255) NOT NULL,
    description TEXT NOT NULL,
    triggering_failures JSONB,
    detection_timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    resolution_timestamp TIMESTAMPTZ,
    resolved_at TIMESTAMPTZ,
    resolution_notes TEXT,
    alert_sent BOOLEAN NOT NULL DEFAULT FALSE,
    alert_sent_at TIMESTAMPTZ,
    CONSTRAINT uq_incidents_run_id UNIQUE (run_id)
);

CREATE INDEX IF NOT EXISTS idx_incidents_run ON incidents(run_id);
CREATE INDEX IF NOT EXISTS idx_incidents_status ON incidents(status);
CREATE INDEX IF NOT EXISTS idx_incidents_severity ON incidents(severity);
CREATE INDEX IF NOT EXISTS idx_incidents_check ON incidents(check_id);



