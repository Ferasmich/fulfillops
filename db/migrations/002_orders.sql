CREATE TABLE orders (
    id UUID PRIMARY KEY,
    customer_id TEXT NOT NULL CHECK (length(customer_id) BETWEEN 1 AND 64),
    status TEXT NOT NULL DEFAULT 'queued'
        CHECK (status IN ('queued', 'processing', 'completed', 'failed')),
    total_cents BIGINT NOT NULL CHECK (total_cents >= 0),
    created_at TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp(),
    completed_at TIMESTAMPTZ
);
CREATE TABLE order_requests (
    key TEXT PRIMARY KEY CHECK (length(key) BETWEEN 8 AND 128 AND key !~ '[^ -~]'),
    canonical_payload JSONB NOT NULL,
    order_id UUID NOT NULL UNIQUE REFERENCES orders(id) DEFERRABLE INITIALLY DEFERRED,
    created_at TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp()
);
CREATE TABLE order_items (
    order_id UUID REFERENCES orders(id),
    sku TEXT REFERENCES products(sku),
    quantity INTEGER NOT NULL CHECK (quantity BETWEEN 1 AND 200),
    unit_price_cents INTEGER NOT NULL CHECK (unit_price_cents > 0),
    PRIMARY KEY (order_id, sku)
);
