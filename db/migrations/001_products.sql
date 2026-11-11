CREATE TABLE products (
    sku TEXT PRIMARY KEY,
    unit_price_cents INTEGER NOT NULL CHECK (unit_price_cents > 0),
    available INTEGER NOT NULL CHECK (available >= 0)
);
