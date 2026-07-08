#!/usr/bin/env python3
"""Genera informe PDF e imágenes PNG del análisis ResSISTEMA (estructura canvas)."""

from __future__ import annotations

import io
import json
import os
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from fpdf import FPDF
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
DATA_PATH = ROOT / "data/processed/annual_series.json"
OUT_DIR = ROOT / "output"
CANVAS_W = 920  # ancho contenido (márgenes blancos al imprimir)
DPI = 150
PAGE_GAP = 14
# A4 apaisado en mm → límite altura del bloque al generar PNG
PAGE_MAX_H_PX = int(250 / 25.4 * DPI)
PDF_SIDE_MARGIN_MM = 24
PDF_CONTENT_W_MM = 210 - 2 * PDF_SIDE_MARGIN_MM
PDF_CONTENT_H_MM = 262

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

C = {
    "page": "#F4F4F5",
    "card": "#FFFFFF",
    "border": "#E4E4E7",
    "text": "#18181B",
    "secondary": "#52525B",
    "muted": "#A1A1AA",
    "info": "#3685BF",
    "info_soft": "#E8F2FA",
    "warning": "#C08532",
    "warning_soft": "#FBF3E6",
    "danger": "#CF2D56",
    "danger_soft": "#FCE8ED",
    "neutral": "#71717A",
    "grid": "#E4E4E7",
    "callout_border": "#E8D4B0",
}

# Proporciones fijas (pulgadas)
FIG_HEADER = (11, 1.2)
FIG_STATS = (11, 0.95)
FIG_CALLOUT = (11, 1.0)
FIG_CHART = (11, 3.35)
FIG_CHART_COMPACT = (11, 2.75)
FIG_CHART_PAIR = (11, 3.2)
FIG_FOOTER = (11, 1.25)
PAGE_GAP = 10


def mil_m(v: float) -> float:
    return round(v / 1000, 1)


def fmt_mil_m(v: float) -> str:
    return f"{mil_m(v):.1f}".replace(".", ",") + " mil M\u20ac"


def yoy_pct(cur: float, prev: float) -> float:
    return round((cur - prev) / prev * 100, 1)


def cagr(first: float, last: float, years: int) -> float:
    return round(((last / first) ** (1 / years) - 1) * 100, 1)


def load_data() -> list[dict]:
    with open(DATA_PATH, encoding="utf-8") as f:
        return json.load(f)


def setup_style() -> None:
    os.environ.setdefault("MPLCONFIGDIR", str(OUT_DIR / ".mplconfig"))
    plt.rcParams.update(
        {
            "figure.facecolor": C["page"],
            "axes.facecolor": C["card"],
            "axes.edgecolor": C["border"],
            "axes.labelcolor": C["secondary"],
            "axes.linewidth": 0.6,
            "xtick.color": C["muted"],
            "ytick.color": C["muted"],
            "text.color": C["text"],
            "font.family": "sans-serif",
            "font.size": 9,
            "legend.frameon": False,
            "grid.color": C["grid"],
            "grid.linewidth": 0.5,
        }
    )


def fig_to_image(fig) -> Image.Image:
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=DPI, facecolor=C["page"], bbox_inches="tight", pad_inches=0.12)
    plt.close(fig)
    buf.seek(0)
    return Image.open(buf).convert("RGB")


def resize_to_width(img: Image.Image, width: int) -> Image.Image:
    if img.width == width:
        return img
    ratio = width / img.width
    return img.resize((width, max(1, int(img.height * ratio))), Image.Resampling.LANCZOS)


def stack_images(images: list[Image.Image], gap: int = PAGE_GAP) -> Image.Image:
    images = [resize_to_width(im, CANVAS_W) for im in images]
    total_h = sum(im.height for im in images) + gap * max(0, len(images) - 1)
    canvas = Image.new("RGB", (CANVAS_W, total_h), C["page"])
    y = 0
    for im in images:
        canvas.paste(im, (0, y))
        y += im.height + gap
    return canvas


def fit_to_max_height(img: Image.Image, max_h: int) -> Image.Image:
    if img.height <= max_h:
        return img
    ratio = max_h / img.height
    new_w = max(1, int(img.width * ratio))
    new_h = max(1, int(img.height * ratio))
    return img.resize((new_w, new_h), Image.Resampling.LANCZOS)


def pad_horizontal(img: Image.Image, canvas_w: int = 1100) -> Image.Image:
    """Centra el bloque en un lienzo más ancho (márgenes blancos a los lados)."""
    if img.width >= canvas_w:
        return img
    canvas = Image.new("RGB", (canvas_w, img.height), C["page"])
    x = (canvas_w - img.width) // 2
    canvas.paste(img, (x, 0))
    return canvas


def card_patch(ax) -> None:
    ax.set_facecolor(C["card"])
    for spine in ax.spines.values():
        spine.set_visible(True)
        spine.set_color(C["border"])
        spine.set_linewidth(0.8)


def style_chart_ax(ax, ylabel: str = "mil M\u20ac") -> None:
    ax.set_ylabel(ylabel, fontsize=8, color=C["secondary"])
    ax.tick_params(axis="both", labelsize=7.5)
    ax.grid(axis="y", alpha=0.85)
    ax.set_axisbelow(True)
    ax.set_box_aspect(None)  # no forzar ratio del eje


def draw_stat_row(ax, stats: list[tuple[str, str, str | None]]) -> None:
    ax.axis("off")
    n = len(stats)
    margin_x, gap = 0.04, 0.018
    total_gap = gap * (n - 1)
    box_w = (1 - 2 * margin_x - total_gap) / n
    box_h, box_y = 0.52, 0.24
    for i, (label, value, tone) in enumerate(stats):
        x0 = margin_x + i * (box_w + gap)
        bg, border, val_color = C["card"], C["border"], C["text"]
        if tone == "info":
            bg, border, val_color = C["info_soft"], "#C5DFF0", C["info"]
        elif tone == "warning":
            bg, border, val_color = C["warning_soft"], "#E8D4B0", C["warning"]
        elif tone == "danger":
            bg, border, val_color = C["danger_soft"], "#F0C5CF", C["danger"]
        rect = mpatches.FancyBboxPatch(
            (x0, box_y), box_w, box_h,
            boxstyle="round,pad=0.006,rounding_size=0.015",
            transform=ax.transAxes,
            facecolor=bg, edgecolor=border, linewidth=0.7,
        )
        ax.add_patch(rect)
        ax.text(x0 + box_w / 2, box_y + box_h * 0.62, value, transform=ax.transAxes, ha="center", va="center",
                fontsize=9.5, fontweight="bold", color=val_color)
        ax.text(x0 + box_w / 2, box_y + box_h * 0.22, label, transform=ax.transAxes, ha="center", va="center",
                fontsize=6.8, color=C["secondary"])


def plot_grouped_bars(ax, categories, series, bar_w: float | None = None):
    n_cat = len(categories)
    n_series = len(series)
    x = list(range(n_cat))
    if bar_w is None:
        if n_cat <= 2:
            bar_w = 0.12
        elif n_cat <= 5:
            bar_w = 0.14
        else:
            bar_w = min(0.4 / n_series, 0.2)
    for i, (name, vals, color) in enumerate(series):
        offset = (i - (n_series - 1) / 2) * bar_w
        ax.bar(
            [xi + offset for xi in x], vals, bar_w * 0.92,
            label=name, color=color, edgecolor="white", linewidth=0.4,
        )
    ax.set_xticks(x, categories, fontsize=7.5)
    pad = 0.55 if n_cat <= 2 else (0.42 if n_cat <= 5 else 0.38)
    ax.set_xlim(-pad, n_cat - 1 + pad)
    if n_series > 1:
        ax.legend(fontsize=7, loc="upper left", ncol=min(3, n_series))


def metrics(data: list[dict]) -> dict:
    first, last, prev = data[0], data[-1], data[-2]
    n = len(data) - 1
    return {
        "first": first,
        "last": last,
        "prev": prev,
        "cot_cagr": cagr(first["cotizaciones"], last["cotizaciones"], n),
        "gast_cagr": cagr(first["gastos"], last["gastos"], n),
        "est_cagr": cagr(first["transferencias_estado"], last["transferencias_estado"], n),
        "cot_yoy_2025": yoy_pct(last["cotizaciones"], prev["cotizaciones"]),
        "gast_yoy_2025": yoy_pct(last["gastos"], prev["gastos"]),
        "deficit_growth": round((last["deficit_cotizaciones"] - first["deficit_cotizaciones"]) / first["deficit_cotizaciones"] * 100),
        "ytd": {
            "cot": yoy_pct(YTD_MAYO_2026["cotizaciones"], YTD_MAYO_2025["cotizaciones"]),
            "gast": yoy_pct(YTD_MAYO_2026["gastos"], YTD_MAYO_2025["gastos"]),
            "est": yoy_pct(YTD_MAYO_2026["transferencias_estado"], YTD_MAYO_2025["transferencias_estado"]),
            "def": yoy_pct(YTD_MAYO_2026["deficit_cotizaciones"], YTD_MAYO_2025["deficit_cotizaciones"]),
        },
    }


def panel_header() -> Image.Image:
    fig = plt.figure(figsize=FIG_HEADER, facecolor=C["page"])
    ax = fig.add_axes([0, 0, 1, 1])
    ax.axis("off")
    ax.text(0.04, 0.84, "Seguridad Social \u2014 Serie hist\u00f3rica anual", fontsize=15, fontweight="bold", color=C["text"], va="top")
    ax.text(
        0.04, 0.42,
        "Cotizaciones sociales frente a gasto total del sistema, y evoluci\u00f3n de las transferencias del Estado.\n"
        "Cifras acumuladas de cierre de ejercicio (ResSISTEMA). Importes en miles de millones de euros.",
        fontsize=9, color=C["secondary"], va="top", linespacing=1.45,
    )
    ax.text(0.04, 0.04, "Fuente: TGSS / Intervenci\u00f3n General de la SS \u00b7 ResSISTEMA 2014\u20132025 (cierre) y mayo 2026 (avance)",
            fontsize=7.8, color=C["muted"], va="bottom")
    return fig_to_image(fig)


def panel_stats(stats: list[tuple[str, str, str | None]]) -> Image.Image:
    fig = plt.figure(figsize=FIG_STATS, facecolor=C["page"])
    ax = fig.add_axes([0.02, 0.05, 0.96, 0.9])
    draw_stat_row(ax, stats)
    return fig_to_image(fig)


def panel_callout(title: str, body: str) -> Image.Image:
    fig = plt.figure(figsize=FIG_CALLOUT, facecolor=C["page"])
    ax = fig.add_axes([0.02, 0.05, 0.96, 0.9])
    ax.axis("off")
    rect = mpatches.FancyBboxPatch(
        (0.01, 0.05), 0.98, 0.9,
        boxstyle="round,pad=0.01,rounding_size=0.015",
        transform=ax.transAxes,
        facecolor=C["warning_soft"], edgecolor=C["callout_border"], linewidth=1,
    )
    ax.add_patch(rect)
    ax.text(0.04, 0.82, title, transform=ax.transAxes, fontsize=9.5, fontweight="600", color=C["warning"])
    ax.text(0.04, 0.52, body, transform=ax.transAxes, fontsize=8.5, color=C["secondary"], va="top", linespacing=1.5)
    return fig_to_image(fig)


def panel_chart(
    title: str,
    subtitle: str,
    caption: str,
    plot_fn,
    figsize=FIG_CHART,
    chart_rect: tuple[float, float, float, float] = (0.06, 0.13, 0.88, 0.67),
) -> Image.Image:
    fig = plt.figure(figsize=figsize, facecolor=C["page"])
    fig.text(0.05, 0.95, title, fontsize=10.5, fontweight="600", color=C["text"], va="top")
    if subtitle:
        fig.text(0.05, 0.89, subtitle, fontsize=8, color=C["muted"], va="top")
    left, bottom, width, height = chart_rect
    ax = fig.add_axes([left, bottom, width, height])
    card_patch(ax)
    plot_fn(ax)
    fig.text(0.05, 0.035, caption, fontsize=7.8, color=C["muted"], va="bottom", wrap=True)
    return fig_to_image(fig)


def panel_chart_pair(left: tuple, right: tuple) -> Image.Image:
    fig = plt.figure(figsize=FIG_CHART_PAIR, facecolor=C["page"])
    for col, (title, subtitle, caption, plot_fn) in enumerate([left, right]):
        x0 = 0.05 + col * 0.49
        fig.text(x0, 0.94, title, fontsize=10, fontweight="600", color=C["text"], va="top")
        if subtitle:
            fig.text(x0, 0.88, subtitle, fontsize=7, color=C["muted"], va="top")
        ax = fig.add_axes([x0, 0.16, 0.44, 0.66])
        card_patch(ax)
        plot_fn(ax)
        fig.text(x0, 0.04, caption, fontsize=6.5, color=C["muted"], va="bottom")
    return fig_to_image(fig)


def panel_footer(m: dict) -> Image.Image:
    fig = plt.figure(figsize=FIG_FOOTER, facecolor=C["page"])
    ax = fig.add_axes([0, 0, 1, 1])
    ax.axis("off")
    ax.text(0.04, 0.88, "Lectura r\u00e1pida", fontsize=10, fontweight="600", color=C["text"], va="top")
    col1 = (
        f"Las cotizaciones (sin transferencias) crecen un {m['cot_cagr']}% anual de media; "
        f"las transferencias del Estado un {m['est_cagr']}% \u2014 m\u00e1s del doble. "
        f"Los gastos crecen un {m['gast_cagr']}% anual. "
        f"En 2025: cotizaciones +{m['cot_yoy_2025']}% y gastos +{m['gast_yoy_2025']}% interanual."
    )
    col2 = (
        f"El Estado aporta cada vez m\u00e1s: de ~{fmt_mil_m(m['first']['transferencias_estado'])} (10% de ingresos) "
        f"a ~{fmt_mil_m(m['last']['transferencias_estado'])} ({m['last']['pct_estado_en_ingresos']}%). "
        f"Sin esas transferencias, el sistema no cuadrar\u00eda."
    )
    ax.text(0.04, 0.78, col1, fontsize=8.5, color=C["secondary"], va="top", wrap=True, linespacing=1.5)
    ax.text(0.51, 0.78, col2, fontsize=8.5, color=C["secondary"], va="top", wrap=True, linespacing=1.5)
    return fig_to_image(fig)


def collect_panels(data: list[dict]) -> list[Image.Image]:
    m = metrics(data)
    years = [str(d["year"]) for d in data]
    cot = [mil_m(d["cotizaciones"]) for d in data]
    gast = [mil_m(d["gastos"]) for d in data]
    est = [mil_m(d["transferencias_estado"]) for d in data]
    deficit = [mil_m(d["deficit_cotizaciones"]) for d in data]
    yoy_years, cot_y, gast_y = [], [], []
    for i in range(1, len(data)):
        yoy_years.append(str(data[i]["year"]))
        cot_y.append(yoy_pct(data[i]["cotizaciones"], data[i - 1]["cotizaciones"]))
        gast_y.append(yoy_pct(data[i]["gastos"], data[i - 1]["gastos"]))
    covid_drop = cot_y[yoy_years.index("2020")]
    y = m["ytd"]

    return [
        panel_header(),
        panel_stats([
            (f"Cotizaciones acum. \u00b7 +{y['cot']}% vs ene\u2013may 2025", fmt_mil_m(YTD_MAYO_2026["cotizaciones"]), "info"),
            (f"Gastos acum. \u00b7 +{y['gast']}% vs ene\u2013may 2025", fmt_mil_m(YTD_MAYO_2026["gastos"]), None),
            (f"Transferencias Estado \u00b7 +{y['est']}% vs ene\u2013may 2025", fmt_mil_m(YTD_MAYO_2026["transferencias_estado"]), "warning"),
            (f"D\u00e9ficit cotiz. acum. \u00b7 +{y['def']}% vs ene\u2013may 2025", fmt_mil_m(YTD_MAYO_2026["deficit_cotizaciones"]), "danger"),
        ]),
        panel_chart(
            "Avance 2026 (enero\u2013mayo)", "Datos acumulados a fin de mayo \u2014 no es cierre anual.", "Eje Y: mil M\u20ac",
            lambda ax: (
                plot_grouped_bars(ax, ["Ene\u2013may 2025", "Ene\u2013may 2026"], [
                    ("Cotizaciones", [mil_m(YTD_MAYO_2025["cotizaciones"]), mil_m(YTD_MAYO_2026["cotizaciones"])], C["info"]),
                    ("Gastos", [mil_m(YTD_MAYO_2025["gastos"]), mil_m(YTD_MAYO_2026["gastos"])], C["danger"]),
                    ("Transferencias Estado", [mil_m(YTD_MAYO_2025["transferencias_estado"]), mil_m(YTD_MAYO_2026["transferencias_estado"])], C["warning"]),
                ], bar_w=0.11),
                style_chart_ax(ax),
            ),
            figsize=FIG_CHART_COMPACT,
            chart_rect=(0.26, 0.14, 0.48, 0.66),
        ),
        panel_stats([
            ("CAGR cotizaciones 2014\u20132025 (sin transferencias)", f"{m['cot_cagr']}%", "info"),
            ("CAGR transferencias Estado 2014\u20132025", f"{m['est_cagr']}%", "warning"),
            ("CAGR gastos 2014\u20132025", f"{m['gast_cagr']}%", None),
            (f"Crecimiento interanual 2025 \u00b7 cotiz. / gastos", f"+{m['cot_yoy_2025']}% / +{m['gast_yoy_2025']}%", "info"),
        ]),
        panel_callout(
            "El salto de 2020",
            "Las transferencias del Estado se duplicaron tras la aplicaci\u00f3n de la Recomendaci\u00f3n 1\u00aa del Pacto de Toledo: "
            "de ~13 mil M\u20ac/a\u00f1o a ~36 mil M\u20ac, y desde entonces rondan el 19% de los ingresos totales del sistema.",
        ),
        panel_chart(
            "Cotizaciones vs gastos del sistema", "Sin incluir transferencias del Estado en los ingresos",
            "Eje Y: mil M\u20ac \u00b7 Recaudaci\u00f3n neta de cotizaciones vs pagos realizados",
            lambda ax: (
                plot_grouped_bars(ax, years, [
                    ("Cotizaciones sociales", cot, C["info"]),
                    ("Gastos totales", gast, C["danger"]),
                ], bar_w=0.19),
                style_chart_ax(ax),
            ),
            chart_rect=(0.05, 0.13, 0.9, 0.67),
        ),
        panel_chart(
            "Crecimiento interanual", "Variaci\u00f3n % respecto al a\u00f1o anterior \u00b7 cotizaciones vs gastos",
            f"Eje Y: variaci\u00f3n interanual (%). CAGR 2014\u20132025: cotizaciones +{m['cot_cagr']}%/a\u00f1o, "
            f"transferencias Estado +{m['est_cagr']}%/a\u00f1o, gastos +{m['gast_cagr']}%/a\u00f1o. "
            f"En 2020 las cotizaciones cayeron {covid_drop}% por la pandemia.",
            lambda ax: (
                plot_grouped_bars(ax, yoy_years, [
                    ("Cotizaciones sociales", cot_y, C["info"]),
                    ("Gastos totales", gast_y, C["danger"]),
                ], bar_w=0.19),
                ax.axhline(0, color=C["neutral"], lw=0.7),
                ax.set_ylabel("%", fontsize=8, color=C["secondary"]),
                ax.grid(axis="y", alpha=0.85),
            ),
        ),
        panel_chart_pair(
            (
                "Transferencias del Estado", "Recaudaci\u00f3n neta \u00b7 cap. 4 ingresos",
                f"Eje Y: mil M\u20ac. CAGR 2014\u20132025: +{m['est_cagr']}%/a\u00f1o.",
                lambda ax: (
                    ax.plot(range(len(years)), est, color=C["warning"], lw=2.2, marker="o", ms=3),
                    ax.fill_between(range(len(years)), est, alpha=0.15, color=C["warning"]),
                    ax.set_xticks(range(len(years)), years, rotation=45, ha="right", fontsize=6.5),
                    style_chart_ax(ax),
                ),
            ),
            (
                "D\u00e9ficit solo con cotizaciones", "Gastos \u2212 cotizaciones (sin transferencias)",
                f"Eje Y: mil M\u20ac \u00b7 +{m['deficit_growth']}% entre 2014 y 2025.",
                lambda ax: (
                    ax.bar(range(len(years)), deficit, color=C["danger"], width=0.8, edgecolor="white", linewidth=0.3),
                    ax.set_xticks(range(len(years)), years, rotation=45, ha="right", fontsize=6.5),
                    style_chart_ax(ax),
                ),
            ),
        ),
        panel_chart(
            "Composici\u00f3n de ingresos", "Cotizaciones + transferencias del Estado",
            "Eje Y: mil M\u20ac \u00b7 Barras apiladas = ingresos corrientes principales del sistema",
            lambda ax: (
                ax.bar(range(len(years)), cot, label="Cotizaciones sociales", color=C["info"], width=0.78, edgecolor="white", linewidth=0.3),
                ax.bar(range(len(years)), est, bottom=cot, label="Transferencias Estado", color=C["warning"], width=0.78, edgecolor="white", linewidth=0.3),
                ax.set_xticks(range(len(years)), years, rotation=45, ha="right", fontsize=7),
                ax.legend(fontsize=7, loc="upper left"),
                style_chart_ax(ax),
            ),
        ),
        panel_footer(m),
    ]


def build_page_blocks(data: list[dict], path1: Path, path2: Path) -> tuple[Path, Path]:
    panels = collect_panels(data)
    # Pág. 1: cabecera → cotizaciones vs gastos | Pág. 2: resto
    split_at = 6
    page1 = pad_horizontal(fit_to_max_height(stack_images(panels[:split_at]), PAGE_MAX_H_PX))
    page2 = pad_horizontal(fit_to_max_height(stack_images(panels[split_at:]), PAGE_MAX_H_PX))
    page1.save(path1, format="PNG", optimize=True)
    page2.save(path2, format="PNG", optimize=True)
    print(f"  \u2192 {path1.name} ({page1.width}\u00d7{page1.height}px)")
    print(f"  \u2192 {path2.name} ({page2.width}\u00d7{page2.height}px)")
    return path1, path2


def build_individual_charts(data: list[dict], out: dict[str, Path]) -> None:
    m = metrics(data)
    years = [str(d["year"]) for d in data]
    cot = [mil_m(d["cotizaciones"]) for d in data]
    gast = [mil_m(d["gastos"]) for d in data]
    est = [mil_m(d["transferencias_estado"]) for d in data]
    deficit = [mil_m(d["deficit_cotizaciones"]) for d in data]
    yoy_years, cot_y, gast_y = [], [], []
    for i in range(1, len(data)):
        yoy_years.append(str(data[i]["year"]))
        cot_y.append(yoy_pct(data[i]["cotizaciones"], data[i - 1]["cotizaciones"]))
        gast_y.append(yoy_pct(data[i]["gastos"], data[i - 1]["gastos"]))

    charts = [
        (out["avance_2026"], "Avance 2026 (enero\u2013mayo)", "Datos acumulados a fin de mayo", "Eje Y: mil M\u20ac",
         lambda ax: (plot_grouped_bars(ax, ["Ene\u2013may 2025", "Ene\u2013may 2026"], [
             ("Cotizaciones", [mil_m(YTD_MAYO_2025["cotizaciones"]), mil_m(YTD_MAYO_2026["cotizaciones"])], C["info"]),
             ("Gastos", [mil_m(YTD_MAYO_2025["gastos"]), mil_m(YTD_MAYO_2026["gastos"])], C["danger"]),
             ("Transferencias Estado", [mil_m(YTD_MAYO_2025["transferencias_estado"]), mil_m(YTD_MAYO_2026["transferencias_estado"])], C["warning"]),
         ], bar_w=0.11), style_chart_ax(ax)), FIG_CHART_COMPACT, (0.26, 0.14, 0.48, 0.66)),
        (out["cot_vs_gastos"], "Cotizaciones vs gastos del sistema", "Sin incluir transferencias del Estado", "Eje Y: mil M\u20ac",
         lambda ax: (plot_grouped_bars(ax, years, [("Cotizaciones sociales", cot, C["info"]), ("Gastos totales", gast, C["danger"])], bar_w=0.19), style_chart_ax(ax)), FIG_CHART, (0.05, 0.13, 0.9, 0.67)),
        (out["yoy"], "Crecimiento interanual", "Variaci\u00f3n % respecto al a\u00f1o anterior", f"CAGR cotiz. +{m['cot_cagr']}%/a\u00f1o",
         lambda ax: (plot_grouped_bars(ax, yoy_years, [("Cotizaciones sociales", cot_y, C["info"]), ("Gastos totales", gast_y, C["danger"])], bar_w=0.19), ax.axhline(0, color=C["neutral"], lw=0.7), ax.set_ylabel("%", fontsize=8, color=C["secondary"]), ax.grid(axis="y", alpha=0.85)), FIG_CHART, (0.06, 0.13, 0.88, 0.67)),
        (out["transferencias"], "Transferencias del Estado", "Recaudaci\u00f3n neta \u00b7 cap. 4 ingresos", f"CAGR +{m['est_cagr']}%/a\u00f1o",
         lambda ax: (ax.plot(range(len(years)), est, color=C["warning"], lw=2.2, marker="o", ms=3), ax.fill_between(range(len(years)), est, alpha=0.15, color=C["warning"]), ax.set_xticks(range(len(years)), years, rotation=45, ha="right", fontsize=7), style_chart_ax(ax)), FIG_CHART, (0.06, 0.13, 0.88, 0.67)),
        (out["deficit"], "D\u00e9ficit solo con cotizaciones", "Gastos \u2212 cotizaciones (sin transferencias)", f"+{m['deficit_growth']}% entre 2014 y 2025",
         lambda ax: (ax.bar(range(len(years)), deficit, color=C["danger"], width=0.8), ax.set_xticks(range(len(years)), years, rotation=45, ha="right", fontsize=7), style_chart_ax(ax)), FIG_CHART, (0.06, 0.13, 0.88, 0.67)),
        (out["composicion"], "Composici\u00f3n de ingresos", "Cotizaciones + transferencias del Estado", "Eje Y: mil M\u20ac",
         lambda ax: (ax.bar(range(len(years)), cot, label="Cotizaciones sociales", color=C["info"], width=0.78), ax.bar(range(len(years)), est, bottom=cot, label="Transferencias Estado", color=C["warning"], width=0.78), ax.set_xticks(range(len(years)), years, rotation=45, ha="right", fontsize=7), ax.legend(fontsize=7), style_chart_ax(ax)), FIG_CHART, (0.06, 0.13, 0.88, 0.67)),
    ]
    for path, title, subtitle, caption, plot_fn, figsize, chart_rect in charts:
        img = panel_chart(title, subtitle, caption, plot_fn, figsize=figsize, chart_rect=chart_rect)
        img.save(path, format="PNG", optimize=True)
        print(f"  \u2192 {path.name}")


def pdf_text(s: str) -> str:
    return s.replace("\u20ac", "").replace("\u2014", "-").replace("\u2013", "-").replace("\u00b7", " - ").replace("\u2212", "-")


class InformePDF(FPDF):
    def footer(self) -> None:
        self.set_y(-12)
        self.set_font("Helvetica", "I", 8)
        self.set_text_color(161, 161, 170)
        self.cell(0, 8, pdf_text(f"Pagina {self.page_no()}/{{nb}} - Fuente: TGSS ResSISTEMA - Eje Y: mil M"), align="C")


def pdf_image_centered(pdf: FPDF, img_path: Path, content_w: float, content_h: float, x_margin: float) -> None:
    """Centra la imagen en el área de contenido, sin estirar."""
    with Image.open(img_path) as im:
        w_px, h_px = im.size
    aspect = h_px / w_px
    w = content_w
    h = w * aspect
    if h > content_h:
        h = content_h
        w = h / aspect
    x = x_margin + (content_w - w) / 2
    y = pdf.get_y()
    pdf.image(str(img_path), x=x, y=y, w=w, h=h)


def build_pdf(page_paths: list[Path], out_path: Path) -> None:
    pdf = InformePDF(orientation="P", unit="mm", format="A4")
    pdf.alias_nb_pages()
    pdf.set_auto_page_break(auto=False)
    pdf.set_margins(PDF_SIDE_MARGIN_MM, 14, PDF_SIDE_MARGIN_MM)

    for page_path in page_paths:
        pdf.add_page()
        pdf_image_centered(pdf, page_path, PDF_CONTENT_W_MM, PDF_CONTENT_H_MM, PDF_SIDE_MARGIN_MM)

    pdf.output(str(out_path))
    print(f"  \u2192 {out_path.name} ({len(page_paths)} paginas)")


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    setup_style()
    data = load_data()

    print("Generando informe en 2 paginas...")
    page1 = OUT_DIR / "informe-seguridad-social-pagina-1.png"
    page2 = OUT_DIR / "informe-seguridad-social-pagina-2.png"
    build_page_blocks(data, page1, page2)

    print("Generando graficos individuales...")
    charts = {
        "avance_2026": OUT_DIR / "01-avance-2026.png",
        "cot_vs_gastos": OUT_DIR / "02-cotizaciones-vs-gastos.png",
        "yoy": OUT_DIR / "03-crecimiento-interanual.png",
        "transferencias": OUT_DIR / "04-transferencias-estado.png",
        "deficit": OUT_DIR / "05-deficit-cotizaciones.png",
        "composicion": OUT_DIR / "06-composicion-ingresos.png",
    }
    build_individual_charts(data, charts)

    print("Generando PDF...")
    build_pdf([page1, page2], OUT_DIR / "informe-seguridad-social.pdf")
    print(f"\nListo: {OUT_DIR}")


if __name__ == "__main__":
    main()
