#!/usr/bin/env python3
"""Descarga XLSX mensuales de altas/bajas de pensiones contributivas (EST23/2575)."""

from __future__ import annotations

import argparse
import json
import re
import ssl
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

BASE = "https://www.seg-social.es"
INDEX_URL = (
    f"{BASE}/wps/portal/wss/internet/"
    "EstadisticasPresupuestosEstudios/Estadisticas/EST23/2575"
)
DEFAULT_OUT = Path(__file__).resolve().parents[1] / "data" / "raw" / "altas_bajas"

# Año → path relativo descubierto en el índice (se redescubre en runtime; estos son fallback)
YEAR_PATH_HINTS: dict[int, str] = {
    2016: "/wps/portal/wss/internet/EstadisticasPresupuestosEstudios/Estadisticas/EST23/2575/3276",
    2017: "/wps/portal/wss/internet/EstadisticasPresupuestosEstudios/Estadisticas/EST23/2575/3585",
    2018: "/wps/portal/wss/internet/EstadisticasPresupuestosEstudios/Estadisticas/EST23/2575/3736",
    2019: "/wps/portal/wss/internet/EstadisticasPresupuestosEstudios/Estadisticas/EST23/2575/5bf7bb50-e3f6-4df2-9892-13745f58edce",
    2020: "/wps/portal/wss/internet/EstadisticasPresupuestosEstudios/Estadisticas/EST23/2575/e62220de-0bb3-40f0-9c3e-207dbef1121e",
    2021: "/wps/portal/wss/internet/EstadisticasPresupuestosEstudios/Estadisticas/EST23/2575/d5ebe7ce-2ded-4acb-8051-9f5a6735e0a7",
    2022: "/wps/portal/wss/internet/EstadisticasPresupuestosEstudios/Estadisticas/EST23/2575/e1950fb1-119d-4afe-96d0-40d944806750",
    2023: "/wps/portal/wss/internet/EstadisticasPresupuestosEstudios/Estadisticas/EST23/2575/c0e31961-9a30-4579-9ff7-f522986d9b3e",
    2024: "/wps/portal/wss/internet/EstadisticasPresupuestosEstudios/Estadisticas/EST23/2575/da3a5213-f22e-4dc2-8dd6-a0dbd5b98bec",
    2025: "/wps/portal/wss/internet/EstadisticasPresupuestosEstudios/Estadisticas/EST23/2575/2d28d73d-5050-47bc-b524-c85c049734a9",
    2026: "/wps/portal/wss/internet/EstadisticasPresupuestosEstudios/Estadisticas/EST23/2575/141d9525-1970-48fa-9b72-112709e1008e",
}


def fetch(url: str, ctx: ssl.SSLContext) -> str:
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": "Mozilla/5.0",
            "Accept-Language": "es-ES,es;q=0.9",
        },
    )
    with urllib.request.urlopen(req, context=ctx, timeout=45) as response:
        return response.read().decode("utf-8", errors="replace")


def fetch_bytes(url: str, ctx: ssl.SSLContext) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, context=ctx, timeout=90) as response:
        return response.read()


def abs_url(href: str) -> str:
    href = href.replace("&amp;", "&")
    if href.startswith("http"):
        return href
    return BASE + href


def discover_year_paths(html: str) -> dict[int, str]:
    found: dict[int, str] = {}
    for href, text in re.findall(r'href="([^"]+)"[^>]*>\s*([^<]{0,80})\s*<', html, re.I):
        m = re.search(r"Año\s+(\d{4})", text, re.I)
        if not m:
            continue
        year = int(m.group(1))
        if "EST23/2575" in href and "!ut/p/" not in href:
            found[year] = href.split("?")[0]
    return found


def find_child_link(html: str, *needles: str, exclude: tuple[str, ...] = ()) -> str | None:
    for href, text in re.findall(r'href="([^"]+)"[^>]*>\s*(.*?)\s*</a>', html, re.I | re.S):
        plain = re.sub(r"<[^>]+>", " ", text)
        plain = re.sub(r"\s+", " ", plain).strip().lower()
        if any(ex in plain for ex in exclude):
            continue
        if all(n.lower() in plain for n in needles):
            if "EST23/2575" in href and "!ut/p/" not in href:
                return href.split("?")[0]
    return None


def find_report_page(year_html: str) -> str | None:
    """Página con listado mensual de altas iniciales y bajas definitivas."""
    # Modern: "Altas y bajas de pensiones contributivas" → then deeper report page
    link = find_child_link(year_html, "altas y bajas de pensiones contributivas")
    return link


def find_monthly_list_page(altas_html: str) -> str | None:
    """Dentro de altas/bajas, la página de informes combinados (no CCAA/sexo solos)."""
    # Prefer exact combined title without CCAA/sexo
    for href, text in re.findall(r'href="([^"]+)"[^>]*>\s*(.*?)\s*</a>', altas_html, re.I | re.S):
        plain = re.sub(r"<[^>]+>", " ", text)
        plain = re.sub(r"\s+", " ", plain).strip().lower()
        if "ccaa" in plain or "sexo" in plain or "edades" in plain:
            continue
        if plain == "altas iniciales y bajas definitivas de pensiones" or (
            "altas iniciales y bajas definitivas de pensiones" in plain
            and "clase" not in plain
            and "sexo" not in plain
        ):
            if "EST23/2575" in href and "!ut/p/" not in href:
                return href.split("?")[0]
    # Legacy: separate altas / bajas pages
    return None


def find_legacy_pages(altas_html: str) -> dict[str, str]:
    out: dict[str, str] = {}
    mapping = {
        "altas": ("altas iniciales de pensiones por clase y ccaa",),
        "bajas": ("bajas definitivas de pensiones por clase y ccaa",),
    }
    for key, needles in mapping.items():
        link = find_child_link(altas_html, *needles)
        if link:
            out[key] = link
    return out


def extract_xlsx_entries(html: str, year: int) -> list[dict]:
    """Extrae descargas .xlsx con nombre AB* del HTML de informes."""
    entries: list[dict] = []
    seen: set[str] = set()
    for href in re.findall(r'href="([^"]+\.xlsx[^"]*)"', html, re.I):
        href_clean = href.replace("&amp;", "&")
        fname_m = re.search(r"(AB[\w\-]*\d{6}\.xlsx|AB\d+\.xlsx)", href_clean, re.I)
        if not fname_m:
            # try AB2/AB3 legacy: AB2201605.xlsx
            fname_m = re.search(r"(AB[238]?\d{5,8}\.xlsx)", href_clean, re.I)
        if not fname_m:
            continue
        fname = fname_m.group(1)
        if fname.lower() in seen:
            continue
        seen.add(fname.lower())

        year_m, month = parse_ab_filename(fname, year)
        fmt = classify_format(fname)
        entries.append(
            {
                "year": year_m or year,
                "month": month,
                "format": fmt,
                "dest_name": fname if fname.upper().startswith("AB") else f"AB_{fname}",
                "url": abs_url(href_clean),
                "source_file": fname,
            }
        )
    return entries


def parse_ab_filename(fname: str, fallback_year: int) -> tuple[int | None, int | None]:
    """Parse ABYYYYMM.xlsx or AB2YYYYMM / AB3YYYYMM / AB8YYYYMM."""
    stem = fname.replace(".xlsx", "").replace(".XLSX", "")
    # Modern AB202601
    m = re.fullmatch(r"AB(\d{4})(\d{2})", stem, re.I)
    if m:
        return int(m.group(1)), int(m.group(2))
    # Legacy AB2201605 = AB2 + 2016 + 05
    m = re.fullmatch(r"AB([238])(\d{4})(\d{2})", stem, re.I)
    if m:
        return int(m.group(2)), int(m.group(3))
    # Fallback AB + digits
    m = re.search(r"(\d{4})(\d{2})$", stem)
    if m:
        return int(m.group(1)), int(m.group(2))
    return fallback_year, None


def classify_format(fname: str) -> str:
    stem = fname.upper().replace(".XLSX", "")
    if re.fullmatch(r"AB\d{6}", stem):
        return "modern"
    if re.fullmatch(r"AB1\d{6}", stem):
        return "ab1"
    if stem.startswith("AB2"):
        return "legacy_altas"
    if stem.startswith("AB3"):
        return "legacy_bajas"
    if stem.startswith("AB8"):
        return "legacy_sexo"
    return "unknown"


def download_file(entry: dict, out_dir: Path, ctx: ssl.SSLContext) -> dict:
    out_dir.mkdir(parents=True, exist_ok=True)
    dest = out_dir / entry["dest_name"]
    if dest.exists() and dest.stat().st_size > 1000:
        return {**entry, "status": "skipped", "bytes": dest.stat().st_size, "path": str(dest)}

    last_error = ""
    for attempt in range(3):
        try:
            data = fetch_bytes(entry["url"], ctx)
        except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError) as exc:
            last_error = str(exc)
            time.sleep(1 + attempt)
            continue
        if len(data) < 1000 or data[:2] != b"PK":
            return {**entry, "status": "invalid", "bytes": len(data)}
        dest.write_bytes(data)
        return {**entry, "status": "ok", "bytes": len(data), "path": str(dest)}
    return {**entry, "status": "fail", "error": last_error}


def crawl_year(year: int, year_path: str, ctx: ssl.SSLContext, delay: float) -> list[dict]:
    year_html = fetch(abs_url(year_path), ctx)
    time.sleep(delay)
    altas_path = find_report_page(year_html)
    if not altas_path:
        print(f"  {year}: no link 'Altas y bajas…'")
        return []

    altas_html = fetch(abs_url(altas_path), ctx)
    time.sleep(delay)

    entries: list[dict] = []
    monthly = find_monthly_list_page(altas_html)
    if monthly:
        # May need one more hop (modern site nests report list)
        list_html = fetch(abs_url(monthly), ctx)
        time.sleep(delay)
        # If still no xlsx, follow deeper unique child under monthly
        found = extract_xlsx_entries(list_html, year)
        if not found:
            deeper = None
            for href in re.findall(r'href="([^"]+)"', list_html):
                if monthly.rstrip("/") in href and href.rstrip("/") != monthly.rstrip("/") and "!ut/p/" not in href:
                    if href.count("/") > monthly.count("/"):
                        deeper = href.split("?")[0]
                        break
            if deeper:
                list_html = fetch(abs_url(deeper), ctx)
                time.sleep(delay)
                found = extract_xlsx_entries(list_html, year)
        entries.extend(found)
    else:
        legacy = find_legacy_pages(altas_html)
        for kind, path in legacy.items():
            page_html = fetch(abs_url(path), ctx)
            time.sleep(delay)
            for e in extract_xlsx_entries(page_html, year):
                e["legacy_kind"] = kind
                entries.append(e)

    # Dedup by dest_name
    by_name: dict[str, dict] = {}
    for e in entries:
        by_name[e["dest_name"].lower()] = e
    return list(by_name.values())


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--from-year", type=int, default=2016)
    parser.add_argument("--to-year", type=int, default=datetime.now().year)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--delay", type=float, default=0.35)
    args = parser.parse_args()

    ctx = ssl.create_default_context()
    index_html = fetch(INDEX_URL, ctx)
    year_paths = {**YEAR_PATH_HINTS, **discover_year_paths(index_html)}

    catalog: list[dict] = []
    results: list[dict] = []
    stats = {"ok": 0, "skipped": 0, "fail": 0, "invalid": 0}

    for year in range(args.from_year, args.to_year + 1):
        path = year_paths.get(year)
        if not path:
            print(f"{year}: sin URL en índice")
            continue
        print(f"{year}: explorando…")
        try:
            entries = crawl_year(year, path, ctx, args.delay)
        except Exception as exc:
            print(f"  {year}: error {exc}")
            continue
        print(f"  {year}: {len(entries)} xlsx")
        catalog.extend(entries)
        for entry in entries:
            if entry.get("month") is None:
                continue
            res = download_file(entry, args.out, ctx)
            results.append(res)
            stats[res["status"]] = stats.get(res["status"], 0) + 1
            time.sleep(args.delay)

    manifest = {
        "source": INDEX_URL,
        "downloaded_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "from_year": args.from_year,
        "to_year": args.to_year,
        "stats": stats,
        "catalog_count": len(catalog),
        "xlsx_on_disk": len(list(args.out.glob("*.xlsx"))) if args.out.exists() else 0,
        "catalog": catalog,
        "results": results,
    }
    args.out.mkdir(parents=True, exist_ok=True)
    (args.out / "manifest.json").write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    print(f"Stats: {stats}")
    print(f"Manifest: {args.out / 'manifest.json'}")


if __name__ == "__main__":
    main()
