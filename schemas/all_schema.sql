--Reset Database--
DROP TABLE IF EXISTS users CASCADE;
DROP TABLE IF EXISTS schools CASCADE;
DROP TABLE IF EXISTS majors CASCADE;
DROP TABLE IF EXISTS programs CASCADE;
DROP TABLE IF EXISTS adm_crit CASCADE;
DROP TABLE IF EXISTS cost_info CASCADE;
DROP TABLE IF EXISTS program_rank_crit CASCADE;
DROP TABLE IF EXISTS school_fav CASCADE;
DROP TABLE IF EXISTS major_fav CASCADE;
DROP TABLE IF EXISTS major_rec CASCADE;
DROP TABLE IF EXISTS school_rec CASCADE;
DROP TABLE IF EXISTS chatlog CASCADE;

--Create Tables--
CREATE TABLE users(
    id SERIAL PRIMARY KEY,
    fname VARCHAR(50) NOT NULL,
    lname VARCHAR(50) NOT NULL,
    email VARCHAR(100) UNIQUE NOT NULL,
    google_auth TEXT NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE schools(
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

CREATE TABLE majors(
    id SERIAL PRIMARY KEY,
    cipcode INT UNIQUE NOT NULL,
    cipdesc TEXT NOT NULL
);

CREATE TABLE programs(
    id SERIAL PRIMARY KEY,
    program_id INT UNIQUE NOT NULL,
    unitid INT NOT NULL,
	cipcode INT NOT NULL,
    credlev INT,
    CONSTRAINT fk_unitid FOREIGN KEY (unitid) REFERENCES schools(unitid),
    CONSTRAINT fk_cip FOREIGN KEY (cipcode) REFERENCES majors(cipcode)
);

CREATE TABLE adm_crit(
    id SERIAL PRIMARY KEY,
    unitid INT NOT NULL,
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
    CONSTRAINT fk_unitid FOREIGN KEY (unitid) REFERENCES schools(unitid)
);

CREATE TABLE cost_info(
    id SERIAL PRIMARY KEY,
    unitid INT NOT NULL,
    npt4 INT,
    npt41 INT,
    npt42 INT,
    npt43 INT,
    npt44 INT,
    npt45 INT,
    tuitionfee_in INT,
    tuitionfee_out INT,
    CONSTRAINT fk_unitid FOREIGN KEY (unitid) REFERENCES schools(unitid)
);

CREATE TABLE program_rank_crit(
    id SERIAL PRIMARY KEY,
	program_id INT NOT NULL,
    earn_count_wne_4yr_nat INT,
    earn_mdn_4yr_nat INT,
    CONSTRAINT fk_prog_id FOREIGN KEY(program_id) REFERENCES programs(program_id)
);

CREATE TABLE major_rec(
    id SERIAL PRIMARY KEY,
	user_id INT NOT NULL,
	major_id INT NOT NULL,
    CONSTRAINT fk_user FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE,
    CONSTRAINT fk_major FOREIGN KEY(major_id) REFERENCES majors(id)
);

CREATE TABLE school_rec(
    id SERIAL PRIMARY KEY,
	user_id INT NOT NULL,
	school_id INT NOT NULL,
    CONSTRAINT fk_user FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE,
    CONSTRAINT fk_school FOREIGN KEY(school_id) REFERENCES schools(id)
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
	major_id INT NOT NULL,
    CONSTRAINT fk_user FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE,
    CONSTRAINT fk_major FOREIGN KEY(major_id) REFERENCES majors(id)
);

CREATE TABLE school_fav(
    id SERIAL PRIMARY KEY,
	user_id INT NOT NULL,
	school_id INT NOT NULL,
    CONSTRAINT fk_user FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE,
    CONSTRAINT fk_school FOREIGN KEY(school_id) REFERENCES schools(id)
);