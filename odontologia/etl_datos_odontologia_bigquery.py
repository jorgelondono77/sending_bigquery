import pandas as pd
import numpy as np 
import sys,os 

PATH_TOOLS = os.environ.get("PATH_TOOLS")
path = os.path.abspath(PATH_TOOLS)
sys.path.insert(1,path)
import func_process
import load_bigquery as loadbq

SQL_ODONTOLOGIA_DATOS_VIEW = """SELECT *
                    FROM reportes.datos_rips_odontologia_view AS r
                    WHERE r.fecha_consulta >= adddate(CURDATE(), INTERVAL -7 DAY)
                """

SQL_BIGQUERY = """
                SELECT g.id_atencion
                FROM {} as g
                WHERE g.id_atencion IN {}
                """

project_id_product = 'ia-bigquery-397516'
dataset_id = 'odontologia'
table_name = 'datos_rips_odontologia_partition'
validator_column = 'id_atencion'

TABLA_BIGQUERY = f'{project_id_product}.{dataset_id}.{table_name}'

# Convertir fechas
def convert_dates(df):
    df.fecha_consulta = pd.to_datetime(df.fecha_consulta, errors='coerce')
    df.hora_cita = df.hora_cita.astype(str)
    df.hora_finaliza_cita = df.hora_finaliza_cita.astype(str)
    df.hora_cita = [row.replace('0 days ','') for row in df.hora_cita]
    df.hora_finaliza_cita = [row.replace('0 days ','') for row in df.hora_finaliza_cita]
    return df

# Leer datos
df_datos_odontologia_bd = func_process.load_df_server(SQL_ODONTOLOGIA_DATOS_VIEW, 'reportes')   

# Convertir tipo de datos
df_datos_odontologia_bd = convert_dates(df_datos_odontologia_bd)

# Obtener datos no duplicados
valores_unicos = tuple(map(str, df_datos_odontologia_bd[validator_column]))
df_datos_odontologia_not_duplicates = loadbq.rows_not_duplicates(df_datos_odontologia_bd,validator_column,SQL_BIGQUERY,TABLA_BIGQUERY,valores_unicos)

# Save data
loadbq.load_data_bigquery(df_datos_odontologia_not_duplicates,TABLA_BIGQUERY)
