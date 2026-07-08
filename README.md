# Observatorio Seguridad Social

Visualización interactiva de ingresos, gastos y transferencias del sistema de la Seguridad Social española, a partir de los informes **ResSISTEMA** ([fuente oficial](https://www.seg-social.es/wps/portal/wss/internet/InformacionEconomicoFinanciera/393/394)).

## Sitio web

**https://gbg93.github.io/observatorio-ss/**

El HTML se genera en [`docs/index.html`](docs/index.html) y GitHub Pages lo publica desde la carpeta `/docs`.

## Datos en el repositorio

| Ruta | Contenido |
|------|-----------|
| `data/processed/annual_breakdown.json` | Cierres anuales (2014–2025) |
| `data/processed/monthly/<año>/<Mes>.json` | Snapshots mensuales extraídos del ResSISTEMA |
| `data/processed/monthly/manifest.json` | Índice y último mes disponible por año |
| `data/raw/res_sistema/manifest.json` | Catálogo de descargas (sin Excel en git) |

Los ficheros `.xlsx` **no se suben** al repo; se procesan en local y se commitean solo los JSON.

## Actualizar datos y publicar

```bash
pip install -r requirements.txt

# 1. (Opcional) Descargar nuevos ResSISTEMA
python3 scripts/download_res_sistema.py

# 2. Extraer JSON anual + mensual desde xlsx locales
python3 scripts/extract_breakdown.py

# 3. Generar el observatorio
python3 scripts/build_observatorio.py
# → docs/index.html

# 4. Commit y push (JSON + docs/index.html)
git add data/processed docs/index.html
git commit -m "Actualizar datos ResSISTEMA"
git push
```

## GitHub Pages

Publicado desde `main` → `/docs`. Tras cada `git push`, el sitio se actualiza en unos minutos.

## Licencia

Código: [MIT](LICENSE).  
Datos agregados: informes públicos de la Tesorería General de la Seguridad Social / Seguridad Social.

¿Quieres contribuir? Lee [CONTRIBUTING.md](CONTRIBUTING.md).
