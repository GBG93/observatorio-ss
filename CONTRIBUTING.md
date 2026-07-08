# Cómo contribuir

Gracias por interesar en el [observatorio-ss](https://github.com/GBG93/observatorio-ss). Este repo es público bajo [MIT](LICENSE); las contribuciones entran por **Pull Request**.

## Antes de empezar

- Abre un [Issue](https://github.com/GBG93/observatorio-ss/issues) si el cambio es grande (nueva pestaña, fuente de datos distinta, rediseño amplio).
- Los datos son agregados del **ResSISTEMA** oficial. Indica siempre mes/año y enlace o fichero fuente.
- **No subas `.xlsx` ni `.pdf`** al repo. Solo JSON procesado y, si aplica, HTML regenerado.

## Flujo recomendado

1. **Fork** del repositorio en tu cuenta de GitHub.
2. **Clona** tu fork y crea una rama descriptiva:
   ```bash
   git checkout -b feat/descripcion-corta
   ```
3. **Implementa** el cambio (código, datos o documentación).
4. **Commit** con mensaje claro en español o inglés.
5. **Push** a tu fork y abre una **Pull Request** hacia `main` de `GBG93/observatorio-ss`.

## Cambios solo de código o textos (UI)

```bash
pip install -r requirements.txt
python3 scripts/build_observatorio.py
```

Incluye en la PR:

- Archivos modificados en `scripts/`
- `docs/index.html` regenerado (sitio publicado en GitHub Pages)

## Actualizar datos ResSISTEMA

Los Excel van en local (`data/raw/res_sistema/`, gitignored). En el repo solo van los JSON.

```bash
pip install -r requirements.txt

# Opcional: descargar nuevos informes
python3 scripts/download_res_sistema.py

# Extraer JSON anual + mensual
python3 scripts/extract_breakdown.py

# Regenerar el observatorio
python3 scripts/build_observatorio.py
```

Incluye en la PR:

- `data/processed/annual_breakdown.json` (si cambia el cierre anual)
- `data/processed/monthly/<año>/<Mes>.json` (meses nuevos o revisados)
- `data/processed/monthly/manifest.json`
- `docs/index.html`

Revisa que las cifras sean coherentes con el ResSISTEMA publicado (totales ingresos/gastos, cotizaciones, transferencias Estado).

## Qué no hace falta tocar

- Configuración de GitHub Pages (`main` → `/docs`) — ya está hecha.
- Ficheros en `data/raw/res_sistema/*.xlsx` — no se versionan.

## Revisión

El mantenedor revisará la PR y puede pedir ajustes. Al mergear en `main`, el sitio se actualiza en unos minutos: https://gbg93.github.io/observatorio-ss/

## Código de conducta

Sé respetuoso en issues y PRs. Este es un proyecto de datos públicos con fines informativos; no es asesoramiento financiero ni legal.
