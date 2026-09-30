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

print(db_functions.get_page(1,10,"schools","instnm",order="ASC"))
close_connector()
# db_functions.add_user(1,"Bryan", "Begley", "begley.bryan3@gmail.com", "blahblah")

# db_functions.add_major_to_favorite(1,1107)
# db_functions.add_major_to_favorite(1,3008)

# db_functions.get_user_fav_majors(1)

# db_functions.remove_from_major_fav(1,69)

# db_functions.remove_user(1)

