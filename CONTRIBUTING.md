# Contribuir al Observatorio SS

Gracias por ayudar a mantener actualizado [observatorio-ss](https://github.com/GBG93/observatorio-ss).

El código está bajo licencia [MIT](LICENSE) y los datos agregados provienen de los informes públicos ResSISTEMA de la Seguridad Social.

**Sitio publicado:** https://gbg93.github.io/observatorio-ss/

---

## Resumen rápido

| Quieres… | Comandos clave | Qué commitear |
|----------|----------------|---------------|
| **Actualizar datos** | `extract_breakdown.py` → `build_observatorio.py` | JSON en `data/processed/` + `docs/index.html` |
| **Cambiar gráficos o textos** | `build_observatorio.py` | `scripts/` + `docs/index.html` |
| **Solo documentación** | — | `.md` u otros docs |

Los ficheros `.xlsx` y `.pdf` del ResSISTEMA **no se suben al repo** (están en `.gitignore`).  
Solo se versionan los JSON procesados.

---

## 1. Fork y rama

1. Haz **fork** de [GBG93/observatorio-ss](https://github.com/GBG93/observatorio-ss).
2. Clona tu fork:

   ```bash
   git clone https://github.com/TU_USUARIO/observatorio-ss.git
   cd observatorio-ss
   ```

3. Añade el remoto upstream (recomendado):

   ```bash
   git remote add upstream https://github.com/GBG93/observatorio-ss.git
   ```

4. Crea una rama desde `main` actualizado:

   ```bash
   git fetch upstream
   git checkout main
   git merge upstream/main
   git checkout -b datos/res-sistema-2025-05   # o feat/... fix/... docs/...
   ```

**Convención de ramas:**

- `datos/...` → actualizaciones del ResSISTEMA
- `feat/...` → nuevas funciones
- `fix/...` → correcciones
- `docs/...` → documentación

---

## 2. Entorno local

```bash
python3 -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

---

## 3. Actualizar datos ResSISTEMA

Fuente oficial: [Información económico-financiera — Seguridad Social](https://www.seg-social.es/wps/portal/wss/internet/InformacionEconomicoFinanciera/393/394).

Coloca los Excel en `data/raw/res_sistema/` (local, no se suben a git).

```bash
# (Opcional) Descargar informes nuevos
python3 scripts/download_res_sistema.py

# Extraer JSON anual + mensual
python3 scripts/extract_breakdown.py

# Regenerar el observatorio
python3 scripts/build_observatorio.py
# → docs/index.html
```

**Archivos que suelen cambiar en una PR de datos:**

- `data/processed/annual_breakdown.json`
- `data/processed/monthly/<año>/<Mes>.json`
- `data/processed/monthly/manifest.json`
- `docs/index.html`

**Comprueba antes de abrir la PR:**

- Totales de ingresos y gastos coinciden con el ResSISTEMA del mes.
- Cotizaciones, prestaciones y transferencias del Estado son coherentes.
- El selector de mes muestra el periodo esperado.

---

## 4. Cambios de código o UI

Si modificas gráficos, textos o pestañas:

```bash
python3 scripts/build_observatorio.py
```

Incluye siempre `docs/index.html` regenerado: es lo que publica GitHub Pages.

Para probar en local:

```bash
python3 -m http.server --directory docs 8080
# http://localhost:8080/
```

---

## 5. Commit y Pull Request

```bash
git add data/processed docs/index.html   # ajusta según tu cambio
git commit -m "datos: ResSISTEMA mayo 2025"
git push origin HEAD
```

Abre la PR hacia `main` en [GBG93/observatorio-ss](https://github.com/GBG93/observatorio-ss).  
GitHub rellenará la plantilla con el checklist; complétala.

**Ejemplos de títulos:**

- `datos: ResSISTEMA abril 2025`
- `feat: leyenda unificada en histórico YoY`
- `fix: orden segmentos en gráfico de ingresos`

---

## 6. Revisión y publicación

- El mantenedor puede pedir cambios o hacer squash merge.
- Tras el merge, GitHub Pages actualiza el sitio en unos minutos.
- No hace falta tocar la configuración (`main` → `/docs`).

---

## Antes de un cambio grande

Abre un [Issue](https://github.com/GBG93/observatorio-ss/issues) si planeas:

- una nueva fuente de datos distinta del ResSISTEMA,
- nuevas pestañas o métricas,
- un rediseño amplio de la UI.

---

## Notas

- Este proyecto es informativo; no sustituye asesoramiento financiero ni legal.
- Por favor, mantén un tono respetuoso en issues y PRs.
