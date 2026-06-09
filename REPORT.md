# Bangladesh Grid Story (2021–2026)

A narrative linking PGCB hourly generation data (43,789 rows, 2021-06-04 to 2026-06-04) with energy-sector events researched for grid context enrichment.

**Annotated figures:** `analysis/daily_timeseries_annotated.png`, `analysis/daily_solar_timeseries_annotated.png`, `analysis/yearly_mix_annotated.png`

---

## Executive summary

Over five years Bangladesh's grid moved from **gas-and-diesel stress** (2022 crisis) toward a **coal-and-imports mix** (2023–2025), with **solar growing steadily** but still under 2% of mean generation. Liquid-fuel peaking surged during the 2022 shortage, then collapsed after the IMF program and coal commissioning. Cross-border imports diversified with **Adani Godda** (~1 GW) and a small **Nepal** link (~40 MW) appearing in PGCB data in late 2024.

---

## 1. Baseline (2021)

| Metric (2021) | Value |
|---------------|-------|
| Mean total generation | 9,680 MW |
| Liquid Fuel | 2,301 MW (24% of mix) |
| Coal | 521 MW (5%) |
| Solar | 26 MW (0.27% share) |
| India imports (Bheramara + Tripura) | ~823 MW |

Gas dominated (~61%); coal and solar were minor. Seasonal pattern already visible: **April peak demand** (12,245 MW mean across all years) driven by irrigation and pre-monsoon heat ([monthly_summary.csv](analysis/monthly_summary.csv)).

---

## 2. The 2022 fuel crisis

### What happened
After the Russia–Ukraine war, LNG and diesel prices spiked. Bangladesh rationed natural gas, ran **diesel peakers heavily**, and imposed **nationwide load-shedding** through much of 2022 ([Daily Star](https://www.thedailystar.net/news/bangladesh/news/nationwide-load-shedding-continue-until-oct-31-3134566)).

### What the data shows
- **Liquid Fuel** yearly mean jumped from 2,301 MW (2021) to **6,391 MW (2022)** — a 178% increase ([yearly_source_mix.csv](analysis/yearly_source_mix.csv)).
- Mean total generation rose only modestly (9,680 → 10,046 MW) because fuel shortage capped output; load was shed rather than served.
- Retail tariffs were raised sharply in August 2022 ([Reuters](https://www.reuters.com/world/asia-pacific/bangladesh-raises-power-prices-steeply-first-since-2020-2022-08-12/)).

See shaded span **"2022 fuel crisis & load-shedding"** on the annotated daily chart.

---

## 3. October 4, 2022 — national grid collapse

The grid malfunctioned around 14:00 local time, causing a **~7-hour blackout** across most of the country amid ongoing gas shortages ([Wikipedia](https://en.wikipedia.org/wiki/2022_Bangladesh_blackout)).

**Data cross-check:** Hourly totals on 4–5 October 2022 fell to a **minimum of 2,830 MW** (vs typical ~10,000+ MW). The vertical marker on `daily_timeseries_annotated.png` marks this event.

---

## 4. Forex crisis and IMF program (2023)

Dwindling reserves and unpaid fuel bills led the IMF to approve a **USD 4.7 billion** extended fund facility on 30 January 2023 ([Reuters](https://www.reuters.com/world/asia-pacific/imf-approves-47-bln-loan-bangladesh-2023-01-30/)). Fuel imports were rationed; expensive oil-fired generation was curtailed.

**Data cross-check:**
- Liquid Fuel mean **fell 73%** from 6,391 MW (2022) to **1,697 MW (2023)**.
- Coal mean **more than doubled** to 2,329 MW as Rampal/Maitree (1,320 MW) came online ([Wikipedia — Electricity sector](https://en.wikipedia.org/wiki/Electricity_sector_in_Bangladesh)).

This is the single largest **mix shift** in the dataset: coal displacing liquid fuel.

---

## 5. Cross-border imports

### India — Bheramara HVDC & Tripura
Long-standing links provided stable baseload: Bheramara ~715–858 MW mean, Tripura ~52–124 MW across 2021–2026.

### India — Adani Godda
Adani's 1,496 MW Godda plant (Jharkhand) began supplying Bangladesh in **April 2023** per news reports ([The Hindu](https://www.thehindu.com/business/Industry/adani-power-starts-supplying-electricity-to-bangladesh-from-godda-plant/article67245678.ece)).

**Data cross-check (important):**
- PGCB `India - Adani` column **first non-zero: 2024-08-28** at 1,515 MW.
- Yearly means: **840 MW (2024)**, **994 MW (2025)**, **1,020 MW (2026)**.

There is a **~16-month lag** between commissioning headlines and systematic PGCB reporting — likely initial sub-threshold flows or reporting classification change.

### Nepal via India
Bangladesh agreed to import **~40 MW** from Nepal through the Indian grid ([Dhaka Tribune](https://www.dhakatribune.com/bangladesh/power-energy/361893/bangladesh-to-import-40mw-electricity-from-nepal)).

**Data cross-check:** `Nepal` column first non-zero **2024-11-14** at **38 MW** — aligns well with the reported deal. Sustained ~38 MW from mid-2025.

---

## 6. Domestic coal capacity

| Plant | Capacity | Grid impact in data |
|-------|----------|---------------------|
| Payra | 660 MW | Operational before window |
| Rampal/Maitree | 1,320 MW | Sync late 2022; coal mean 874→2,329 MW (2022→2023) |
| Matarbari | 1,200 MW (phased) | Under construction; contributes to 2025–26 coal rise |

Coal share of mean generation rose from **5% (2021)** to **32% (2026)** while liquid fuel fell from **24%** to **7%**.

---

## 7. Tariff adjustments

BERC approved multiple retail hikes in 2022–2024 to pass through fuel costs ([Aug 2022](https://www.reuters.com/world/asia-pacific/bangladesh-raises-power-prices-steeply-first-since-2020-2022-08-12/), [Jan 2023 ~5%](https://www.reuters.com/world/asia-pacific/bangladesh-raises-electricity-prices-by-5-average-2023-01-31/)). Tariffs do not appear directly in PGCB generation data but coincide with the fuel-cost crisis period.

---

## 8. Solar and renewables

Solar grew steadily but remains a small share:

| Year | Mean solar (MW) | Max solar (MW) | Solar share % |
|------|-----------------|----------------|---------------|
| 2021 | 26 | 185 | 0.27 |
| 2022 | 50 | 316 | 0.50 |
| 2023 | 92 | 457 | 0.87 |
| 2024 | 116 | 665 | 1.04 |
| 2025 | 149 | **929** | 1.25 |
| 2026 | 162 | 770 | 1.44 |

YoY solar growth was **91% (2022)** and **84% (2023)** — fastest expansion during the crisis years when diesel was expensive. Wind first appeared 2023-05-13 but remains marginal (~10 MW mean).

Overall renewable share: **1.3% (2021) → 2.0% (2026)**. Hydro is seasonal; solar peaks at **midday hour 12** (344 MW avg).

See `analysis/solar_yearly_growth.png` and the annotated solar daily chart.

---

## 9. Political transitions (power-sector lens only)

- **January 2024 election:** Awami League returned; no abrupt generation shift in monthly data.
- **August 2024 interim government (Yunus):** Followed Hasina's resignation ([Reuters](https://www.reuters.com/world/asia-pacific/bangladeshs-interim-leader-yunus-takes-oath-2024-08-08/)). Generation remained stable ~11,000–12,000 MW daily mean; policy focus shifted to reviewing import contracts (Adani payments).

---

## 10. Seasonal demand

| Month | Mean total (MW) | Notes |
|-------|-----------------|-------|
| April | **12,245** | Peak — Boro irrigation + heat |
| December | 8,281 | Trough — mild weather |

Solar is highest in **March–April** (119–125 MW mean) but **total demand** also peaks then, so solar *share* does not peak in summer. May–June show solar dip (83 MW) while demand stays high — irrigation pumps dominate.

---

## Data–event verification summary

| Event | Reported date | Data signal | Match? |
|-------|---------------|-------------|--------|
| 2022 liquid-fuel crisis | 2022 | Liquid Fuel mean 6,391 MW | ✅ |
| Oct 2022 blackout | 2022-10-04 | Min gen 2,830 MW | ✅ |
| IMF program | 2023-01-30 | Liquid Fuel −73% in 2023 | ✅ |
| Rampal coal | 2022-11 | Coal mean 874→2,329 MW | ✅ |
| Adani Godda supply | 2023-04-06 | Column starts 2024-08-28 | ⚠️ ~16 mo lag |
| Nepal import | 2024 | First nonzero 2024-11-14, 38 MW | ✅ |
| Solar growth | ongoing | 26→162 MW mean | ✅ |

---

## Files produced

| Deliverable | Path |
|-------------|------|
| Raw research | `.firecrawl/*.md`, `.firecrawl/research_summary.json` |
| Events dataset | `analysis/grid_context_events.json` |
| Annotation script | `annotate.py` |
| Annotated charts | `analysis/*_annotated.png` |
| This report | `REPORT.md` |

---

## Sources refresh (2026-06-06)

- **11 search JSON files** scraped via Firecrawl CLI (`.firecrawl/search-*.json`); ~548 credits used.
- **New primary sources:** Reuters Oct 2022 blackout, MEA India Nov 2024 Nepal inauguration, Enerdata Mar 2022 Payra commissioning, Reuters May 2023 fuel-payment crisis.
- **6 new grid events** added to `grid_context_events.json` (Payra, Nov 2022 tariff, May 2023 dollar shortage, Adani renegotiation/restoration, Feb 2026 election).
- **7 existing events** upgraded with better `source_url` or richer descriptions (blackout, Nepal, fuel crisis, solar policy, Adani PGCB, interim govt).

## Research notes

Firecrawl CLI v1.19.0 authenticated; full topic search refresh completed 2026-06-06 via `.firecrawl/scratchpad/run_research_batched.ps1` (concurrency=2).

```bash
npm install -g firecrawl-cli
firecrawl login --browser
python analyze.py
python annotate.py
```
