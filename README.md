# Power Grid Generation Scraper

Downloads the hourly generation data from the Power Grid Bangladesh PLC ERP
portal and saves it to CSV and Excel.

Source: <https://erp.powergrid.gov.bd/w/generations/view_generations>

The data is a paginated table (`?page=N`). At the time of writing there are
~1990 pages and roughly 100,000 hourly rows. Each row contains:

`Date, Time, Generation(MW), Gas, Liquid Fuel, Coal, Hydro, Solar, Wind,
India - Bheramara HVDC, India - Tripura, India - Adani, Nepal, Remarks`

## Setup

```bash
python -m pip install -r requirements.txt
```

## Usage

```bash
# Download everything (auto-detects the last page) -> CSV + Excel
python scrape.py

# Only pages 1-50
python scrape.py --start 1 --end 50

# First 10 pages, CSV only, politer delay
python scrape.py --pages 10 --no-excel --delay 1.0

# Drop duplicate (Date, Time) rows
python scrape.py --dedupe
```

### Options

| Flag | Description |
| --- | --- |
| `--start N` | First page (default `1`) |
| `--end N` | Last page (default: auto-detected) |
| `--pages N` | Fetch N pages from `--start` (overrides `--end`) |
| `--out NAME` | Output filename base (default `powergrid_generations`) |
| `--delay S` | Seconds between requests (default `0.5`) |
| `--retries N` | Max attempts per page (default `4`) |
| `--dedupe` | Drop duplicate rows by `(Date, Time)` |
| `--no-excel` | Write only CSV |

## Notes

- Rows are streamed to the CSV as each page is fetched, so an interrupted run
  (Ctrl+C) still leaves a valid partial file.
- A full run of all pages takes roughly 20-40 minutes depending on the delay
  and network. Increase `--delay` if the server rate-limits you.
- Excel has a ~1,048,576-row limit; the CSV has none.
