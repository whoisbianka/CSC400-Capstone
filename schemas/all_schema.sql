--Reset Database--
DROP TABLE IF EXISTS public.users CASCADE;
DROP TABLE IF EXISTS public.schools CASCADE;
DROP TABLE IF EXISTS public.majors CASCADE;
DROP TABLE IF EXISTS public.programs CASCADE;
DROP TABLE IF EXISTS public.adm_crit CASCADE;
DROP TABLE IF EXISTS public.cost_info CASCADE;
DROP TABLE IF EXISTS public.program_rank_crit CASCADE;
DROP TABLE IF EXISTS public.major_fav CASCADE;
DROP TABLE IF EXISTS public.major_rec CASCADE;
DROP TABLE IF EXISTS public.program_rec CASCADE;
DROP TABLE IF EXISTS public.program_fav CASCADE;
DROP TABLE IF EXISTS public.chatlog CASCADE;
DROP TABLE IF EXISTS public.major_info CASCADE;
DROP TABLE IF EXISTS public.keywords CASCADE;
DROP TABLE IF EXISTS public.major_keywords CASCADE;
DROP TABLE IF EXISTS public.user_keywords CASCADE;

--Create Tables--
CREATE TABLE public.users(
    id SERIAL PRIMARY KEY,
    fname VARCHAR(50) NOT NULL,
    lname VARCHAR(50) NOT NULL,
    email VARCHAR(100) UNIQUE NOT NULL,
    google_auth TEXT NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE public.schools(
    id SERIAL PRIMARY KEY,
    unitid INT UNIQUE NOT NULL,
    opeid6 INT NOT NULL,
    instnm TEXT NOT NULL,
    ug12mn INT,
    city TEXT,
    stabbr VARCHAR(3),
    longitude NUMERIC(9,6),
    latitude NUMERIC(9,6),
    iclevel INT,
    insturl TEXT
);

CREATE TABLE public.majors(
    id SERIAL PRIMARY KEY,
    cipcode INT UNIQUE NOT NULL,
    cipdesc TEXT NOT NULL
);

CREATE TABLE public.major_info(
    id SERIAL PRIMARY KEY,
    cipcode INT UNIQUE NOT NULL,
    mdn_earnings INT,
    major_description TEXT,
    description_source TEXT,
    CONSTRAINT fk_cipcode FOREIGN KEY (cipcode) REFERENCES public.majors(cipcode)
);

CREATE TABLE public.keywords(
    id SERIAL PRIMARY KEY,
    keyword TEXT
);

CREATE TABLE public.major_keywords(
    id SERIAL PRIMARY KEY,
    cipcode INT NOT NULL,
    keyword_id INT NOT NULL,
    CONSTRAINT fk_major_id FOREIGN KEY (cipcode) REFERENCES public.majors(cipcode),
    CONSTRAINT fk_kwd_id FOREIGN KEY (keyword_id) REFERENCES public.keywords(id)
);

CREATE TABLE public.programs(
    id SERIAL PRIMARY KEY,
    program_id INT UNIQUE NOT NULL,
    unitid INT NOT NULL,
	cipcode INT NOT NULL,
    credlev INT,
    CONSTRAINT fk_unitid FOREIGN KEY (unitid) REFERENCES public.schools(unitid),
    CONSTRAINT fk_cip FOREIGN KEY (cipcode) REFERENCES public.majors(cipcode)
);

CREATE TABLE public.adm_crit(
    id SERIAL PRIMARY KEY,
    unitid INT UNIQUE NOT NULL,
    adm_rate DECIMAL(6,4),
    satmt25 INT,
    satmt75 INT,
    satvr25 INT,
    satvr75 INT,
    satwr25 INT,
    satwr75 INT,
    acten25 INT,
    acten75 INT,
    actmt25 INT,
    actmt75 INT,
    actwr25 INT,
    actwr75 INT,
    CONSTRAINT fk_unitid FOREIGN KEY (unitid) REFERENCES public.schools(unitid)
);

CREATE TABLE public.cost_info(
    id SERIAL PRIMARY KEY,
    unitid INT UNIQUE NOT NULL,
    npt4 INT,
    npt41 INT,
    npt42 INT,
    npt43 INT,
    npt44 INT,
    npt45 INT,
    tuitionfee_in INT,
    tuitionfee_out INT,
    CONSTRAINT fk_unitid FOREIGN KEY (unitid) REFERENCES public.schools(unitid)
);

CREATE TABLE program_rank_crit(
    id SERIAL PRIMARY KEY,
	program_id INT UNIQUE NOT NULL,
    earn_count_wne_4yr_nat INT,
    earn_mdn_4yr_nat INT,
    CONSTRAINT fk_prog_id FOREIGN KEY(program_id) REFERENCES public.programs(program_id)
);

CREATE TABLE public.major_rec(
    id SERIAL PRIMARY KEY,
	user_id INT NOT NULL,
	cipcode INT NOT NULL,
    CONSTRAINT fk_user FOREIGN KEY(user_id) REFERENCES public.users(id) ON DELETE CASCADE,
    CONSTRAINT fk_major FOREIGN KEY(cipcode) REFERENCES public.majors(cipcode)
);

CREATE TABLE public.program_rec(
    id SERIAL PRIMARY KEY,
	user_id INT NOT NULL,
	program_id INT NOT NULL,
    CONSTRAINT fk_user FOREIGN KEY(user_id) REFERENCES public.users(id) ON DELETE CASCADE,
    CONSTRAINT fk_program FOREIGN KEY(program_id) REFERENCES public.programs(program_id)
);

CREATE TABLE public.chatlog(
    id SERIAL PRIMARY KEY,
	user_id INT NOT NULL,
    chat_text TEXT,
    isUser BOOLEAN NOT NULL,
    createdAt TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_user FOREIGN KEY(user_id) REFERENCES public.users(id) ON DELETE CASCADE
);

CREATE TABLE public.major_fav(
    id SERIAL PRIMARY KEY,
	user_id INT NOT NULL,
	cipcode INT NOT NULL,
    CONSTRAINT fk_user FOREIGN KEY(user_id) REFERENCES public.users(id) ON DELETE CASCADE,
    CONSTRAINT fk_major FOREIGN KEY(cipcode) REFERENCES public.majors(cipcode)
);

CREATE TABLE public.program_fav(
    id SERIAL PRIMARY KEY,
	user_id INT NOT NULL,
	program_id INT NOT NULL,
    CONSTRAINT fk_user FOREIGN KEY(user_id) REFERENCES public.users(id) ON DELETE CASCADE,
    CONSTRAINT fk_program FOREIGN KEY(program_id) REFERENCES public.programs(program_id)
);

CREATE TABLE public.user_keywords(
    id SERIAL PRIMARY KEY,
    user_id INT NOT NULL,
    keyword_id INT NOT NULL,
    CONSTRAINT fk_user_id FOREIGN KEY (user_id) REFERENCES public.users(id),
    CONSTRAINT fk_kwd_id FOREIGN KEY (keyword_id) REFERENCES public.keywords(id)
);


--Create Role for Python_connection--
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_roles WHERE rolname = 'app_runtime'
    ) THEN
        CREATE ROLE app_runtime NOLOGIN;
    END IF;
END
$$;

GRANT USAGE ON SCHEMA public TO app_runtime;

GRANT SELECT ON TABLE
    public.schools,
    public.majors,
    public.major_info,
    public.programs,
    public.cost_info,
    public.adm_crit,
    public.program_rank_crit,
    public.keywords,
    public.major_keywords
TO app_runtime;

GRANT SELECT, INSERT, UPDATE, DELETE ON TABLE
    public.users,
    public.major_fav,
    public.program_fav,
    public.major_rec,
    public.program_rec,
    public.chatlog,
    public.user_keywords
TO app_runtime;

GRANT USAGE ON SEQUENCE
    public.users_id_seq,
    public.major_fav_id_seq,
    public.program_fav_id_seq,
    public.major_rec_id_seq,
    public.program_rec_id_seq,
    public.chatlog_id_seq,
    public.user_keywords_id_seq
TO app_runtime;

GRANT app_runtime TO python_connection;