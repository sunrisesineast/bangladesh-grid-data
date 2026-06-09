"""
Scrape hourly generation data from the Power Grid Bangladesh ERP and save it
to CSV (and optionally Excel).

Source: https://erp.powergrid.gov.bd/w/generations/view_generations

The table is server-rendered and paginated via a `?page=N` query parameter.
Rows are written to CSV incrementally as each page is fetched, so a long run
will not lose data and memory stays low. An Excel copy is produced at the end.

Examples
--------
# Download everything (auto-detects the last page), CSV + Excel:
python scrape.py

# Download only pages 1-50:
python scrape.py --start 1 --end 50

# Download the first 10 pages, CSV only, slower/politer:
python scrape.py --pages 10 --no-excel --delay 1.0
"""

from __future__ import annotations

import argparse
import csv
import re
import sys
import time
from pathlib import Path

import requests
from bs4 import BeautifulSoup

BASE_URL = "https://erp.powergrid.gov.bd/w/generations/view_generations"

# The HTML header spans two rows: "India" is a colspan covering three
# sub-columns (Bheramara HVDC, Tripura, Adani). These are the flattened
# columns in the exact order the <td> cells appear in each table row.
COLUMNS = [
    "Date",
    "Time",
    "Generation(MW)",
    "Gas",
    "Liquid Fuel",
    "Coal",
    "Hydro",
    "Solar",
    "Wind",
    "India - Bheramara HVDC",
    "India - Tripura",
    "India - Adani",
    "Nepal",
    "Remarks",
]

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
}


def enable_os_trust_store() -> bool:
    """Use the operating system's certificate store for TLS verification.

    The ERP server presents an incomplete certificate chain that Python's
    bundled CA bundle (certifi) cannot verify, even though browsers and curl
    can. truststore delegates verification to the OS (Windows SChannel /
    macOS Security framework), which resolves the missing intermediates.
    """
    try:
        import truststore
        truststore.inject_into_ssl()
        return True
    except Exception:
        return False


def make_session(insecure: bool) -> requests.Session:
    session = requests.Session()
    session.headers.update(HEADERS)
    if insecure:
        session.verify = False
        import urllib3
        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
    return session


def fetch(session: requests.Session, page: int, retries: int, delay: float) -> str:
    """Fetch a single page's HTML, retrying with backoff on failure."""
    url = BASE_URL if page == 1 else f"{BASE_URL}?page={page}"
    last_err: Exception | None = None
    for attempt in range(1, retries + 1):
        try:
            resp = session.get(url, timeout=30)
            if resp.status_code == 200:
                return resp.text
            last_err = RuntimeError(f"HTTP {resp.status_code}")
        except requests.RequestException as exc:  # network/timeout errors
            last_err = exc
        wait = delay * (2 ** (attempt - 1))
        print(f"  ! page {page} attempt {attempt}/{retries} failed "
              f"({last_err}); retrying in {wait:.1f}s", file=sys.stderr)
        time.sleep(wait)
    raise RuntimeError(f"Failed to fetch page {page}: {last_err}")


def detect_last_page(html: str) -> int:
    """Find the highest `?page=N` value referenced by the pagination links."""
    pages = [int(n) for n in re.findall(r"[?&]page=(\d+)", html)]
    return max(pages) if pages else 1


def parse_rows(html: str, page: int) -> list[list[str]]:
    """Extract data rows from a page. Returns a list of cell lists."""
    soup = BeautifulSoup(html, "lxml")
    table = soup.find("table")
    if table is None:
        return []
    body = table.find("tbody") or table
    rows: list[list[str]] = []
    for tr in body.find_all("tr"):
        cells = [td.get_text(strip=True) for td in tr.find_all("td")]
        if not cells:
            continue  # header / separator row
        if len(cells) != len(COLUMNS):
            print(f"  ! page {page}: row has {len(cells)} cells, "
                  f"expected {len(COLUMNS)} -> {cells}", file=sys.stderr)
            # Pad or trim so the CSV stays aligned.
            cells = (cells + [""] * len(COLUMNS))[: len(COLUMNS)]
        rows.append(cells)
    return rows


def scrape(args: argparse.Namespace) -> None:
    if not args.insecure and not enable_os_trust_store():
        print("  ! truststore unavailable; if you hit SSL certificate errors, "
              "install it (pip install truststore) or rerun with --insecure.",
              file=sys.stderr)
    session = make_session(args.insecure)

    print(f"Fetching page 1 from {BASE_URL} ...")
    first_html = fetch(session, 1, args.retries, args.delay)

    start = args.start
    if args.pages is not None:
        end = start + args.pages - 1
    elif args.end is not None:
        end = args.end
    else:
        end = detect_last_page(first_html)
        print(f"Auto-detected last page: {end}")

    if end < start:
        print(f"Nothing to do: end page ({end}) < start page ({start}).")
        return

    csv_path = Path(f"{args.out}.csv")
    seen: set[tuple[str, str]] = set()
    total_rows = 0

    with csv_path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.writer(fh)
        writer.writerow(COLUMNS)

        for page in range(start, end + 1):
            html = first_html if page == 1 else fetch(
                session, page, args.retries, args.delay)
            rows = parse_rows(html, page)

            if not rows and page != start:
                print(f"Page {page}: no rows found; stopping.")
                break

            written = 0
            for row in rows:
                if args.dedupe:
                    key = (row[0], row[1])  # (Date, Time)
                    if key in seen:
                        continue
                    seen.add(key)
                writer.writerow(row)
                written += 1

            total_rows += written
            fh.flush()
            print(f"Page {page}/{end}: +{written} rows "
                  f"(total {total_rows})")

            if page != end:
                time.sleep(args.delay)

    print(f"\nSaved {total_rows} rows to {csv_path.resolve()}")

    if not args.no_excel:
        write_excel(csv_path, Path(f"{args.out}.xlsx"))


def write_excel(csv_path: Path, xlsx_path: Path) -> None:
    try:
        import pandas as pd
    except ImportError:
        print("pandas not installed; skipping Excel export.", file=sys.stderr)
        return
    print(f"Writing Excel file {xlsx_path} ...")
    df = pd.read_csv(csv_path, dtype=str, keep_default_na=False)
    if len(df) > 1_048_575:
        print("  ! More than ~1.05M rows; Excel cannot hold them all. "
              "Use the CSV instead.", file=sys.stderr)
        return
    df.to_excel(xlsx_path, index=False)
    print(f"Saved {xlsx_path.resolve()}")


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--start", type=int, default=1, help="First page (default 1)")
    p.add_argument("--end", type=int, default=None,
                   help="Last page (default: auto-detect highest page)")
    p.add_argument("--pages", type=int, default=None,
                   help="Number of pages to fetch from --start (overrides --end)")
    p.add_argument("--out", default="powergrid_generations",
                   help="Output filename base (default: powergrid_generations)")
    p.add_argument("--delay", type=float, default=0.5,
                   help="Seconds to wait between page requests (default 0.5)")
    p.add_argument("--retries", type=int, default=4,
                   help="Max attempts per page (default 4)")
    p.add_argument("--dedupe", action="store_true",
                   help="Drop duplicate rows by (Date, Time)")
    p.add_argument("--no-excel", action="store_true",
                   help="Write only CSV, skip the Excel export")
    p.add_argument("--insecure", action="store_true",
                   help="Disable TLS certificate verification (last resort)")
    return p


def main() -> None:
    args = build_parser().parse_args()
    try:
        scrape(args)
    except KeyboardInterrupt:
        print("\nInterrupted. Partial CSV has been saved.", file=sys.stderr)
        sys.exit(130)


if __name__ == "__main__":
    main()
