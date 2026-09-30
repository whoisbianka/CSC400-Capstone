import pandas as pd
from sqlalchemy import create_engine, text
import sqlalchemy
import numpy as np
import os
from dotenv import load_dotenv
from google.cloud.sql.connector import Connector
from cloud_sql_connection import connect_with_connector, close_connector

load_dotenv()

engine=connect_with_connector()

##CREATE Functions
#Add User
def add_user(user_id,fname,lname,email,google_auth):
    with engine.begin() as connection:
        query=text("""
                INSERT INTO users(user_id,fname,lname,email,google_auth)
                VALUES (:user_id, :fname, :lname, :email, :google_auth)
                """)
        connection.execute(query,{"user_id":user_id,
                                  "fname":fname,
                                  "lname":lname,
                                  "email":email,
                                  "google_auth":google_auth})

#Add a given major(by cipcode) to a user's favorites
def add_major_to_favorite(user_id,cipcode):
    with engine.begin() as connection:
        major_id=get_major_id_from_cipcode(cipcode)
        query=text("""
                INSERT INTO major_fav(user_id,major_id)
                VALUES (:user_id, :major_id)
                """)
        connection.execute(query,{"user_id":user_id,"major_id":major_id})

#Add a given major(by cipcode) to a user's recommendation list
def add_major_rec(user_id,cipcode):
    with engine.begin() as connection:
        major_id=get_major_id_from_cipcode(cipcode)
        query=text("""
                INSERT INTO major_rec(user_id,major_id)
                VALUES (:user_id, :major_id)
                """)
        connection.execute(query,{"user_id":user_id,"major_id":major_id})

#Add a given school(by unitid) to a user's favorites
def add_fav_school(user_id,unitid):
    with engine.begin() as connection:
        school_id=get_school_id_from_unitid(unitid)
        query=text("""
                INSERT INTO school_fav(user_id,school_id)
                VALUES (:user_id, :school_id)
                """)
        connection.execute(query,{"user_id":user_id,"school_id":school_id})

#Add a given school(by unitid) to a user's recommendation list
def add_school_rec(user_id,unitid):
    with engine.begin() as connection:
        school_id=get_school_id_from_unitid(unitid)
        query=text("""
                INSERT INTO school_rec(user_id,school_id)
                VALUES (:user_id, :school_id)
                """)
        connection.execute(query,{"user_id":user_id,"school_id":school_id})

#Add a chat to a user's chatlog
def add_to_chat_to_log(user_id,chat_text,isUser):
    with engine.begin() as connection:
        query=text("""
                INSERT INTO chatlog(user_id, chat_text, isUser)
                VALUES(:user_id, :chat_text, :isUser)""")
        connection.execute(query,{"user_id":user_id,"chat_text":chat_text,"isUser":isUser})

##READ Functions
#Get all admission criteria for a school(by unitid)
def get_school_adm_crit(unitid):
    with engine.connect() as connection:
        query=text("""
        SELECT a.unitid, s.instnm, a.adm_rate, a.satmt25,a.satmt75,a.satvr25,a.satvr75,a.satwr25,a.satwr75,a.actmt25,a.actmt75,a.acten25,a.acten75,a.actwr25,a.actwr75
        FROM adm_crit a
        JOIN schools s ON a.unitid = s.unitid
        WHERE a.unitid=:unitid""")
        result=connection.execute(query, {"unitid":unitid})

        schools_list={}

        for row in result:
            schools_list[f"{unitid}"]={
                "instnm":row.instnm,
                "adm_rate":row.adm_rate,
                "satmt25":row.satmt25,
                "satmt75":row.satmt75,
                "satvr25":row.satvr25,
                "satvr75":row.satvr75,
                "satwr25":row.satwr25,
                "satwr75":row.satwr75,
                "actmt25":row.actmt25,
                "actmt75":row.actmt75,
                "acten25":row.acten25,
                "acten75":row.acten75,
                "actwr25":row.actwr25,
                "actwr75":row.actwr75}
    return schools_list

#Get all cost info for a school(by unitid)
def get_cost_info(unitid):
    with engine.connect() as connection:
        query=text("""
        SELECT c.unitid, s.instnm, c.npt4, c.npt41, c.npt42, c.npt43, c.npt44, c.npt45, c.tuitionfee_in, c.tuitionfee_out
        FROM cost_info c
        JOIN schools s ON c.unitid = s.unitid
        WHERE c.unitid=:unitid""")
        result=connection.execute(query, {"unitid":unitid})

        schools_list={}

        for row in result:
            schools_list[f"{unitid}"]={
                "instnm":row.instnm,
                "npt4":row.npt4,
                "npt41":row.npt41,
                "npt42":row.npt42,
                "npt43":row.npt43,
                "npt44":row.npt44,
                "npt45":row.npt45,
                "tuitionfee_in":row.tuitionfee_in,
                "tuitionfee_out":row.tuitionfee_out}
    return schools_list

#Get all net average price information for a school(by unitid)
def get_all_npt_info(unitid):
    with engine.connect() as connection:
        query=text("""
        SELECT c.unitid, s.instnm, c.npt4, c.npt41, c.npt42, c.npt43, c.npt44, c.npt45
        FROM cost_info c
        JOIN schools s ON c.unitid = s.unitid
        WHERE c.unitid=:unitid""")
        result=connection.execute(query, {"unitid":unitid})

        schools_list={}

        for row in result:
            schools_list[f"{unitid}"]={
                "instnm":row.instnm,
                "npt4":row.npt4,
                "npt41":row.npt41,
                "npt42":row.npt42,
                "npt43":row.npt43,
                "npt44":row.npt44,
                "npt45":row.npt45}
    return schools_list

#Get tuition info for a school(by unitid)
def get_tuition_info(unitid):
    with engine.connect() as connection:
        query=text("""
        SELECT c.unitid, s.instnm, c.tuitionfee_in, c.tuitionfee_out
        FROM cost_info c
        JOIN schools s ON c.unitid = s.unitid
        WHERE c.unitid=:unitid""")
        result=connection.execute(query, {"unitid":unitid})

        schools_list={}

        for row in result:
            schools_list[f"{unitid}"]={
                "instnm":row.instnm,
                "tuitionfee_in":row.tuitionfee_in,
                "tuitionfee_out":row.tuitionfee_out}
    return schools_list

#Get the location of a school(by unitid)
def get_city_state(unitid):
    with engine.connect() as connection:
        query=text("""
        SELECT s.unitid, s.instnm, s.city, s.stabbr, s.longitude, s.latitude
        FROM schools s
        WHERE s.unitid=:unitid""")
        result=connection.execute(query, {"unitid":unitid})

        schools_list={}

        for row in result:
            schools_list[f"{unitid}"]={
                "instnm":row.instnm,
                "city":row.city,
                "stabbr":row.stabbr,
                "longitude":row.longitude,
                "latitude":row.latitude}
    return schools_list

#Get school url
def get_school_url(unitid):
    with engine.connect() as connection:
        query=text("""
        SELECT s.insturl
        FROM schools s
        WHERE s.unitid=:unitid""")
        result=connection.execute(query, {"unitid":unitid})

        for row in result:
            out=row.insturl
    return out

#Get SAT Criteria for a school(by unitid)
def get_sat_crit(unitid):
    with engine.connect() as connection:
        query=text("""
        SELECT a.unitid, s.instnm, a.satmt25,a.satmt75,a.satvr25,a.satvr75,a.satwr25,a.satwr75
        FROM adm_crit a
        JOIN schools s ON a.unitid = s.unitid
        WHERE a.unitid=:unitid""")
        result=connection.execute(query, {"unitid":unitid})

        schools_list={}

        for row in result:
            schools_list[f"{unitid}"]={
                "instnm":row.instnm,
                "satmt25":row.satmt25,
                "satmt75":row.satmt75,
                "satvr25":row.satvr25,
                "satvr75":row.satvr75,
                "satwr25":row.satwr25,
                "satwr75":row.satwr75}
    return schools_list

#Get ACT Criteria for a School(by unitid)
def get_school_adm_crit(unitid):
    with engine.connect() as connection:
        query=text("""
        SELECT a.unitid, s.instnm, a.actmt25,a.actmt75,a.acten25,a.acten75,a.actwr25,a.actwr75
        FROM adm_crit a
        JOIN schools s ON a.unitid = s.unitid
        WHERE a.unitid=:unitid""")
        result=connection.execute(query, {"unitid":unitid})

        schools_list={}

        for row in result:
            schools_list[f"{unitid}"]={
                "instnm":row.instnm,
                "actmt25":row.actmt25,
                "actmt75":row.actmt75,
                "acten25":row.acten25,
                "acten75":row.acten75,
                "actwr25":row.actwr25,
                "actwr75":row.actwr75}
    return schools_list

#Get schools where given SAT Math and Reading Scores are above 25% of students at that school
def get_school_list_from_satscores(math_sat_score,reading_sat_score):
    with engine.connect() as connection:
        query=text("""
        SELECT a.unitid, s.instnm 
        FROM adm_crit a
        JOIN schools s ON a.unitid = s.unitid
        WHERE satmt25 <= :thresholdmt AND satvr25 <= :thresholdvr""")
        result=connection.execute(query, {"thresholdmt":math_sat_score, "thresholdvr":reading_sat_score})

        schools_list=[]

        for row in result:
            schools_list.append({"unitid":row.unitid,"instnm":row.instnm})

    print(f"Number of schools that would accept those Scores: {len(schools_list)}")
    return schools_list

#Get Income Bracket from Income
def get_bracket(income):
    if income<30001 or income=='a':
        return "npt41"
    if income<48001 or income=='b':
        return "npt42"
    if income<75001 or income=='c':
        return "npt43"
    if income<110001 or income=='d':
        return "npt44"
    else:
        return "npt45"

#Get Net Average Price for a Given Income Bracket
def get_npt(unitid,inc_bracket):
    with engine.connect() as connection:
        query=text(f"""
        SELECT {inc_bracket}
        FROM cost_info
        WHERE unitid=:inp_unitid""")
        result=connection.execute(query, {"inp_unitid":unitid})

        res=result.one()
    return res[0]

#Get All Programs from a Cipcode, All schools that offer a major
def get_programs_from_cipcode(cipcode):
    with engine.connect() as connection:
        query=text("""
                SELECT s.unitid, p.program_id
                FROM programs p
                JOIN schools s ON s.unitid = p.unitid
                WHERE cipcode=:cip
                """)
        result=connection.execute(query,{"cip":cipcode})

        res=[]
        for row in result:
            res.append({"unitid":row.unitid,"program_id":row.program_id,"cipcode":cipcode,})
    return res

#Get mdn earnings of a specific program(program_id)
def get_mdn_earnings(program_id):
    with engine.connect() as connection:
        query=text("""
                SELECT pc.earn_mdn_4yr_nat
                FROM program_rank_crit pc
                WHERE pc.program_id=:program_id""")
        result=connection.execute(query,{"program_id":program_id})
    for row in result:
        out=row.earn_mdn_4yr_nat
    return out

#Helper Function: Get Program Id from Cipcode and Unitid
def get_program_id_fom_unit_and_cip(unitid,cipcode):
    with engine.connect() as connection:
        query=text("""
                SELECT p.program_id
                FROM programs p
                WHERE p.unitid=:unitid AND p.cipcode=:cipcode""")
        result=connection.execute(query,{"unitid":unitid,"cipcode":cipcode})
    for row in result:
        out=row.program_id
    return out

#Helper Function: Get Cipcode and Unitid from Program Id
def get_unit_and_cip_from_program_id(program_id):
    with engine.connect() as connection:
        query=text("""
                SELECT p.unitid, p.cipcode
                FROM programs p
                WHERE p.program_id=:program_id""")
        result=connection.execute(query,{"program_id":program_id})
    for row in result:
        out=(row.unitid, row.cipcode)
    return out


#Get the x best programs for a major(by cipcode) given a criteria
def get_best_progs_from_cip(x,cip,criteria):
    with engine.connect() as connection:
        query=text(f"""
            SELECT s.instnm,s.unitid, m.cipdesc, p.program_id,r.earn_mdn_4yr_nat
            FROM programs p
            JOIN schools s ON p.unitid = s.unitid
            JOIN program_rank_crit r ON p.program_id=r.program_id
            JOIN majors m ON p.cipcode=m.cipcode
            WHERE p.cipcode=:cip
            ORDER BY r.{criteria} DESC
            LIMIT {x}
            """)
        result=connection.execute(query,{"cip":cip})
        results=[]
        i=1
        for row in result:
            print(f"\n{i}. SCHOOL: {row.instnm}\nMAJOR:{row.cipdesc}\nEarnings:{row.earn_mdn_4yr_nat}\n")
            results.append({"School":row.instnm,"unitid":row.unitid,"Major":row.cipdesc,"Earnings":row.earn_mdn_4yr_nat})
            i+=1
    return results

#Get user's favorited majors
def get_user_fav_majors(user_id):
    with engine.connect() as connection:
        query=text("""
                    SELECT m.cipdesc, m.cipcode
                    FROM major_fav f
                    JOIN majors m ON m.major_id = f.major_id
                    WHERE f.user_id=:user_id""")
        result=connection.execute(query,{"user_id":user_id})
        results=[]
        for row in result:
            print(f"\nMajor: {row.cipdesc}\nCIPCODE: {row.cipcode}")
            results.append({"cipdesc":row.cipdesc,"cipcode":row.cipcode})
    return results

#Helper Function: Get a major_id from a cipcode
def get_major_id_from_cipcode(cipcode):
    with engine.connect() as connection:
        query=text("""
                    SELECT m.major_id
                    FROM majors m
                    WHERE m.cipcode=:cipcode""")
        result=connection.execute(query,{"cipcode":cipcode})
        results=[]
        for row in result:
            results.append(row.major_id)
    return results[0]

#Helper Function: Get a cipcode from a major_id
def get_cipcode_from_major_id(major_id):
    with engine.connect() as connection:
        query=text("""
                    SELECT m.cipcode
                    FROM majors m
                    WHERE m.major_id=:major_id""")
        result=connection.execute(query,{"major_id":major_id})
        results=[]
        for row in result:
            results.append(row.cipcode)
    return results[0]

#Helper Function: Get a school_id from a unitid
def get_school_id_from_unitid(unitid):
    with engine.connect() as connection:
        query=text("""
                    SELECT s.school_id
                    FROM schools s
                    WHERE s.unitid=:unitid""")
        result=connection.execute(query,{"unitid":unitid})
        results=[]
        for row in result:
            results.append(row.school_id)
    return results[0]

#Helper Function: Get a unitid from a school_id
def get_unitid_from_school_id(school_id):
    with engine.connect() as connection:
        query=text("""
                    SELECT s.unitid
                    FROM schools s
                    WHERE s.school_id=:school_id""")
        result=connection.execute(query,{"school_id":school_id})
        results=[]
        for row in result:
            results.append(row.unitid)
    return results[0]

#Get user's favorited schools
def get_user_fav_schools(user_id):
    with engine.connect() as connection:
        query=text("""
                    SELECT s.instnm, s.unitid
                    FROM school_fav sf
                    JOIN schools s ON s.school_id = sf.school_id
                    WHERE sf.user_id=:user_id""")
        result=connection.execute(query,{"user_id":user_id})
        results=[]
        for row in result:
            print(f"\nSchool: {row.instnm}\nUnitId: {row.unitid}")
            results.append({"instnm":row.instnm,"unitid":row.unitid})
    return results

#Get user's recommended majors
def get_user_major_recs(user_id):
    with engine.connect() as connection:
        query=text("""
                    SELECT m.cipdesc, m.cipcode
                    FROM major_rec mr
                    JOIN majors m ON m.major_id = mr.major_id
                    WHERE mr.user_id=:user_id""")
        result=connection.execute(query,{"user_id":user_id})
        results=[]
        for row in result:
            print(f"\nMajor: {row.cipdesc}\nCipcode: {row.cipcode}")
            results.append({"cipdesc":row.cipdesc,"cipcode":row.cipcode})
    return results

#Get user's recommended schools
def get_user_school_recs(user_id):
    with engine.connect() as connection:
        query=text("""
                    SELECT s.instnm, s.unitid
                    FROM school_rec sr
                    JOIN schools s ON s.school_id = sr.school_id
                    WHERE sr.user_id=:user_id""")
        result=connection.execute(query,{"user_id":user_id})
        results=[]
        for row in result:
            print(f"\nSchool: {row.instnm}\nUnitId: {row.unitid}")
            results.append({"instnm":row.instnm,"unitid":row.unitid})
    return results

#Get user's chatlog
def get_user_chatlog(user_id):
    with engine.connect() as connection:
        query=text("""
            SELECT cl.createdAt, cl.chat_text, cl.isUser
            FROM chatlog cl
            WHERE cl.user_id=:user_id
            ORDER BY cl.createdAt ASC""")
        result=connection.execute(query,{"user_id":user_id})

    results=[]
    for row in result:
        results.append({"Time":row.createdAt,"Text":row.chat_text,"isUser":row.isUser})
    return results

#Page(Integer), Page_count(Integer), Table_Name(String), column_to_sort(String), order(String) "ASC" or "DESC"
def get_a_page(page,page_count,table_name,column_to_sort,order):
    allowed_tables=["schools","majors","programs"]

    if table_name not in allowed_tables:
        raise ValueError(f"Unauthorized table name: '{table_name}'")

    order = "DESC" if order.upper() == "DESC" else "ASC"
    offset=(page - 1) * page_count
    with engine.connect() as connection:
        query=text(f"""
                SELECT * FROM {table_name}
                ORDER BY {column_to_sort} {order}, id ASC
                LIMIT :limit offset :offset""")
        result=connection.execute(query,{"limit":page_count,"offset":offset})

    return result.mappings().all()

#Input a table_name and the last_id(the id 1 before the start of the return)
def paginate(table_name,last_id):
    with engine.connect() as connection:
        query=text(f"""
                SELECT * FROM {table_name}
                WHERE id>:last_id
                ORDER BY id ASC
                LIMIT 2000""")
        result=connection.execute(query,{"last_id":last_id})
    return result.mappings().all()

##UPDATE Functions

##DELETE Functions
#Delete a user
def remove_user(user_id):
    with engine.begin() as connection:
        query=text("""
                DELETE from users
                WHERE user_id=:user_id""")
        connection.execute(query,{"user_id":user_id})

#Remove a major from user's favorites
def remove_from_major_fav(user_id,major_id):
    with engine.begin() as connection:
        query=text("""
                DELETE from major_fav
                WHERE user_id=:user_id AND major_id=:major_id
                """)
        connection.execute(query,{"user_id":user_id,"major_id":major_id})

#Remove a major from user's recommendations
def remove_major_rec(user_id,major_id):
    with engine.begin() as connection:
        query=text("""
                DELETE from major_rec
                WHERE user_id=:user_id AND major_id=:major_id
                """)
        connection.execute(query,{"user_id":user_id,"major_id":major_id})

#Remove a school from user's favorites
def remove_school_fav(user_id,school_id):
    with engine.begin() as connection:
        query=text("""
                DELETE from school_fav
                WHERE user_id=:user_id AND school_id=:school_id
                """)
        connection.execute(query,{"user_id":user_id,"school_id":school_id})

#Remove a school from user's recommendations
def remove_school_rec(user_id,school_id):
    with engine.begin() as connection:
        query=text("""
                DELETE from school_rec
                WHERE user_id=:user_id AND school_id=:school_id
                """)
        connection.execute(query,{"user_id":user_id,"school_id":school_id})

#Remove a user's Chatlog
def delete_chatlog(user_id):
    with engine.begin() as connection:
        query=text("""
                DELETE from chatlog
                WHERE user_id=:user_id""")
        connection.execute(query,{"user_id":user_id})

