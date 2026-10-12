DROP TABLE IF EXISTS public.users CASCADE;
DROP TABLE IF EXISTS public.major_fav CASCADE;
DROP TABLE IF EXISTS public.major_rec CASCADE;
DROP TABLE IF EXISTS public.program_rec CASCADE;
DROP TABLE IF EXISTS public.program_fav CASCADE;
DROP TABLE IF EXISTS public.chatlog CASCADE;
DROP TABLE IF EXISTS public.user_keywords CASCADE;

CREATE TABLE public.users(
    id SERIAL PRIMARY KEY,
    fname VARCHAR(50) NOT NULL,
    lname VARCHAR(50) NOT NULL,
    email VARCHAR(100) UNIQUE NOT NULL,
    google_auth TEXT NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
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