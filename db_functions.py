import pandas as pd
from sqlalchemy import create_engine, text, bindparam
import sqlalchemy
import numpy as np
import os
import re
from dotenv import load_dotenv
from google.cloud.sql.connector import Connector
from cloud_sql_connection import connect_with_connector, close_connector
from time import perf_counter
from contextlib import ExitStack
import json

load_dotenv()

engine=connect_with_connector()

SCHOOL_SEARCH_ALIASES = {
    "uconn": ("University of Connecticut",),
    "umass": ("University of Massachusetts",),
    "mit": ("Massachusetts Institute of Technology",),
    "caltech": ("California Institute of Technology",),
    "ucla": ("University of California-Los Angeles", "University of California, Los Angeles"),
    "upenn": ("University of Pennsylvania",),
    "pennstate": ("Pennsylvania State University",),
}

##CREATE Functions
#Add User
def create_or_update_user(clerk_user_id):
    insert_query=text("""
            INSERT INTO public.users(clerk_user_id)
            VALUES (:clerk_user_id)
            ON CONFLICT(clerk_user_id)
            DO NOTHING
            RETURNING id, clerk_user_id;
            """)
    lookup_query=text("""
                    SELECT id, clerk_user_id
                    FROM users
                    WHERE clerk_user_id=:clerk_user_id""")
    params={"clerk_user_id":clerk_user_id}

    with engine.begin() as connection:
        row=connection.execute(insert_query,params).mappings().one_or_none()
        if row is None:
            row=connection.execute(lookup_query,params).mappings().one()
    return dict(row)

#Add a given major(by cipcode) to a user's favorites
def add_major_fav(user_id,cipcode):
    with engine.begin() as connection:
        major_exists=connection.execute(
            text("""
                    SELECT 1
                    FROM public.majors
                    WHERE cipcode=:cipcode"""),{"cipcode":cipcode}).scalar_one_or_none()
        if major_exists is None:
            return False
        query=text("""
                INSERT INTO major_fav(user_id,cipcode)
                VALUES (:user_id, :cipcode)
                ON CONFLICT (user_id,cipcode) DO NOTHING
                """)
        connection.execute(query,{"user_id":user_id,"cipcode":cipcode})
    return True

#Add a given school(by unitid) to a user's favorites
def add_program_fav(user_id, program_id):
    with engine.begin() as connection:
        exists = connection.execute(text("""
            SELECT 1 FROM public.programs WHERE program_id = :program_id
        """), {"program_id": program_id}).scalar_one_or_none()
        if exists is None:
            return False
        connection.execute(text("""
            INSERT INTO public.program_fav (user_id, program_id)
            VALUES (:user_id, :program_id)
            ON CONFLICT (user_id, program_id) DO NOTHING
        """), {"user_id": user_id, "program_id": program_id})
    return True

#Add a given school(by unitid) to a user's recommendation list
def add_program_rec(user_id,program_id):
    with engine.begin() as connection:
        query=text("""
                INSERT INTO program_rec(user_id,program_id)
                VALUES (:user_id, :program_id)
                """)
        connection.execute(query,{"user_id":user_id,"program_id":program_id})

#Add a chat to a user's chatlog
def add_to_chat_to_log(user_id,content,sender):
    with engine.begin() as connection:
        query=text("""
                INSERT INTO chatlog(user_id, content, sender)
                VALUES(:user_id, :content, :sender)""")
        connection.execute(query,{"user_id":user_id,"content":content,"sender":sender})

#Add a keyword for user
def add_user_keyword(user_id,keyword_id,evidence):
    query=text("""
            INSERT INTO user_keywords(user_id, keyword_id, evidence)
            VALUES(:user_id, :keyword_id,:evidence)
            ON CONFLICT (user_id, keyword_id) DO NOTHING
            """)
    params={"user_id":user_id,"keyword_id":keyword_id,"evidence":evidence}
    with engine.begin() as connection:
        connection.execute(query,params)

#Helper Function: Get keyword_id from keyword
def get_a_keyword_id_from_keyword(keyword):
    query=text("""
                SELECT id
                FROM keywords
                WHERE keyword=:keyword""")
    params={"keyword":keyword}
    with engine.connect() as connection:
        result=connection.execute(query,params)
        out=result.one()
    return out

def get_a_keyword_from_keyword_id(keyword_id):
    query=text("""
                SELECT keyword
                FROM keywords
                WHERE id=:keyword_id""")
    params={"keyword_id":keyword_id}
    with engine.connect() as connection:
        result=connection.execute(query,params)
        out=result.one()
    return out

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
    return out if out is not None else None

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
def get_school_act_crit(unitid):
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
    if isinstance(income, str):
        brackets = {
            "a": "npt41",
            "b": "npt42",
            "c": "npt43",
            "d": "npt44",
            "e": "npt45",
        }

        letter = income.strip().lower()

        if letter not in brackets:
            raise ValueError("Income bracket must be a, b, c, d, or e.")

        return brackets[letter]

    if income < 30001:
        return "npt41"
    if income < 48001:
        return "npt42"
    if income < 75001:
        return "npt43"
    if income < 110001:
        return "npt44"

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

#Helper Function: Get a major_id from a cipcode
def get_major_id_from_cipcode(cipcode):
    with engine.connect() as connection:
        query=text("""
                    SELECT m.id
                    FROM majors m
                    WHERE m.cipcode=:cipcode""")
        result=connection.execute(query,{"cipcode":cipcode})
        results=[]
        for row in result:
            results.append(row.id)
    return results[0]

#Helper Function: Get a cipcode from a major_id
def get_cipcode_from_major_id(major_id):
    with engine.connect() as connection:
        query=text("""
                    SELECT m.cipcode
                    FROM majors m
                    WHERE m.id=:major_id""")
        result=connection.execute(query,{"major_id":major_id})
        results=[]
        for row in result:
            results.append(row.cipcode)
    return results[0]

#Helper Function: Get a school_id from a unitid
def get_school_id_from_unitid(unitid):
    with engine.connect() as connection:
        query=text("""
                    SELECT s.id
                    FROM schools s
                    WHERE s.unitid=:unitid""")
        result=connection.execute(query,{"unitid":unitid})
        results=[]
        for row in result:
            results.append(row.id)
    return results[0]

#Helper Function: Get a unitid from a school_id
def get_unitid_from_school_id(school_id):
    with engine.connect() as connection:
        query=text("""
                    SELECT s.unitid
                    FROM schools s
                    WHERE s.id=:school_id""")
        result=connection.execute(query,{"school_id":school_id})
        results=[]
        for row in result:
            results.append(row.unitid)
    return results[0]

#Get user's chatlog
def get_recent_chatlog(user_id,limit=20):
    with engine.connect() as connection:
        query=text("""
            SELECT cl.content, cl.sender
            FROM chatlog cl
            WHERE cl.user_id=:user_id
            ORDER BY cl.createdAt DESC, id DESC
            LIMIT :limit""")
        rows=connection.execute(query,{"user_id":user_id,"limit":limit}).mappings().all()

    return [{"role":row["sender"],"content":row["content"]}for row in reversed(rows)]

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

#input table(String) and a batch size(default=5000) to scan the whole table
#Each row of the batch will be yielded, allowing for chatbot to analyze each row
def scan_entire_table(table_name, batch_size=5000):
    query = text(f"""
        SELECT * FROM {table_name}
        WHERE id > :last_id
        ORDER BY id ASC
        LIMIT :batch_size
    """)

    last_id = 0

    with engine.connect() as connection:
        while True:
            # Fetch a large chunk
            result = connection.execute(query, {
                "last_id": last_id,
                "batch_size": batch_size
            }).all()

            # If no rows are returned, table has been scanned
            if not result:
                break

            # Yield the rows to a loop
            for row in result:
                yield row
                # Update the cursor to the last ID seen in this batch
                last_id = row.id

##Get a page of schools
#page: an Integer representing the page number to display(default=1)
#page count: an Integer representing the amount items on each page(default=10)
#
##SORTING(optional inputs, by default sorts based on m.id, in ascending order)
#column_to_sort: a String that is the name of a column from one of the tables being joined, beginning with an abbreviation
#schools(s.column_to_sort), cost_info(c.column_to_sort), adm_crit(a.column_to_sort)
#
#order: a String, either "ASC" or "DESC" depending on how the list should be sorted
#
#FILTERING(optional, by default applies no filter)
#criteria: a String, should be a column name to be filtered(same syntax as column_to_sort)
#threshhold: a String containing a value to filter the criteria column based on
#operator: a String, representing how to filter the criteria column in regards to the threshhold
#operator should be one of the following: ">", ">=", "<", "<=", "="
def get_page_schools(page=1,page_count=10,column_to_sort="s.id",order="ASC",criteria="s.id",operator=">=",threshhold=0):
    order = "DESC" if order.upper() == "DESC" else "ASC"
    offset=(page - 1) * page_count
    with engine.connect() as connection:
        query=text(f"""
                SELECT *
                FROM schools s
                JOIN cost_info c ON c.unitid = s.unitid
                JOIN adm_crit a ON a.unitid = s.unitid
                WHERE {criteria} {operator} :threshhold
                ORDER BY {column_to_sort} {order}, s.id {order}
                LIMIT :limit OFFSET :offset""")
        result=connection.execute(query,{"threshhold":threshhold,"limit":page_count,"offset":offset})

    return result.mappings().all()

def get_a_program(program_id):
    query=text("""
                SELECT p.program_id AS id,
                p.unitid,
                p.cipcode,
                m.cipdesc AS major,
                s.instnm AS college,
                s.city,
                s.stabbr AS state,
                r.earn_mdn_4yr_nat AS earnings,
                mi.major_description AS description,
                mi.description_source,
                c.npt4,
                c.npt41,
                c.npt42,
                c.npt43,
                c.npt44,
                c.npt45,
                c.tuitionfee_in,
                c.tuitionfee_out,
                a.adm_rate,
                a.satmt25,
                a.satmt75,
                a.satvr25,
                a.satvr75,
                a.satwr25,
                a.satwr75,
                a.actmt25,
                a.actmt75,
                a.acten25,
                a.acten75,
                a.actwr25,
                a.actwr75,
                s.insturl AS website
                FROM programs p
                JOIN schools s ON s.unitid = p.unitid
                JOIN majors m ON m.cipcode=p.cipcode
                LEFT JOIN program_rank_crit r ON r.program_id=p.program_id
                LEFT JOIN cost_info c ON c.unitid = p.unitid
                LEFT JOIN major_info mi ON mi.cipcode = p.cipcode
                LEFT JOIN adm_crit a ON a.unitid = p.unitid
                WHERE p.program_id=:program_id""")
    params={"program_id":program_id}
    with engine.connect() as connection:
        row=(connection.execute(query,params).mappings().one_or_none())

    return dict(row) if row is not None else None
    

##Get a page of programs
#page: an Integer representing the page number to display(default=1)
#page count: an Integer representing the amount items on each page(default=10)
#
##SORTING(optional inputs, by default sorts based on m.id, in ascending order)
#column_to_sort: a String that is the name of a column from one of the tables being joined, beginning with an abbreviation
#programs(p.column_to_sort), program_rank_crit(r.column_to_sort)
#schools(s.column_to_sort), cost_info(c.column_to_sort), adm_crit(a.column_to_sort)
#
#order: a String, either "ASC" or "DESC" depending on how the list should be sorted
#
#FILTERING(optional, by default applies no filter)
#criteria: a String, should be a column name to be filtered(same syntax as column_to_sort)
#threshhold: a value to filter the criteria column based on
#operator: a String, representing how to filter the criteria column in regards to the threshhold
#operator should be one of the following: ">", ">=", "<", "<=", "="
def get_page_programs(
        page=1,
        page_count=25,
        sort_option="school_name",
        sort_order="ASC",
        filters=None):
    if type(page) is not int or not 1 <= page <= 100000:
        raise ValueError("page must be an integer between 1 and 100000.")
    
    if type(page_count) is not int or not 1 <= page_count <= 100:
        raise ValueError("page_count must be an integer between 1 and 100.")

    if filters is None:
        filters = {}
    elif not isinstance(filters, dict):
        raise ValueError("filters must be a dictionary.")
    else:
        filters = filters.copy()

    conditions=[]
    params={}

    validate_program_filters(filters)

    # Search words may match either the major or the school name.
    for index, word in enumerate(filters.get("q", "").split()):
        key = f"search_{index}"
        params[key] = "%" + word.lower().replace("!", "!!").replace("%", "!%").replace("_", "!_") + "%"
        matches = [f"LOWER(s.instnm) LIKE :{key} ESCAPE '!'",
                   f"LOWER(m.cipdesc) LIKE :{key} ESCAPE '!'"]
        alias = re.sub(r"[^a-z0-9]", "", word.casefold())
        for alias_index, school_name in enumerate(SCHOOL_SEARCH_ALIASES.get(alias, ())):
            alias_key = f"search_alias_{index}_{alias_index}"
            params[alias_key] = "%" + school_name.lower() + "%"
            matches.append(f"LOWER(s.instnm) LIKE :{alias_key}")
        conditions.append("(" + " OR ".join(matches) + ")")


    if filters.get("cipcode") is not None:
        conditions.append("p.cipcode=:cipcode")
        params["cipcode"]=filters["cipcode"]
    if filters.get("cipcodes") is not None:
        conditions.append("p.cipcode IN :cipcodes")
        params["cipcodes"] = filters["cipcodes"]
    if filters.get("major_name"):
        conditions.append("LOWER(m.cipdesc) = LOWER(:major_name)")
        params["major_name"] = filters["major_name"].strip()
    if filters.get("unitid") is not None:
        conditions.append("p.unitid=:unitid")
        params["unitid"]=filters["unitid"]
    if filters.get("school_name"):
        escaped = filters["school_name"].strip().replace("!", "!!").replace("%", "!%").replace("_", "!_")
        conditions.append("LOWER(s.instnm) LIKE LOWER(:school_name) ESCAPE '!'")
        params["school_name"] = "%" + escaped + "%"
    if filters.get("state"):
        conditions.append("LOWER(s.stabbr)=LOWER(:state)")
        params["state"]=filters["state"]
    if filters.get("city"):
        conditions.append("LOWER(s.city)=LOWER(:city)")
        params["city"]=filters["city"]
    if filters.get("net_price_max") is not None:
        conditions.append("c.npt4<=:net_price_max")
        params["net_price_max"]=filters["net_price_max"]
    if filters.get("acceptance_min") is not None:
        conditions.append("a.adm_rate>=:acceptance_min")
        params["acceptance_min"]=filters["acceptance_min"]/100
    if filters.get("acceptance_max") is not None:
        conditions.append("a.adm_rate<=:acceptance_max")
        params["acceptance_max"]=filters["acceptance_max"]/100
    if filters.get("degrees"):
        conditions.append("p.credlev IN :degrees")
        params["degrees"]=filters["degrees"]
    if filters.get("tuition_in_max") is not None:
        conditions.append("c.tuitionfee_in <=:tuition_in_max")
        params["tuition_in_max"]=filters["tuition_in_max"]
    if filters.get("tuition_out_max") is not None:
        conditions.append("c.tuitionfee_out <=:tuition_out_max")
        params["tuition_out_max"]=filters["tuition_out_max"]
    if filters.get("satmt") is not None:
        conditions.append("a.satmt25<=:satmt")
        params["satmt"]=filters["satmt"]
    if filters.get("satvr") is not None:
        conditions.append("a.satvr25<=:satvr")
        params["satvr"]=filters["satvr"]
    if filters.get("satwr") is not None:
        conditions.append("a.satwr25<=:satwr")
        params["satwr"]=filters["satwr"]
    if filters.get("actmt") is not None:
        conditions.append("a.actmt25<=:actmt")
        params["actmt"]=filters["actmt"]
    if filters.get("acten") is not None:
        conditions.append("a.acten25<=:acten")
        params["acten"]=filters["acten"]
    if filters.get("actwr") is not None:
        conditions.append("a.actwr25<=:actwr")
        params["actwr"]=filters["actwr"]
    
    sql_where=" AND ".join(conditions) if conditions else "TRUE"

    sort_order=sort_order.upper()
    sort_order_options=["ASC","DESC"]
    if sort_order not in sort_order_options:
        raise ValueError("Invalid sort order.")

    sort_options={
        "program_id":f"p.program_id {sort_order}",
        "school_name":f"s.instnm {sort_order}, p.program_id {sort_order}",
        "adm_rate":f"a.adm_rate {sort_order} NULLS LAST, p.program_id {sort_order}",
        "earnings":f"r.earn_mdn_4yr_nat {sort_order} NULLS LAST, p.program_id {sort_order}",
        "npt4":f"c.npt4 {sort_order} NULLS LAST, p.program_id {sort_order}",
        "npt41":f"c.npt41 {sort_order} NULLS LAST, p.program_id {sort_order}",
        "tuitionfee_in":f"c.tuitionfee_in {sort_order} NULLS LAST, p.program_id {sort_order}",
        "tuitionfee_out":f"c.tuitionfee_out {sort_order} NULLS LAST, p.program_id {sort_order}",
        "satmt25":f"a.satmt25 {sort_order} NULLS LAST, p.program_id {sort_order}",
        "satmt75":f"a.satmt75 {sort_order} NULLS LAST, p.program_id {sort_order}",
        "satvr25":f"a.satvr25 {sort_order} NULLS LAST, p.program_id {sort_order}",
        "satvr75":f"a.satvr75 {sort_order} NULLS LAST, p.program_id {sort_order}",
        "satwr25":f"a.satwr25 {sort_order} NULLS LAST, p.program_id {sort_order}",
        "satwr75":f"a.satwr75 {sort_order} NULLS LAST, p.program_id {sort_order}",
        "actmt25":f"a.actmt25 {sort_order} NULLS LAST, p.program_id {sort_order}",
        "actmt75":f"a.actmt75 {sort_order} NULLS LAST, p.program_id {sort_order}",
        "acten25":f"a.acten25 {sort_order} NULLS LAST, p.program_id {sort_order}",
        "acten75":f"a.acten75 {sort_order} NULLS LAST, p.program_id {sort_order}",
        "actwr25":f"a.actwr25 {sort_order} NULLS LAST, p.program_id {sort_order}",
        "actwr75":f"a.actwr75 {sort_order} NULLS LAST, p.program_id {sort_order}"
        }

    if sort_option not in sort_options:
        raise ValueError("Invalid sort option.")
    else:
        sql_order=sort_options[sort_option]

    params["offset"]=(page-1)*page_count
    params["limit"]=page_count+1

    query=text(f"""
                SELECT 
                    p.program_id AS id, 
                    p.unitid, 
                    p.cipcode, 
                    p.credlev, 
                    m.cipdesc AS major,
                    s.instnm AS college,
                    s.city,
                    s.stabbr AS state,
                    s.insturl AS website,
                    s.ug12mn AS enrollment,
                    c.npt4,
                    c.tuitionfee_in,
                    c.tuitionfee_out,
                    a.adm_rate,
                    r.earn_mdn_4yr_nat AS earnings,
                    a.satmt25,
                    a.satmt75,
                    a.satvr25,
                    a.satvr75,
                    a.actmt25,
                    a.actmt75,
                    a.acten25,
                    a.acten75
                FROM programs p
                LEFT JOIN program_rank_crit r ON r.program_id = p.program_id
                LEFT JOIN schools s ON s.unitid = p.unitid
                LEFT JOIN cost_info c ON c.unitid = p.unitid
                LEFT JOIN adm_crit a ON a.unitid = p.unitid
                LEFT JOIN majors m ON p.cipcode = m.cipcode
                WHERE {sql_where}
                ORDER BY {sql_order}
                LIMIT :limit OFFSET :offset""")

    for key in ("degrees", "cipcodes"):
        if key in params:
            query = query.bindparams(bindparam(key, expanding=True))

    start=perf_counter()  
    with engine.connect() as connection:
        connected=perf_counter()
        matches=connection.execute(query, params).mappings().all()
        finished=perf_counter()

    print(f"Connection checkout/setup: {connected-start:.3f}s; "
          f"query and fetch: {finished-connected:.3f}s")
    return{
        "rows":[dict(row) for row in matches[:page_count]],
        "page":page,
        "has_next":len(matches)>page_count
    }

#helper function to validate program filters
def validate_program_filters(filters):
    if "q" in filters and (not isinstance(filters["q"], str) or len(filters["q"]) > 200):
        raise ValueError("Search must be text of at most 200 characters.")
    school_name = filters.get("school_name")
    if school_name is not None and (
        not isinstance(school_name, str) or not 1 <= len(school_name.strip()) <= 200
    ):
        raise ValueError("School name must contain 1 to 200 characters.")
    cipcodes = filters.get("cipcodes")
    if cipcodes is not None:
        if not isinstance(cipcodes, (list, tuple)) or any(
            type(code) is not int or not 1 <= code <= 2147483647 for code in cipcodes
        ):
            raise ValueError("cipcodes must be a list of positive major codes.")
    major_name = filters.get("major_name")
    if major_name is not None and (
        not isinstance(major_name, str) or not 1 <= len(major_name.strip()) <= 200
    ):
        raise ValueError("Enter a major name between 1 and 200 characters.")

    numeric_ranges = {
        "cipcode": (1, 2147483647),
        "unitid": (1, 2147483647),
        "net_price_max": (0, 2147483647),
        "tuition_in_max": (0, 2147483647),
        "tuition_out_max": (0, 2147483647),
        "acceptance_min": (0, 100),
        "acceptance_max": (0, 100),
        "satmt": (200, 800),
        "satvr": (200, 800),
        "satwr": (200, 800),
        "actmt": (1, 36),
        "acten": (1, 36),
        "actwr": (2, 12),
    }

    for name, (minimum, maximum) in numeric_ranges.items():
        value = filters.get(name)

        if value is None:
            continue

        if type(value) is not int or not minimum <= value <= maximum:
            raise ValueError(
                f"{name} must be an integer between {minimum} and {maximum}."
            )
        
    minimum = filters.get("acceptance_min")
    maximum = filters.get("acceptance_max")

    if minimum is not None and maximum is not None:
        if minimum > maximum:
            raise ValueError(
                "Minimum acceptance rate cannot exceed maximum acceptance rate."
            )

    degrees = filters.get("degrees")

    if degrees is not None:
        if not isinstance(degrees, (list, tuple)):
            raise ValueError("degrees must be a list or tuple.")

        if any(type(degree) is not int or degree not in (2, 3)
            for degree in degrees):
            raise ValueError("Degree levels must be 2 or 3.")

##Get a page of majors
#Inputs:
#page: an Integer representing the page number to display(default=1)
#page count: an Integer representing the amount items on each page(default=10)
#
##SORTING(optional inputs, by default sorts based on m.id, in ascending order)
#column_to_sort: a String that is the name of a column from one of the tables being joined, beginning with an abbreviation
#m.column_to_sort(majors table is currently the only table)
#
#order: a String, either "ASC" or "DESC" depending on how the list should be sorted
#
#FILTERING(optional, by default applies no filter)
#criteria: a String, should be a column name to be filtered(same syntax as column_to_sort)
#threshhold: a value to filter the criteria column based on
#operator: a String, representing how to filter the criteria column in regards to the threshhold
#operator should be one of the following: ">", ">=", "<", "<=", "="
def get_page_majors(page=1,page_count=10,column_to_sort="m.id",order="ASC",criteria="m.id",operator=">=",threshhold="0"):
    order = "DESC" if order.upper() == "DESC" else "ASC"
    offset=(page - 1) * page_count
    with engine.connect() as connection:
        query=text(f"""
                SELECT *
                FROM majors m
                WHERE {criteria} {operator} :threshhold
                ORDER BY {column_to_sort} {order}, m.id {order}
                LIMIT :limit offset :offset""")
        result=connection.execute(query,{"threshhold":threshhold,"limit":page_count,"offset":offset})

    return result.mappings().all()

##Get a page of program recommendations for a given user
#Inputs:
#user_id: the current user's id
#
#page: an Integer representing the page number to display(default=1)
#page count: an Integer representing the amount items on each page(default=10)
#
#column_to_sort: a String that is the name of a column from one of the tables being joined, beginning with an abbreviation
#program_rec(prec.column_to_sort), programs(p.column_to_sort), program_rank_crit(r.column_to_sort)
#schools(s.column_to_sort), cost_info(c.column_to_sort), adm_crit(a.column_to_sort)
#
#order: a String, either "ASC" or "DESC" depending on how the list should be sorted
#criteria: a String, should be a column name to be filtered(same syntax as column_to_sort)
#threshhold: a value to filter the criteria column based on
#operator: a String, representing how to filter the criteria column in regards to the threshhold
#operator should be one of the following: ">", ">=", "<", "<=", "="
def get_page_program_recs(user_id,page=1,page_count=10,column_to_sort="prec.id",order="ASC",criteria="prec.id",operator=">=",threshhold=0):
    order = "DESC" if order.upper() == "DESC" else "ASC"
    offset=(page - 1) * page_count
    query=text(f"""
                SELECT *
                FROM program_rec prec
                JOIN programs p ON prec.program_id=p.program_id
                JOIN program_rank_crit r ON prec.program_id = r.program_id
                JOIN schools s ON s.unitid = p.unitid
                JOIN cost_info c ON c.unitid = p.unitid
                JOIN adm_crit a ON a.unitid = p.unitid
                WHERE prec.user_id=:user_id AND {criteria} {operator} :threshhold
                ORDER BY {column_to_sort} {order}, prec.id {order}
                LIMIT :limit OFFSET :offset""")
    params={"user_id":user_id,"threshhold":threshhold,"limit":page_count,"offset":offset}
    with engine.connect() as connection:
        result=connection.execute(query,params)
    return result.mappings().all()

##Get a page of program favorites for a given user
#Inputs:
#user_id: the current user's id
#
#page: an Integer representing the page number to display(default=1)
#page count: an Integer representing the amount items on each page(default=10)
#
#column_to_sort: a String that is the name of a column from one of the tables being joined, beginning with an abbreviation
#program_fav(pf.column_to_sort), programs(p.column_to_sort), program_rank_crit(r.column_to_sort)
#schools(s.column_to_sort), cost_info(c.column_to_sort), adm_crit(a.column_to_sort)
#
#order: a String, either "ASC" or "DESC" depending on how the list should be sorted
#criteria: a String, should be a column name to be filtered(same syntax as column_to_sort)
#threshhold: a value to filter the criteria column based on
#operator: a String, representing how to filter the criteria column in regards to the threshhold
#operator should be one of the following: ">", ">=", "<", "<=", "="
def get_page_program_favs(user_id,page=1,page_count=10,column_to_sort="pf.id",order="ASC",criteria="pf.id",operator=">=",threshhold="0"):
    order = "DESC" if order.upper() == "DESC" else "ASC"
    offset=(page - 1) * page_count
    query=text(f"""
                SELECT *
                FROM program_fav pf
                JOIN programs p ON pf.program_id=p.program_id
                JOIN program_rank_crit r ON pf.program_id = r.program_id
                JOIN schools s ON s.unitid = p.unitid
                JOIN cost_info c ON c.unitid = p.unitid
                JOIN adm_crit a ON a.unitid = p.unitid
                WHERE pf.user_id=:user_id AND {criteria} {operator} :threshhold
                ORDER BY {column_to_sort} {order}, pf.id {order}
                LIMIT :limit OFFSET :offset""")
    params={"user_id":user_id,"threshhold":threshhold,"limit":page_count,"offset":offset}
    with engine.connect() as connection:
        result=connection.execute(query,params)
    return result.mappings().all()


##Get a page of major recommendations for a given user
#Inputs:
#user_id: the current user's id
#
#page: an Integer representing the page number to display(default=1)
#page count: an Integer representing the amount items on each page(default=10)
#
#column_to_sort: a String that is the name of a column from one of the tables being joined, beginning with an abbreviation
#major_rec(mr.column_to_sort), majors(m.column_to_sort)
#
#order: a String, either "ASC" or "DESC" depending on how the list should be sorted
#criteria: a String, should be a column name to be filtered(same syntax as column_to_sort)
#threshhold: a value to filter the criteria column based on
#operator: a String, representing how to filter the criteria column in regards to the threshhold
#operator should be one of the following: ">", ">=", "<", "<=", "="
def get_page_major_recs(user_id,page=1,page_count=10,column_to_sort="mr.id",order="ASC",criteria="mr.id",operator=">=",threshhold="0"):
    order = "DESC" if order.upper() == "DESC" else "ASC"
    offset=(page - 1) * page_count
    query=text(f"""
                SELECT *
                FROM major_rec mr
                JOIN majors m ON mr.cipcode = m.cipcode
                WHERE mr.user_id=:user_id AND {criteria} {operator} :threshhold
                ORDER BY {column_to_sort} {order}, mr.id {order}
                LIMIT :limit OFFSET :offset""")
    params={"user_id":user_id,"threshhold":threshhold,"limit":page_count,"offset":offset}
    with engine.connect() as connection:
        result=connection.execute(query,params)
    return result.mappings().all()


##Get a page of major recommendations for a given user
#Inputs:
#user_id: the current user's id
#
#page: an Integer representing the page number to display(default=1)
#page count: an Integer representing the amount items on each page(default=10)
#
#column_to_sort: a String that is the name of a column from one of the tables being joined, beginning with an abbreviation
#major_fav(mf.column_to_sort), majors(m.column_to_sort)
#
#order: a String, either "ASC" or "DESC" depending on how the list should be sorted
#criteria: a String, should be a column name to be filtered(same syntax as column_to_sort)
#threshhold: a value to filter the criteria column based on
#operator: a String, representing how to filter the criteria column in regards to the threshhold
#operator should be one of the following: ">", ">=", "<", "<=", "="
def get_page_major_favs(user_id,page=1,page_count=10,column_to_sort="mf.id",order="ASC",criteria="mf.id",operator=">=",threshhold="0"):
    order = "DESC" if order.upper() == "DESC" else "ASC"
    offset=(page - 1) * page_count
    query=text(f"""
                SELECT *
                FROM major_fav mf
                JOIN majors m ON mf.cipcode = m.cipcode
                WHERE mf.user_id=:user_id AND {criteria} {operator} :threshhold
                ORDER BY {column_to_sort} {order}, mf.id {order}
                LIMIT :limit OFFSET :offset""")
    params={"user_id":user_id,"threshhold":threshhold,"limit":page_count,"offset":offset}
    with engine.connect() as connection:
        result=connection.execute(query,params)
    return result.mappings().all()

#get a user's keywords
def get_user_keywords(user_id):
    query=text("""
            SELECT k.id AS keyword_id, k.keyword, uk.evidence
            FROM public.user_keywords uk
            JOIN public.keywords k ON uk.keyword_id = k.id
            WHERE uk.user_id=:user_id""")
    params={"user_id":user_id}
    with engine.connect() as connection:
        rows=connection.execute(query,params).mappings().all()
    return [dict(row) for row in rows]

#get all keywords
def get_keywords():
    query=text("""
            SELECT id AS keyword_id, keyword
            FROM keywords
            ORDER BY id ASC""")
    with engine.connect() as connection:
        rows=connection.execute(query).mappings().all()
    return [dict(row) for row in rows]

def get_user(clerk_user_id):
    query=text("""
                SELECT id,clerk_user_id
                FROM users
                WHERE clerk_user_id=:clerk_user_id""")
    params={"clerk_user_id":clerk_user_id}
    with engine.connect() as connection:
        row=connection.execute(query,params).mappings().one_or_none()
    return dict(row) if row is not None else None

##UPDATE Functions

#save chat_turn
def save_chat_turn(user_id, user_message, turn):
    chat_query = text("""
        INSERT INTO public.chatlog (
            user_id,
            content,
            sender
        )
        VALUES (
            :user_id,
            :message,
            :sender
        )
    """)

    add_query = text("""
        INSERT INTO public.user_keywords (
            user_id,
            keyword_id,
            evidence
        )
        VALUES (
            :user_id,
            :keyword_id,
            :evidence
        )
        ON CONFLICT (user_id, keyword_id)
        DO UPDATE SET evidence = EXCLUDED.evidence
    """)

    remove_query = text("""
        DELETE FROM public.user_keywords
        WHERE user_id = :user_id
          AND keyword_id = :keyword_id
    """)

    chat_params = [
        {
            "user_id": user_id,
            "message": user_message,
            "sender": "user",
        },
        {
            "user_id": user_id,
            "message": turn.reply,
            "sender": "assistant",
        },
    ]

    add_params = [
        {
            "user_id": user_id,
            "keyword_id": addition.keyword_id,
            "evidence": addition.evidence,
        }
        for addition in turn.keyword_additions
    ]

    remove_params = [
        {
            "user_id": user_id,
            "keyword_id": keyword_id,
        }
        for keyword_id in turn.keyword_removals
    ]

    with engine.begin() as connection:
        existing_user = connection.execute(
            text("""
                SELECT id
                FROM public.users
                WHERE id = :user_id
                FOR UPDATE
            """),
            {"user_id": user_id},
        ).scalar_one_or_none()

        if existing_user is None:
            raise ValueError("User does not exist.")

        connection.execute(chat_query, chat_params)

        if remove_params:
            connection.execute(remove_query, remove_params)

        if add_params:
            connection.execute(add_query, add_params)

        recommendations = _refresh_user_recommendations(
            connection,
            user_id,
        )

    return recommendations


##DELETE Functions
#Delete a user
def remove_user(user_id):
    with engine.begin() as connection:
        query=text("""
                DELETE from users
                WHERE id=:user_id""")
        connection.execute(query,{"user_id":user_id})

#Remove a major from user's favorites
def remove_from_major_fav(user_id,cipcode):
    with engine.begin() as connection:
        query=text("""
                DELETE from public.major_fav
                WHERE user_id=:user_id AND cipcode=:cipcode
                """)
        connection.execute(query,{"user_id":user_id,"cipcode":cipcode})

#Remove a major from user's recommendations
def remove_major_rec(user_id,cipcode):
    with engine.begin() as connection:
        query=text("""
                DELETE from major_rec
                WHERE user_id=:user_id AND cipcode=:cipcode
                """)
        connection.execute(query,{"user_id":user_id,"cipcode":cipcode})

#Remove a school from user's favorites
def remove_school_fav(user_id,program_id):
    with engine.begin() as connection:
        query=text("""
                DELETE from public.program_fav
                WHERE user_id=:user_id AND program_id=:program_id
                """)
        connection.execute(query,{"user_id":user_id,"program_id":program_id})

#Remove a school from user's recommendations
def remove_program_rec(user_id,program_id):
    with engine.begin() as connection:
        query=text("""
                DELETE from program_rec
                WHERE user_id=:user_id AND program_id=:program_id
                """)
        connection.execute(query,{"user_id":user_id,"program_id":program_id})

#Remove a user's Chatlog
def delete_chatlog(user_id):
    with engine.begin() as connection:
        query=text("""
                DELETE from chatlog
                WHERE user_id=:user_id""")
        connection.execute(query,{"user_id":user_id})

#Remove a user keyword
def remove_user_keyword(user_id,keyword_id):
    query=text("""
                DELETE from user_keywords
                WHERE user_id=:user_id AND keyword_id=:keyword_id""")
    params={"user_id":user_id,"keyword_id":keyword_id}
    with engine.begin() as connection:
        connection.execute(query, params)


def get_major_info(cipcode):
    """Return the catalog description and its attribution for a major."""
    query = text("""
        SELECT major_description, description_source
        FROM major_info
        WHERE cipcode = :cipcode
    """)
    with engine.connect() as connection:
        row = connection.execute(query, {"cipcode": cipcode}).mappings().first()
        return dict(row) if row is not None else {}


def warm_database_connections(engine, size=5):
    with ExitStack() as stack:
        for _ in range(size):
            connection=stack.enter_context(engine.connect())
            connection.execute(text("SELECT 1"))

#Updating Recommendations based on current keywords for a user

def _rank_majors_from_keywords(connection, saved_keywords):
    """
    Rank up to six majors using saved keyword dictionaries.

    Each keyword dictionary contains:
        keyword_id
        evidence

    The caller supplies the database connection so this function
    can participate in an existing transaction.
    """
    keywords_by_id = {
        item["keyword_id"]: item
        for item in saved_keywords
    }

    if not keywords_by_id:
        return []

    query = text("""
        WITH ranked_majors AS (
            SELECT
                mk.cipcode,
                COUNT(DISTINCT mk.keyword_id) AS matching_keywords
            FROM public.major_keywords mk
            WHERE mk.keyword_id IN :keyword_ids
            GROUP BY mk.cipcode
            ORDER BY matching_keywords DESC, mk.cipcode ASC
            LIMIT 6
        )
        SELECT DISTINCT
            ranked.cipcode,
            m.cipdesc AS major,
            ranked.matching_keywords,
            k.id AS keyword_id,
            k.keyword
        FROM ranked_majors ranked
        JOIN public.majors m
            ON m.cipcode = ranked.cipcode
        JOIN public.major_keywords mk
            ON mk.cipcode = ranked.cipcode
        JOIN public.keywords k
            ON k.id = mk.keyword_id
        WHERE mk.keyword_id IN :keyword_ids
        ORDER BY
            ranked.matching_keywords DESC,
            ranked.cipcode ASC,
            k.keyword ASC,
            k.id ASC
    """).bindparams(
        bindparam("keyword_ids", expanding=True)
    )

    rows = connection.execute(
        query,
        {"keyword_ids": list(keywords_by_id)},
    ).mappings().all()

    recommendations = {}

    for row in rows:
        cipcode = row["cipcode"]

        if cipcode not in recommendations:
            recommendations[cipcode] = {
                "cipcode": cipcode,
                "major": row["major"],
                "matching_keywords": row["matching_keywords"],
                "evidence": [],
            }

        saved_keyword = keywords_by_id[row["keyword_id"]]

        recommendations[cipcode]["evidence"].append({
            "keyword_id": row["keyword_id"],
            "keyword": row["keyword"],
            "evidence": saved_keyword["evidence"],
        })

    return list(recommendations.values())


def get_recommendations_for_keywords(saved_keywords):
    """
    Generate recommendations without saving account records.

    Used for guests, whose results are saved in guest_sessions.state.
    """
    with engine.connect() as connection:
        return _rank_majors_from_keywords(
            connection,
            saved_keywords,
        )

def _refresh_user_recommendations(connection, user_id):
    """
    Read current account keywords, rank majors, and replace saved results.

    Must run inside a transaction whose caller has locked the user row.
    """
    keyword_query = text("""
        SELECT keyword_id, evidence
        FROM public.user_keywords
        WHERE user_id = :user_id
    """)

    rows = connection.execute(
        keyword_query,
        {"user_id": user_id},
    ).mappings().all()

    saved_keywords = [dict(row) for row in rows]

    recommendations = _rank_majors_from_keywords(
        connection,
        saved_keywords,
    )

    connection.execute(
        text("""
            DELETE FROM public.major_rec
            WHERE user_id = :user_id
        """),
        {"user_id": user_id},
    )

    if recommendations:
        connection.execute(
            text("""
                INSERT INTO public.major_rec (
                    user_id,
                    cipcode,
                    matching_keywords
                )
                VALUES (
                    :user_id,
                    :cipcode,
                    :matching_keywords
                )
            """),
            [
                {
                    "user_id": user_id,
                    "cipcode": item["cipcode"],
                    "matching_keywords": item["matching_keywords"],
                }
                for item in recommendations
            ],
        )

    return recommendations

def create_recommendations(user_id):
    with engine.begin() as connection:
        existing_user = connection.execute(
            text("""
                SELECT id
                FROM public.users
                WHERE id = :user_id
                FOR UPDATE
            """),
            {"user_id": user_id},
        ).scalar_one_or_none()

        if existing_user is None:
            raise ValueError("User does not exist.")

        return _refresh_user_recommendations(
            connection,
            user_id,
        )

def get_recommendations(user_id):
    query = text("""
        SELECT DISTINCT
            mr.cipcode,
            m.cipdesc AS major,
            k.id AS keyword_id,
            k.keyword,
            uk.evidence,
            mr.matching_keywords
        FROM public.major_rec mr
        JOIN public.majors m
            ON m.cipcode=mr.cipcode
        JOIN public.major_keywords mk
            ON mk.cipcode = mr.cipcode
        JOIN public.user_keywords uk
            ON uk.keyword_id = mk.keyword_id
            AND uk.user_id = mr.user_id
        JOIN public.keywords k
            ON k.id = uk.keyword_id
        WHERE mr.user_id = :user_id
        ORDER BY mr.matching_keywords DESC, mr.cipcode, k.keyword, k.id
    """)

    with engine.connect() as connection:
        rows = connection.execute(
            query,
            {
                "user_id": user_id
            },
        ).mappings().all()
    recs={}
    for row in rows:
        cipcode=row["cipcode"]
        if cipcode not in recs:
            recs[cipcode]={
            "cipcode":cipcode,
            "major":row["major"],
            "matching_keywords":row["matching_keywords"],
            "evidence":[]
            }
        rec=recs[cipcode]
        rec["evidence"].append({
            "keyword_id":row["keyword_id"],
            "keyword":row["keyword"],
            "evidence":row["evidence"]
        })
    
    return list(recs.values())


##Guest Sessions

def create_guest_session(guest_id):
    state = {
        "messages": [],
        "keywords": [],
        "preferences": {},
        "recommendations": [],
    }

    query = text("""
        INSERT INTO public.guest_sessions (guest_id, state)
        VALUES (:guest_id, CAST(:state AS JSONB))
        RETURNING state, version
    """)

    with engine.begin() as connection:
        row = connection.execute(
            query,
            {
                "guest_id": guest_id,
                "state": json.dumps(state),
            },
        ).mappings().one()

    return dict(row)


def get_guest_session(guest_id):
    query = text("""
        SELECT state, version
        FROM public.guest_sessions
        WHERE guest_id = :guest_id
          AND expires_at > CURRENT_TIMESTAMP
    """)

    with engine.connect() as connection:
        row = connection.execute(
            query,
            {"guest_id": guest_id},
        ).mappings().one_or_none()

    return dict(row) if row is not None else None


def save_guest_session(guest_id, state, expected_version):
    query = text("""
        UPDATE public.guest_sessions
        SET state = CAST(:state AS JSONB),
            version = version + 1,
            expires_at = CURRENT_TIMESTAMP + INTERVAL '24 hours'
        WHERE guest_id = :guest_id
          AND version = :expected_version
          AND expires_at > CURRENT_TIMESTAMP
        RETURNING version
    """)

    with engine.begin() as connection:
        new_version = connection.execute(
            query,
            {
                "guest_id": guest_id,
                "state": json.dumps(state),
                "expected_version": expected_version,
            },
        ).scalar_one_or_none()

    # None means the session expired or another request updated it.
    return new_version


def delete_expired_guest_sessions():
    query = text("""
        DELETE FROM public.guest_sessions
        WHERE expires_at <= CURRENT_TIMESTAMP
    """)

    with engine.begin() as connection:
        result = connection.execute(query)
        return result.rowcount



def get_major_favorites(user_id):
    with engine.connect() as connection:
        rows = connection.execute(
            text("""
                SELECT
                    m.cipcode,
                    m.cipdesc AS major
                FROM public.major_fav AS f
                JOIN public.majors AS m
                    ON m.cipcode = f.cipcode
                WHERE f.user_id = :user_id
                ORDER BY m.cipdesc, m.cipcode
            """),
            {"user_id": user_id},
        ).mappings().all()

    return [dict(row) for row in rows]

def get_comparison_favorites(user_id, kind):
    """Return only this user's favorites, including optional statistics."""
    if kind == "majors":
        query = text("""
            SELECT m.cipcode AS id, m.cipdesc AS name,
                   mi.mdn_earnings AS earnings,
                   mi.major_description AS description, mi.description_source,
                   (SELECT COUNT(*) FROM public.programs p
                    WHERE p.cipcode = m.cipcode) AS program_count,
                   (SELECT COUNT(DISTINCT p.unitid) FROM public.programs p
                    WHERE p.cipcode = m.cipcode) AS school_count
            FROM public.major_fav f
            JOIN public.majors m ON m.cipcode = f.cipcode
            LEFT JOIN public.major_info mi ON mi.cipcode = m.cipcode
            WHERE f.user_id = :user_id
            ORDER BY m.cipdesc, m.cipcode
        """)
    elif kind == "programs":
        query = text("""
            SELECT p.program_id AS id, m.cipdesc AS name, p.credlev,
                   s.instnm AS college, s.city, s.stabbr AS state,
                   s.ug12mn AS enrollment,
                   r.earn_mdn_4yr_nat AS earnings,
                   c.npt4, c.npt41, c.npt42, c.npt43, c.npt44, c.npt45,
                   c.tuitionfee_in, c.tuitionfee_out,
                   a.adm_rate, a.satmt25, a.satmt75, a.satvr25, a.satvr75,
                   a.satwr25, a.satwr75, a.actmt25, a.actmt75,
                   a.acten25, a.acten75, a.actwr25, a.actwr75
            FROM public.program_fav f
            JOIN public.programs p ON p.program_id = f.program_id
            JOIN public.majors m ON m.cipcode = p.cipcode
            JOIN public.schools s ON s.unitid = p.unitid
            LEFT JOIN public.cost_info c ON c.unitid = p.unitid
            LEFT JOIN public.adm_crit a ON a.unitid = p.unitid
            LEFT JOIN public.program_rank_crit r ON r.program_id = p.program_id
            WHERE f.user_id = :user_id
            ORDER BY m.cipdesc, s.instnm, p.credlev, p.program_id
        """)
    else:
        raise ValueError("Choose majors or programs.")
    with engine.connect() as connection:
        rows = connection.execute(query, {"user_id": user_id}).mappings().all()
    return [dict(row) for row in rows]


def is_program_favorite(user_id, program_id):
    with engine.connect() as connection:
        return connection.execute(text("""
            SELECT EXISTS (
                SELECT 1 FROM public.program_fav
                WHERE user_id = :user_id AND program_id = :program_id
            )
        """), {"user_id": user_id, "program_id": program_id}).scalar_one()


def get_program_favorites(user_id):
    """Lightweight list for Favorites and program-card saved states."""
    with engine.connect() as connection:
        rows = connection.execute(text("""
            SELECT p.program_id, p.cipcode, p.credlev,
                   m.cipdesc AS major, s.instnm AS college,
                   s.city, s.stabbr AS state
            FROM public.program_fav f
            JOIN public.programs p ON p.program_id = f.program_id
            JOIN public.majors m ON m.cipcode = p.cipcode
            JOIN public.schools s ON s.unitid = p.unitid
            WHERE f.user_id = :user_id
            ORDER BY m.cipdesc, s.instnm, p.credlev, p.program_id
        """), {"user_id": user_id}).mappings().all()
    return [dict(row) for row in rows]


def get_major_name_suggestions(query):
    # Treat LIKE wildcards in user input as literal characters.
    escaped = query.replace("!", "!!").replace("%", "!%").replace("_", "!_")
    with engine.connect() as connection:
        rows = connection.execute(text("""
            SELECT cipcode, cipdesc AS name
            FROM public.majors
            WHERE LOWER(cipdesc) LIKE LOWER(:query) ESCAPE '!'
            ORDER BY cipdesc, cipcode
            LIMIT 20
        """), {"query": "%" + escaped + "%"}).mappings().all()
    return [dict(row) for row in rows]


def get_major_catalog_page(page=1, page_count=25, *, query='', sort='name_asc',
                           earnings_min=None, favorites_only=False,
                           has_programs=False, user_id=None):
    """Page through majors, independently of the program catalog."""
    if type(page) is not int or not 1 <= page <= 100000:
        raise ValueError('Invalid page.')
    if type(page_count) is not int or not 1 <= page_count <= 100:
        raise ValueError('Invalid page size.')
    if not isinstance(query, str) or len(query.strip()) > 200:
        raise ValueError('Search must be at most 200 characters.')
    if earnings_min is not None and (type(earnings_min) is not int or not 0 <= earnings_min <= 2147483647):
        raise ValueError('Invalid minimum earnings.')
    if type(favorites_only) is not bool or type(has_programs) is not bool:
        raise ValueError('Invalid major filters.')
    if user_id is not None and (type(user_id) is not int or user_id <= 0):
        raise ValueError('Invalid user.')
    if favorites_only and user_id is None:
        raise ValueError('Sign in to filter your favorites.')
    sorts = {
        'name_asc': 'm.cipdesc ASC, m.cipcode ASC',
        'name_desc': 'm.cipdesc DESC, m.cipcode ASC',
        'earnings_desc': 'mi.mdn_earnings DESC NULLS LAST, m.cipcode ASC',
        'earnings_asc': 'mi.mdn_earnings ASC NULLS LAST, m.cipcode ASC',
        'programs_desc': 'COALESCE(counts.program_count, 0) DESC, m.cipcode ASC',
    }
    if sort not in sorts:
        raise ValueError('Invalid major sort.')
    params = {'user_id': user_id, 'limit': page_count + 1, 'offset': (page - 1) * page_count}
    conditions = []
    if query.strip():
        escaped = query.strip().replace('!', '!!').replace('%', '!%').replace('_', '!_')
        conditions.append("LOWER(m.cipdesc) LIKE LOWER(:query) ESCAPE '!'")
        params['query'] = '%' + escaped + '%'
    if earnings_min is not None:
        conditions.append('mi.mdn_earnings >= :earnings_min')
        params['earnings_min'] = earnings_min
    if favorites_only:
        conditions.append('EXISTS (SELECT 1 FROM public.major_fav f WHERE f.cipcode = m.cipcode AND f.user_id = :user_id)')
    if has_programs:
        conditions.append('COALESCE(counts.program_count, 0) > 0')
    where = ' AND '.join(conditions) if conditions else 'TRUE'
    statement = text(f"""
        SELECT m.cipcode, m.cipdesc AS major, mi.mdn_earnings AS earnings,
               mi.major_description AS description, mi.description_source,
               COALESCE(counts.program_count, 0) AS program_count,
               COALESCE(counts.school_count, 0) AS school_count,
               EXISTS (SELECT 1 FROM public.major_fav f
                       WHERE f.cipcode = m.cipcode AND f.user_id = :user_id) AS is_favorite
        FROM public.majors m
        LEFT JOIN public.major_info mi ON mi.cipcode = m.cipcode
        LEFT JOIN (
            SELECT cipcode, COUNT(*) AS program_count, COUNT(DISTINCT unitid) AS school_count
            FROM public.programs GROUP BY cipcode
        ) counts ON counts.cipcode = m.cipcode
        WHERE {where}
        ORDER BY {sorts[sort]}
        LIMIT :limit OFFSET :offset
    """)
    with engine.connect() as connection:
        rows = connection.execute(statement, params).mappings().all()
    return {'rows': [dict(row) for row in rows[:page_count]], 'page': page, 'has_next': len(rows) > page_count}
