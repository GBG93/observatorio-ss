#!/usr/bin/env python3
"""Exporta cada sección del canvas a PNG (estructura y textos idénticos)."""

from __future__ import annotations

import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA_PATH = ROOT / "data/processed/annual_series.json"
OUT_DIR = ROOT / "output" / "canvas"
HTML_PATH = ROOT / "export" / "canvas-export.html"

YTD_MAYO_2025 = {
    "cotizaciones": 71700.7,
    "gastos": 86100.8,
    "transferencias_estado": 13359.2,
    "deficit_cotizaciones": 14400.1,
}
YTD_MAYO_2026 = {
    "cotizaciones": 77295.4,
    "gastos": 92084.5,
    "transferencias_estado": 14624.0,
    "deficit_cotizaciones": 14789.1,
}


def mil_m(v: float) -> float:
    return round(v / 1000, 1)


def fmt_mil_m(v: float) -> str:
    return f"{mil_m(v):.1f}".replace(".", ",") + " mil M\u20ac"


def yoy_pct(cur: float, prev: float) -> float:
    return round((cur - prev) / prev * 100, 1)


def load_rows() -> list[dict]:
    with open(DATA_PATH, encoding="utf-8") as f:
        return json.load(f)


def build_model(rows: list[dict]) -> dict:
    first, last, prev = rows[0], rows[-1], rows[-2]
    n = len(rows) - 1
    cot_cagr = round((math.pow(last["cotizaciones"] / first["cotizaciones"], 1 / n) - 1) * 1000) / 10
    gast_cagr = round((math.pow(last["gastos"] / first["gastos"], 1 / n) - 1) * 1000) / 10
    est_cagr = round((math.pow(last["transferencias_estado"] / first["transferencias_estado"], 1 / n) - 1) * 1000) / 10
    cot_yoy_2025 = yoy_pct(last["cotizaciones"], prev["cotizaciones"])
    gast_yoy_2025 = yoy_pct(last["gastos"], prev["gastos"])
    deficit_growth = round((last["deficit_cotizaciones"] - first["deficit_cotizaciones"]) / first["deficit_cotizaciones"] * 100)

    ytd = {
        "cot": yoy_pct(YTD_MAYO_2026["cotizaciones"], YTD_MAYO_2025["cotizaciones"]),
        "gast": yoy_pct(YTD_MAYO_2026["gastos"], YTD_MAYO_2025["gastos"]),
        "est": yoy_pct(YTD_MAYO_2026["transferencias_estado"], YTD_MAYO_2025["transferencias_estado"]),
        "def": yoy_pct(YTD_MAYO_2026["deficit_cotizaciones"], YTD_MAYO_2025["deficit_cotizaciones"]),
    }

    years = [str(r["year"]) for r in rows]
    cot = [mil_m(r["cotizaciones"]) for r in rows]
    gast = [mil_m(r["gastos"]) for r in rows]
    est = [mil_m(r["transferencias_estado"]) for r in rows]
    deficit = [mil_m(r["deficit_cotizaciones"]) for r in rows]

    yoy_years, cot_y, gast_y = [], [], []
    for i in range(1, len(rows)):
        yoy_years.append(str(rows[i]["year"]))
        cot_y.append(yoy_pct(rows[i]["cotizaciones"], rows[i - 1]["cotizaciones"]))
        gast_y.append(yoy_pct(rows[i]["gastos"], rows[i - 1]["gastos"]))
    covid_drop = cot_y[yoy_years.index("2020")]

    return {
        "years": years,
        "cot": cot,
        "gast": gast,
        "est": est,
        "deficit": deficit,
        "yoy_years": yoy_years,
        "cot_y": cot_y,
        "gast_y": gast_y,
        "cot_cagr": cot_cagr,
        "gast_cagr": gast_cagr,
        "est_cagr": est_cagr,
        "cot_yoy_2025": cot_yoy_2025,
        "gast_yoy_2025": gast_yoy_2025,
        "deficit_growth": deficit_growth,
        "covid_drop": covid_drop,
        "ytd": ytd,
        "fmt_first_est": fmt_mil_m(first["transferencias_estado"]),
        "fmt_last_est": fmt_mil_m(last["transferencias_estado"]),
        "pct_estado": last["pct_estado_en_ingresos"],
        "avance_cats": ["Ene\u2013may 2025", "Ene\u2013may 2026"],
        "avance_cot": [mil_m(YTD_MAYO_2025["cotizaciones"]), mil_m(YTD_MAYO_2026["cotizaciones"])],
        "avance_gast": [mil_m(YTD_MAYO_2025["gastos"]), mil_m(YTD_MAYO_2026["gastos"])],
        "avance_est": [mil_m(YTD_MAYO_2025["transferencias_estado"]), mil_m(YTD_MAYO_2026["transferencias_estado"])],
        "fmt_ytd_cot": fmt_mil_m(YTD_MAYO_2026["cotizaciones"]),
        "fmt_ytd_gast": fmt_mil_m(YTD_MAYO_2026["gastos"]),
        "fmt_ytd_est": fmt_mil_m(YTD_MAYO_2026["transferencias_estado"]),
        "fmt_ytd_def": fmt_mil_m(YTD_MAYO_2026["deficit_cotizaciones"]),
        "ref_estado_2014": mil_m(first["transferencias_estado"]),
    }


def render_html(m: dict, *, site: bool = False, updated: str = "") -> str:
    y = m["ytd"]
    sign = lambda v: f"+{v}" if v > 0 else str(v)

    title = "Observatorio \u00b7 Finanzas Seguridad Social" if site else "Seguridad Social \u2014 export canvas"
    h1 = "Observatorio de finanzas de la Seguridad Social" if site else "Seguridad Social \u2014 Serie hist\u00f3rica anual"
    export_attr = lambda name: "" if site else f' data-export="{name}" id="export-{name}"'

    site_head = ""
    site_styles = ""
    site_header = ""
    site_footer = ""
    if site:
        site_head = f"""
<meta name="viewport" content="width=device-width, initial-scale=1" />
<meta name="description" content="Cotizaciones, gastos y transferencias del Estado en el sistema de la Seguridad Social espa\u00f1ola. Datos ResSISTEMA 2014\u20132025." />
<link rel="icon" href="data:image/svg+xml,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 100 100'><text y='.9em' font-size='90'>\u2696\ufe0f</text></svg>" />"""
        site_styles = """
  .site-header { background: #fff; border-bottom: 1px solid #e4e4e7; padding: 12px 24px; position: sticky; top: 0; z-index: 10; }
  .site-header-inner { max-width: 1100px; margin: 0 auto; display: flex; justify-content: space-between; align-items: center; gap: 16px; flex-wrap: wrap; }
  .site-brand { font-size: 14px; font-weight: 600; color: #3685bf; }
  .site-meta { font-size: 12px; color: #a1a1aa; }
  .site-footer { max-width: 1100px; margin: 32px auto 0; padding: 16px 24px 32px; border-top: 1px solid #e4e4e7; font-size: 12px; color: #71717a; line-height: 1.6; }
  .site-footer a { color: #3685bf; text-decoration: none; }
  .site-footer a:hover { text-decoration: underline; }
  @media (max-width: 720px) {
    .grid-4 { grid-template-columns: repeat(2, 1fr); }
    .grid-2-export, .grid-2 { grid-template-columns: 1fr; }
  }"""
        site_header = f"""
<header class="site-header">
  <div class="site-header-inner">
    <span class="site-brand">Observatorio SS</span>
    <span class="site-meta">Actualizado {updated or "—"}</span>
  </div>
</header>"""
        site_footer = """
<footer class="site-footer">
  <p>Datos oficiales ResSISTEMA (TGSS / Intervenci\u00f3n General de la SS). Los importes del presupuesto est\u00e1n en millones de euros; aqu\u00ed en miles de millones (mil M\u20ac).</p>
  <p>
    <a href="data/annual_series.json">Descargar serie anual (JSON)</a> &middot;
    <a href="https://www.seg-social.es/wps/portal/wss/internet/InformacionEconomicoFinanciera/393/394" target="_blank" rel="noopener">ResSISTEMA en seg-social.es</a>
  </p>
</footer>"""

    return f"""<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="utf-8" />
<title>{title}</title>{site_head}
<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.1/dist/chart.umd.min.js"></script>
<style>
  * {{ box-sizing: border-box; }}
  body {{
    margin: 0; padding: 24px;
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
    background: #fafafa; color: #18181b;
  }}
  .page {{ max-width: 1100px; margin: 0 auto; display: flex; flex-direction: column; gap: 24px; }}
  .stack {{ display: flex; flex-direction: column; gap: 8px; }}
  .stack-12 {{ display: flex; flex-direction: column; gap: 12px; }}
  .stack-4 {{ display: flex; flex-direction: column; gap: 4px; }}
  h1 {{ font-size: 24px; font-weight: 600; margin: 0; line-height: 1.2; }}
  h3 {{ font-size: 16px; font-weight: 600; margin: 0; }}
  .text-secondary {{ color: #52525b; line-height: 1.5; max-width: 720px; margin: 0; font-size: 14px; }}
  .caption {{ color: #a1a1aa; font-size: 12px; line-height: 1.45; margin: 0; }}
  .card {{
    background: #fff; border: 1px solid #e4e4e7; border-radius: 8px; overflow: visible;
  }}
  .card.borderless {{ border: none; background: transparent; }}
  .card-header {{
    padding: 12px 16px 0; font-size: 14px; font-weight: 600;
  }}
  .card-body {{ padding: 12px 16px 16px; }}
  .grid-4 {{ display: grid; grid-template-columns: repeat(4, 1fr); gap: 12px; }}
  .grid-2 {{ display: grid; grid-template-columns: 1fr 1fr; gap: 16px; }}
  .stat {{ display: flex; flex-direction: column; gap: 4px; min-width: 0; }}
  .stat-value {{ font-size: 22px; font-weight: 600; line-height: 1.1; }}
  .stat-label {{ font-size: 11px; color: #52525b; line-height: 1.35; }}
  .tone-info {{ color: #3685bf; }}
  .tone-warning {{ color: #c08532; }}
  .tone-danger {{ color: #cf2d56; }}
  .callout {{
    background: #fbf3e6; border: 1px solid #e8d4b0; border-radius: 8px;
    padding: 12px 16px; display: flex; flex-direction: column; gap: 6px;
  }}
  .callout-title {{ font-size: 14px; font-weight: 600; color: #c08532; }}
  .callout-body {{ font-size: 14px; color: #52525b; line-height: 1.5; margin: 0; }}
  .chart {{ width: 100%; position: relative; overflow: visible; padding: 0 8px; }}
  .grid-2-export {{ display: grid; grid-template-columns: 1fr 1fr; gap: 16px; width: 100%; padding: 0 4px 0 0; box-sizing: border-box; }}
  .grid-2-export .chart {{ padding: 0 6px 0 10px; }}
  .grid-2-export .card:last-child .card-body {{ padding-right: 20px; }}
  .spacer-8 {{ height: 8px; }}
  [data-export] {{ background: #fafafa; padding: 0; }}{site_styles}
</style>
</head>
<body>
{site_header}
<div class="page">

  <div class="stack"{export_attr("00-header")}>
    <h1>{h1}</h1>
    <p class="text-secondary">Cotizaciones sociales frente a gasto total del sistema, y evoluci\u00f3n de las transferencias del Estado.
      Cifras acumuladas de cierre de ejercicio (ResSISTEMA). Los importes del presupuesto de la SS est\u00e1n en millones de euros; aqu\u00ed se muestran en miles de millones de euros.</p>
    <p class="caption">Fuente: TGSS / Intervenci\u00f3n General de la SS \u00b7 ResSISTEMA 2014\u20132025 (cierre) y mayo 2026 (avance)</p>
  </div>

  <div class="card"{export_attr("01-avance-2026")}>
    <div class="card-header">Avance 2026 (enero\u2013mayo)</div>
    <div class="card-body">
      <div class="stack-12">
        <p class="caption">Datos acumulados a fin de mayo \u2014 no es cierre anual. Se compara con el mismo periodo de 2025.</p>
        <div class="grid-4">
          <div class="stat"><div class="stat-value tone-info">{m['fmt_ytd_cot']}</div><div class="stat-label">Cotizaciones acum. \u00b7 {sign(y['cot'])}% vs ene\u2013may 2025</div></div>
          <div class="stat"><div class="stat-value">{m['fmt_ytd_gast']}</div><div class="stat-label">Gastos acum. \u00b7 {sign(y['gast'])}% vs ene\u2013may 2025</div></div>
          <div class="stat"><div class="stat-value tone-warning">{m['fmt_ytd_est']}</div><div class="stat-label">Transferencias Estado \u00b7 {sign(y['est'])}% vs ene\u2013may 2025</div></div>
          <div class="stat"><div class="stat-value tone-danger">{m['fmt_ytd_def']}</div><div class="stat-label">D\u00e9ficit cotiz. acum. \u00b7 {sign(y['def'])}% vs ene\u2013may 2025</div></div>
        </div>
        <div class="chart" style="height:220px"><canvas id="chart-avance"></canvas></div>
        <p class="caption">Eje Y: mil M\u20ac</p>
        <p class="caption">Ritmo similar a 2025: cotizaciones +{y['cot']}% ({m['fmt_ytd_cot']} acum.), gastos +{y['gast']}% ({m['fmt_ytd_gast']}), transferencias Estado +{y['est']}% ({m['fmt_ytd_est']}). D\u00e9ficit cotizaciones +{y['def']}% ({m['fmt_ytd_def']}).</p>
      </div>
    </div>
  </div>

  <div class="grid-4"{export_attr("02-cagr-stats")}>
    <div class="stat"><div class="stat-value tone-info">{m['cot_cagr']}%</div><div class="stat-label">CAGR cotizaciones 2014\u20132025 (sin transferencias)</div></div>
    <div class="stat"><div class="stat-value tone-warning">{m['est_cagr']}%</div><div class="stat-label">CAGR transferencias Estado 2014\u20132025</div></div>
    <div class="stat"><div class="stat-value">{m['gast_cagr']}%</div><div class="stat-label">CAGR gastos 2014\u20132025</div></div>
    <div class="stat"><div class="stat-value tone-info">+{m['cot_yoy_2025']}% / +{m['gast_yoy_2025']}%</div><div class="stat-label">Crecimiento interanual 2025 \u00b7 cotiz. / gastos</div></div>
  </div>

  <div class="callout"{export_attr("03-callout-2020")}>
    <div class="callout-title">El salto de 2020</div>
    <p class="callout-body">Las transferencias del Estado se duplicaron tras la aplicaci\u00f3n de la Recomendaci\u00f3n 1\u00aa del Pacto de Toledo: de ~13 mil M\u20ac/a\u00f1o a ~36 mil M\u20ac, y desde entonces rondan el 19% de los ingresos totales del sistema.</p>
  </div>

  <div class="card"{export_attr("04-cotizaciones-vs-gastos")}>
    <div class="card-header">Cotizaciones vs gastos del sistema</div>
    <div class="card-body">
      <div class="stack-4">
        <p class="caption">Sin incluir transferencias del Estado en los ingresos</p>
        <div class="chart" style="height:320px"><canvas id="chart-cot-gast"></canvas></div>
        <div class="spacer-8"></div>
        <p class="caption">Eje Y: mil M\u20ac \u00b7 Recaudaci\u00f3n neta de cotizaciones vs pagos realizados del agregado del sistema</p>
      </div>
    </div>
  </div>

  <div class="card"{export_attr("05-crecimiento-interanual")}>
    <div class="card-header">Crecimiento interanual</div>
    <div class="card-body">
      <div class="stack-4">
        <p class="caption">Variaci\u00f3n % respecto al a\u00f1o anterior \u00b7 cotizaciones vs gastos</p>
        <div class="chart" style="height:300px"><canvas id="chart-yoy"></canvas></div>
        <div class="spacer-8"></div>
        <p class="caption">Eje Y: variaci\u00f3n interanual (%). CAGR 2014\u20132025: cotizaciones +{m['cot_cagr']}%/a\u00f1o, transferencias Estado +{m['est_cagr']}%/a\u00f1o, gastos +{m['gast_cagr']}%/a\u00f1o. En 2020 las cotizaciones cayeron {m['covid_drop']}% por la pandemia.</p>
      </div>
    </div>
  </div>

  <div class="grid-2-export"{export_attr("06-transferencias-deficit")}>
    <div class="card">
      <div class="card-header">Transferencias del Estado</div>
      <div class="card-body">
        <div class="stack-4">
          <p class="caption">Recaudaci\u00f3n neta \u00b7 cap. 4 ingresos</p>
          <div class="chart" style="height:280px"><canvas id="chart-estado"></canvas></div>
          <div class="spacer-8"></div>
          <p class="caption">Eje Y: mil M\u20ac. CAGR 2014\u20132025: +{m['est_cagr']}%/a\u00f1o.</p>
        </div>
      </div>
    </div>
    <div class="card">
      <div class="card-header">D\u00e9ficit solo con cotizaciones</div>
      <div class="card-body">
        <div class="stack-4">
          <p class="caption">Gastos \u2212 cotizaciones (sin transferencias)</p>
          <div class="chart" style="height:280px"><canvas id="chart-deficit"></canvas></div>
          <div class="spacer-8"></div>
          <p class="caption">Eje Y: mil M\u20ac \u00b7 Gastos \u2212 cotizaciones, sin transferencias. +{m['deficit_growth']}% entre 2014 y 2025.</p>
        </div>
      </div>
    </div>
  </div>

  <div class="card"{export_attr("07-composicion-ingresos")}>
    <div class="card-header">Composici\u00f3n de ingresos</div>
    <div class="card-body">
      <div class="stack-4">
        <p class="caption">Cotizaciones + transferencias del Estado</p>
        <div class="chart chart-tall" style="height:330px"><canvas id="chart-comp"></canvas></div>
        <div class="spacer-8"></div>
        <p class="caption">Eje Y: mil M\u20ac \u00b7 Barras apiladas = ingresos corrientes principales del sistema (sin tasas ni otros ingresos menores)</p>
      </div>
    </div>
  </div>

  <div class="card borderless"{export_attr("08-lectura-rapida")}>
    <div class="card-body">
      <div class="stack-12">
        <h3>Lectura r\u00e1pida</h3>
        <div class="grid-2">
          <p class="text-secondary" style="max-width:none;margin:0">Las cotizaciones (sin transferencias) crecen un {m['cot_cagr']}% anual de media; las transferencias del Estado un {m['est_cagr']}% \u2014 m\u00e1s del doble. Los gastos crecen un {m['gast_cagr']}% anual. En 2025: cotizaciones +{m['cot_yoy_2025']}% y gastos +{m['gast_yoy_2025']}% interanual.</p>
          <p class="text-secondary" style="max-width:none;margin:0">El Estado aporta cada vez m\u00e1s: de ~{m['fmt_first_est']} (10% de ingresos) a ~{m['fmt_last_est']} ({m['pct_estado']}%). Sin esas transferencias, el sistema no cuadrar\u00eda.</p>
        </div>
      </div>
    </div>
  </div>

</div>
{site_footer}
<script>
const COLORS = {{ info: '#3685BF', danger: '#CF2D56', warning: '#C08532', grid: '#E4E4E7', muted: '#A1A1AA' }};
const chartDefaults = {{
  responsive: true,
  maintainAspectRatio: false,
  animation: false,
  layout: {{ padding: {{ left: 16, right: 20, top: 4, bottom: 4 }} }},
  plugins: {{
    legend: {{ position: 'top', align: 'start', labels: {{ boxWidth: 12, font: {{ size: 11 }} }} }},
    tooltip: {{ enabled: false }}
  }},
  scales: {{
    x: {{ grid: {{ display: false }}, offset: true, ticks: {{ font: {{ size: 11 }}, color: COLORS.muted }} }},
    y: {{ grid: {{ color: COLORS.grid }}, border: {{ display: false }}, ticks: {{ font: {{ size: 11 }}, color: COLORS.muted }} }}
  }}
}};

const barOptions = {{
  ...chartDefaults,
  datasets: {{ bar: {{ categoryPercentage: 0.68, barPercentage: 0.88 }} }},
  scales: chartDefaults.scales,
}};

const wideBarLayout = {{ padding: {{ left: 40, right: 44, top: 8, bottom: 18 }} }};
const narrowBarLayout = {{ padding: {{ left: 20, right: 48, top: 8, bottom: 18 }} }};

function groupedBar(id, labels, datasets) {{
  new Chart(document.getElementById(id), {{
    type: 'bar',
    data: {{ labels, datasets }},
    options: barOptions,
  }});
}}

const years = {json.dumps(m['years'])};
const cot = {json.dumps(m['cot'])};
const gast = {json.dumps(m['gast'])};
const est = {json.dumps(m['est'])};
const deficit = {json.dumps(m['deficit'])};
const yoyYears = {json.dumps(m['yoy_years'])};
const cotY = {json.dumps(m['cot_y'])};
const gastY = {json.dumps(m['gast_y'])};

groupedBar('chart-avance', {json.dumps(m['avance_cats'])}, [
  {{ label: 'Cotizaciones', data: {json.dumps(m['avance_cot'])}, backgroundColor: COLORS.info }},
  {{ label: 'Gastos', data: {json.dumps(m['avance_gast'])}, backgroundColor: COLORS.danger }},
  {{ label: 'Transferencias Estado', data: {json.dumps(m['avance_est'])}, backgroundColor: COLORS.warning }},
]);

groupedBar('chart-cot-gast', years, [
  {{ label: 'Cotizaciones sociales', data: cot, backgroundColor: COLORS.info }},
  {{ label: 'Gastos totales', data: gast, backgroundColor: COLORS.danger }},
]);
// margen extra en series largas
Chart.getChart('chart-cot-gast').options.layout = wideBarLayout;
Chart.getChart('chart-cot-gast').options.datasets.bar.categoryPercentage = 0.58;
Chart.getChart('chart-cot-gast').update();

new Chart(document.getElementById('chart-yoy'), {{
  type: 'bar',
  data: {{
    labels: yoyYears,
    datasets: [
      {{ label: 'Cotizaciones sociales', data: cotY, backgroundColor: COLORS.info }},
      {{ label: 'Gastos totales', data: gastY, backgroundColor: COLORS.danger }},
    ]
  }},
  options: {{
    ...barOptions,
    scales: {{
      ...chartDefaults.scales,
      y: {{ ...chartDefaults.scales.y, ticks: {{ callback: v => v + '%' }} }},
    }},
    plugins: {{
      ...chartDefaults.plugins,
      annotation: undefined
    }}
  }},
  plugins: [{{
    id: 'zeroLine',
    afterDraw(chart) {{
      const yScale = chart.scales.y;
      const y0 = yScale.getPixelForValue(0);
      const ctx = chart.ctx;
      ctx.save();
      ctx.strokeStyle = COLORS.muted;
      ctx.lineWidth = 1;
      ctx.beginPath();
      ctx.moveTo(chart.chartArea.left, y0);
      ctx.lineTo(chart.chartArea.right, y0);
      ctx.stroke();
      ctx.restore();
    }}
  }}]
}});
Chart.getChart('chart-yoy').options.layout = wideBarLayout;
Chart.getChart('chart-yoy').options.datasets.bar.categoryPercentage = 0.58;
Chart.getChart('chart-yoy').update();

new Chart(document.getElementById('chart-estado'), {{
  type: 'line',
  data: {{
    labels: years,
    datasets: [{{
      label: 'Transferencias Estado',
      data: est,
      borderColor: COLORS.warning,
      backgroundColor: 'rgba(192, 133, 50, 0.15)',
      fill: true,
      tension: 0.15,
      pointRadius: 3,
      borderWidth: 2
    }}]
  }},
  options: {{
    ...chartDefaults,
    layout: narrowBarLayout,
  }}
}});

new Chart(document.getElementById('chart-deficit'), {{
  type: 'bar',
  data: {{
    labels: years,
    datasets: [{{ label: 'D\u00e9ficit estructural', data: deficit, backgroundColor: COLORS.danger }}]
  }},
  options: {{
    ...barOptions,
    layout: narrowBarLayout,
    datasets: {{ bar: {{ categoryPercentage: 0.42, barPercentage: 0.82 }} }},
    scales: {{
      x: {{
        ...chartDefaults.scales.x,
        offset: true,
        bounds: 'ticks',
        grid: {{ display: false, offset: true }},
        ticks: {{ font: {{ size: 10 }}, color: COLORS.muted, autoSkip: false, maxRotation: 0 }},
      }},
      y: chartDefaults.scales.y,
    }}
  }}
}});

new Chart(document.getElementById('chart-comp'), {{
  type: 'bar',
  data: {{
    labels: years,
    datasets: [
      {{ label: 'Cotizaciones sociales', data: cot, backgroundColor: COLORS.info, stack: 's' }},
      {{ label: 'Transferencias Estado', data: est, backgroundColor: COLORS.warning, stack: 's' }},
    ]
  }},
  options: {{
    ...barOptions,
    layout: wideBarLayout,
    datasets: {{ bar: {{ categoryPercentage: 0.55, barPercentage: 0.86 }} }},
    scales: {{
      x: {{
        ...chartDefaults.scales.x,
        stacked: true,
        offset: true,
        bounds: 'ticks',
        grid: {{ display: false, offset: true }},
        ticks: {{ font: {{ size: 11 }}, color: COLORS.muted, autoSkip: false, maxRotation: 0 }},
      }},
      y: {{ ...chartDefaults.scales.y, stacked: true }}
    }}
  }}
}});

document.body.setAttribute('data-ready', '1');
</script>
</body>
</html>"""


EXPORTS = [
    ("00-header", "#export-00-header"),
    ("01-avance-2026", "#export-01-avance-2026"),
    ("02-cagr-stats", "#export-02-cagr-stats"),
    ("03-callout-2020", "#export-03-callout-2020"),
    ("04-cotizaciones-vs-gastos", "#export-04-cotizaciones-vs-gastos"),
    ("05-crecimiento-interanual", "#export-05-crecimiento-interanual"),
    ("06-transferencias-deficit", "#export-06-transferencias-deficit"),
    ("07-composicion-ingresos", "#export-07-composicion-ingresos"),
    ("08-lectura-rapida", "#export-08-lectura-rapida"),
]

PAGE1_KEYS = ["00-header", "01-avance-2026", "02-cagr-stats", "03-callout-2020", "04-cotizaciones-vs-gastos"]
PAGE2_KEYS = ["05-crecimiento-interanual", "06-transferencias-deficit", "07-composicion-ingresos", "08-lectura-rapida"]

SCREENSHOT_PAD = {
    "06-transferencias-deficit": 12,
}

SCREENSHOT_LOCATOR = {
    "04-cotizaciones-vs-gastos",
    "05-crecimiento-interanual",
    "06-transferencias-deficit",
    "07-composicion-ingresos",
}


def element_clip(page, selector: str, pad: int = 8) -> dict:
    return page.evaluate(
        """([sel, pad]) => {
        const el = document.querySelector(sel);
        if (!el) return null;
        const r = el.getBoundingClientRect();
        return {
          x: Math.max(0, r.left - pad),
          y: Math.max(0, r.top - pad),
          width: r.width + pad * 2,
          height: r.height + pad * 2,
        };
    }""",
        [selector, pad],
    )


def screenshot_export(page, name: str, selector: str, out: Path) -> None:
    loc = page.locator(selector)
    loc.scroll_into_view_if_needed()
    if name in SCREENSHOT_LOCATOR:
        loc.screenshot(path=str(out))
        return
    pad = SCREENSHOT_PAD.get(name, 8)
    clip = element_clip(page, selector, pad)
    if clip:
        page.screenshot(path=str(out), clip=clip)
    else:
        loc.screenshot(path=str(out))


def screenshot_sections() -> None:
    from playwright.sync_api import sync_playwright
    from PIL import Image

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    HTML_PATH.parent.mkdir(parents=True, exist_ok=True)

    rows = load_rows()
    m = build_model(rows)
    HTML_PATH.write_text(render_html(m), encoding="utf-8")

    url = HTML_PATH.resolve().as_uri()
    shots: dict[str, Path] = {}

    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={"width": 1400, "height": 1200}, device_scale_factor=2)
        page.goto(url, wait_until="networkidle")
        page.wait_for_selector("[data-ready='1']", timeout=15000)
        page.wait_for_function(
            "() => document.querySelectorAll('canvas').length >= 6 && "
            "[...document.querySelectorAll('canvas')].every(c => c.width > 0 && c.height > 0)",
            timeout=15000,
        )
        page.wait_for_timeout(500)

        for name, selector in EXPORTS:
            out = OUT_DIR / f"{name}.png"
            screenshot_export(page, name, selector, out)
            shots[name] = out
            print(f"  \u2192 canvas/{name}.png")

        browser.close()

    # Páginas compuestas (misma estructura, dos bloques)
    def stack_page(keys: list[str], out_name: str, pad_x: int = 90) -> None:
        images = [Image.open(shots[key]) for key in keys]
        w = 1100
        scaled = []
        for im in images:
            ratio = w / im.width
            scaled.append(im.resize((w, int(im.height * ratio)), Image.Resampling.LANCZOS))
        gap = 24
        total_h = sum(im.height for im in scaled) + gap * (len(scaled) - 1)
        canvas = Image.new("RGB", (w + pad_x * 2, total_h), "#fafafa")
        y = 0
        for im in scaled:
            canvas.paste(im, (pad_x, y))
            y += im.height + gap
        page_path = OUT_DIR.parent / out_name
        canvas.save(page_path, optimize=True)
        print(f"  \u2192 {out_name} ({canvas.width}\u00d7{canvas.height}px)")

    stack_page(PAGE1_KEYS, "informe-seguridad-social-pagina-1.png")
    stack_page(PAGE2_KEYS, "informe-seguridad-social-pagina-2.png")


def build_pdf_from_pages() -> None:
    from fpdf import FPDF
    from PIL import Image

    pdf = FPDF(orientation="P", unit="mm", format="A4")
    pdf.set_margins(24, 14, 24)
    content_w = 210 - 48
    content_h = 262

    for page_png in ["informe-seguridad-social-pagina-1.png", "informe-seguridad-social-pagina-2.png"]:
        path = OUT_DIR.parent / page_png
        if not path.exists():
            continue
        with Image.open(path) as im:
            aspect = im.height / im.width
        pdf.add_page()
        w = content_w
        h = w * aspect
        if h > content_h:
            h = content_h
            w = h / aspect
        x = 24 + (content_w - w) / 2
        pdf.image(str(path), x=x, w=w, h=h)

    out = OUT_DIR.parent / "informe-seguridad-social.pdf"
    pdf.output(str(out))
    print(f"  \u2192 {out.name}")


def main() -> None:
    print("Exportando secciones del canvas...")
    screenshot_sections()
    print("Generando PDF (2 paginas)...")
    build_pdf_from_pages()
    print(f"\nListo: {OUT_DIR} y {OUT_DIR.parent}/informe-seguridad-social-pagina-*.png")


if __name__ == "__main__":
    main()
