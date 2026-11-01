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

Se mantiene HAPI 5.5.2 porque GOFR depende de su particionado por URL (`/fhir/DEFAULT/...`, una partición por fuente de datos). Con HAPI 5.5 el dialecto es `PostgreSQL10Dialect`, porque `HapiFhirPostgres94Dialect` no existe en esa versión.

## Resultado esperado del primer arranque

GOFR carga sus perfiles en la partición `DEFAULT` y termina con `Done loading Default data`: 48 StructureDefinition, 29 CodeSystem, 30 ValueSet, 4 Questionnaire y 1 Location, sin errores. Si HAPI tarda más de 120 s en arrancar con la base vacía, GOFR sale y `restart: unless-stopped` lo vuelve a intentar.

## Pendiente

- Cargar los establecimientos de Chile (DEIS) y probar la reconciliación entre fuentes.
- Usar el mismo servidor FHIR que iHRIS: hoy cada uno tiene su HAPI, porque GOFR necesita HAPI 5.5 con particiones e iHRIS usa 6.8.
