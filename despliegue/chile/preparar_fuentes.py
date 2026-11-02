"""Convierte el CSV del DEIS y la capa del geoportal al CSV que sube GOFR: codigo, nombre, region, comuna,
latitud, longitud. Solo establecimientos vigentes. Región y comuna se nombran desde el CUT con los nombres
del DEIS, para que la jerarquía de ambas fuentes coincida y la reconciliación compare establecimientos.
Uso: python -I preparar_fuentes.py <deis.csv> <geoportal.zip> <dir-salida>"""
import csv, os, sys
sys.path.insert(0, os.path.dirname(__file__))
from leer_dbf import leer

deis_csv, geo_zip, salida = sys.argv[1:4]
COLS = ['codigo', 'nombre', 'region', 'comuna', 'latitud', 'longitud']

deis = list(csv.DictReader(open(deis_csv, encoding='utf-8-sig', newline=''), delimiter=';'))
comunas = {x['ComunaCodigo'].zfill(5): (x['RegionGlosa'], x['ComunaGlosa']) for x in deis}


def num(v):
    try:
        return '%.6f' % float(v) if v else ''
    except ValueError:
        return ''


def escribir(nombre, filas):
    with open(os.path.join(salida, nombre), 'w', encoding='utf-8', newline='') as f:
        w = csv.DictWriter(f, COLS)
        w.writeheader()
        w.writerows(filas)
    print(nombre, len(filas))


escribir('deis.csv', [
    {'codigo': x['EstablecimientoCodigo'], 'nombre': x['EstablecimientoGlosa'].strip(),
     'region': x['RegionGlosa'], 'comuna': x['ComunaGlosa'],
     'latitud': num(x['Latitud']), 'longitud': num(x['Longitud'])}
    for x in deis if x['EstadoFuncionamiento'].lower().startswith('vigente')])

_, geo = leer(geo_zip)
filas, sin_comuna = [], 0
for x in geo:
    if not x['ESTADO'].lower().startswith('vigente'):
        continue
    cut = x['CUT_COMUNA'].zfill(5)
    if cut not in comunas:
        sin_comuna += 1
        continue
    region, comuna = comunas[cut]
    filas.append({'codigo': str(int(float(x['COD_VIG']))), 'nombre': x['NOMBRE'].strip(), 'region': region,
                  'comuna': comuna, 'latitud': num(x['LATITUD']), 'longitud': num(x['LONGITUD'])})
escribir('geoportal.csv', filas)
print('geoportal sin comuna DEIS:', sin_comuna)
