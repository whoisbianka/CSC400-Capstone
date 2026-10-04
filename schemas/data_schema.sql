--Reset Database--
DROP TABLE IF EXISTS schools CASCADE;
DROP TABLE IF EXISTS majors CASCADE;
DROP TABLE IF EXISTS programs CASCADE;
DROP TABLE IF EXISTS adm_crit CASCADE;
DROP TABLE IF EXISTS cost_info CASCADE;
DROP TABLE IF EXISTS program_rank_crit CASCADE;
DROP TABLE IF EXISTS major_info CASCADE;
DROP TABLE IF EXISTS keywords CASCADE;
DROP TABLE IF EXISTS major_keywords CASCADE;

--Create Tables--
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

CREATE TABLE major_info(
    id SERIAL PRIMARY KEY,
    cipcode INT UNIQUE NOT NULL,
    mdn_earnings INT,
    major_description TEXT,
    description_source TEXT,
    CONSTRAINT fk_cipcode FOREIGN KEY (cipcode) REFERENCES majors(cipcode)
);

CREATE TABLE keywords(
    id SERIAL PRIMARY KEY,
    keyword TEXT
);

CREATE TABLE major_keywords(
    id SERIAL PRIMARY KEY,
    cipcode INT NOT NULL,
    keyword_id INT NOT NULL,
    CONSTRAINT fk_major_id FOREIGN KEY (cipcode) REFERENCES majors(cipcode),
    CONSTRAINT fk_kwd_id FOREIGN KEY (keyword_id) REFERENCES keywords(id)
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