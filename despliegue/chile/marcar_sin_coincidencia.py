"""Marca como «sin coincidencia» los establecimientos de la fuente 1 que quedaron sin coincidencia exacta en la
última reconciliación (reco_nivel<N>.json que deja reconciliar.py). Uso: python -I marcar_sin_coincidencia.py [nivel]"""
import json, os, sys
sys.path.insert(0, os.path.dirname(__file__))
import gofr_api as g

nivel = sys.argv[1] if len(sys.argv) > 1 else '4'
datos = json.load(open(os.path.join(os.path.dirname(__file__), '..', f'reco_nivel{nivel}.json'), encoding='utf-8'))
pendientes = [x['source1'] for x in datos['scoreResults'] if not x.get('exactMatch')]

assert g.login('root@gofr.org', os.environ['GOFR_CLAVE']) == 200
fuentes = {s['display']: s for s in g.get('/datasource/getSource/' + g.USER_ID)[1]['sources']}
s1, s2 = fuentes['Geoportal'], fuentes['DEIS']
nombre_par = (s1['name'] + s2['display']).lower()
par = next(p for p in g.get('/datasource/getSourcePair/' + g.USER_ID)[1] if p.get('name', '').lower() == nombre_par)
ok = 0
for x in pendientes:
    st, r = g.post('/match/noMatch/nomatch', {
        'partition1': s1['name'], 'partition2': s2['name'], 'mappingPartition': par['name'], 'source1Id': x['id'],
        'recoLevel': nivel, 'totalLevels': datos.get('totalSource1Levels', 4), 'pairId': par['id']})
    ok += st == 200
    if st != 200:
        print('falló', x['name'], st, r)
print(f'marcados sin coincidencia: {ok} de {len(pendientes)}')
