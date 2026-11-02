"""Cliente mínimo de la API de GOFR (sesión por cookie y formularios multipart como la interfaz)."""
import http.cookiejar, json, os, time, urllib.parse, urllib.request, uuid

BASE = os.environ.get('GOFR_URL', 'http://127.0.0.1:18302')
USER_ID = 'pJryMYLm5MFB6Skk5EsE1m'  # GOFR Admin del IG de ejemplo
_op = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()))


def _req(metodo, ruta, datos=None, archivo=None, cuerpo_json=None):
    h = {}
    cuerpo = None
    if cuerpo_json is not None:
        cuerpo, h['Content-Type'] = json.dumps(cuerpo_json).encode(), 'application/json'
    elif datos is not None or archivo:
        b = uuid.uuid4().hex
        partes = []
        for k, v in (datos or {}).items():
            partes.append(f'--{b}\r\nContent-Disposition: form-data; name="{k}"\r\n\r\n{v}\r\n'.encode())
        if archivo:
            nombre, ruta_local = archivo
            partes.append(f'--{b}\r\nContent-Disposition: form-data; name="file"; filename="{os.path.basename(ruta_local)}"\r\n'
                          'Content-Type: text/csv\r\n\r\n'.encode() + open(ruta_local, 'rb').read() + b'\r\n')
        cuerpo = b''.join(partes) + f'--{b}--\r\n'.encode()
        h['Content-Type'] = f'multipart/form-data; boundary={b}'
    r = urllib.request.Request(BASE + ruta, data=cuerpo, headers=h, method=metodo)
    try:
        with _op.open(r, timeout=600) as resp:
            t = resp.read()
            return resp.status, (json.loads(t) if t[:1] in (b'{', b'[') else t.decode('utf-8', 'replace'))
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode('utf-8', 'replace')[:2000]


def login(usuario, clave):
    return _req('POST', '/auth/login', cuerpo_json={'username': usuario, 'password': clave})[0]


def get(ruta, **q):
    return _req('GET', ruta + ('?' + urllib.parse.urlencode(q) if q else ''))


def post(ruta, datos=None, archivo=None):
    return _req('POST', ruta, datos=datos, archivo=archivo)


def esperar(tipo, client_id, limite=1800):
    t0, ultimo = time.time(), None
    while time.time() - t0 < limite:
        st, p = get(f'/progress/{tipo}/{client_id}')
        if isinstance(p, dict):
            if p != ultimo:
                print('  ', {k: p.get(k) for k in ('status', 'percent', 'error')}, flush=True)
                ultimo = p
            if p.get('error') or p.get('status') == 'Done':
                return p
        time.sleep(5)
    return None
