"""
Overlay grid-context events on daily generation charts.

Reads analysis/grid_context_events.json and analysis/daily_timeseries.csv,
then reproduces the daily total and solar charts from analyze.py with event
markers (vertical lines) and shaded spans for sustained periods.

Outputs:
    analysis/daily_timeseries_annotated.png
    analysis/daily_solar_timeseries_annotated.png

Usage:
    python annotate.py
"""

from __future__ import annotations

import json
import os
from datetime import datetime

import pandas as pd

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.dates as mdates

# --------------------------------------------------------------------------- #
# Config (mirrors analyze.py)
# --------------------------------------------------------------------------- #
OUT_DIR = "analysis"
EVENTS_PATH = os.path.join(OUT_DIR, "grid_context_events.json")
DAILY_CSV = os.path.join(OUT_DIR, "daily_timeseries.csv")
DPI = 130

# Categories -> colors for markers / spans
CAT_COLORS = {
    "fuel": "#E45756",
    "blackout": "#000000",
    "import-deal": "#4C78A8",
    "tariff": "#F58518",
    "capacity": "#54A24B",
    "policy": "#B279A2",
    "political": "#9D755D",
}

plt.rcParams.update({
    "figure.autolayout": True,
    "axes.grid": True,
    "grid.alpha": 0.3,
    "axes.titleweight": "bold",
})


def load_events(path: str) -> list[dict]:
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def event_date(ev: dict) -> pd.Timestamp | None:
    if "date" in ev:
        return pd.Timestamp(ev["date"])
    if "start" in ev:
        return pd.Timestamp(ev["start"])
    return None


def annotate_ax(ax, events: list[dict], y_top_frac: float = 0.92) -> None:
    """Draw shaded spans and vertical markers with short labels."""
    ymin, ymax = ax.get_ylim()
    label_y = ymin + (ymax - ymin) * y_top_frac
    used_x: list[float] = []

    # Spans first (behind lines)
    for ev in events:
        if "start" not in ev or "end" not in ev:
            continue
        t0 = pd.Timestamp(ev["start"])
        t1 = pd.Timestamp(ev["end"])
        color = CAT_COLORS.get(ev["category"], "#999999")
        ax.axvspan(t0, t1, alpha=0.12, color=color, zorder=1)
        # Short span label at start
        short = ev["title"][:28] + ("…" if len(ev["title"]) > 28 else "")
        ax.text(
            t0, label_y, short, fontsize=6, color=color, rotation=90,
            va="top", ha="left", alpha=0.85, zorder=4,
        )

    # Point events
    for ev in events:
        if "date" not in ev:
            continue
        t = pd.Timestamp(ev["date"])
        color = CAT_COLORS.get(ev["category"], "#999999")
        ax.axvline(t, color=color, lw=0.9, ls="--", alpha=0.75, zorder=3)
        short = ev["title"][:22] + ("…" if len(ev["title"]) > 22 else "")
        x_num = mdates.date2num(t)
        # Stagger labels that cluster
        offset = 0
        for ux in used_x:
            if abs(x_num - ux) < 25:
                offset += 12
        used_x.append(x_num)
        ax.annotate(
            short,
            xy=(t, label_y - offset),
            fontsize=6,
            color=color,
            rotation=90,
            va="top",
            ha="center",
            xytext=(0, 0),
            textcoords="offset points",
            zorder=5,
        )


def daily_total_chart(daily_df: pd.DataFrame, events: list[dict]) -> None:
    fig, ax = plt.subplots(figsize=(14, 6))
    ax.plot(daily_df.index, daily_df["mean_total_MW"], color="#4C72B0", lw=0.8,
            label="Daily mean total", zorder=2)
    ax.plot(daily_df.index, daily_df["peak_total_MW"], color="#C44E52", lw=0.6,
            alpha=0.6, label="Daily peak total", zorder=2)
    ax.plot(daily_df.index, daily_df["mean_total_MW"].rolling(30).mean(),
            color="black", lw=1.5, label="30-day rolling mean", zorder=2)
    annotate_ax(ax, events)
    ax.set_title("Daily Total Generation (annotated with grid events)")
    ax.set_ylabel("MW")
    ax.legend(fontsize=8, loc="upper left")
    path = os.path.join(OUT_DIR, "daily_timeseries_annotated.png")
    fig.savefig(path, dpi=DPI, bbox_inches="tight")
    plt.close(fig)
    print(f"  [figure] {path}")


def daily_solar_chart(daily_df: pd.DataFrame, events: list[dict]) -> None:
    # Only solar-relevant events + general capacity/policy spans
    solar_cats = {"capacity", "policy", "import-deal", "fuel", "political"}
    filtered = [e for e in events if e["category"] in solar_cats or "solar" in e["title"].lower()
                or "Adani" in e["title"] or "Nepal" in e["title"] or "coal" in e["title"].lower()]

    fig, ax = plt.subplots(figsize=(14, 5))
    ax.plot(daily_df.index, daily_df["mean_solar_MW"], color="#DD8452", lw=0.8, zorder=2)
    ax.plot(daily_df.index, daily_df["mean_solar_MW"].rolling(30).mean(),
            color="black", lw=1.5, label="30-day rolling mean", zorder=2)
    annotate_ax(ax, filtered, y_top_frac=0.88)
    ax.set_title("Daily Mean Solar Generation (annotated with grid events)")
    ax.set_ylabel("MW")
    ax.legend(fontsize=8)
    path = os.path.join(OUT_DIR, "daily_solar_timeseries_annotated.png")
    fig.savefig(path, dpi=DPI, bbox_inches="tight")
    plt.close(fig)
    print(f"  [figure] {path}")


def yearly_mix_chart(events: list[dict]) -> None:
    """Optional: annotate yearly mix if source mix CSV exists."""
    mix_path = os.path.join(OUT_DIR, "yearly_source_mix.csv")
    if not os.path.isfile(mix_path):
        return
    mix = pd.read_csv(mix_path, index_col=0)
    fig, ax = plt.subplots(figsize=(11, 6))
    bottom = pd.Series(0.0, index=mix.index)
    source_cols = [c for c in mix.columns if c in mix]
    for col in source_cols:
        vals = mix[col].fillna(0)
        ax.bar(mix.index.astype(str), vals, bottom=bottom, label=col)
        bottom += vals
    # Mark years with major events
    year_events = {
        2022: "Fuel crisis",
        2023: "IMF / coal ramp",
        2024: "Adani + Nepal",
        2025: "Solar peak",
    }
    for yr, lbl in year_events.items():
        if str(yr) in mix.index.astype(str).tolist():
            idx = list(mix.index.astype(int)).index(yr)
            ax.text(idx, bottom.iloc[idx] * 1.02, lbl, ha="center", fontsize=7, color="#333")
    ax.set_title("Generation Mix by Year (annotated milestones)")
    ax.set_ylabel("Mean MW")
    ax.legend(fontsize=7, ncol=2)
    path = os.path.join(OUT_DIR, "yearly_mix_annotated.png")
    fig.savefig(path, dpi=DPI, bbox_inches="tight")
    plt.close(fig)
    print(f"  [figure] {path}")


def main() -> None:
    if not os.path.isfile(EVENTS_PATH):
        raise SystemExit(f"Missing {EVENTS_PATH} — run research consolidation first.")
    if not os.path.isfile(DAILY_CSV):
        raise SystemExit(f"Missing {DAILY_CSV} — run analyze.py first.")

    events = load_events(EVENTS_PATH)
    daily_df = pd.read_csv(DAILY_CSV, index_col=0, parse_dates=True)
    daily_df.index.name = "date"

    print(f"Loaded {len(events)} events, {len(daily_df):,} daily rows")
    daily_total_chart(daily_df, events)
    daily_solar_chart(daily_df, events)
    yearly_mix_chart(events)
    print("Annotation complete.")


if __name__ == "__main__":
    main()
