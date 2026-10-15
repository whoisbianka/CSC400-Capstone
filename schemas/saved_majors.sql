-- Optional manual setup; Flask also creates this table on first authenticated use.
CREATE TABLE IF NOT EXISTS saved_majors (
    clerk_user_id TEXT NOT NULL,
    cipcode INTEGER NOT NULL REFERENCES majors(cipcode),
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (clerk_user_id, cipcode)
);
