-- PostgreSQL Schema Definitions (SQL DDL) for AI Software Factory

-- Create issues table
CREATE TABLE IF NOT EXISTS issues (
    issue_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    repo_url TEXT NOT NULL,
    issue_title TEXT NOT NULL,
    issue_description TEXT NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Create fsm_states ledger table
CREATE TABLE IF NOT EXISTS fsm_states (
    state_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    issue_id UUID REFERENCES issues(issue_id) ON DELETE CASCADE,
    state_name VARCHAR(50) NOT NULL,
    retry_count INT DEFAULT 0,
    payload JSONB,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Create patches table
CREATE TABLE IF NOT EXISTS patches (
    patch_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    issue_id UUID REFERENCES issues(issue_id) ON DELETE CASCADE,
    patch_diff TEXT NOT NULL,
    is_compiled BOOLEAN DEFAULT FALSE,
    passes_lint BOOLEAN DEFAULT FALSE,
    passes_tests BOOLEAN DEFAULT FALSE,
    mutation_score FLOAT DEFAULT 0.0,
    risk_score FLOAT DEFAULT 1.0,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Create human_reviews table
CREATE TABLE IF NOT EXISTS human_reviews (
    review_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    issue_id UUID REFERENCES issues(issue_id) ON DELETE CASCADE,
    patch_id UUID REFERENCES patches(patch_id) ON DELETE CASCADE,
    reviewer_name VARCHAR(100),
    decision VARCHAR(20) CHECK (decision IN ('APPROVED', 'REJECTED')),
    comments TEXT,
    reviewed_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Index for performance on issue queries
CREATE INDEX IF NOT EXISTS idx_fsm_states_issue_id ON fsm_states(issue_id);
CREATE INDEX IF NOT EXISTS idx_patches_issue_id ON patches(issue_id);
CREATE INDEX IF NOT EXISTS idx_human_reviews_issue_id ON human_reviews(issue_id);
