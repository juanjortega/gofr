"""Crea el par Geoportal (fuente 1) -> DEIS (fuente 2, lista maestra) en GOFR y corre la reconciliación nivel
por nivel. Uso: python -I reconciliar.py"""
import json, os, sys, uuid
sys.path.insert(0, os.path.dirname(__file__))
import gofr_api as g

assert g.login('root@gofr.org', os.environ['GOFR_CLAVE']) == 200
fuentes = {s['display']: s for s in g.get('/datasource/getSource/' + g.USER_ID)[1]['sources']}
s1, s2 = fuentes['Geoportal'], fuentes['DEIS']

st, pares = g.get('/datasource/getSourcePair/' + g.USER_ID)
nombre_par = (s1['name'] + s2['display']).lower()
par = next((p for p in (pares if isinstance(pares, list) else []) if p.get('name', '').lower() == nombre_par), None)
if not par:
    st, r = g.post('/datasource/createSourcePair', {'source1': json.dumps(s1), 'source2': json.dumps(s2), 'name': 'Geoportal-DEIS',
                                                    'userID': g.USER_ID, 'orgId': '', 'singlePair': 'false', 'activePairID': 'false'})
    print('createSourcePair', st, r)
    st, pares = g.get('/datasource/getSourcePair/' + g.USER_ID)
    par = next(p for p in pares if p.get('name', '').lower() == nombre_par)
print('par', par['id'], par['name'])

st, niveles = g.get('/datasource/countLevels', source1Id=s1['id'], source1DB=s1['name'], source2Id=s2['id'],
                    source2DB=s2['name'], sourcesLimitOrgId=json.dumps({'source1LimitOrgId': [], 'source2LimitOrgId': []}))
print('countLevels', st, niveles)
t1, t2 = niveles['totalSource1Levels'], niveles['totalSource2Levels']

for nivel in range(2, t1 + 1):
    cid = uuid.uuid4().hex
    st, r = g.get('/match/reconcile', id='', partition1=s1['name'], partition2=s2['name'], mappingPartition=par['name'],
                  source1LimitOrgId='[]', source2LimitOrgId='[]', totalSource1Levels=t1, totalSource2Levels=t2,
                  recoLevel=nivel, clientId=cid, userID=g.USER_ID, parentConstraint='true', getPotential='true')
    if st != 200:
        print('nivel', nivel, 'HTTP', st, str(r)[:500])
        break
    p = g.esperar('scoreResults', cid) if not (isinstance(r, dict) and r.get('scoreResults')) else r
    datos = (p or {}).get('responseData') or r
    if not isinstance(datos, dict):
        print('nivel', nivel, 'sin resultados:', str(p)[:500])
        break
    res = datos.get('scoreResults', [])
    exactos = sum(1 for x in res if x.get('exactMatch'))
    con_potencial = sum(1 for x in res if not x.get('exactMatch') and x.get('potentialMatches'))
    sin = len(res) - exactos - con_potencial
    print(f'nivel {nivel}: {len(res)} de fuente 1 -> exactos {exactos}, con candidatos {con_potencial}, sin candidato {sin}',
          {k: datos.get(k) for k in ('totalAllMapped', 'totalAllNotMapped', 'totalAllFlagged', 'totalAllNoMatch')})
    json.dump(datos, open(os.path.join(os.path.dirname(__file__), '..', f'reco_nivel{nivel}.json'), 'w', encoding='utf-8'), ensure_ascii=False)
