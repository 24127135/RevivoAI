CREATE EXTENSION IF NOT EXISTS pgcrypto;

CREATE TABLE IF NOT EXISTS execution_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id UUID NOT NULL REFERENCES "Session"(session_id) ON DELETE CASCADE,
    iteration INT NOT NULL DEFAULT 1,
    status VARCHAR NOT NULL,
    patched_code TEXT,
    error_trace TEXT,
    llm_metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);