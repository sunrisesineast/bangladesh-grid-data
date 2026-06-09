"""
Exploratory data analysis of Power Grid Bangladesh (PGCB) hourly generation data.

Focus: last 5 years of generation, with daily / monthly / hourly / yearly trends
and a deep dive on renewable energy, especially SOLAR.

Outputs:
    analysis/*.png   -> figures
    analysis/*.csv   -> summary tables
Prints summary tables to stdout.

Usage:
    python analyze.py
"""

from __future__ import annotations

import os
import sys
from datetime import datetime

import pandas as pd

import matplotlib
matplotlib.use("Agg")  # headless / non-interactive backend
import matplotlib.pyplot as plt  # noqa: E402

# --------------------------------------------------------------------------- #
# Config
# --------------------------------------------------------------------------- #
CSV_PATH = "powergrid_generations.csv"
OUT_DIR = "analysis"
DPI = 130

# "Today" per the task spec.
TODAY = pd.Timestamp("2026-06-04")
YEARS_BACK = 5
CUTOFF = TODAY - pd.DateOffset(years=YEARS_BACK)  # 2021-06-04

SOURCE_COLS = [
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
]
IMPORT_COLS = ["India - Bheramara HVDC", "India - Tripura", "India - Adani", "Nepal"]
RENEWABLE_COLS = ["Solar", "Wind", "Hydro"]
TOTAL_COL = "Generation(MW)"

plt.rcParams.update({
    "figure.autolayout": True,
    "axes.grid": True,
    "grid.alpha": 0.3,
    "axes.titleweight": "bold",
})


def banner(title: str) -> None:
    line = "=" * 78
    print(f"\n{line}\n{title}\n{line}")


def save_fig(fig, name: str) -> str:
    path = os.path.join(OUT_DIR, name)
    fig.savefig(path, dpi=DPI, bbox_inches="tight")
    plt.close(fig)
    print(f"  [figure] {path}")
    return path


def save_table(df: pd.DataFrame, name: str) -> str:
    path = os.path.join(OUT_DIR, name)
    df.to_csv(path)
    print(f"  [table]  {path}")
    return path


# --------------------------------------------------------------------------- #
# Load + clean
# --------------------------------------------------------------------------- #
def load_clean() -> pd.DataFrame:
    banner("LOADING & CLEANING")
    df = pd.read_csv(CSV_PATH, dtype=str)  # read as strings, coerce ourselves
    print(f"Raw rows: {len(df):,}")

    # Strip whitespace on all string cells and column names.
    df.columns = [c.strip() for c in df.columns]
    for c in df.columns:
        df[c] = df[c].astype(str).str.strip()
        # Normalise empty-ish tokens to NA
        df[c] = df[c].replace({"": pd.NA, "nan": pd.NA, "NaN": pd.NA, "None": pd.NA})

    # Build datetime (dayfirst). Time may occasionally be 30-min cadence.
    dt = pd.to_datetime(
        df["Date"].astype(str) + " " + df["Time"].astype(str),
        format="%d-%m-%Y %H:%M:%S",
        errors="coerce",
        dayfirst=True,
    )
    df["datetime"] = dt
    bad = df["datetime"].isna().sum()
    if bad:
        print(f"Dropping {bad:,} rows with unparseable datetime")
    df = df.dropna(subset=["datetime"])

    # Coerce numeric columns.
    numeric_cols = [TOTAL_COL] + SOURCE_COLS
    for c in numeric_cols:
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors="coerce")

    # --- Physical-plausibility sanity cleaning -------------------------------
    # The raw export contains a handful of data-entry errors that wreck every
    # aggregate if left in. We remove only physically-impossible values.

    # (a) Garbage dates: a few rows parsed to years like 0008, 0021, 0050 ...
    yr_all = df["datetime"].dt.year
    bad_year = (yr_all < 2014) | (yr_all > 2026)
    if bad_year.any():
        print(f"Dropping {int(bad_year.sum()):,} rows with implausible year "
              f"(values: {sorted(yr_all[bad_year].unique().tolist())})")
        df = df[~bad_year]

    # (b) Impossible total generation. Bangladesh peak demand is ~17 GW; any
    #     value far above that (e.g. the 64,526,500 MW row) is a typo.
    TOTAL_CAP = 25_000
    bad_total = (df[TOTAL_COL] <= 0) | (df[TOTAL_COL] > TOTAL_CAP)
    if bad_total.any():
        print(f"Dropping {int(bad_total.sum()):,} rows with implausible total "
              f"(<=0 or > {TOTAL_CAP:,} MW)")
        df = df[~bad_total]

    # (c) Negative source readings -> NaN.
    for c in numeric_cols:
        neg = df[c] < 0
        if neg.any():
            df.loc[neg, c] = pd.NA

    # (d) Physically-impossible solar spikes. BD utility solar capacity only
    #     reached ~1 GW by 2024-25, so any single reading > 1,500 MW (e.g. the
    #     isolated 2398/2901/2998 MW spikes amid single-digit neighbours) is an
    #     error. Legitimate midday peaks in this dataset top out near ~770 MW.
    SOLAR_CAP = 1_500
    bad_solar = df["Solar"] > SOLAR_CAP
    if bad_solar.any():
        print(f"Nulling {int(bad_solar.sum()):,} implausible solar readings "
              f"(> {SOLAR_CAP:,} MW)")
        df.loc[bad_solar, "Solar"] = pd.NA
    # -------------------------------------------------------------------------

    # Dedupe on (Date, Time) -> keep last (most complete tends to be later scrape).
    before = len(df)
    df = df.sort_values("datetime").drop_duplicates(subset=["datetime"], keep="last")
    print(f"Removed {before - len(df):,} duplicate (Date,Time) rows")

    df = df.sort_values("datetime").reset_index(drop=True)

    # Helper time fields.
    df["year"] = df["datetime"].dt.year
    df["month"] = df["datetime"].dt.month
    df["hour"] = df["datetime"].dt.hour
    df["date"] = df["datetime"].dt.normalize()
    df["dow"] = df["datetime"].dt.dayofweek  # 0=Mon

    # Renewable total + import total (treat NaN as 0 for additive aggregates).
    df["Renewable"] = df[RENEWABLE_COLS].sum(axis=1, min_count=1)
    df["Imports"] = df[IMPORT_COLS].sum(axis=1, min_count=1)

    print(f"Full clean range: {df['datetime'].min()}  ->  {df['datetime'].max()}")
    print(f"Clean rows: {len(df):,}")
    return df


# --------------------------------------------------------------------------- #
# Renewable / solar first-appearance detection (over FULL history)
# --------------------------------------------------------------------------- #
def first_appearance(df_full: pd.DataFrame) -> None:
    banner("RENEWABLE FIRST-APPEARANCE (full history)")
    for col in ["Solar", "Wind"]:
        nonzero = df_full[(df_full[col].notna()) & (df_full[col] > 0)]
        first_nonempty = df_full[df_full[col].notna()]
        if len(nonzero):
            r = nonzero.iloc[0]
            print(f"{col}: first NON-ZERO output on {r['datetime']}  ({r[col]:.0f} MW)")
        if len(first_nonempty):
            r = first_nonempty.iloc[0]
            print(f"{col}: first NON-EMPTY value on {r['datetime']}  ({r[col]:.0f} MW)")


# --------------------------------------------------------------------------- #
# Yearly
# --------------------------------------------------------------------------- #
def yearly(df: pd.DataFrame) -> pd.DataFrame:
    banner("YEARLY TRENDS")
    g = df.groupby("year")
    yr = pd.DataFrame({
        "mean_total_MW": g[TOTAL_COL].mean(),
        "peak_total_MW": g[TOTAL_COL].max(),
        "mean_solar_MW": g["Solar"].mean(),
        "max_solar_MW": g["Solar"].max(),
        "mean_wind_MW": g["Wind"].mean(),
        "mean_hydro_MW": g["Hydro"].mean(),
        "mean_renewable_MW": g["Renewable"].mean(),
    })
    # Renewable share % uses mean MW ratio.
    yr["renewable_share_%"] = 100 * yr["mean_renewable_MW"] / yr["mean_total_MW"]
    yr["solar_share_%"] = 100 * yr["mean_solar_MW"] / yr["mean_total_MW"]

    # Solar growth YoY (based on yearly mean solar).
    yr["solar_yoy_%"] = yr["mean_solar_MW"].pct_change() * 100

    pd.set_option("display.float_format", lambda x: f"{x:,.1f}")
    print(yr.to_string())
    save_table(yr.round(2), "yearly_summary.csv")

    # Generation mix by source per year (mean MW per source).
    mix = df.groupby("year")[SOURCE_COLS].mean()
    save_table(mix.round(1), "yearly_source_mix.csv")
    print("\nMean MW by source per year:")
    print(mix.round(0).to_string())

    # --- Figures ---
    # Yearly mean + peak total
    fig, ax = plt.subplots(figsize=(9, 5))
    ax.bar(yr.index.astype(str), yr["mean_total_MW"], color="#4C72B0", label="Mean MW")
    ax.plot(yr.index.astype(str), yr["peak_total_MW"], "o-", color="#C44E52", label="Peak MW")
    ax.set_title("PGCB Total Generation by Year (mean bar, peak line)")
    ax.set_ylabel("MW")
    ax.legend()
    save_fig(fig, "yearly_total_generation.png")

    # Stacked generation mix
    fig, ax = plt.subplots(figsize=(10, 6))
    mix_plot = mix.fillna(0)
    bottom = pd.Series(0.0, index=mix_plot.index)
    for col in SOURCE_COLS:
        ax.bar(mix_plot.index.astype(str), mix_plot[col], bottom=bottom, label=col)
        bottom += mix_plot[col]
    ax.set_title("Generation Mix by Source per Year (mean MW, stacked)")
    ax.set_ylabel("MW")
    ax.legend(fontsize=8, ncol=2)
    save_fig(fig, "yearly_mix.png")

    # Renewable share by year
    fig, ax = plt.subplots(figsize=(9, 5))
    ax.bar(yr.index.astype(str), yr["mean_renewable_MW"], color="#55A868", label="Renewable mean MW")
    ax2 = ax.twinx()
    ax2.plot(yr.index.astype(str), yr["renewable_share_%"], "o-", color="#8172B3", label="Renewable share %")
    ax2.plot(yr.index.astype(str), yr["solar_share_%"], "s--", color="#CCB974", label="Solar share %")
    ax.set_ylabel("Renewable MW")
    ax2.set_ylabel("Share of total (%)")
    ax2.grid(False)
    ax.set_title("Renewable Generation & Share by Year")
    lines = ax.get_legend_handles_labels()
    lines2 = ax2.get_legend_handles_labels()
    ax.legend(lines[0] + lines2[0], lines[1] + lines2[1], loc="upper left", fontsize=8)
    save_fig(fig, "renewable_share_by_year.png")

    return yr


# --------------------------------------------------------------------------- #
# Monthly
# --------------------------------------------------------------------------- #
MONTH_NAMES = ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
               "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]


def monthly(df: pd.DataFrame) -> pd.DataFrame:
    banner("MONTHLY / SEASONAL TRENDS")
    g = df.groupby("month")
    mo = pd.DataFrame({
        "mean_total_MW": g[TOTAL_COL].mean(),
        "peak_total_MW": g[TOTAL_COL].max(),
        "mean_solar_MW": g["Solar"].mean(),
        "mean_renewable_MW": g["Renewable"].mean(),
    })
    mo.index = [MONTH_NAMES[m - 1] for m in mo.index]
    mo["solar_share_%"] = 100 * mo["mean_solar_MW"] / mo["mean_total_MW"]
    print(mo.to_string())
    save_table(mo.round(2), "monthly_summary.csv")

    hi = mo["mean_total_MW"].idxmax()
    lo = mo["mean_total_MW"].idxmin()
    print(f"\nHighest demand month: {hi} ({mo.loc[hi, 'mean_total_MW']:,.0f} MW avg)")
    print(f"Lowest demand month:  {lo} ({mo.loc[lo, 'mean_total_MW']:,.0f} MW avg)")
    print(f"Highest solar month:  {mo['mean_solar_MW'].idxmax()} "
          f"({mo['mean_solar_MW'].max():,.0f} MW avg)")

    fig, ax = plt.subplots(figsize=(10, 5))
    x = range(len(mo))
    ax.bar(x, mo["mean_total_MW"], color="#4C72B0", label="Mean total MW")
    ax.set_xticks(list(x))
    ax.set_xticklabels(mo.index)
    ax2 = ax.twinx()
    ax2.plot(x, mo["mean_solar_MW"], "o-", color="#DD8452", label="Mean solar MW")
    ax2.plot(x, mo["mean_renewable_MW"], "s--", color="#55A868", label="Mean renewable MW")
    ax2.grid(False)
    ax.set_ylabel("Total MW")
    ax2.set_ylabel("Solar / Renewable MW")
    ax.set_title("Monthly Seasonality: Total Demand vs Solar / Renewable")
    lines = ax.get_legend_handles_labels()
    lines2 = ax2.get_legend_handles_labels()
    ax.legend(lines[0] + lines2[0], lines[1] + lines2[1], loc="upper left", fontsize=8)
    save_fig(fig, "monthly_seasonality.png")
    return mo


# --------------------------------------------------------------------------- #
# Daily
# --------------------------------------------------------------------------- #
DOW_NAMES = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]


def daily(df: pd.DataFrame) -> pd.DataFrame:
    banner("DAILY TRENDS")
    daily_df = df.groupby("date").agg(
        mean_total_MW=(TOTAL_COL, "mean"),
        peak_total_MW=(TOTAL_COL, "max"),
        mean_solar_MW=("Solar", "mean"),
        mean_renewable_MW=("Renewable", "mean"),
    )
    save_table(daily_df.round(2), "daily_timeseries.csv")
    print(f"Daily series rows: {len(daily_df):,}")
    print(daily_df.describe().round(1).to_string())

    # Time series figure
    fig, ax = plt.subplots(figsize=(12, 5))
    ax.plot(daily_df.index, daily_df["mean_total_MW"], color="#4C72B0", lw=0.8, label="Daily mean total")
    ax.plot(daily_df.index, daily_df["peak_total_MW"], color="#C44E52", lw=0.6, alpha=0.6, label="Daily peak total")
    # 30-day rolling mean for trend
    ax.plot(daily_df.index, daily_df["mean_total_MW"].rolling(30).mean(),
            color="black", lw=1.5, label="30-day rolling mean")
    ax.set_title("Daily Total Generation Over the Last 5 Years")
    ax.set_ylabel("MW")
    ax.legend(fontsize=8)
    save_fig(fig, "daily_timeseries.png")

    # Solar daily time series
    fig, ax = plt.subplots(figsize=(12, 4))
    ax.plot(daily_df.index, daily_df["mean_solar_MW"], color="#DD8452", lw=0.8)
    ax.plot(daily_df.index, daily_df["mean_solar_MW"].rolling(30).mean(), color="black", lw=1.5,
            label="30-day rolling mean")
    ax.set_title("Daily Mean Solar Generation Over the Last 5 Years")
    ax.set_ylabel("MW")
    ax.legend(fontsize=8)
    save_fig(fig, "daily_solar_timeseries.png")

    # Day-of-week profile
    dow = df.groupby("dow")[TOTAL_COL].mean()
    dow.index = [DOW_NAMES[i] for i in dow.index]
    save_table(dow.to_frame("mean_total_MW").round(1), "dayofweek_profile.csv")
    fig, ax = plt.subplots(figsize=(8, 4))
    ax.bar(dow.index, dow.values, color="#4C72B0")
    ax.set_title("Average Generation by Day of Week")
    ax.set_ylabel("Mean MW")
    save_fig(fig, "dayofweek_profile.png")
    print("\nDay-of-week mean MW:")
    print(dow.round(0).to_string())
    return daily_df


# --------------------------------------------------------------------------- #
# Hourly
# --------------------------------------------------------------------------- #
def hourly(df: pd.DataFrame) -> pd.DataFrame:
    banner("HOURLY TRENDS")
    g = df.groupby("hour")
    hr = pd.DataFrame({
        "mean_total_MW": g[TOTAL_COL].mean(),
        "mean_solar_MW": g["Solar"].mean(),
        "mean_wind_MW": g["Wind"].mean(),
        "mean_renewable_MW": g["Renewable"].mean(),
    })
    save_table(hr.round(2), "hourly_profile.csv")
    print(hr.round(1).to_string())

    peak_hour = hr["mean_total_MW"].idxmax()
    solar_peak_hour = hr["mean_solar_MW"].idxmax()
    print(f"\nPeak total-generation hour: {peak_hour:02d}:00 "
          f"({hr.loc[peak_hour, 'mean_total_MW']:,.0f} MW avg)")
    print(f"Peak solar hour:            {solar_peak_hour:02d}:00 "
          f"({hr.loc[solar_peak_hour, 'mean_solar_MW']:,.0f} MW avg)")

    # Total hourly profile
    fig, ax = plt.subplots(figsize=(10, 5))
    ax.plot(hr.index, hr["mean_total_MW"], "o-", color="#4C72B0")
    ax.set_title("Average Total Generation Profile by Hour of Day")
    ax.set_xlabel("Hour")
    ax.set_ylabel("Mean MW")
    ax.set_xticks(range(0, 24))
    save_fig(fig, "hourly_total_profile.png")

    # Solar hourly profile (the midday "duck")
    fig, ax = plt.subplots(figsize=(10, 5))
    ax.plot(hr.index, hr["mean_solar_MW"], "o-", color="#DD8452", label="Solar")
    ax.plot(hr.index, hr["mean_wind_MW"], "s--", color="#55A868", label="Wind")
    ax.axvline(solar_peak_hour, color="gray", ls=":", alpha=0.7)
    ax.set_title("Average Solar & Wind Generation Profile by Hour of Day")
    ax.set_xlabel("Hour")
    ax.set_ylabel("Mean MW")
    ax.set_xticks(range(0, 24))
    ax.legend()
    save_fig(fig, "hourly_solar_profile.png")

    # Day Peak / Evening Peak from Remarks
    if "Remarks" in df.columns:
        rmk = df.dropna(subset=["Remarks"])
        for marker in ["Day Peak", "Evening Peak"]:
            sub = rmk[rmk["Remarks"].str.contains(marker, case=False, na=False)]
            if len(sub):
                hours = sub["hour"]
                print(f"'{marker}' marker: n={len(sub)}, "
                      f"typical hour={int(hours.mode().iloc[0]):02d}:00, "
                      f"mean MW={sub[TOTAL_COL].mean():,.0f}")
    return hr


# --------------------------------------------------------------------------- #
# Solar / renewable deep dive
# --------------------------------------------------------------------------- #
def solar_deepdive(df: pd.DataFrame, df_full: pd.DataFrame) -> None:
    banner("RENEWABLE & SOLAR DEEP DIVE")

    solar = df[df["Solar"].notna()]
    if len(solar):
        peak = solar.loc[solar["Solar"].idxmax()]
        print(f"Peak solar (in 5y window): {peak['Solar']:.0f} MW on {peak['datetime']}")

    full_solar = df_full[df_full["Solar"].notna()]
    if len(full_solar):
        peak_all = full_solar.loc[full_solar["Solar"].idxmax()]
        print(f"Peak solar (all history):  {peak_all['Solar']:.0f} MW on {peak_all['datetime']}")

    # Yearly max solar = proxy for installed capacity growth (full history)
    cap = df_full.groupby("year").agg(
        max_solar_MW=("Solar", "max"),
        p99_solar_MW=("Solar", lambda s: s.quantile(0.99)),
        mean_solar_MW=("Solar", "mean"),
        max_wind_MW=("Wind", "max"),
        max_hydro_MW=("Hydro", "max"),
    )
    save_table(cap.round(1), "solar_capacity_growth.csv")
    print("\nYearly MAX solar (proxy for installed capacity) — full history:")
    print(cap.round(0).to_string())

    fig, ax = plt.subplots(figsize=(10, 5))
    ax.bar(cap.index.astype(str), cap["max_solar_MW"], color="#DD8452", label="Yearly max solar MW")
    ax.plot(cap.index.astype(str), cap["mean_solar_MW"], "o-", color="black", label="Yearly mean solar MW")
    ax.set_title("Solar Growth: Yearly Max (capacity proxy) & Mean Output")
    ax.set_ylabel("MW")
    ax.legend()
    save_fig(fig, "solar_yearly_growth.png")

    # Solar share by month (within window)
    sm = df.groupby("month").apply(
        lambda x: 100 * x["Solar"].mean() / x[TOTAL_COL].mean(), include_groups=False
    )
    sm.index = [MONTH_NAMES[m - 1] for m in sm.index]
    print("\nSolar share of total by month (%):")
    print(sm.round(2).to_string())

    # Source comparison: solar vs wind vs hydro (mean MW within window)
    comp = df[RENEWABLE_COLS].mean()
    print("\nMean renewable contribution within window (MW):")
    print(comp.round(1).to_string())
    save_table(comp.to_frame("mean_MW").round(2), "renewable_source_comparison.csv")

    fig, ax = plt.subplots(figsize=(7, 5))
    ax.bar(comp.index, comp.values, color=["#DD8452", "#55A868", "#4C72B0"])
    ax.set_title("Renewable Source Comparison (mean MW, last 5y)")
    ax.set_ylabel("Mean MW")
    save_fig(fig, "renewable_source_comparison.png")

    # Overall solar share
    overall_solar_share = 100 * df["Solar"].mean() / df[TOTAL_COL].mean()
    overall_ren_share = 100 * df["Renewable"].mean() / df[TOTAL_COL].mean()
    print(f"\nOverall solar share (5y window):     {overall_solar_share:.2f}%")
    print(f"Overall renewable share (5y window): {overall_ren_share:.2f}%")


# --------------------------------------------------------------------------- #
# Main
# --------------------------------------------------------------------------- #
def main() -> None:
    os.makedirs(OUT_DIR, exist_ok=True)

    df_full = load_clean()

    first_appearance(df_full)

    # Filter to last 5 years.
    banner("FILTERING TO LAST 5 YEARS")
    df = df_full[df_full["datetime"] >= CUTOFF].copy()
    print(f"Cutoff: {CUTOFF.date()}  (today = {TODAY.date()})")
    print(f"Analyzed range: {df['datetime'].min()}  ->  {df['datetime'].max()}")
    print(f"Rows in window: {len(df):,}")

    yearly(df)
    monthly(df)
    daily(df)
    hourly(df)
    solar_deepdive(df, df_full)

    banner("DONE")
    print(f"All figures and tables written to ./{OUT_DIR}/")


if __name__ == "__main__":
    main()
