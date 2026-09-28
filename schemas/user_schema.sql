DROP TABLE IF EXISTS users CASCADE;
DROP TABLE IF EXISTS school_fav CASCADE;
DROP TABLE IF EXISTS major_fav CASCADE;
DROP TABLE IF EXISTS major_rec CASCADE;
DROP TABLE IF EXISTS school_rec CASCADE;
DROP TABLE IF EXISTS chatlog CASCADE;

CREATE TABLE users(
    user_id SERIAL PRIMARY KEY,
    fname VARCHAR(50) NOT NULL,
    lname VARCHAR(50) NOT NULL,
    email VARCHAR(100) UNIQUE NOT NULL,
    google_auth TEXT NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE major_rec(
    mrec_id SERIAL PRIMARY KEY,
	user_id INT NOT NULL,
	major_id INT NOT NULL,
    CONSTRAINT fk_user FOREIGN KEY(user_id) REFERENCES users(user_id) ON DELETE CASCADE,
    CONSTRAINT fk_major FOREIGN KEY(major_id) REFERENCES majors(major_id)
);

CREATE TABLE school_rec(
    srec_id SERIAL PRIMARY KEY,
	user_id INT NOT NULL,
	school_id INT NOT NULL,
    CONSTRAINT fk_user FOREIGN KEY(user_id) REFERENCES users(user_id) ON DELETE CASCADE,
    CONSTRAINT fk_school FOREIGN KEY(school_id) REFERENCES schools(school_id)
);

CREATE TABLE chatlog(
    chat_id SERIAL PRIMARY KEY,
	user_id INT NOT NULL,
    chat_text TEXT,
    isUser BOOLEAN NOT NULL,
    createdAt TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_user FOREIGN KEY(user_id) REFERENCES users(user_id) ON DELETE CASCADE
);

CREATE TABLE major_fav(
    mfav_id SERIAL PRIMARY KEY,
	user_id INT NOT NULL,
	major_id INT NOT NULL,
    CONSTRAINT fk_user FOREIGN KEY(user_id) REFERENCES users(user_id) ON DELETE CASCADE,
    CONSTRAINT fk_major FOREIGN KEY(major_id) REFERENCES majors(major_id)
);

CREATE TABLE school_fav(
    sfav_id SERIAL PRIMARY KEY,
	user_id INT NOT NULL,
	school_id INT NOT NULL,
    CONSTRAINT fk_user FOREIGN KEY(user_id) REFERENCES users(user_id) ON DELETE CASCADE,
    CONSTRAINT fk_school FOREIGN KEY(school_id) REFERENCES schools(school_id)
);