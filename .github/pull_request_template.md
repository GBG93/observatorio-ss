## Qué cambia

<!-- 1–3 frases: qué hace esta PR y por qué -->

## Tipo

- [ ] **Datos** — nuevo mes o revisión ResSISTEMA
- [ ] **Código / UI** — gráficos, textos o lógica del observatorio
- [ ] **Documentación**
- [ ] **Otro** — describe abajo

---

## Datos ResSISTEMA *(marca solo si aplica)*

| Campo | Valor |
|-------|-------|
| Mes / año | |
| Enlace o fichero fuente | |
| ¿Revisión de mes ya publicado? | Sí / No |

**Checklist datos**

- [ ] `python3 scripts/extract_breakdown.py` ejecutado sin errores
- [ ] JSON actualizados en `data/processed/` (anual, mensual, manifest)
- [ ] Totales ingresos / gastos / transferencias revisados contra la fuente
- [ ] `docs/index.html` regenerado con `build_observatorio.py`

---

## Código / UI *(marca solo si aplica)*

**Checklist código**

- [ ] `python3 scripts/build_observatorio.py` ejecutado
- [ ] `docs/index.html` incluido en el commit
- [ ] Probado en local (`docs/index.html` o `python3 -m http.server --directory docs`)

**Pestañas o gráficos tocados:**

<!-- p. ej. Panorama, Histórico, Transferencias -->

---

## General

- [ ] No incluyo `.xlsx`, `.pdf`, `.env` ni secretos
- [ ] El diff es acotado a lo necesario para este cambio

## Cómo probar

<!-- Pasos concretos para quien revise la PR -->

## Capturas *(opcional, recomendado si cambia la UI)*

<!-- Arrastra imágenes aquí -->

## Issue relacionado

<!-- Closes #123 — o "N/A" -->
