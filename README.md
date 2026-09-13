# Observatorio Seguridad Social

Visualización interactiva de ingresos, gastos y transferencias del sistema de la Seguridad Social española, basada en los informes oficiales **ResSISTEMA** ([fuente](https://www.seg-social.es/wps/portal/wss/internet/InformacionEconomicoFinanciera/393/394)).

## Sitio web

**https://gbg93.github.io/observatorio-ss/**

El HTML final se genera en [`docs/index.html`](docs/index.html).  
GitHub Pages publica el sitio desde la carpeta `/docs`.

## Datos incluidos en el repositorio

| Ruta | Contenido |
|------|-----------|
| `data/processed/annual_breakdown.json` | Cierres anuales (2014–2025) |
| `data/processed/monthly/<año>/<Mes>.json` | Snapshots mensuales extraídos del ResSISTEMA |
| `data/processed/monthly/manifest.json` | Índice y último mes disponible por año |
| `data/processed/altas_bajas/monthly.json` | Altas/bajas de pensiones contributivas (clase × tipo, 2016–hoy) |
| `data/raw/res_sistema/manifest.json` | Catálogo de descargas ResSISTEMA (sin Excel en git) |
| `data/raw/altas_bajas/manifest.json` | Catálogo de descargas EST23/2575 (sin Excel en git) |

Los ficheros `.xlsx` del ResSISTEMA y de altas/bajas **no se suben** al repositorio.  
Se procesan en local y solo se versionan los JSON generados.

## Actualizar datos y publicar

```bash
pip install -r requirements.txt

# 1. (Opcional) Descargar nuevos ResSISTEMA
python3 scripts/download_res_sistema.py

# 2. Extraer JSON anual + mensual desde los xlsx locales
python3 scripts/extract_breakdown.py

# 2b. (Opcional) Altas/bajas de pensiones (EST23/2575)
python3 scripts/download_altas_bajas.py
python3 scripts/extract_altas_bajas.py

# 3. Generar el observatorio
python3 scripts/build_observatorio.py
# → docs/index.html

# 4. Commit y push (JSON + docs/index.html)
git add data/processed docs/index.html
git commit -m "Actualizar datos ResSISTEMA"
git push
```

## GitHub Pages

El sitio se publica desde `main` → `/docs`.  
Tras cada push, GitHub Pages actualiza la web en unos minutos.

## Contribuir

Las pull requests son bienvenidas. Guía completa en **[CONTRIBUTING.md](CONTRIBUTING.md)**.

Resumen del flujo:

**fork** → rama (`datos/…` o `feat/…`) → extractores + `build_observatorio.py` → commit JSON + `docs/index.html` → **PR** hacia `main`

(Si solo cambias código o textos del observatorio, basta con `build_observatorio.py`.)

## Licencia

Código: [MIT](LICENSE).  
Datos agregados: informes públicos de la Tesorería General de la Seguridad Social / Seguridad Social.
