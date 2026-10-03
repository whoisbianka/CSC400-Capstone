import pandas as pd
from sqlalchemy import create_engine, text
import numpy as np
import os
from dotenv import load_dotenv
from cloud_sql_connection import connect_with_connector, close_connector

load_dotenv()
engine=connect_with_connector()

#--FORMAT PANDAS DATAFRAMES AND CSV FILES--
p_df=pd.read_csv("./data/Most-Recent-Cohorts-Field-of-Study.csv")
p_df=p_df[['UNITID','OPEID6','INSTNM','CIPCODE','CIPDESC','CREDLEV','EARN_COUNT_WNE_4YR_NAT','EARN_MDN_4YR_NAT']].copy()
p_df=p_df[(((p_df['CREDLEV']==3) | (p_df['CREDLEV']==2)))]
p_df['EARN_COUNT_WNE_4YR_NAT']=p_df['EARN_COUNT_WNE_4YR_NAT'].replace('PS',np.nan)
p_df['EARN_MDN_4YR_NAT']=p_df['EARN_MDN_4YR_NAT'].replace('PS',np.nan)
p_df.dropna(subset=['EARN_MDN_4YR_NAT'],inplace=True)
p_df.dropna(subset=['EARN_COUNT_WNE_4YR_NAT'],inplace=True)


institution_df=pd.read_csv("./data/Most-Recent-Cohorts-Institution.csv", low_memory=False)

#Combine NPT_PUB and NPT_PRIV columns to just NPT Column
npt_data=pd.DataFrame({
    'NPT4':institution_df['NPT4_PUB'].combine_first(institution_df['NPT4_PRIV']),
    'NPT41':institution_df['NPT41_PUB'].combine_first(institution_df['NPT41_PRIV']),
    'NPT42':institution_df['NPT42_PUB'].combine_first(institution_df['NPT42_PRIV']),
    'NPT43':institution_df['NPT43_PUB'].combine_first(institution_df['NPT43_PRIV']),
    'NPT44':institution_df['NPT44_PUB'].combine_first(institution_df['NPT44_PRIV']),
    'NPT45':institution_df['NPT45_PUB'].combine_first(institution_df['NPT45_PRIV'])
})

#Select columns to keep in the database
i_df=institution_df[['UNITID','OPEID6','INSTNM','LATITUDE','LONGITUDE',
                    'CITY','STABBR','ADM_RATE','UG12MN','INSTURL',
                   'SATVR25','SATVR75','SATMT25','SATMT75','SATWR25','SATWR75',
                   'ACTEN25','ACTEN75','ACTMT25','ACTMT75','ACTWR25','ACTWR75',
                   'TUITIONFEE_IN','TUITIONFEE_OUT','ICLEVEL',
                   'RET_FT4_POOLED','RET_FTL4_POOLED','MD_EARN_WNE_P6']].copy()

i_df=pd.concat([i_df,npt_data], axis=1)

i_df.dropna(subset='UG12MN', inplace=True)

i_df=i_df[i_df['UNITID'].isin(p_df['UNITID'])]
p_df=p_df[p_df['UNITID'].isin(i_df['UNITID'])]


p_df.to_csv("./data/FieldOfStudy.csv",index=False)
i_df.to_csv("./data/Institution.csv", index=False)
#-----

prog_df=pd.read_csv("./data/FieldOfStudy.csv")
institution_df=pd.read_csv("./data/Institution.csv", low_memory=False)
prog_df['program_id']=prog_df.index+1

prog_df=prog_df.merge(institution_df[['UNITID','UG12MN']], on='UNITID', how='left')

#Maybe Add a Score
# prog_df['score']=((prog_df['EARN_COUNT_WNE_4YR_NAT']/prog_df['UG12MN'])*prog_df['EARN_MDN_4YR_NAT'])
# prog_df['score']=(prog_df['EARN_COUNT_WNE_4YR_NAT']*prog_df['EARN_MDN_4YR_NAT'])

schools_df=institution_df[['UNITID','OPEID6','INSTNM','UG12MN','CITY','STABBR','LONGITUDE','LATITUDE','ICLEVEL','INSTURL']].rename(columns=str.lower)
majors_df=prog_df[['CIPCODE','CIPDESC']].drop_duplicates(subset=['CIPCODE']).rename(columns=str.lower)
programs_df=prog_df[['program_id','UNITID','CIPCODE','CREDLEV']].rename(columns=str.lower)
adm_crit_df=institution_df[['UNITID','ADM_RATE','SATMT25','SATMT75','SATVR25','SATVR75','SATWR25','SATWR75',
                            'ACTEN25','ACTEN75','ACTMT25','ACTMT75','ACTWR25','ACTWR75']].rename(columns=str.lower)
cost_info_df=institution_df[['UNITID','NPT4','NPT41','NPT42','NPT43','NPT44','NPT45','TUITIONFEE_IN','TUITIONFEE_OUT']].rename(columns=str.lower)
program_rank_crit=prog_df[['program_id','EARN_COUNT_WNE_4YR_NAT','EARN_MDN_4YR_NAT']].rename(columns=str.lower)

#Add Median Earnings for each Major based on all programs
majors=[]
earnings_mdn=[]
earnings_avg=[]
for major in majors_df['cipcode']:
    mdn_earnings=prog_df[["CIPCODE","EARN_MDN_4YR_NAT"]]
    mdn_earnings=mdn_earnings[mdn_earnings["CIPCODE"]==major]
    majors.append(major)
    earn_mdn=mdn_earnings["EARN_MDN_4YR_NAT"].median()
    earnings_mdn.append(earn_mdn)
majors1={
    "cipcode":majors,
    "mdn_earnings":earnings_mdn
}

majors1_df=pd.DataFrame(majors1)
majors_df=majors_df.merge(majors1_df[['cipcode','mdn_earnings']], on='cipcode', how='left')


schools_df.to_csv("./tables/schools.csv", index=False)
program_rank_crit.to_csv("./tables/program_rank_crit.csv", index=False)
majors_df.to_csv("./tables/majors.csv", index=False)
programs_df.to_csv("./tables/programs.csv", index=False)
cost_info_df.to_csv("./tables/cost_info.csv", index=False)
adm_crit_df.to_csv("./tables/adm_crit.csv", index=False)

with engine.begin() as connection:
    with open("./schemas/all_schema.sql", "r") as f:
        schema=f.read()
        statements=schema.split(";")
        for statement in statements:
            if statement.strip():
                connection.execute(text(statement))

#If running this, reset database by running schema first
upload=[
    ("schools", schools_df),
    ("majors", majors_df),
    ("programs", programs_df),
    ("adm_crit",adm_crit_df),
    ("cost_info",cost_info_df),
    ("program_rank_crit",program_rank_crit)
]

for table_name, df in upload:
    df.to_sql(
        name=table_name,
        con=engine,
        if_exists="append",
        index=False,
        chunksize=1000,
        method="multi"
    )

engine.dispose()
close_connector()



