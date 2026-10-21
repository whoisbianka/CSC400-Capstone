-- Run as the owner of public.majors (or a database administrator).
-- Additive: this does not drop tables or modify existing saved selections.
BEGIN;

CREATE TABLE IF NOT EXISTS public.saved_majors (
    clerk_user_id TEXT NOT NULL,
    cipcode INTEGER NOT NULL REFERENCES public.majors(cipcode),
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (clerk_user_id, cipcode)
);

-- The application only needs to read, save, and remove its account-owned rows.
-- Keep CREATE and REFERENCES privileges with the database owner.
GRANT SELECT, INSERT, DELETE ON TABLE public.saved_majors TO app_runtime;

COMMIT;
