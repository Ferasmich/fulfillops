CREATE TABLE jobs (
    order_id UUID PRIMARY KEY REFERENCES orders(id),
    state TEXT NOT NULL DEFAULT 'queued'
        CHECK (state IN ('queued', 'processing', 'completed', 'failed')),
    attempts INTEGER NOT NULL DEFAULT 0 CHECK (attempts >= 0),
    max_attempts INTEGER NOT NULL DEFAULT 5 CHECK (max_attempts > 0),
    available_at TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp(),
    lease_until TIMESTAMPTZ,
    claim_token UUID,
    last_error_code TEXT,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp(),
    CHECK (attempts <= max_attempts),
    CHECK ((state = 'processing' AND claim_token IS NOT NULL AND lease_until IS NOT NULL)
        OR (state <> 'processing' AND claim_token IS NULL AND lease_until IS NULL))
);
CREATE INDEX jobs_due ON jobs(available_at) WHERE state = 'queued';
CREATE INDEX jobs_expired ON jobs(lease_until) WHERE state = 'processing';
CREATE TABLE job_attempts (
    order_id UUID REFERENCES jobs(order_id),
    attempt_number INTEGER NOT NULL CHECK (attempt_number > 0),
    claim_token UUID NOT NULL UNIQUE,
    started_at TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp(),
    ended_at TIMESTAMPTZ,
    outcome TEXT NOT NULL CHECK (outcome IN
        ('claimed', 'completed', 'retry', 'failed', 'lease_expired')),
    error_code TEXT,
    PRIMARY KEY (order_id, attempt_number)
);
CREATE TABLE completion_receipts (
    order_id UUID PRIMARY KEY REFERENCES orders(id),
    completed_at TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp()
);
