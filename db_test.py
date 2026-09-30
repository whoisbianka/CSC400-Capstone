import pandas as pd
from sqlalchemy import create_engine
import numpy as np
import db_functions
from cloud_sql_connection import close_connector

crit="earn_mdn_4yr_nat"
n=10
cipc1=1107
cipc2=3008

# res=db_functions.get_best_progs_from_cip(n,cipc1,crit)
# close_connector()

#EXAMPLES OF GET_A_PAGE and SCAN_ENTIRE_TABLE USAGE
print(db_functions.get_a_page(1,10,"schools","instnm",order="ASC"))
def process_row(input_row):
    if input_row.stabbr=="CT":
        print(input_row.instnm)

for row in db_functions.scan_entire_table("schools",5000):
    process_row(row)
    
close_connector()
# db_functions.add_user(1,"Bryan", "Begley", "begley.bryan3@gmail.com", "blahblah")

# db_functions.add_major_to_favorite(1,1107)
# db_functions.add_major_to_favorite(1,3008)

# db_functions.get_user_fav_majors(1)

# db_functions.remove_from_major_fav(1,69)

# db_functions.remove_user(1)

