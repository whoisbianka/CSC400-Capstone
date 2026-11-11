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
    public.major_keywords,
    public.careers
TO app_runtime;

GRANT SELECT, INSERT, UPDATE, DELETE ON TABLE
    public.users,
    public.major_fav,
    public.program_fav,
    public.major_rec,
    public.chatlog,
    public.user_keywords,
    public.guest_sessions,
    public.major_search,
    public.program_search
TO app_runtime;

GRANT USAGE ON SEQUENCE
    public.users_id_seq,
    public.major_fav_id_seq,
    public.program_fav_id_seq,
    public.major_rec_id_seq,
    public.chatlog_id_seq,
    public.user_keywords_id_seq,
    public.major_search_id_seq,
    public.program_search_id_seq
TO app_runtime;

GRANT app_runtime TO python_connection;