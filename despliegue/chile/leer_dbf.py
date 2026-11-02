"""Lee el .dbf de un shapefile dentro de un zip. Uso: python -I leer_dbf.py <zip> [salida.csv]"""
import csv, struct, sys, zipfile


def leer(zip_path):
    z = zipfile.ZipFile(zip_path)
    nombre = next(n for n in z.namelist() if n.lower().endswith('.dbf'))
    b = z.read(nombre)
    n, hlen, rlen = struct.unpack('<IHH', b[4:12])
    campos, p = [], 32
    while b[p] != 0x0D:
        campos.append((b[p:p + 11].split(b'\0')[0].decode('ascii'), chr(b[p + 11]), b[p + 16]))
        p += 32
    filas = []
    for i in range(n):
        r = b[hlen + i * rlen: hlen + (i + 1) * rlen]
        if r[:1] == b'*':
            continue
        o, fila = 1, {}
        for nom, _, largo in campos:
            crudo = r[o:o + largo]
            try:
                fila[nom] = crudo.decode('utf-8').strip()
            except UnicodeDecodeError:
                fila[nom] = crudo.decode('latin-1').strip()
            o += largo
        filas.append(fila)
    return [c[0] for c in campos], filas


if __name__ == '__main__':
    cols, filas = leer(sys.argv[1])
    if len(sys.argv) > 2:
        with open(sys.argv[2], 'w', encoding='utf-8', newline='') as f:
            w = csv.DictWriter(f, cols)
            w.writeheader()
            w.writerows(filas)
    print(len(filas), cols)
    print(filas[0])
