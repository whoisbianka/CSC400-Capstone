import pandas as pd
from sqlalchemy import create_engine, text
import numpy as np
import os
from dotenv import load_dotenv
from database_connection import connect_with_connector, close_connector
import sqlparse

DATABASE_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_DIR = os.path.dirname(DATABASE_DIR)

DATA_DIR = os.path.join(PROJECT_DIR, "data")
TABLES_DIR = os.path.join(PROJECT_DIR, "tables")
SEED_DIR = os.path.join(DATABASE_DIR, "seed_data")

def main():
    load_dotenv()
    engine=connect_with_connector(admin=True)

    schools_df=pd.read_csv(os.path.join(SEED_DIR,"schools.csv"), low_memory=False)
    program_rank_crit=pd.read_csv(os.path.join(SEED_DIR,"program_rank_crit.csv"), low_memory=False)
    majors_df=pd.read_csv(os.path.join(SEED_DIR,"majors.csv"), low_memory=False)
    programs_df=pd.read_csv(os.path.join(SEED_DIR,"programs.csv"), low_memory=False)
    cost_info_df=pd.read_csv(os.path.join(SEED_DIR,"cost_info.csv"), low_memory=False)
    adm_crit_df=pd.read_csv(os.path.join(SEED_DIR,"adm_crit.csv"), low_memory=False)
    major_info_df=pd.read_csv(os.path.join(SEED_DIR,"major_info.csv"),low_memory=False)
    careers_df=pd.read_csv(os.path.join(SEED_DIR,"careers.csv"), low_memory=False)
    kwd_df=pd.read_csv(os.path.join(SEED_DIR,"kwd_list.csv"),low_memory=False)
    major_kwds_df=pd.read_csv(os.path.join(SEED_DIR,"major_keywords.csv"),low_memory=False)

    upload=[
        ("schools", schools_df),
        ("majors", majors_df),
        ("programs", programs_df),
        ("adm_crit",adm_crit_df),
        ("cost_info",cost_info_df),
        ("program_rank_crit",program_rank_crit),
        ("major_info",major_info_df),
        ("keywords",kwd_df),
        ("major_keywords",major_kwds_df),
        ("careers",careers_df)
    ]

    try:
        if os.environ["DATABASE_MODE"]=="cloud":
            with engine.begin() as connection:
                with open(os.path.join(DATABASE_DIR,"schemas","all_schema.sql"), "r") as f:
                    schema=f.read()
                    for statement in sqlparse.split(schema):
                        if statement.strip():
                            connection.execute(text(statement))

        with engine.begin() as connection:
            for table_name, df in upload:
                df.to_sql(
                    name=table_name,
                    schema="public",
                    con=connection,
                    if_exists="append",
                    index=False,
                    chunksize=1000,
                    method="multi",
                )
    finally:
        engine.dispose()
        close_connector(admin=True)


if __name__ == "__main__":
    main()