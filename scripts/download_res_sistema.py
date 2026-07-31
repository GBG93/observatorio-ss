#!/usr/bin/env python3
"""Descarga históricos ResSISTEMA (sistema agregado SS) desde las páginas anuales."""

from __future__ import annotations

import argparse
import socket
import json
import re
import ssl
import time
import urllib.error
import urllib.request
from pathlib import Path

BASE = "https://www.seg-social.es"
SOURCE_PAGE = (
    "https://www.seg-social.es/wps/portal/wss/internet/"
    "InformacionEconomicoFinanciera/393/394"
)

YEAR_URLS: dict[int, str] = {
    2005: f"{BASE}/wps/portal/wss/internet/InformacionEconomicoFinanciera/393/394/401",
    2006: f"{BASE}/wps/portal/wss/internet/InformacionEconomicoFinanciera/393/394/402",
    2007: f"{BASE}/wps/portal/wss/internet/InformacionEconomicoFinanciera/393/394/403",
    2008: f"{BASE}/wps/portal/wss/internet/InformacionEconomicoFinanciera/393/394/404",
    2009: f"{BASE}/wps/portal/wss/internet/InformacionEconomicoFinanciera/393/394/1345",
    2010: f"{BASE}/wps/portal/wss/internet/InformacionEconomicoFinanciera/393/394/1788",
    2011: f"{BASE}/wps/portal/wss/internet/InformacionEconomicoFinanciera/393/394/1806",
    2012: f"{BASE}/wps/portal/wss/internet/InformacionEconomicoFinanciera/393/394/2246",
    2013: f"{BASE}/wps/portal/wss/internet/InformacionEconomicoFinanciera/393/394/2458",
    2014: f"{BASE}/wps/portal/wss/internet/InformacionEconomicoFinanciera/393/394/2694",
    2015: f"{BASE}/wps/portal/wss/internet/InformacionEconomicoFinanciera/393/394/2931",
    2016: f"{BASE}/wps/portal/wss/internet/InformacionEconomicoFinanciera/393/394/3205",
    2017: f"{BASE}/wps/portal/wss/internet/InformacionEconomicoFinanciera/393/394/3510",
    2018: f"{BASE}/wps/portal/wss/internet/InformacionEconomicoFinanciera/393/394/3778",
    2019: f"{BASE}/wps/portal/wss/internet/InformacionEconomicoFinanciera/393/394/19fc1557-ef85-47d9-b694-d1b4f089c9a2",
    2020: f"{BASE}/wps/portal/wss/internet/InformacionEconomicoFinanciera/393/394/5463ce49-c410-402b-a85f-25302ac98551",
    2021: f"{BASE}/wps/portal/wss/internet/InformacionEconomicoFinanciera/393/394/0a640a9b-6825-4de6-9d90-54c9e018e4b3",
    2022: f"{BASE}/wps/portal/wss/internet/InformacionEconomicoFinanciera/393/394/f0226d1b-4634-4122-9841-18c0fba239a4",
    2023: f"{BASE}/wps/portal/wss/internet/InformacionEconomicoFinanciera/393/394/e74cd1d7-d9e8-4e06-84e0-33699cabc829",
    2024: f"{BASE}/wps/portal/wss/internet/InformacionEconomicoFinanciera/393/394/243c53c5-b944-462d-9874-6272e32ad29d",
    2025: f"{BASE}/wps/portal/wss/internet/InformacionEconomicoFinanciera/393/394/bfe1d970-2455-4344-a550-035771dbbf49",
    2026: f"{BASE}/wps/portal/wss/internet/InformacionEconomicoFinanciera/393/394/7176e17a-7290-405f-b877-8d71a8d4d018",
}

DEFAULT_OUT = Path(__file__).resolve().parents[1] / "data" / "raw" / "res_sistema"
DEFAULT_PDF_OUT = Path(__file__).resolve().parents[1] / "data" / "raw" / "res_sistema_pdf"

SISTEMA_MARKERS = (
    "SISTEMA DE LA S.S",
    "SISTEMA DE LA SEGURIDAD",
    "SISTEMA DE LA SS",
)
EXCLUDE_MARKERS = ("MUTUAS", "EE.GG", "E.G.", "EG Y", "AGREGADO")

MONTH_ALIASES = {
    "diciembre (cierre definitivo)": "DiciembreDefinitivo",
    "diciembre (cierre provisional)": "DiciembreProvisional",
    "diciembre provisional": "DiciembreProvisional",
    "diciembre definitivo": "DiciembreDefinitivo",
    "january": "Enero",
    "february": "Febrero",
    "march": "Marzo",
    "april": "Abril",
    "may": "Mayo",
    "june": "Junio",
    "july": "Julio",
    "august": "Agosto",
    "september": "Septiembre",
    "october": "Octubre",
    "november": "Noviembre",
    "december": "Diciembre",
}


def fetch(url: str, ctx: ssl.SSLContext) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, context=ctx, timeout=30) as response:
        return response.read().decode("utf-8", errors="replace")


def normalize_month(title: str) -> str:
    t = title.strip()
    key = t.lower()
    if key in MONTH_ALIASES:
        return MONTH_ALIASES[key]
    if t.lower().startswith("diciembre"):
        if "definitivo" in t.lower():
            return "DiciembreDefinitivo"
        if "provisional" in t.lower():
            return "DiciembreProvisional"
        return "Diciembre"
    return t.split()[0]


def is_sistema_row(text: str) -> bool:
    upper = text.upper()
    if any(marker in upper for marker in EXCLUDE_MARKERS):
        return False
    if any(marker in upper for marker in SISTEMA_MARKERS):
        return True
    return bool(re.search(r"\bSISTEMA\b", upper))


def extract_table_downloads(html: str, fmt: str) -> list[tuple[str, str]]:
    """Extrae descargas SISTEMA por formato (XLSX o PDF) desde filas de tabla."""
    found: list[tuple[str, str]] = []
    for row in re.split(r"<tr[^>]*>", html, flags=re.I):
        if "/descarga/es/" not in row:
            continue
        text = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", row))
        if fmt.upper() not in text.upper() or not is_sistema_row(text):
            continue
        ids = re.findall(r"/descarga/es/(\d+)", row)
        if ids:
            file_id = ids[0]
            found.append((file_id, f"{BASE}/descarga/es/{file_id}"))
    return found


def extract_named_ressistema(html: str, ext: str) -> list[tuple[str, str]]:
    found: list[tuple[str, str]] = []
    for path, fname in re.findall(rf'href="(/descarga/es/([^"]+\.{ext}))"', html, re.I):
        fname = fname.strip()
        if "RESSISTEMA" in fname.upper():
            found.append((fname, f"{BASE}{path}"))
    return found


def extract_numeric_ressistema(html: str) -> list[tuple[str, str]]:
    return extract_table_downloads(html, "XLSX")


def extract_numeric_ressistema_pdf(html: str) -> list[tuple[str, str]]:
    return extract_table_downloads(html, "PDF")


def discover_year(year: int, year_url: str, ctx: ssl.SSLContext, delay: float) -> list[dict]:
    html = fetch(year_url, ctx)
    subpages = sorted(
        {
            sp
            for sp in re.findall(
                r'href="(/wps/portal/wss/internet/InformacionEconomicoFinanciera/393/394/[^"?]+)"',
                html,
            )
            if "!ut/p/" not in sp
        }
    )

    entries: list[dict] = []
    seen_urls: set[str] = set()

    for subpage in subpages:
        full = BASE + subpage
        if full.rstrip("/") == year_url.rstrip("/"):
            continue
        try:
            month_html = fetch(full, ctx)
        except urllib.error.HTTPError:
            continue

        title_match = re.search(r"<h1[^>]*>\s*([^<]+?)\s*</h1>", month_html)
        if not title_match:
            continue
        month = normalize_month(title_match.group(1))
        if month.lower().startswith("ejercicio"):
            continue

        candidates = extract_named_ressistema(month_html, "xlsx") or [
            (file_id, url) for file_id, url in extract_numeric_ressistema(month_html)
        ]
        file_format = "xlsx"

        if not candidates:
            candidates = extract_named_ressistema(month_html, "pdf") or [
                (file_id, url) for file_id, url in extract_numeric_ressistema_pdf(month_html)
            ]
            file_format = "pdf"

        # Página creada sin tabla de descargas: probar URL directa ResSISTEMA_{Mes}_{año}.xlsx
        if not candidates and month not in ("", "Ejercicio"):
            dest_name = f"ResSISTEMA_{month}_{year}.xlsx"
            candidates = [(dest_name, f"{BASE}/descarga/es/{dest_name}")]
            file_format = "xlsx"

        for source_id, url in candidates:
            if url in seen_urls:
                continue
            seen_urls.add(url)
            if source_id.lower().endswith(f".{file_format}"):
                dest_name = source_id.strip()
                if not dest_name.lower().startswith("ressistema"):
                    dest_name = f"ResSISTEMA_{dest_name}"
            else:
                dest_name = f"ResSISTEMA_{month}_{year}.{file_format}"
            dest_name = dest_name.replace(" ", "")
            entries.append(
                {
                    "year": year,
                    "month": month,
                    "format": file_format,
                    "dest_name": dest_name,
                    "source_id": source_id,
                    "url": url,
                }
            )
        time.sleep(delay)

    return entries


def download_entry(entry: dict, out_dir: Path, pdf_dir: Path, ctx: ssl.SSLContext) -> dict:
    target_dir = pdf_dir if entry.get("format") == "pdf" else out_dir
    target_dir.mkdir(parents=True, exist_ok=True)
    dest = target_dir / entry["dest_name"]
    if dest.exists() and dest.stat().st_size > 1000:
        return {**entry, "status": "skipped", "bytes": dest.stat().st_size, "path": str(dest)}

    url = entry["url"].replace(" ", "%20")
    min_size = 1000 if entry.get("format") == "pdf" else 5000
    last_error = ""

    for attempt in range(3):
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        try:
            with urllib.request.urlopen(req, context=ctx, timeout=90) as response:
                data = response.read()
        except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError, socket.timeout) as exc:
            last_error = str(exc)
            time.sleep(1 + attempt)
            continue

        valid = data[:4] == b"%PDF" if entry.get("format") == "pdf" else data[:2] == b"PK"
        if len(data) < min_size or not valid:
            return {**entry, "status": "invalid", "bytes": len(data)}

        dest.write_bytes(data)
        return {**entry, "status": "ok", "bytes": len(data), "path": str(dest)}

    return {**entry, "status": "fail", "error": last_error}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--from-year", type=int, default=2005)
    parser.add_argument("--to-year", type=int, default=2026)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--pdf-out", type=Path, default=DEFAULT_PDF_OUT)
    parser.add_argument("--delay", type=float, default=0.1)
    args = parser.parse_args()

    args.out.mkdir(parents=True, exist_ok=True)
    args.pdf_out.mkdir(parents=True, exist_ok=True)
    ctx = ssl.create_default_context()

    catalog: list[dict] = []
    results: list[dict] = []

    for year in range(args.from_year, args.to_year + 1):
        year_url = YEAR_URLS.get(year)
        if not year_url:
            print(f"! Año sin URL configurada: {year}")
            continue
        entries = discover_year(year, year_url, ctx, args.delay)
        catalog.extend(entries)
        xlsx_n = sum(1 for e in entries if e.get("format") == "xlsx")
        pdf_n = sum(1 for e in entries if e.get("format") == "pdf")
        print(f"{year}: {xlsx_n} xlsx + {pdf_n} pdf")
        time.sleep(args.delay)

    for entry in catalog:
        result = download_entry(entry, args.out, args.pdf_out, ctx)
        results.append(result)
        if result["status"] == "ok":
            print(f"  ✓ {result['dest_name']}")
        elif result["status"] == "fail":
            print(f"  ✗ {result['dest_name']}: {result.get('error', '')[:80]}")
        time.sleep(args.delay)

    stats: dict[str, int] = {}
    for result in results:
        stats[result["status"]] = stats.get(result["status"], 0) + 1

    manifest = {
        "source": SOURCE_PAGE,
        "year_urls": {str(y): u for y, u in YEAR_URLS.items() if args.from_year <= y <= args.to_year},
        "downloaded_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "stats": stats,
        "catalog_count": len(catalog),
        "xlsx_on_disk": len(list(args.out.glob("ResSISTEMA*.xlsx"))),
        "pdf_on_disk": len(list(args.pdf_out.glob("ResSISTEMA*.pdf"))),
        "catalog": catalog,
        "results": results,
        "notes": [
            "2005-2013: solo PDF en seg-social.es",
            "2015+: XLSX disponible (preferido para análisis)",
            "Datos acumulados YTD hasta fin de mes",
        ],
    }
    manifest_path = args.out / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")

    print(
        f"\nCatálogo: {len(catalog)} | XLSX: {manifest['xlsx_on_disk']} | "
        f"PDF: {manifest['pdf_on_disk']} | Stats: {stats}"
    )
    print(f"Manifest: {manifest_path}")


if __name__ == "__main__":
    main()
