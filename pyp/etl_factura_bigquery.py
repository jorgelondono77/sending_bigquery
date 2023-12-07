import sys,os
import pandas as pd
from datetime import datetime,timedelta

PATH_TOOLS = os.environ.get("PATH_TOOLS")
path = os.path.abspath(PATH_TOOLS)
sys.path.insert(1,path)
import func_process
import load_bigquery as loadbq


fecha_mes = func_process.pd.to_datetime(datetime.now() - timedelta(days=15))
fecha_capita = func_process.pd.to_datetime(fecha_mes).strftime('%Y-%m-15')
fecha_i = func_process.pd.to_datetime(fecha_mes).strftime('%Y-%m-01 00:00:00')
fecha_f = f"{fecha_mes.strftime('%Y-%m')}-{fecha_mes.days_in_month} 23:59:59"


#CARGAMOS LA TABLAS TABLAS QUE VAMOS A ORGANIZAR
sql_capita_poblaciones = f"""
                            SELECT 
                                FECHA_CAPITA, 
                                NOMBRE_IPS, 
                                POBLACION_TOTAL, 
                                MENORES_A_18_ANOS, 
                                MAYORES_DE_18_ANOS, 
                                MUJERES_MAYORES_IGUAL_18_ANOS 
                            FROM `ia-bigquery-397516.pacientes.capitas_poblaciones`
                            WHERE FECHA_CAPITA = '{fecha_capita}';
                        """

sql_salud_familiar = f"""
                        SELECT * 
                        FROM salud_familiar 
                        WHERE (codigo_prestacion IN ('50120','50130','50140','50380','50382','50150','50190','37702'))
                            AND fecha_emision_orden BETWEEN '{fecha_i}' AND '{str(fecha_f)}'
                        ORDER BY fecha_emision_orden ASC;
                    """

sql_rips_obstetricia = f"""
                            SELECT * 
                            FROM `ia-bigquery-397516.rips.rips_auditoria_poblacion_2`
                            WHERE (codigo_sura IN ('50380','50382','7000075','7000076','7000077','70100','70101')) 
                                AND (FECHA_CAPITA = '{fecha_capita}') 
                            ORDER BY hora_fecha ASC;
                        """

sql_empleados_gestal = f"""
                            SELECT 
                                identificacion as identificacion_profesional_remite, 
                                estado_activo, 
                                sede as sede_gestal, 
                                cargo as cargo_gestal
                            FROM `ia-bigquery-397516.empleados.historicos`
                        """

# Parametros bigquery
project_id_product = 'ia-bigquery-397516'

# Rips
dataset_id_rips = 'rips'
table_name_rips_auditoria = 'rips_auditoria_poblacion_2'
TABLA_BIGQUERY_RIPS = f'{project_id_product}.{dataset_id_rips}.{table_name_rips_auditoria}'

# empleados
dataset_id_empleados = 'empleados'
table_name_historico = 'historico'
TABLA_BIGQUERY_EMPLEADOS = f'{project_id_product}.{dataset_id_empleados}.{table_name_historico}'

# Capita poblaciones
dataset_id_pacientes = 'pacientes'
table_name_capita_poblaciones = 'capitas_poblaciones'
TABLA_BIGQUERY_PACIENTES = f'{project_id_product}.{dataset_id_pacientes}.{table_name_capita_poblaciones}'


# Rips
dataset_id_rips = 'rips'
table_name_rips_auditoria = 'rips_auditoria_poblacion_2'
TABLA_BIGQUERY = f'{project_id_product}.{dataset_id_rips}.{table_name_rips_auditoria}'

#Creamos funcion para agregar columna con el nombre de la Consulta
def n_prestacion(codigo_prestacion):
    if codigo_prestacion == '50120':
        return 'Consultas MI'
    elif codigo_prestacion == '50130':
        return 'Consultas Pediatria'
    elif codigo_prestacion == '50140':
        return 'Consultas Ginecologia'
    elif (codigo_prestacion == '50380') | (codigo_prestacion == '50382'):
        return 'Consultas Obstetricia'
    elif codigo_prestacion == '50150':
        return 'Consultas Cirugia General'
    elif codigo_prestacion == '50190':
        return 'Consultas Dermatologia'
    elif codigo_prestacion == '37702':
        return 'Consultas Psicologia'
    
def p_total(f_capita, n_ips='COOPSANA IPS'):
    poblacion_total = df_capita_poblaciones_m[(df_capita_poblaciones_m['FECHA_CAPITA'] == f_capita) & (df_capita_poblaciones_m['NOMBRE_IPS'] == n_ips)].POBLACION_TOTAL.iloc[0]
    return poblacion_total


# Definir estado de profesional
def state_emp(id):
    if ((id == df_empleados[df_empleados['estado_activo'] == '1'].identificacion_profesional_remite).sum()) > 0:
        return 'ACTIVO'
    elif ((id == df_empleados[df_empleados['estado_activo'] == '2'].identificacion_profesional_remite).sum()) > 0:
        return 'INACTIVO'
    elif ((id == df_empleados[df_empleados['estado_activo'] == '3'].identificacion_profesional_remite).sum()) > 0:
        return 'INACTIVO'
    elif ((id == df_empleados[df_empleados['estado_activo'].isnull()].identificacion_profesional_remite).sum()) > 0:
        return 'INACTIVO'
    else:
        return 'EXTERNO'
    
# Read Data
df_capita_poblaciones = loadbq.read_data_bigquery(sql_capita_poblaciones,TABLA_BIGQUERY_PACIENTES)
df_salud_familiar = func_process.load_df_server(sql_salud_familiar, 'reportes')
df_rips_auditoria_obstetricia_2 = loadbq.read_data_bigquery(sql_rips_obstetricia,TABLA_BIGQUERY_RIPS)
df_empleados = loadbq.read_data_bigquery(sql_empleados_gestal,TABLA_BIGQUERY_EMPLEADOS)

# Transform
df_capita_poblaciones['FECHA_CAPITA'] = func_process.pd.to_datetime(df_capita_poblaciones['FECHA_CAPITA'],errors='coerce').dt.tz_convert(None)
df_salud_familiar.insert(0, 'FECHA_CAPITA', df_salud_familiar['fecha_emision_orden'].apply(lambda row: '{}{}{:02d}{}{}'.format(row.year, '-', row.month, '-', 15)))
df_salud_familiar.insert(1, 'NOMBRE_IPS', func_process.np.nan)
df_salud_familiar.loc[df_salud_familiar['ips_atiende'] == '35', 'NOMBRE_IPS'] = 'CENTRO'
df_salud_familiar.loc[df_salud_familiar['ips_atiende'] == '1013', 'NOMBRE_IPS'] = 'CALASANZ'
df_salud_familiar.loc[df_salud_familiar['ips_atiende'] == '2136', 'NOMBRE_IPS'] = 'NORTE'
df_salud_familiar.loc[df_salud_familiar['ips_atiende'] == '115393', 'NOMBRE_IPS'] = 'AVENIDA ORIENTAL'
df_salud_familiar.loc[df_salud_familiar['ips_atiende'] == '2715', 'NOMBRE_IPS'] = 'PAC'
df_salud_familiar["FECHA_CAPITA"] = func_process.pd.to_datetime(df_salud_familiar["FECHA_CAPITA"])
df_salud_familiar.insert(4, 'NOMBRE_PRESTACION', df_salud_familiar['codigo_prestacion'].apply(n_prestacion))

df_rips_auditoria_obstetricia_2_unicos = df_rips_auditoria_obstetricia_2.drop_duplicates(subset = ['identificacion_pac', 'fecha_capita'])
df_total_maternas = df_rips_auditoria_obstetricia_2_unicos.groupby(['fecha_capita', 'nombre_ips']).agg({'identificacion_pac':'count'}).reset_index().rename(columns={'fecha_capita':'FECHA_CAPITA', 'nombre_ips':'NOMBRE_IPS', 'identificacion_pac':'poblacion_maternas'})
df_total_maternas['FECHA_CAPITA'] = func_process.pd.to_datetime(df_total_maternas['FECHA_CAPITA'],errors='coerce').dt.tz_convert(None)
poblacion_maternas_coopsana = df_total_maternas.poblacion_maternas.sum()
atenciones_coopsana = func_process.pd.Series([fecha_capita,'COOPSANA IPS',poblacion_maternas_coopsana], index=df_total_maternas.columns )
df_total_maternas.loc[df_total_maternas.index.max()+1] = atenciones_coopsana

df_total_maternas['FECHA_CAPITA'] = func_process.pd.to_datetime(df_total_maternas['FECHA_CAPITA'])
df_capita_poblaciones_m = df_capita_poblaciones.merge(df_total_maternas, on= ['FECHA_CAPITA', 'NOMBRE_IPS'], how= 'left')
df_salud_familiar_poblacion = df_salud_familiar.merge(df_capita_poblaciones_m, how='left', on=['FECHA_CAPITA','NOMBRE_IPS'])
df_salud_familiar_poblacion.fillna(' ', inplace= True)

df_salud_familiar_poblacion['POBLACION_TOTAL_COOPSANA'] = df_salud_familiar_poblacion.apply(lambda x: p_total(x['FECHA_CAPITA']), axis=1)
df_salud_familiar_poblacion = df_salud_familiar_poblacion.loc[:, ['FECHA_CAPITA', 'NOMBRE_IPS', 'fecha_emision_orden', 'codigo_prestacion', 'NOMBRE_PRESTACION', 'ips_atiende', 'identificacion_profesional_remite', 'nombre_medico_remite', 'identificacion_paciente', 'nombre_paciente', 'edad', 'sexo', 'telefono', 'codigo_dx', 'descripcion_dx', 'identificacion_medico_familia', 'nombre_medico_familia', 'numero_orden', 'POBLACION_TOTAL', 'MENORES_A_18_ANOS', 'MAYORES_DE_18_ANOS', 'MUJERES_MAYORES_IGUAL_18_ANOS', 'poblacion_maternas', 'POBLACION_TOTAL_COOPSANA']]
df_salud_familiar_poblacion.poblacion_maternas = df_salud_familiar_poblacion.poblacion_maternas.astype('int64')
df_salud_familiar_poblacion['FECHA_CAPITA'] = df_salud_familiar_poblacion['FECHA_CAPITA'].astype('str')
df_salud_familiar_poblacion['fecha_emision_orden'] = df_salud_familiar_poblacion['fecha_emision_orden'].astype('str')
df_salud_familiar_poblacion['estado_empleado'] = df_salud_familiar_poblacion['identificacion_profesional_remite'].apply(state_emp)

df_empleados['identificacion_profesional_remite'] = df_empleados['identificacion_profesional_remite'].astype('str')
df_salud_familiar_poblacion['identificacion_profesional_remite'] = df_salud_familiar_poblacion['identificacion_profesional_remite'].astype('str')
df_salud_familiar_poblacion_gestal = df_salud_familiar_poblacion.merge(df_empleados[['identificacion_profesional_remite', 'sede_gestal', 'cargo_gestal']], on='identificacion_profesional_remite', how='left')
df_salud_familiar_poblacion_gestal.loc[df_salud_familiar_poblacion_gestal['sede_gestal'].isnull(), "sede_gestal"] = "EXTERNO"
df_salud_familiar_poblacion_gestal.loc[df_salud_familiar_poblacion_gestal['cargo_gestal'].isnull(), "cargo_gestal"] = "EXTERNO"

print(df_salud_familiar_poblacion_gestal.head())
# Load
#func_process.save_df_server(df_salud_familiar_poblacion_gestal, 'salud_familiar_poblacion', 'analitica')