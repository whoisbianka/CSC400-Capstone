DROP TABLE IF EXISTS users CASCADE;
DROP TABLE IF EXISTS major_fav CASCADE;
DROP TABLE IF EXISTS major_rec CASCADE;
DROP TABLE IF EXISTS program_rec CASCADE;
DROP TABLE IF EXISTS program_fav CASCADE;
DROP TABLE IF EXISTS chatlog CASCADE;
DROP TABLE IF EXISTS user_keywords CASCADE;

CREATE TABLE users(
    id SERIAL PRIMARY KEY,
    fname VARCHAR(50) NOT NULL,
    lname VARCHAR(50) NOT NULL,
    email VARCHAR(100) UNIQUE NOT NULL,
    google_auth TEXT NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE major_rec(
    id SERIAL PRIMARY KEY,
	user_id INT NOT NULL,
	cipcode INT NOT NULL,
    CONSTRAINT fk_user FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE,
    CONSTRAINT fk_major FOREIGN KEY(cipcode) REFERENCES majors(cipcode)
);

CREATE TABLE program_rec(
    id SERIAL PRIMARY KEY,
	user_id INT NOT NULL,
	program_id INT NOT NULL,
    CONSTRAINT fk_user FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE,
    CONSTRAINT fk_program FOREIGN KEY(program_id) REFERENCES programs(program_id)
);

CREATE TABLE chatlog(
    id SERIAL PRIMARY KEY,
	user_id INT NOT NULL,
    chat_text TEXT,
    isUser BOOLEAN NOT NULL,
    createdAt TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_user FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
);

CREATE TABLE major_fav(
    id SERIAL PRIMARY KEY,
	user_id INT NOT NULL,
	cipcode INT NOT NULL,
    CONSTRAINT fk_user FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE,
    CONSTRAINT fk_major FOREIGN KEY(cipcode) REFERENCES majors(cipcode)
);

CREATE TABLE program_fav(
    id SERIAL PRIMARY KEY,
	user_id INT NOT NULL,
	program_id INT NOT NULL,
    CONSTRAINT fk_user FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE,
    CONSTRAINT fk_program FOREIGN KEY(program_id) REFERENCES programs(program_id)
);

CREATE TABLE user_keywords(
    id SERIAL PRIMARY KEY,
    user_id INT NOT NULL,
    keyword_id INT NOT NULL,
    CONSTRAINT fk_user_id FOREIGN KEY (user_id) REFERENCES users(id),
    CONSTRAINT fk_kwd_id FOREIGN KEY (keyword_id) REFERENCES keywords(id)
);