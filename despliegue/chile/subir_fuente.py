"""Sube un CSV a GOFR como fuente de datos. Uso: python -I subir_fuente.py <nombre> <csv>"""
import os, sys, uuid
sys.path.insert(0, os.path.dirname(__file__))
import gofr_api as g

nombre, ruta = sys.argv[1:3]
assert g.login('root@gofr.org', os.environ['GOFR_CLAVE']) == 200
cid = uuid.uuid4().hex
campos = {'csvName': nombre, 'facility': 'nombre', 'code': 'codigo', 'lat': 'latitud', 'long': 'longitud',
          'level1': 'region', 'level2': 'comuna', 'level3': '', 'level4': '', 'level5': '', 'level6': '', 'level7': '',
          'clientId': cid, 'userID': g.USER_ID, 'orgId': ''}
st, r = g.post('/uploadCSV', campos, archivo=('file', ruta))
print('uploadCSV', st, r if st != 200 else '')
if st != 200:
    sys.exit(1)
p = g.esperar('uploadProgress', cid)
st, r2 = g.post('/datasource/addSource', {
    'host': '', 'sourceType': 'upload', 'source': 'upload', 'orgId': '', 'shareToSameOrgid': 'false', 'shareToAll': 'false',
    'limitByUserLocation': 'false', 'username': '', 'password': '', 'name': nombre, 'clientId': cid,
    'partitionID': r['partitionID'], 'levelData': r['levelData'], 'userID': g.USER_ID})
print('addSource', st, r2)
