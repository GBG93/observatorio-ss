#!/usr/bin/env python3
"""Genera observatorio local con pestañas y gráficos Chart.js interactivos."""

from __future__ import annotations

import json
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA_PATH = ROOT / "data" / "processed" / "annual_breakdown.json"
OUT_DIR = ROOT / "docs"
OUT_FILE = OUT_DIR / "index.html"


def period_label(through_month: str | None, year: int) -> str:
    if not through_month:
        return str(year)
    if through_month == "Enero":
        return f"ene {year}"
    return f"ene–{MONTH_SHORT.get(through_month, through_month[:3]).lower()} {year}"


def load_ytd() -> dict:
    """Dato provisional acumulado del ejercicio actual desde JSON mensual."""
    import sys
    sys.path.insert(0, str(ROOT / "scripts"))
    from extract_breakdown import latest_monthly, load_monthly

    cur, cur_month = latest_monthly(2026)
    if not cur or not cur_month:
        return {}
    prev = load_monthly(2025, cur_month) or {}
    period = period_label(cur_month, 2026)
    prev_period = period_label(cur_month, 2025) if prev else None

    def yoy(a: float | None, b: float | None) -> float | None:
        if a is None or b is None or not b:
            return None
        return round((a - b) / b * 1000) / 10

    def pct_est_cot(d: dict) -> float | None:
        cot, est = d.get("cotizaciones"), d.get("transf_estado")
        if cot and est:
            return round(est / cot * 1000) / 10
        return None

    cur["period"] = period
    cur["prev_period"] = prev_period
    cur["through_month"] = cur_month
    cur["source_file"] = cur.get("source_file")
    cur["prev"] = prev
    cur["yoy"] = {
        "cotizaciones": yoy(cur.get("cotizaciones"), prev.get("cotizaciones")),
        "gastos_totales": yoy(cur.get("gastos_totales"), prev.get("gastos_totales")),
        "transf_estado": yoy(cur.get("transf_estado"), prev.get("transf_estado")),
    }
    cot = cur.get("cotizaciones") or 0
    gast = cur.get("gastos_totales") or 0
    ing = cur.get("ingresos_totales") or 0
    est = cur.get("transf_estado") or 0
    cur["cobertura_cotizaciones_pct"] = round(cot / gast * 100, 1) if gast else None
    cur["pct_estado_en_ingresos"] = round(est / ing * 100, 1) if ing and est else None
    cur["pct_estado_sobre_cotizaciones"] = pct_est_cot(cur)
    cur["pct_estado_sobre_cotizaciones_prev"] = pct_est_cot(prev)
    if cur["pct_estado_sobre_cotizaciones"] is not None and cur["pct_estado_sobre_cotizaciones_prev"] is not None:
        cur["pct_estado_sobre_cotizaciones_delta"] = round(
            cur["pct_estado_sobre_cotizaciones"] - cur["pct_estado_sobre_cotizaciones_prev"], 1
        )
    cur["deficit_cotizaciones"] = round(gast - cot, 1) if gast and cot else None
    try:
        annual = load_data()
        if annual:
            cur["cobertura_cierre_ref"] = annual[-1].get("cobertura_cotizaciones_pct")
            cur["cobertura_cierre_year"] = annual[-1]["year"]
    except Exception:
        pass
    out = {k: (round(v, 1) if isinstance(v, float) else v) for k, v in cur.items()}
    out["prev"] = {k: (round(v, 1) if isinstance(v, float) else v) for k, v in prev.items()}
    return out


MONTH_ORDER = {
    "Enero": 1, "Febrero": 2, "Marzo": 3, "Abril": 4, "Mayo": 5, "Junio": 6,
    "Julio": 7, "Agosto": 8, "Septiembre": 9, "Octubre": 10, "Noviembre": 11,
    "Diciembre": 12,
}
MONTH_SHORT = {
    "Enero": "Ene", "Febrero": "Feb", "Marzo": "Mar", "Abril": "Abr", "Mayo": "May",
    "Junio": "Jun", "Julio": "Jul", "Agosto": "Ago", "Septiembre": "Sep",
    "Octubre": "Oct", "Noviembre": "Nov", "Diciembre": "Dic",
}


def load_exercise_monthly(year: int = 2026) -> dict:
    import sys
    sys.path.insert(0, str(ROOT / "scripts"))
    from extract_breakdown import list_monthly_year

    months: list[dict] = []
    for row in list_monthly_year(year):
        row = {k: (round(v, 1) if isinstance(v, float) else v) for k, v in row.items()}
        month = row["month"]
        row["month_short"] = MONTH_SHORT.get(month, month[:3])
        months.append(row)
    return {"year": year, "months": months, "through": months[-1]["month"] if months else None}


def load_data() -> list[dict]:
    with open(DATA_PATH, encoding="utf-8") as f:
        return json.load(f)


def main() -> None:
    data = load_data()
    ytd = load_ytd()
    exercise = load_exercise_monthly(2026)
    payload = json.dumps(data, ensure_ascii=False)
    ytd_payload = json.dumps(ytd, ensure_ascii=False)
    exercise_payload = json.dumps(exercise, ensure_ascii=False)
    updated = date.today().isoformat()
    last_closed = data[-1]
    closed_label = f"{last_closed['year']} ({last_closed.get('source_month', 'cierre')})"

    html = f"""<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="utf-8" />
<meta name="viewport" content="width=device-width, initial-scale=1" />
<title>Observatorio: Seguridad Social</title>
<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.1/dist/chart.umd.min.js"></script>
<style>
  :root {{
    --bg: #f4f4f5; --card: #fff; --border: #e4e4e7; --text: #18181b;
    --muted: #71717a; --caption: #a1a1aa;
    --info: #3685bf; --danger: #cf2d56; --warning: #c08532;
    --success: #2d8a5c; --purple: #7c5cbf; --teal: #1a9e8f; --gray: #94a3b8;
  }}
  * {{ box-sizing: border-box; }}
  body {{ margin: 0; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
    background: var(--bg); color: var(--text); }}
  .topbar {{ background: var(--card); border-bottom: 1px solid var(--border); padding: 14px 24px;
    position: sticky; top: 0; z-index: 20; }}
  .topbar-inner {{ max-width: 1140px; margin: 0 auto; display: flex; justify-content: space-between;
    align-items: center; gap: 12px; flex-wrap: wrap; }}
  .brand {{ font-weight: 600; color: var(--info); font-size: 15px; }}
  .meta {{ font-size: 12px; color: var(--caption); }}
  .wrap {{ max-width: 1140px; margin: 0 auto; padding: 20px 24px 48px; }}
  .tabs {{ display: flex; gap: 4px; flex-wrap: wrap; margin-bottom: 20px; background: var(--card);
    border: 1px solid var(--border); border-radius: 10px; padding: 6px; }}
  .tab-btn {{ border: none; background: transparent; padding: 10px 16px; border-radius: 8px;
    font-size: 13px; font-weight: 500; color: var(--muted); cursor: pointer; transition: .15s; }}
  .tab-btn:hover {{ background: #f4f4f5; color: var(--text); }}
  .tab-btn.active {{ background: var(--info); color: #fff; }}
  .panel {{ display: none; flex-direction: column; gap: 20px; }}
  .panel.active {{ display: flex; }}
  .card {{ background: var(--card); border: 1px solid var(--border); border-radius: 10px; overflow: visible; }}
  .card-h {{ padding: 14px 18px 0; font-size: 15px; font-weight: 600; }}
  .card-b {{ padding: 14px 18px 18px; }}
  .caption {{ font-size: 12px; color: var(--caption); line-height: 1.5; margin: 0; }}
  .grid-3 {{ display: grid; grid-template-columns: repeat(3, 1fr); gap: 12px; }}
  .grid-4 {{ display: grid; grid-template-columns: repeat(4, 1fr); gap: 12px; }}
  .grid-2 {{ display: grid; grid-template-columns: 1fr 1fr; gap: 16px; }}
  .stat {{ display: flex; flex-direction: column; gap: 4px; }}
  .stat-v {{ font-size: 22px; font-weight: 600; }}
  .stat-l {{ font-size: 11px; color: var(--muted); line-height: 1.35; }}
  .callout {{ background: #fbf3e6; border: 1px solid #e8d4b0; border-radius: 10px; padding: 14px 18px; }}
  .callout-t {{ font-weight: 600; color: var(--warning); font-size: 14px; margin-bottom: 6px; }}
  .callout-b {{ font-size: 14px; color: var(--muted); line-height: 1.55; margin: 0; }}
  .lectura-pan {{ background: #eef5fb; border-color: #c5d9ed; margin-bottom: 16px; }}
  .lectura-pan .callout-t {{ color: var(--info); margin-bottom: 10px; }}
  .lectura-pan p {{ margin: 0 0 10px; font-size: 15px; line-height: 1.6; color: var(--text); }}
  .lectura-pan p:last-child {{ margin-bottom: 0; color: var(--muted); font-size: 13px; }}
  .lectura-pan .lectura-hint {{ font-size: 12px; color: var(--caption); }}
  .lectura-pan strong {{ font-weight: 600; color: var(--text); }}
  .chart-box {{ position: relative; width: 100%; }}
  .chart-box.tall {{ height: 360px; }}
  .chart-box.mid {{ height: 300px; }}
  .chart-box.short {{ height: 260px; }}
  .year-row {{ display: flex; align-items: center; gap: 12px; margin-bottom: 12px; flex-wrap: wrap; }}
  .year-nav {{ display: inline-flex; align-items: center; gap: 6px; }}
  .year-nav button {{
    width: 32px; height: 32px; border: 1px solid var(--border); border-radius: 8px;
    background: var(--card); cursor: pointer; font-size: 18px; line-height: 1; color: var(--muted);
  }}
  .year-nav button:hover {{ background: #f4f4f5; color: var(--text); }}
  .year-nav input[type=number] {{
    width: 72px; padding: 6px 8px; border: 1px solid var(--border); border-radius: 8px;
    font-size: 14px; font-weight: 600; text-align: center;
  }}
  .year-nav input[type=number]::-webkit-inner-spin-button {{ opacity: 1; }}
  .ejercicio-tag {{
    display: inline-block; font-size: 11px; font-weight: 600; color: var(--info);
    background: rgba(54,133,191,.1); padding: 3px 8px; border-radius: 6px; margin-left: 8px;
  }}
  .stat-pct .stat-v {{ font-size: 26px; }}
  .stat-pct .stat-unit {{ font-size: 14px; font-weight: 500; color: var(--text); }}
  .tone-info {{ color: var(--info); }} .tone-warn {{ color: var(--warning); }}
  .tone-danger {{ color: var(--danger); }} .tone-ok {{ color: var(--success); }}
  .tone-estado {{ color: #464c89; }}
  .tone-muted {{ color: var(--muted); font-weight: 500; }}
  .tr-pct-stat {{ background: #f8fafc; border: 1px solid var(--border); border-radius: 10px; padding: 14px 16px; }}
  .tr-pct-stat .stat-v {{ font-size: 24px; }}
  .hist-tcac-stat {{ text-align: center; }}
  .hist-tcac-stat .stat-v {{ font-size: 28px; }}
  .hist-tcac-unit {{ font-size: 15px; font-weight: 500; color: var(--text); }}
  @media (max-width: 800px) {{
    .grid-3, .grid-4 {{ grid-template-columns: 1fr; }}
    .grid-2 {{ grid-template-columns: 1fr; }}
  }}
</style>
</head>
<body>
<header class="topbar">
  <div class="topbar-inner">
    <span class="brand">Observatorio: Seguridad Social</span>
    <span class="meta">ResSISTEMA · mil M€ · Cierre {closed_label} · Actualizado {updated}</span>
  </div>
</header>
<div class="wrap">
  <nav class="tabs" role="tablist">
    <button class="tab-btn active" data-tab="panorama">Panorama</button>
    <button class="tab-btn" data-tab="ingresos">Ingresos</button>
    <button class="tab-btn" data-tab="gastos">Gastos</button>
    <button class="tab-btn" data-tab="transferencias">Transferencias</button>
    <button class="tab-btn" data-tab="historico">Histórico</button>
  </nav>

  <!-- PANORAMA = EJERCICIO ACTUAL -->
  <section id="panel-panorama" class="panel active">
    <div class="callout lectura-pan">
      <div class="callout-t" id="lectura-panorama-title">Lectura rápida</div>
      <div id="lectura-panorama"></div>
    </div>
    <p class="caption" id="panorama-period-note" style="margin:-8px 0 12px"></p>
    <div class="grid-4" id="kpi-panorama"></div>
    <div class="card">
      <div class="card-h" id="pan-main-title">Ingresos vs gastos — desglose de ingresos</div>
      <div class="card-b">
        <p class="caption">Ingresos: paleta Datawrapper ordenada por peso (base oscura = mayor segmento, arriba claro = menor). Gastos en gris-azulado neutro.</p>
        <div class="chart-box tall"><canvas id="chart-pan-ing-vs-gast"></canvas></div>
      </div>
    </div>
    <div class="grid-2">
      <div class="card">
        <div class="card-h">Transferencias del Estado (PGE)</div>
        <div class="card-b">
          <p class="caption">Evolución acumulada · mil M€.</p>
          <div class="chart-box mid"><canvas id="chart-pan-transf-est"></canvas></div>
        </div>
      </div>
      <div class="card">
        <div class="card-h">Déficit sin aportaciones del Estado (PGE)</div>
        <div class="card-b">
          <p class="caption">Ingresos sin transferencias PGE − gastos totales · mil M€. Por debajo de cero = déficit estructural.</p>
          <div class="chart-box mid"><canvas id="chart-pan-gast-sin-est"></canvas></div>
        </div>
      </div>
    </div>
  </section>

  <!-- INGRESOS -->
  <section id="panel-ingresos" class="panel">
    <div class="callout">
      <div class="callout-t">De dónde entra el dinero</div>
      <p class="callout-b">Los ingresos del sistema combinan cotizaciones sociales (principal fuente), transferencias corrientes (Estado, movimientos internos SS, CCAA…) y otros conceptos menores. Las cifras son recaudación neta acumulada a cierre de ejercicio.</p>
    </div>
    <div class="card">
      <div class="card-h">Evolución desglosada de ingresos</div>
      <div class="card-b">
        <div class="chart-box tall"><canvas id="chart-ing-stack"></canvas></div>
        <p class="caption">Eje Y: mil M€ · Apila cotizaciones, transferencias del Estado, transferencias internas SS, tasas y otros.</p>
      </div>
    </div>
    <div class="card">
      <div class="card-h">Evolución cotizaciones por régimen</div>
      <div class="card-b">
        <div class="chart-box tall"><canvas id="chart-ing-cot-stack"></canvas></div>
        <p class="caption">Eje Y: mil M€ · Desglose anual de cotizaciones por régimen de la Seguridad Social.</p>
      </div>
    </div>
  </section>

  <!-- GASTOS -->
  <section id="panel-gastos" class="panel">
    <div class="callout">
      <div class="callout-t">A dónde va el dinero</div>
      <p class="callout-b">La mayor parte del gasto son prestaciones: pensiones contributivas, subsidios (IT, desempleo…) y el bloque no contributivo (IMV, complementos a mínimos). La gestión (personal + bienes y servicios) es una fracción pequeña del total.</p>
    </div>
    <div class="card">
      <div class="card-h">Evolución desglosada de gastos</div>
      <div class="card-b">
        <div class="chart-box tall"><canvas id="chart-gast-stack"></canvas></div>
        <p class="caption">Eje Y: mil M€ · Pensiones, subsidios, no contributivo, gestión, inversiones y otras transferencias de salida.</p>
      </div>
    </div>
    <div class="card">
      <div class="card-h">Evolución del gasto en prestaciones</div>
      <div class="card-b">
        <div class="chart-box tall"><canvas id="chart-gast-prest-stack"></canvas></div>
        <p class="caption">Eje Y: mil M€ · Pensiones por tipo, IT, desempleo, IMV, complementos a mínimos y otras prestaciones.</p>
      </div>
    </div>
  </section>

  <!-- TRANSFERENCIAS -->
  <section id="panel-transferencias" class="panel">
    <div class="callout">
      <div class="callout-t">Dos cosas distintas bajo «transferencias»</div>
      <div class="callout-b">
        <p><strong>Lo que entra en el sistema</strong><br>
        Es dinero que llega desde fuera: del Estado, de las Comunidades Autónomas o de otras entidades de la Seguridad Social. Es financiación — ayuda a pagar pensiones y prestaciones.</p>
        <p style="margin-top:10px"><strong>Lo que sale del sistema</strong><br>
        Son las prestaciones que se pagan a la gente: pensiones, subsidios, ayudas por incapacidad, etc. Es gasto social — dinero que va a los ciudadanos.</p>
        <p style="margin-top:10px;font-size:13px;color:var(--caption)">Arriba: lo que entra. Abajo: lo que sale. No son el mismo concepto ni se comparan entre sí.</p>
      </div>
    </div>
    <div class="card">
      <div class="card-h">Lo que entra en el sistema</div>
      <div class="card-b">
        <div class="chart-box tall"><canvas id="chart-tr-ing-stack"></canvas></div>
        <p class="caption">Eje Y: mil M€ · Estado (PGE), movimientos internos SS, CCAA y otros aportes.</p>
      </div>
    </div>
    <div class="card">
      <div class="card-h">Lo que sale del sistema</div>
      <div class="card-b">
        <div class="chart-box tall"><canvas id="chart-tr-gast-stack"></canvas></div>
        <p class="caption">Eje Y: mil M€ · Pensiones, subsidios, ayudas no contributivas y otras salidas a terceros.</p>
      </div>
    </div>
    <div class="card">
      <div class="card-h">Transferencias del Estado / cotizaciones (%)</div>
      <div class="card-b">
        <div class="grid-3" id="tr-pct-kpi" style="margin-bottom:12px"></div>
        <div class="chart-box mid"><canvas id="chart-tr-pct-est-cot"></canvas></div>
        <p class="caption">Evolución anual: aportación del Estado (PGE) como % de las cotizaciones. Cierres 2014–2025; tramo discontinuo hasta 2026 (provisional) con el último ResSISTEMA disponible.</p>
      </div>
    </div>
  </section>

  <!-- HISTÓRICO -->
  <section id="panel-historico" class="panel">
    <div class="grid-3" id="hist-tcac-kpi"></div>
    <p class="caption" id="hist-tcac-note" style="margin:-8px 0 4px"></p>
    <div class="card">
      <div class="card-h">Ingresos vs gastos — cierres anuales</div>
      <div class="card-b">
        <p class="caption">Eje Y: mil M€ · Misma segmentación que Panorama: ingresos por color (mayor abajo), gastos en gris. Cierres 2014–2025; barra 2026 provisional si hay ResSISTEMA mensual.</p>
        <div class="chart-box tall"><canvas id="chart-hist-cot-gast"></canvas></div>
      </div>
    </div>
    <div class="grid-2">
      <div class="card">
        <div class="card-h">Transferencias del Estado (PGE) — acumulado histórico</div>
        <div class="card-b">
          <p class="caption">Suma de transferencias del PGE desde 2014 · mil M€.</p>
          <div class="chart-box mid"><canvas id="chart-hist-transf-est"></canvas></div>
        </div>
      </div>
      <div class="card">
        <div class="card-h">Déficit sin PGE — acumulado histórico</div>
        <div class="card-b">
          <p class="caption">Suma del déficit sin PGE desde 2014 · mil M€.</p>
          <div class="chart-box mid"><canvas id="chart-hist-deficit-sin-pge"></canvas></div>
        </div>
      </div>
    </div>
    <div class="card">
      <div class="card-h">Cobertura cotiz./gastos (%)</div>
      <div class="card-b">
        <div class="chart-box mid"><canvas id="chart-hist-cobertura"></canvas></div>
        <p class="caption">Cierres anuales 2014–2025; tramo discontinuo hasta 2026 (provisional). El dato provisional ene–may (~84%) no es comparable: las pagas extras de pensiones (julio+) aún no están en el acumulado y el cierre anual ronda ~72%.</p>
      </div>
    </div>
    <div class="card">
      <div class="card-h">Peso del Estado en los ingresos totales (%)</div>
      <div class="card-b">
        <div class="chart-box mid"><canvas id="chart-hist-pct-estado"></canvas></div>
        <p class="caption">Transferencias del Estado (PGE) ÷ ingresos totales del sistema · cierres 2014–2025; tramo discontinuo 2026 (provisional).</p>
      </div>
    </div>
    <div class="card">
      <div class="card-h">Crecimiento interanual por bloque</div>
      <div class="card-b">
        <div class="chart-box tall"><canvas id="chart-hist-yoy"></canvas></div>
        <p class="caption">Variación % respecto al año anterior · cotizaciones, transferencias Estado y gastos totales.</p>
      </div>
    </div>
  </section>
</div>

<script>
const DATA = {payload};
const YTD = {ytd_payload};
const EXERCISE = {exercise_payload};
// Paleta Panorama (Datawrapper por peso, base oscura) · gastos gris-azulado neutro
const PAN_ING_PALETTE = ['#ffa600', '#ff6b59', '#dd4d88', '#954e9b', '#464c89', '#003f5c'];
const PAN_BAR = {{ gastos: '#8fa0b3', gastosHover: '#758799' }};
const HIST_LINE = {{ blue: '#0c2d41', red: '#f03351', light: '#bfbdb2' }};
// Misma asignación que «Crecimiento interanual por bloque»
const YOY_LINE = {{
  cotizaciones: HIST_LINE.light,
  transferencias: HIST_LINE.red,
  gastos: HIST_LINE.blue,
}};
const PAN_ING_SEGMENTS = [
  {{ key: 'cot', label: 'Cotizaciones', color: PAN_ING_PALETTE[5] }},
  {{ key: 'est', label: 'Transferencias Estado (PGE)', color: PAN_ING_PALETTE[4] }},
  {{ key: 'ss', label: 'SS internas', color: PAN_ING_PALETTE[3] }},
  {{ key: 'tasas', label: 'Tasas y otros', color: PAN_ING_PALETTE[0] }},
];
const COLORS = {{
  cot: PAN_ING_PALETTE[5], estado: PAN_ING_PALETTE[4], ssInt: PAN_ING_PALETTE[3],
  tasas: PAN_ING_PALETTE[0], patrim: PAN_ING_PALETTE[1],
  pensiones: PAN_ING_PALETTE[5], subsidios: PAN_ING_PALETTE[2], noCont: PAN_ING_PALETTE[4],
  gestion: PAN_ING_PALETTE[1], inv: PAN_ING_PALETTE[0], transfOut: PAN_ING_PALETTE[3],
  gastos: PAN_BAR.gastos,
  jub: PAN_ING_PALETTE[5], viud: PAN_ING_PALETTE[4], it: PAN_ING_PALETTE[2],
  imv: PAN_ING_PALETTE[1], gray: PAN_ING_PALETTE[0],
  aut: PAN_ING_PALETTE[4], atep: PAN_ING_PALETTE[3], des: PAN_ING_PALETTE[2], mei: PAN_ING_PALETTE[1],
}};
const charts = {{}};

const stackSum = ds => ds.data.reduce((s, v) => s + (v == null ? 0 : Math.abs(v)), 0);
/** Apila de mayor (base) a menor (cima), por suma acumulada de la serie. */
function sortStackDatasets(datasets) {{
  const groups = new Map();
  const stackOrder = [];
  datasets.forEach(ds => {{
    const key = ds.stack || '__single__';
    if (!groups.has(key)) {{
      groups.set(key, []);
      stackOrder.push(key);
    }}
    groups.get(key).push(ds);
  }});
  return stackOrder.flatMap(key =>
    [...groups.get(key)].sort((a, b) => stackSum(b) - stackSum(a))
  );
}}

const mil = v => Math.round(v / 1000 * 10) / 10;
const fmt = v => mil(v).toLocaleString('es-ES', {{minimumFractionDigits:1, maximumFractionDigits:1}}) + ' mil M€';
const pct = (a, b) => b ? Math.round(a / b * 1000) / 10 : 0;
const years = DATA.map(d => d.year);
const last = DATA[DATA.length - 1];

const chartOpts = (extra = {{}}) => {{
  const valueUnit = extra.valueUnit || 'milM';
  const {{ valueUnit: _drop, ...restExtra }} = extra;
  return {{
  responsive: true,
  maintainAspectRatio: false,
  valueUnit,
  interaction: {{ mode: 'index', intersect: false }},
  plugins: {{
    legend: {{ position: 'top', align: 'start', labels: {{ boxWidth: 12, font: {{ size: 11 }}, padding: 14 }} }},
    tooltip: {{
      callbacks: {{
        label: ctx => {{
          const v = ctx.parsed.y ?? ctx.parsed;
          if (v == null || v === '') return null;
          if (ctx.chart.config.type === 'doughnut' || ctx.chart.config.type === 'pie') {{
            const total = ctx.dataset.data.reduce((a,b)=>a+b,0);
            const p = total ? Math.round(ctx.parsed/total*1000)/10 : 0;
            return `${{ctx.label}}: ${{ctx.parsed.toLocaleString('es-ES')}} mil M€ (${{p}}%)`;
          }}
          const unit = ctx.chart.options.valueUnit || 'milM';
          const formatted = typeof v === 'number' ? v.toLocaleString('es-ES') : v;
          const name = ctx.dataset.label || ctx.chart.options.seriesLabel || '';
          if (unit === 'pct') return `${{name}}: ${{formatted}}%`;
          return `${{name}}: ${{formatted}} mil M€`;
        }}
      }}
    }}
  }},
  scales: {{
    x: {{ grid: {{ display: false }}, ticks: {{ font: {{ size: 11 }}, color: '#a1a1aa' }} }},
    y: {{ grid: {{ color: '#e4e4e7' }}, border: {{ display: false }},
      ticks: {{ font: {{ size: 11 }}, color: '#a1a1aa' }} }}
  }},
  ...restExtra
}};
}};

function transfIngStack(d) {{
  return {{
    est: mil(d.transf_estado || 0),
    ss: mil(d.transf_ss_internas || 0),
    ccaa: mil(d.transf_ccaa || 0),
    priv: mil(d.transf_privados || 0),
  }};
}}

function transfGastStack(d) {{
  const pen = d.pensiones || 0, sub = d.subsidios_prestaciones || 0, nc = d.gastos_no_contributivos || 0;
  const out = Math.max(0, (d.gasto_transf_ss||0) + (d.gasto_transf_ccaa||0) + (d.gasto_transf_estado||0));
  return {{ pensiones: mil(pen), subsidios: mil(sub), noCont: mil(nc), salidas: mil(out) }};
}}

function pctEstadoCot(d) {{
  return d.transf_estado && d.cotizaciones ? Math.round(d.transf_estado / d.cotizaciones * 1000) / 10 : null;
}}

function ingresoStack(d) {{
  const cot = d.cotizaciones || 0;
  const est = d.transf_estado || 0;
  const ss = d.transf_ss_internas || 0;
  const tas = d.tasas_otros || 0;
  const pat = d.ingresos_patrimoniales || 0;
  const ing = d.ingresos_totales || 0;
  const otros = Math.max(0, ing - cot - est - ss - tas - pat);
  return {{ cot: mil(cot), est: mil(est), ss: mil(ss), tas: mil(tas), otros: mil(otros + pat) }};
}}

function panIngresoStack(d) {{
  const cot = d.cotizaciones || 0;
  const ss = d.transf_ss_internas || 0;
  const est = d.transf_estado || 0;
  const ing = d.ingresos_totales || 0;
  const tasasOtros = Math.max(0, ing - cot - ss - est);
  return {{ cot: mil(cot), ss: mil(ss), tasas: mil(tasasOtros), est: mil(est) }};
}}

function ingresoSinPge(d) {{
  return (d.ingresos_totales || 0) - (d.transf_estado || 0);
}}

function deficitSinPge(d) {{
  return mil(ingresoSinPge(d) - (d.gastos_totales || 0));
}}

function plainMoney(v) {{
  return fmtMilMillones(v, true);
}}

function fmtMilMillones(v, withEuros = true) {{
  if (v == null || Number.isNaN(v)) return '—';
  const neg = v < 0;
  const n = (Math.abs(v) / 1000).toLocaleString('es-ES', {{
    maximumFractionDigits: 1,
    minimumFractionDigits: 1,
  }});
  const body = withEuros ? `${{n}} mil millones de euros` : `${{n}} mil millones`;
  return neg ? `−${{body}}` : body;
}}

function lecturaPeriodo(isYtd, d) {{
  if (!isYtd) return `En ${{d.year}}`;
  const year = EXERCISE?.year || 2026;
  if (EXERCISE?.through) {{
    return `Entre enero y ${{EXERCISE.through.toLowerCase()}} de ${{year}}`;
  }}
  const p = YTD?.period || 'ene–may 2026';
  if (/ene/i.test(p)) return `Entre enero y mayo de ${{year}}`;
  return p.charAt(0).toUpperCase() + p.slice(1);
}}

function buildLecturaPanorama(d, isYtd) {{
  const cot = d.cotizaciones || 0;
  const gast = d.gastos_totales || 0;
  const est = d.transf_estado || 0;
  const ing = d.ingresos_totales || 0;
  const saldo = ing - gast;
  const sinEstado = ing - est - gast;
  const cob = d.cobertura_cotizaciones_pct;
  const intro = lecturaPeriodo(isYtd, d);
  const refYear = last.year;
  const refCob = last.cobertura_cotizaciones_pct;
  const cobStr = cob != null
    ? Number(cob).toLocaleString('es-ES', {{ maximumFractionDigits: 1 }})
    : null;

  if (isYtd) {{
    const mes = EXERCISE?.through?.toLowerCase() || 'mayo';
    const saldoLine = saldo >= 0
      ? `Las cuentas cuadran con ${{fmtMilMillones(saldo, false)}} de margen`
      : `Hay un déficit de ${{fmtMilMillones(Math.abs(saldo), false)}}`;
    const parts = [
      `<p><strong>${{intro}}</strong> · datos provisionales. Entran <strong>${{fmtMilMillones(cot, false)}}</strong> en cotizaciones y salen <strong>${{fmtMilMillones(gast, false)}}</strong> en gastos — sin pagas extra de verano ni Navidad.</p>`,
      est > 0
        ? `<p>${{saldoLine}}; el Estado aporta <strong>${{fmtMilMillones(est, false)}}</strong> del PGE. <strong>Sin esa ayuda: ${{fmtMilMillones(sinEstado, false)}}.</strong></p>`
        : `<p>${{saldoLine}}.</p>`,
      cobStr != null && refCob != null
        ? `<p>Cobertura <strong>${{cobStr}}%</strong> hasta ${{mes}} (sube antes de las pagas extra; cierre ${{refYear}}: <strong>${{refCob}}%</strong>).</p>`
        : cobStr != null
          ? `<p>Las cotizaciones cubren el <strong>${{cobStr}}%</strong> del gasto acumulado.</p>`
          : '',
      `<p class="lectura-hint">Gráfico: colores = ingresos (mayor abajo) · gris = gasto.</p>`,
    ];
    return parts.filter(Boolean).join('');
  }}

  const saldoLine = saldo >= 0
    ? `Cierre con margen de <strong>${{fmtMilMillones(saldo, false)}}</strong>`
    : `Déficit de <strong>${{fmtMilMillones(Math.abs(saldo), false)}}</strong>`;
  const parts = [
    `<p><strong>${{intro}}</strong>, cotizaciones <strong>${{fmtMilMillones(cot, false)}}</strong> y gastos <strong>${{fmtMilMillones(gast, false)}}</strong>.</p>`,
    est > 0
      ? `<p>${{saldoLine}}. El Estado aportó <strong>${{fmtMilMillones(est, false)}}</strong>; sin PGE, <strong>${{fmtMilMillones(sinEstado, false)}}</strong>.</p>`
      : `<p>${{saldoLine}}.</p>`,
    cobStr != null
      ? `<p>Cobertura anual: cotizaciones = <strong>${{cobStr}}%</strong> del gasto.</p>`
      : '',
    `<p class="lectura-hint">Gráfico: colores = ingresos · gris = gasto.</p>`,
  ];
  return parts.filter(Boolean).join('');
}}

function gastoStack(d) {{
  const pen = d.pensiones || 0;
  const sub = d.subsidios_prestaciones || 0;
  const nc = d.gastos_no_contributivos || 0;
  const ges = (d.gasto_personal || 0) + (d.gasto_bienes_servicios || 0);
  const inv = d.gasto_inversiones || 0;
  const gt = d.gasto_transferencias || 0;
  const transfResto = Math.max(0, gt - pen - sub);
  const total = d.gastos_totales || 0;
  const otros = Math.max(0, total - pen - sub - nc - ges - inv - transfResto);
  return {{
    pensiones: mil(pen), subsidios: mil(sub), noCont: mil(nc),
    gestion: mil(ges), inv: mil(inv), transfOut: mil(transfResto), otros: mil(otros)
  }};
}}

function cotRegimenStack(d) {{
  return {{
    rg: mil(d.cot_regimen_general || 0),
    aut: mil(d.cot_autonomos || 0),
    atep: mil(d.cot_at_ep || 0),
    des: mil(d.cot_desempleo || 0),
    mei: mil(d.cot_mei || 0),
    otros: mil(d.cot_otros_regimenes || 0),
  }};
}}

function prestacionStack(d) {{
  const otrasPrest = Math.max(0,
    (d.subsidios_prestaciones || 0) - (d.prest_it || 0) - (d.prest_desempleo || 0) +
    (d.gastos_no_contributivos || 0) - (d.imv || 0) - (d.complementos_minimos || 0) -
    (d.pensiones_no_contributivas || 0)
  );
  return {{
    jub: mil(d.pension_jubilacion || 0),
    viud: mil(d.pension_viudedad || 0),
    incap: mil(d.pension_incap_permanente || 0),
    it: mil(d.prest_it || 0),
    des: mil(d.prest_desempleo || 0),
    imv: mil(d.imv || 0),
    min: mil(d.complementos_minimos || 0),
    otras: mil(otrasPrest),
  }};
}}

function destroy(id) {{ if (charts[id]) {{ charts[id].destroy(); delete charts[id]; }} }}

const LINE_STYLE = {{
  tension: 0.4,
  borderWidth: 1.5,
  pointRadius: 0,
  pointHoverRadius: 4,
  pointHitRadius: 14,
}};

function styleLineDataset(ds) {{
  return {{
    tension: LINE_STYLE.tension,
    borderWidth: LINE_STYLE.borderWidth,
    pointRadius: LINE_STYLE.pointRadius,
    pointHoverRadius: LINE_STYLE.pointHoverRadius,
    pointHitRadius: LINE_STYLE.pointHitRadius,
    ...ds,
  }};
}}

function makeLine(id, labels, datasets, extraOpts = {{}}) {{
  destroy(id);
  charts[id] = new Chart(document.getElementById(id), {{
    type: 'line',
    data: {{ labels, datasets: datasets.map(styleLineDataset) }},
    options: chartOpts(extraOpts),
  }});
}}

function makeLineProvisional(id, {{
  labels, values, provisional, label, borderColor, backgroundColor,
  fill = true, provisionalLabel = '2026 (provisional)', yScalePct = true,
}}) {{
  const lineData = [...values];
  const lbls = [...labels];
  const hasProv = provisional != null;
  if (hasProv) {{
    lbls.push(provisionalLabel);
    lineData.push(provisional);
  }}
  const lastIdx = lineData.length - 1;
  makeLine(id, lbls, [{{
    label,
    data: lineData,
    borderColor,
    backgroundColor,
    fill,
    segment: {{
      borderDash: ctx => hasProv && ctx.p1DataIndex === lastIdx ? [6, 4] : undefined,
    }},
  }}], yScalePct ? {{
    valueUnit: 'pct',
    scales: {{ y: {{ ticks: {{ callback: v => v + '%' }} }} }},
    plugins: {{ legend: {{ display: false }} }},
  }} : {{ plugins: {{ legend: {{ display: false }} }} }});
}}

function makeBar(id, labels, datasets, stacked=false) {{
  destroy(id);
  const el = document.getElementById(id);
  const data = stacked ? sortStackDatasets(datasets) : datasets;
  charts[id] = new Chart(el, {{
    type: 'bar',
    data: {{ labels, datasets: data }},
    options: chartOpts({{
      scales: {{
        x: {{ stacked, grid: {{ display: false }}, ticks: {{ font: {{ size: 11 }}, color: '#a1a1aa' }} }},
        y: {{ stacked, grid: {{ color: '#e4e4e7' }}, border: {{ display: false }},
          ticks: {{ font: {{ size: 11 }}, color: '#a1a1aa' }} }}
      }},
      datasets: {{ bar: {{ categoryPercentage: stacked ? 0.72 : 0.65, barPercentage: 0.88 }} }}
    }})
  }});
}}

function ingresoVsGastosDatasets(rows) {{
  const ing = rows.map(panIngresoStack);
  const segDatasets = sortStackDatasets(PAN_ING_SEGMENTS.map(seg => ({{
    label: seg.label,
    data: ing.map(s => s[seg.key]),
    backgroundColor: seg.color,
    stack: 'ingresos',
    borderWidth: 0,
  }})));
  return [
    ...segDatasets,
    {{ label: 'Gastos totales', data: rows.map(r => mil(r.gastos_totales)),
       backgroundColor: PAN_BAR.gastos, stack: 'gastos', borderWidth: 0, hoverBackgroundColor: PAN_BAR.gastosHover }},
  ];
}}

const panIngGastBarOpts = {{
  scales: {{
    x: {{
      stacked: true,
      offset: true,
      grid: {{ display: false }},
      ticks: {{ font: {{ size: 11 }}, color: '#a1a1aa' }},
    }},
    y: {{
      stacked: true,
      grid: {{ color: '#e4e4e7' }},
      border: {{ display: false }},
      ticks: {{ font: {{ size: 11 }}, color: '#a1a1aa' }},
    }},
  }},
  datasets: {{ bar: {{ categoryPercentage: 0.72, barPercentage: 0.92 }} }},
}};

function makeIngVsGast(id, labels, rows) {{
  destroy(id);
  charts[id] = new Chart(document.getElementById(id), {{
    type: 'bar',
    data: {{ labels, datasets: ingresoVsGastosDatasets(rows) }},
    options: chartOpts(panIngGastBarOpts),
  }});
}}

function makeIngVsGastSnapshot(id, row) {{
  const ing = panIngresoStack(row);
  const gast = mil(row.gastos_totales);
  destroy(id);
  charts[id] = new Chart(document.getElementById(id), {{
    type: 'bar',
    data: {{
      labels: ['Ingresos', 'Gastos'],
      datasets: sortStackDatasets([
        ...PAN_ING_SEGMENTS.map(seg => ({{
          label: seg.label,
          data: [ing[seg.key], null],
          backgroundColor: seg.color,
          stack: 'ingresos',
          borderWidth: 0,
        }})),
        {{ label: 'Gastos totales', data: [null, gast], backgroundColor: PAN_BAR.gastos, stack: 'gastos', borderWidth: 0,
           hoverBackgroundColor: PAN_BAR.gastosHover }},
      ]),
    }},
    options: chartOpts({{
      ...panIngGastBarOpts,
      datasets: {{ bar: {{ categoryPercentage: 0.45, barPercentage: 0.92 }} }},
    }}),
  }});
}}

function makeDoughnut(id, labels, values, colors) {{
  destroy(id);
  charts[id] = new Chart(document.getElementById(id), {{
    type: 'doughnut',
    data: {{ labels, datasets: [{{ data: values, backgroundColor: colors, borderWidth: 2, borderColor: '#fff' }}] }},
    options: {{
      responsive: true,
      maintainAspectRatio: false,
      plugins: {{
        legend: {{ position: 'right', labels: {{ boxWidth: 12, font: {{ size: 11 }}, padding: 10 }} }},
        tooltip: {{
          callbacks: {{
            label: ctx => {{
              const total = ctx.dataset.data.reduce((a,b)=>a+b,0);
              const p = total ? Math.round(ctx.parsed/total*1000)/10 : 0;
              return `${{ctx.label}}: ${{ctx.parsed.toLocaleString('es-ES')}} mil M€ (${{p}}%)`;
            }}
          }}
        }}
      }},
      scales: {{ x: {{ display: false }}, y: {{ display: false }} }},
      cutout: '55%',
    }}
  }});
}}

function renderKPIs() {{
  const el = document.getElementById('kpi-panorama');
  const note = document.getElementById('panorama-period-note');
  const lectura = document.getElementById('lectura-panorama');
  const lecturaTitle = document.getElementById('lectura-panorama-title');
  const sign = v => v == null ? '' : (v > 0 ? `+${{v}}%` : `${{v}}%`);
  const useYtd = YTD && YTD.cotizaciones;

  if (useYtd) {{
    const through = EXERCISE.through ? `hasta ${{EXERCISE.through.toLowerCase()}}` : YTD.period;
    if (lecturaTitle) lecturaTitle.textContent = `Lectura rápida · ${{YTD.period || '2026'}}`;
    note.textContent = `Cifras acumuladas (${{through}}). Unidad: miles de millones de euros (mil M€), salvo cobertura (%).`;
    const cob = YTD.cobertura_cotizaciones_pct;
    const cobStr = cob != null ? cob.toLocaleString('es-ES', {{ minimumFractionDigits: 1, maximumFractionDigits: 1 }}) : '—';
    const y = YTD.yoy || {{}};
    const kpis = [
      [fmt(YTD.cotizaciones), `Cotizaciones acum. · ${{sign(y.cotizaciones)}} vs ${{YTD.prev_period}}`, false],
      [fmt(YTD.gastos_totales), `Gastos acum. · ${{sign(y.gastos_totales)}} vs ${{YTD.prev_period}}`, false],
      [fmt(YTD.transf_estado), `Transferencias Estado · ${{sign(y.transf_estado)}} vs ${{YTD.prev_period}}`, false],
      [cobStr, `Cobertura acumulada · ${{YTD.period}}`, true],
    ];
    el.innerHTML = kpis.map(([v, l, isPct]) =>
      `<div class="stat${{isPct ? ' stat-pct' : ''}}"><div class="stat-v">${{v}}${{isPct ? '<span class="stat-unit"> % cotiz. ÷ gastos</span>' : ''}}</div><div class="stat-l">${{l}}</div></div>`
    ).join('');
    if (lectura) lectura.innerHTML = buildLecturaPanorama(YTD, true);
    return;
  }}

  if (lecturaTitle) lecturaTitle.textContent = `Lectura rápida · ${{last.year}}`;
  note.textContent = `Cierre anual ${{last.year}} (${{last.source_month || 'cierre'}}). Unidad: mil M€; cobertura en %.`;
  const cob = last.cobertura_cotizaciones_pct;
  const kpis = [
    [fmt(last.cotizaciones), 'Cotizaciones ' + last.year, false],
    [fmt(last.gastos_totales), 'Gastos ' + last.year, false],
    [fmt(last.transf_estado), 'Transferencias Estado (PGE)', false],
    [last.cobertura_cotizaciones_pct.toLocaleString('es-ES', {{ minimumFractionDigits: 1, maximumFractionDigits: 1 }}),
      'Cobertura anual cotiz. ÷ gastos', true],
  ];
  el.innerHTML = kpis.map(([v, l, isPct]) =>
    `<div class="stat${{isPct ? ' stat-pct' : ''}}"><div class="stat-v">${{v}}${{isPct ? '<span class="stat-unit"> % cotiz. ÷ gastos</span>' : ''}}</div><div class="stat-l">${{l}}</div></div>`
  ).join('');
  if (lectura) lectura.innerHTML = buildLecturaPanorama(last, false);
}}

function transfEstLineDataset(data) {{
  return {{
    label: 'Transferencias Estado (PGE)',
    data,
    borderColor: YOY_LINE.gastos,
    backgroundColor: 'rgba(12,45,65,.12)',
    fill: true,
  }};
}}

function deficitSinEstLineDataset(data) {{
  return {{
    label: 'Ingresos sin PGE − gastos',
    data,
    borderColor: YOY_LINE.transferencias,
    backgroundColor: 'rgba(240,51,81,.12)',
    fill: true,
    segment: {{
      borderColor: ctx => (ctx.p1.parsed.y < 0 ? YOY_LINE.transferencias : YOY_LINE.gastos),
      backgroundColor: ctx => (ctx.p1.parsed.y < 0 ? 'rgba(240,51,81,.12)' : 'rgba(12,45,65,.12)'),
    }},
  }};
}}

function tcacPct(first, last, yearsSpan) {{
  if (first == null || last == null || first <= 0 || yearsSpan <= 0) return null;
  return Math.round((Math.pow(last / first, 1 / yearsSpan) - 1) * 1000) / 10;
}}

function deficitSinPgeRaw(d) {{
  return ingresoSinPge(d) - (d.gastos_totales || 0);
}}

function runningCumulativeMil(rows, rawFn) {{
  let acc = 0;
  return rows.map(d => {{
    acc += rawFn(d);
    return mil(acc);
  }});
}}

function histCumulativeLineSeries(rawFn) {{
  const rows = [...DATA];
  const labels = years.map(String);
  const data = runningCumulativeMil(rows, rawFn);
  const hasProv = Boolean(YTD?.cotizaciones);
  if (hasProv) {{
    labels.push('2026 (prov.)');
    data.push(...runningCumulativeMil([...rows, YTD], rawFn).slice(-1));
  }}
  return {{ labels, data, hasProv, lastIdx: data.length - 1 }};
}}

function histCumulativeTransfDataset(data) {{
  return {{
    ...transfEstLineDataset(data),
    label: 'Transferencias Estado acumuladas (desde 2014)',
  }};
}}

function histCumulativeDeficitDataset(data) {{
  return {{
    ...deficitSinEstLineDataset(data),
    label: 'Déficit estructural acumulado (sin PGE)',
  }};
}}

function withProvisionalDash(ds, hasProv, lastIdx) {{
  const baseSegment = ds.segment || {{}};
  return {{
    ...ds,
    segment: {{
      borderColor: ctx => {{
        if (hasProv && ctx.p1DataIndex === lastIdx) return baseSegment.borderColor?.(ctx) ?? ds.borderColor;
        return baseSegment.borderColor?.(ctx) ?? ds.borderColor;
      }},
      backgroundColor: ctx => baseSegment.backgroundColor?.(ctx) ?? ds.backgroundColor,
      borderDash: ctx => (hasProv && ctx.p1DataIndex === lastIdx ? [6, 4] : undefined),
    }},
  }};
}}

function renderHistTcac() {{
  const el = document.getElementById('hist-tcac-kpi');
  const note = document.getElementById('hist-tcac-note');
  if (!el) return;
  const first = DATA[0];
  const lastAnnual = DATA[DATA.length - 1];
  const span = lastAnnual.year - first.year;
  const fmtTcac = v => {{
    if (v == null) return '—';
    const sign = v > 0 ? '+' : '';
    return `${{sign}}${{v.toLocaleString('es-ES', {{ minimumFractionDigits: 1, maximumFractionDigits: 1 }})}}`;
  }};
  const items = [
    ['cotizaciones', 'Cotizaciones', 'tone-info'],
    ['gastos_totales', 'Gastos totales', ''],
    ['transf_estado', 'Transferencias Estado', 'tone-estado'],
  ];
  el.innerHTML = items.map(([key, label, tone]) => `
    <div class="stat tr-pct-stat hist-tcac-stat">
      <div class="stat-v ${{tone}}">${{fmtTcac(tcacPct(first[key], lastAnnual[key], span))}}<span class="hist-tcac-unit"> %/año</span></div>
      <div class="stat-l">${{label}}</div>
    </div>`).join('');
  if (note) note.textContent = `Crecimiento medio anual compuesto (TCAC) · cierres ${{first.year}}–${{lastAnnual.year}}`;
}}

function renderPanorama() {{
  const src = (YTD && YTD.cotizaciones) ? YTD : last;
  const period = (YTD && YTD.period) ? YTD.period : String(last.year);

  if (EXERCISE.months && EXERCISE.months.length) {{
    const labels = EXERCISE.months.map(m => m.month_short);
    makeIngVsGast('chart-pan-ing-vs-gast', labels, EXERCISE.months);
    makeLine('chart-pan-transf-est', labels, [transfEstLineDataset(
      EXERCISE.months.map(m => mil(m.transf_estado))
    )], {{ plugins: {{ legend: {{ display: false }} }} }});
    makeLine('chart-pan-gast-sin-est', labels, [deficitSinEstLineDataset(
      EXERCISE.months.map(deficitSinPge)
    )], {{ plugins: {{ legend: {{ display: false }} }} }});
    const titleEl = document.getElementById('pan-main-title');
    if (titleEl) titleEl.textContent = `Ingresos vs gastos — ejercicio ${{EXERCISE.year}} (acumulado mensual)`;
  }} else {{
    makeIngVsGastSnapshot('chart-pan-ing-vs-gast', src);
    makeLine('chart-pan-transf-est', [period], [transfEstLineDataset([mil(src.transf_estado)])],
      {{ plugins: {{ legend: {{ display: false }} }} }});
    makeLine('chart-pan-gast-sin-est', [period], [deficitSinEstLineDataset([deficitSinPge(src)])],
      {{ plugins: {{ legend: {{ display: false }} }} }});
  }}
}}

function renderIngresos() {{
  const stacks = DATA.map(ingresoStack);
  makeBar('chart-ing-stack', years.map(String), [
    {{ label: 'Cotizaciones', data: stacks.map(s => s.cot), backgroundColor: COLORS.cot, stack: 'i' }},
    {{ label: 'Transferencias Estado', data: stacks.map(s => s.est), backgroundColor: COLORS.estado, stack: 'i' }},
    {{ label: 'Transferencias SS internas', data: stacks.map(s => s.ss), backgroundColor: COLORS.ssInt, stack: 'i' }},
    {{ label: 'Tasas y otros', data: stacks.map(s => s.tas + s.otros), backgroundColor: COLORS.tasas, stack: 'i' }},
  ], true);
  const cr = DATA.map(cotRegimenStack);
  makeBar('chart-ing-cot-stack', years.map(String), [
    {{ label: 'Régimen General', data: cr.map(s => s.rg), backgroundColor: COLORS.cot, stack: 'c' }},
    {{ label: 'Autónomos', data: cr.map(s => s.aut), backgroundColor: COLORS.aut, stack: 'c' }},
    {{ label: 'AT/EP', data: cr.map(s => s.atep), backgroundColor: COLORS.atep, stack: 'c' }},
    {{ label: 'Desempleo/ERTE', data: cr.map(s => s.des), backgroundColor: COLORS.des, stack: 'c' }},
    {{ label: 'MEI', data: cr.map(s => s.mei), backgroundColor: COLORS.mei, stack: 'c' }},
    {{ label: 'Otros regímenes', data: cr.map(s => s.otros), backgroundColor: COLORS.gray, stack: 'c' }},
  ], true);
}}

function renderGastos() {{
  const stacks = DATA.map(gastoStack);
  makeBar('chart-gast-stack', years.map(String), [
    {{ label: 'Pensiones', data: stacks.map(s => s.pensiones), backgroundColor: COLORS.pensiones, stack: 'g' }},
    {{ label: 'Subsidios y prestaciones', data: stacks.map(s => s.subsidios), backgroundColor: COLORS.subsidios, stack: 'g' }},
    {{ label: 'No contributivo (IMV…)', data: stacks.map(s => s.noCont), backgroundColor: COLORS.noCont, stack: 'g' }},
    {{ label: 'Gestión', data: stacks.map(s => s.gestion), backgroundColor: COLORS.gestion, stack: 'g' }},
    {{ label: 'Inversiones y resto', data: stacks.map(s => s.inv + s.transfOut + s.otros), backgroundColor: COLORS.inv, stack: 'g' }},
  ], true);
  const pr = DATA.map(prestacionStack);
  makeBar('chart-gast-prest-stack', years.map(String), [
    {{ label: 'Jubilación', data: pr.map(s => s.jub), backgroundColor: COLORS.jub, stack: 'p' }},
    {{ label: 'Viudedad', data: pr.map(s => s.viud), backgroundColor: COLORS.viud, stack: 'p' }},
    {{ label: 'Incap. permanente', data: pr.map(s => s.incap), backgroundColor: COLORS.ssInt, stack: 'p' }},
    {{ label: 'Incap. temporal', data: pr.map(s => s.it), backgroundColor: COLORS.it, stack: 'p' }},
    {{ label: 'Desempleo', data: pr.map(s => s.des), backgroundColor: COLORS.subsidios, stack: 'p' }},
    {{ label: 'IMV', data: pr.map(s => s.imv), backgroundColor: COLORS.imv, stack: 'p' }},
    {{ label: 'Compl. mínimos', data: pr.map(s => s.min), backgroundColor: COLORS.noCont, stack: 'p' }},
    {{ label: 'Otras prest.', data: pr.map(s => s.otras), backgroundColor: COLORS.gray, stack: 'p' }},
  ], true);
}}

function renderTransferencias() {{
  const ti = DATA.map(transfIngStack);
  makeBar('chart-tr-ing-stack', years.map(String), [
    {{ label: 'Estado (PGE)', data: ti.map(s => s.est), backgroundColor: COLORS.estado, stack: 't' }},
    {{ label: 'SS internas', data: ti.map(s => s.ss), backgroundColor: COLORS.ssInt, stack: 't' }},
    {{ label: 'CCAA', data: ti.map(s => s.ccaa), backgroundColor: COLORS.tasas, stack: 't' }},
    {{ label: 'Privados/otros', data: ti.map(s => s.priv), backgroundColor: COLORS.gray, stack: 't' }},
  ], true);
  const tg = DATA.map(transfGastStack);
  makeBar('chart-tr-gast-stack', years.map(String), [
    {{ label: 'Pensiones', data: tg.map(s => s.pensiones), backgroundColor: COLORS.pensiones, stack: 'g' }},
    {{ label: 'Subsidios', data: tg.map(s => s.subsidios), backgroundColor: COLORS.subsidios, stack: 'g' }},
    {{ label: 'No contributivo', data: tg.map(s => s.noCont), backgroundColor: COLORS.noCont, stack: 'g' }},
    {{ label: 'Salidas a terceros', data: tg.map(s => s.salidas), backgroundColor: COLORS.transfOut, stack: 'g' }},
  ], true);
  renderTrPctActual();
  renderTrPctEstCot();
}}

function renderTrPctActual() {{
  const el = document.getElementById('tr-pct-kpi');
  if (!el) return;
  const p = YTD?.pct_estado_sobre_cotizaciones;
  if (p == null) {{
    el.innerHTML = '';
    return;
  }}
  const prev = YTD.pct_estado_sobre_cotizaciones_prev;
  const delta = YTD.pct_estado_sobre_cotizaciones_delta;
  const deltaTxt = delta != null
    ? `<span class="tone-muted">${{delta >= 0 ? '+' : ''}}${{delta}} pp vs ${{YTD.prev_period || 'ene–may 2025'}}</span>`
    : '';
  const lastClose = pctEstadoCot(DATA[DATA.length - 1]);
  const stat = (v, label, highlight = false) => {{
    const display = v == null || v === '—' ? '—' : `${{v}}%`;
    return `
    <div class="stat tr-pct-stat">
      <div class="stat-v ${{highlight ? 'tone-estado' : ''}}">${{display}}</div>
      <div class="stat-l">${{label}}</div>
    </div>`;
  }};
  el.innerHTML = [
    stat(p, `Provisional 2026 · ${{YTD.period}} · Transferencias Estado / cotizaciones`, true),
    stat(lastClose ?? '—', `Cierre ${{years[years.length - 1]}} (referencia anual)`),
    stat(prev ?? '—', `Mismo periodo 2025${{deltaTxt ? ' · ' + deltaTxt : ''}}`),
  ].join('');
}}

function renderTrPctEstCot() {{
  makeLineProvisional('chart-tr-pct-est-cot', {{
    labels: years.map(String),
    values: DATA.map(pctEstadoCot),
    provisional: YTD?.pct_estado_sobre_cotizaciones ?? null,
    label: 'Estado / cotizaciones (%)',
    borderColor: COLORS.estado,
    backgroundColor: 'rgba(70,76,137,.12)',
  }});
}}

function renderHistorico() {{
  renderHistTcac();
  const histLabels = years.map(String);
  const histRows = [...DATA];
  if (YTD?.cotizaciones) {{
    histLabels.push('2026 (prov.)');
    histRows.push(YTD);
  }}
  makeIngVsGast('chart-hist-cot-gast', histLabels, histRows);
  const transfSeries = histCumulativeLineSeries(d => d.transf_estado || 0);
  makeLine('chart-hist-transf-est', transfSeries.labels, [
    withProvisionalDash(histCumulativeTransfDataset(transfSeries.data), transfSeries.hasProv, transfSeries.lastIdx),
  ], {{ plugins: {{ legend: {{ display: false }} }} }});
  const deficitSeries = histCumulativeLineSeries(deficitSinPgeRaw);
  makeLine('chart-hist-deficit-sin-pge', deficitSeries.labels, [
    withProvisionalDash(histCumulativeDeficitDataset(deficitSeries.data), deficitSeries.hasProv, deficitSeries.lastIdx),
  ], {{ plugins: {{ legend: {{ display: false }} }} }});
  makeLineProvisional('chart-hist-cobertura', {{
    labels: years.map(String),
    values: DATA.map(d => d.cobertura_cotizaciones_pct),
    provisional: YTD?.cobertura_cotizaciones_pct ?? null,
    label: 'Cobertura cotiz./gastos',
    borderColor: COLORS.cot,
    backgroundColor: 'rgba(0,63,92,.12)',
  }});
  makeLineProvisional('chart-hist-pct-estado', {{
    labels: years.map(String),
    values: DATA.map(d => d.pct_estado_en_ingresos),
    provisional: YTD?.pct_estado_en_ingresos ?? null,
    label: 'Estado / ingresos totales (%)',
    borderColor: COLORS.estado,
    backgroundColor: 'rgba(70,76,137,.12)',
  }});
  const yoy = (key) => DATA.map((d,i) => i === 0 ? null : Math.round((d[key]-DATA[i-1][key])/DATA[i-1][key]*1000)/10);
  const yoyLabels = years.slice(1).map(String);
  makeLine('chart-hist-yoy', yoyLabels, [
    {{ label: 'Cotizaciones', data: yoy('cotizaciones').slice(1), borderColor: YOY_LINE.cotizaciones }},
    {{ label: 'Transferencias Estado', data: yoy('transf_estado').slice(1), borderColor: YOY_LINE.transferencias }},
    {{ label: 'Gastos totales', data: yoy('gastos_totales').slice(1), borderColor: YOY_LINE.gastos }},
  ], {{
    valueUnit: 'pct',
    scales: {{ y: {{ ticks: {{ callback: v => v + '%' }} }} }},
    plugins: {{
      legend: {{
        position: 'top',
        align: 'start',
        labels: {{
          usePointStyle: true,
          pointStyle: 'line',
          boxWidth: 28,
          boxHeight: 2,
          padding: 14,
        }},
      }},
    }},
  }});
}}

// Tabs
document.querySelectorAll('.tab-btn').forEach(btn => {{
  btn.addEventListener('click', () => {{
    document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
    document.querySelectorAll('.panel').forEach(p => p.classList.remove('active'));
    btn.classList.add('active');
    document.getElementById('panel-' + btn.dataset.tab).classList.add('active');
    setTimeout(() => Object.values(charts).forEach(c => c.resize()), 50);
  }});
}});

renderKPIs();
renderPanorama();
renderIngresos();
renderGastos();
renderTransferencias();
renderHistorico();
</script>
</body>
</html>"""

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    OUT_FILE.write_text(html, encoding="utf-8")
    print(f"→ {OUT_FILE}")
    print("Abrir en navegador: file://" + OUT_FILE.resolve().as_posix())


if __name__ == "__main__":
    main()
