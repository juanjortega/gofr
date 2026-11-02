# Despliegue de GOFR

Stack Docker Compose para levantar GOFR (registro de establecimientos mCSD) con su servidor FHIR (HAPI 5.5 sobre PostgreSQL) y Redis. Se usa como directorio de establecimientos en otros proyectos, junto con iHRIS para los prestadores (ver `juanjortega/iHRIS`, rama `despliegue`).

```bash
python scripts/generar_env.py
docker compose up -d
```

- GOFR: http://localhost:18302
- FHIR: http://localhost:18303/fhir/DEFAULT

Los puertos solo escuchan en 127.0.0.1. Se cambian con `GOFR_PUERTO` y `GOFR_FHIR_PUERTO`, y la versión de la imagen con `GOFR_VERSION` (por defecto `22d71e4b`, la última publicada en Docker Hub).

## Qué cambia respecto de `instant/docker/docker-compose.yml`

| Original | Este despliegue |
|---|---|
| HAPI guarda en H2 dentro del contenedor: los datos se pierden al recrearlo | HAPI guarda en PostgreSQL, en un volumen |
| Índice Lucene en `target/lucenefiles`, fuera del volumen | Índice en `/data/hapi/lucene`, con el servicio `permisos` que deja el volumen del usuario 65532 de HAPI |
| `intrahealth/gofr:latest` y `redis:alpine` | Versiones fijas |
| Puertos 8080 y 4000 abiertos en todas las interfaces | Solo 127.0.0.1, en puertos que no chocan con iHRIS (18300 y 18301) |
| `app__installed=${false}` (interpolación inválida) | Se omite: GOFR carga sus datos iniciales al primer arranque |
| GOFR no sabe dónde está la base de HAPI y busca `localhost:5432` | `database__*` apunta al servicio `db` (ver abajo) |

**GOFR usa la base de HAPI directamente.** Al subir una fuente escribe, además de los `Location` por FHIR, una tabla SQL con el nombre de la partición en la misma base PostgreSQL de HAPI (`modules/uploadToSql.js`), y la reconciliación lee esas tablas. Sin `database__*` la subida parece terminar bien, pero no se crea la tabla y la reconciliación queda colgada en «1/3 Loading Source2 and Source1 Data» (`ECONNREFUSED 127.0.0.1:5432` o `relation "…" does not exist` en el log). Por esta dependencia GOFR no puede usar un servidor FHIR que no sea un HAPI con PostgreSQL al que tenga acceso SQL.

Se mantiene HAPI 5.5.2 porque GOFR depende de su particionado por URL (`/fhir/DEFAULT/...`, una partición por fuente de datos). Con HAPI 5.5 el dialecto es `PostgreSQL10Dialect`, porque `HapiFhirPostgres94Dialect` no existe en esa versión.

## Resultado esperado del primer arranque

GOFR carga sus perfiles en la partición `DEFAULT` y termina con `Done loading Default data`: 48 StructureDefinition, 29 CodeSystem, 30 ValueSet, 4 Questionnaire y 1 Location, sin errores. Si HAPI tarda más de 120 s en arrancar con la base vacía, GOFR sale y `restart: unless-stopped` lo vuelve a intentar.

Usuario de ejemplo: `root@gofr.org`, contraseña `gofr` (del IG de GOFR; verificado con `POST /auth/login`). Cambiarla antes de exponer el servicio.

## Establecimientos de Chile (`chile/`)

Scripts para cargar dos fuentes oficiales y reconciliarlas, con la API que usa la interfaz:

| Fuente | Origen | Vigentes |
|---|---|---|
| DEIS | [datos.gob.cl, «Establecimientos de Salud»](https://datos.gob.cl/dataset/establecimientos-de-salud-vigentes) (CSV `;`, corte 28-10-2026) | 5.406 |
| Geoportal | [IDE-Minsal, capa de establecimientos](https://www.minsal.cl/?p=96477) (shapefile, corte 12-06-2026) | 5.295 |

```bash
python -I chile/preparar_fuentes.py establecimientos_20261028.csv ESTABLECIMIENTOS_12062026_DES.zip salida/
GOFR_CLAVE=gofr python -I chile/subir_fuente.py DEIS salida/deis.csv
GOFR_CLAVE=gofr python -I chile/subir_fuente.py Geoportal salida/geoportal.csv
GOFR_CLAVE=gofr python -I chile/reconciliar.py
GOFR_CLAVE=gofr python -I chile/marcar_sin_coincidencia.py 4
```

`preparar_fuentes.py` deja ambas en el formato que espera GOFR (código, nombre, región, comuna, latitud y longitud, separado por comas), con la jerarquía región → comuna → establecimiento. Región y comuna se nombran desde el CUT con los nombres del DEIS para que la jerarquía coincida entre fuentes. `reconciliar.py` crea el par Geoportal (fuente 1) → DEIS (fuente 2, lista maestra) y calcula los puntajes nivel por nivel; deja el resultado de cada nivel en `reco_nivel<N>.json`. `marcar_sin_coincidencia.py` marca como «sin coincidencia» lo que quedó sin coincidencia exacta en ese nivel (revisar el JSON antes: aplica a todos).

Resultado verificado (las dos subidas juntas tardaron más de 10 minutos):

| Nivel | Fuente 1 | Coincidencia exacta | Solo con candidatos |
|---|---|---|---|
| Región | 16 | 16 | 0 |
| Comuna | 344 | 344 | 0 |
| Establecimiento | 5.295 | 5.276 | 19 |

- Las coincidencias exactas son por código DEIS, incluidos 21 establecimientos que cambiaron de nombre entre los dos cortes.
- Los 19 sin coincidencia exacta son establecimientos del geoportal que ya no están vigentes en el DEIS. GOFR les propone candidatos por nombre que son falsos positivos (por ejemplo, «SAPU Baquedano» con «SAPU Papudo», de otra comuna); quedaron marcados como «sin coincidencia» con `marcar_sin_coincidencia.py`. Una nueva reconciliación da 5.276 exactos, 19 sin coincidencia y 0 pendientes.
- 130 establecimientos del DEIS no están en el geoportal: son posteriores a junio.

### Farmacias

No hay una fuente abierta con el registro completo de farmacias. La de datos.gob.cl («Farmacias en Chile», Minsal) apunta a la API de Farmanet (`midas.minsal.cl/farmacia_v2/WS/getLocales.php`), que solo devuelve los locales que abren el día de la consulta (656 un domingo) y las farmacias de turno; no sirve como lista maestra. El registro del ISP no está publicado como datos abiertos. Queda pendiente conseguirlo por convenio.

## Servidor FHIR compartido con iHRIS

`compose.ihris.yaml` agrega iHRIS 5 sobre el mismo HAPI, en la partición `DEFAULT`:

```bash
docker compose -f compose.yaml -f compose.ihris.yaml up -d
```

Probado en un stack aparte con las imágenes publicadas y volúmenes vacíos: la configuración de iHRIS carga (316 de 317 recursos), iHRIS responde en :18301 con login de `demo@ihris.org`, y GOFR sigue funcionando con login de `root@gofr.org`. El cargador de iHRIS envía en paralelo y puede dejar algún recurso sin crear con un 409; en ese caso se repite la carga con `docker compose -f compose.yaml -f compose.ihris.yaml up -d --no-deps --force-recreate ihris-configuracion`. Diferencias respecto de iHRIS sobre HAPI 6.8:

- `ImplementationGuide/ihris` no carga (HAPI 5.5 responde 422). Es un recurso descriptivo; iHRIS no lo usa para funcionar.
- 35 CodeSystem y ValueSet estándar de HL7 (`location-mode`, `address-use`, `service-type`, etc.) existen en ambas configuraciones con el mismo id y la misma URL canónica; queda la copia que se carga al final (iHRIS). También se sobrescribe `StructureDefinition/ContactPoint`.
- El log de iHRIS muestra `Resource Basic/ihris-role-hrmanager is not known`, igual que sobre HAPI 6.8: es un defecto de la configuración de demostración, no del servidor compartido.

Es la única forma de compartir servidor: GOFR no funciona sobre HAPI 6.8 ni sobre otro servidor FHIR porque necesita las particiones por URL y acceso SQL a la base. El costo es quedar en HAPI 5.5.2 (2021), sin parches de seguridad recientes.

## Advertencias

- `uploadToSql.js` arma los `insert` interpolando código e id del CSV sin escapar (solo el nombre usa `escapeLiteral`). Subir solo CSV de fuentes confiables.

## Pendiente

- Conseguir el registro de farmacias (ISP o SEREMI) y sumarlo como fuente.
- Publicar la lista maestra reconciliada como mCSD hacia el servidor FHIR de producción.
