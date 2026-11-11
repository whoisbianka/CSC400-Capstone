DROP TABLE IF EXISTS public.users CASCADE;
DROP TABLE IF EXISTS public.major_fav CASCADE;
DROP TABLE IF EXISTS public.major_rec CASCADE;
DROP TABLE IF EXISTS public.program_rec CASCADE;
DROP TABLE IF EXISTS public.program_fav CASCADE;
DROP TABLE IF EXISTS public.chatlog CASCADE;
DROP TABLE IF EXISTS public.user_keywords CASCADE;
DROP TABLE IF EXISTS public.user_info CASCADE;
DROP TABLE IF EXISTS public.guest_sessions CASCADE;
DROP TABLE IF EXISTS public.program_search CASCADE;
DROP TABLE IF EXISTS public.major_search CASCADE;

CREATE TABLE public.users(
    id SERIAL PRIMARY KEY,
    clerk_user_id TEXT UNIQUE NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE public.program_search(
    id SERIAL PRIMARY KEY,
    user_id INT NOT NULL,
    sort_order TEXT NOT NULL,
    search_text TEXT,
    majors TEXT[],
    colleges TEXT[],
    states TEXT[],
    degrees TEXT,
    net_price_max INT,
    tuition_in_max INT,
    tuition_out_max INT,
    acceptance_min DECIMAL(7,4)
        CHECK (acceptance_min BETWEEN 0 AND 100),
    acceptance_max DECIMAL(7,4)
        CHECK (acceptance_max BETWEEN 0 AND 100),
    satmt INT,
    satvr INT,
    satwr INT,
    actmt INT,
    acten INT,
    actwr INT,
    created_at TIMESTAMPTZ,
    CONSTRAINT fk_user_id FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE,
    CONSTRAINT uq_prog_search UNIQUE NULLS NOT DISTINCT (
        user_id, majors, colleges, states, degrees,
        net_price_max, tuition_in_max, tuition_out_max,
        acceptance_min, acceptance_max,
        satmt, satvr, satwr, actmt, acten, actwr,
        search_text, sort_order
    ),
    CONSTRAINT ck_search_acceptance_range
        CHECK (
            acceptance_min IS NULL
            OR acceptance_max IS NULL
            OR acceptance_min <= acceptance_max
        )
);

CREATE TABLE public.major_search(
    id SERIAL PRIMARY KEY,
    user_id INT NOT NULL,
    sort_order TEXT NOT NULL,
    search_text TEXT,
    majors TEXT[],
    earnings_min INT,
    saved BOOLEAN,
    recs BOOLEAN,
    created_at TIMESTAMPTZ,
    CONSTRAINT fk_maj_search_uid FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE,
    CONSTRAINT uq_maj_search UNIQUE NULLS NOT DISTINCT (
        user_id, majors, earnings_min, saved, recs,
        search_text, sort_order
    )
);

CREATE TABLE public.major_rec(
    id SERIAL PRIMARY KEY,
	user_id INT NOT NULL,
	cipcode INT NOT NULL,
    matching_keywords INT NOT NULL,
    CONSTRAINT fk_user FOREIGN KEY(user_id) REFERENCES public.users(id) ON DELETE CASCADE,
    CONSTRAINT fk_major FOREIGN KEY(cipcode) REFERENCES public.majors(cipcode),
    CONSTRAINT uq_uid_cip_mr UNIQUE (user_id, cipcode)
);

CREATE TABLE public.program_rec(
    id SERIAL PRIMARY KEY,
	user_id INT NOT NULL,
	program_id INT NOT NULL,
    CONSTRAINT fk_user FOREIGN KEY(user_id) REFERENCES public.users(id) ON DELETE CASCADE,
    CONSTRAINT fk_program FOREIGN KEY(program_id) REFERENCES public.programs(program_id),
    CONSTRAINT uq_uid_pid_pr UNIQUE (user_id, program_id)
);

CREATE TABLE public.chatlog(
    id SERIAL PRIMARY KEY,
	user_id INT NOT NULL,
    content TEXT NOT NULL,
    sender TEXT NOT NULL CHECK(sender IN('user','assistant')),
    createdAt TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_user FOREIGN KEY(user_id) REFERENCES public.users(id) ON DELETE CASCADE
);

CREATE TABLE public.major_fav(
    id SERIAL PRIMARY KEY,
	user_id INT NOT NULL,
	cipcode INT NOT NULL,
    CONSTRAINT fk_user FOREIGN KEY(user_id) REFERENCES public.users(id) ON DELETE CASCADE,
    CONSTRAINT fk_major FOREIGN KEY(cipcode) REFERENCES public.majors(cipcode),
    CONSTRAINT uq_uid_cip_mf UNIQUE (user_id, cipcode)
);

CREATE TABLE public.program_fav(
    id SERIAL PRIMARY KEY,
	user_id INT NOT NULL,
	program_id INT NOT NULL,
    CONSTRAINT fk_user FOREIGN KEY(user_id) REFERENCES public.users(id) ON DELETE CASCADE,
    CONSTRAINT fk_program FOREIGN KEY(program_id) REFERENCES public.programs(program_id),
    CONSTRAINT uq_uid_pid_pf UNIQUE (user_id, program_id)
);

CREATE TABLE public.user_keywords(
    id SERIAL PRIMARY KEY,
    user_id INT NOT NULL,
    keyword_id INT NOT NULL,
    evidence TEXT NOT NULL,
    CONSTRAINT fk_user_id FOREIGN KEY (user_id) REFERENCES public.users(id) ON DELETE CASCADE,
    CONSTRAINT fk_kwd_id FOREIGN KEY (keyword_id) REFERENCES public.keywords(id),
    CONSTRAINT uq_uid_kwd UNIQUE (user_id, keyword_id)
);

CREATE TABLE public.guest_sessions (
    guest_id TEXT PRIMARY KEY,

    state JSONB NOT NULL DEFAULT '{}'::jsonb,
    version INTEGER NOT NULL DEFAULT 0,

    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMPTZ NOT NULL
        DEFAULT (CURRENT_TIMESTAMP + INTERVAL '24 hours'),

    CHECK (jsonb_typeof(state) = 'object')
);

CREATE INDEX guest_sessions_expires_at_idx
    ON public.guest_sessions (expires_at);
