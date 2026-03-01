import base64
import io
from pathlib import Path

import pandas as pd
import matplotlib.pyplot as plt


DATA_PATH = Path("data/prices.csv")


def _normalize_text(x: str | None) -> str | None:
    if x is None:
        return None
    return str(x).strip().lower()


def _parse_date(d: str) -> pd.Timestamp:
    # expects "DD-MM-YYYY"
    return pd.to_datetime(d, format="%d-%m-%Y", errors="raise")


def build_fluctuation_graph_base64(
    start_date: str,
    end_date: str,
    variety: str,
    shop: str | None = None,
    size: str | None = None,
):
    if not DATA_PATH.exists():
        raise FileNotFoundError(DATA_PATH)

    start = _parse_date(start_date)
    end = _parse_date(end_date)
    if end < start:
        raise ValueError("end_date must be after start_date")

    df = pd.read_csv(DATA_PATH)

    # Your actual CSV columns
    required = {"date", "variety", "seller_price_per_stem"}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"CSV missing columns: {sorted(list(missing))}")

    df["date"] = pd.to_datetime(df["date"], errors="coerce", dayfirst=True)
    df = df.dropna(subset=["date"])

    df["variety_n"] = df["variety"].astype(str).str.strip().str.lower()
    df = df[df["variety_n"] == _normalize_text(variety)]

    if shop is not None and "shop" in df.columns:
        df["shop_n"] = df["shop"].astype(str).str.strip().str.lower()
        df = df[df["shop_n"] == _normalize_text(shop)]

    if size is not None and "size" in df.columns:
        df["size_n"] = df["size"].astype(str).str.strip().str.lower()
        df = df[df["size_n"] == _normalize_text(size)]

    df = df[(df["date"] >= start) & (df["date"] <= end)].sort_values("date")

    if df.empty:
        raise ValueError("No data found for given filters")

    # Use seller_price_per_stem
    df["seller_price_per_stem"] = pd.to_numeric(df["seller_price_per_stem"], errors="coerce")
    df = df.dropna(subset=["seller_price_per_stem"])
    if df.empty:
        raise ValueError("No valid numeric prices after filtering")

    # Build daily average for smoother line graph
    daily = (
        df.groupby(df["date"].dt.date)["seller_price_per_stem"]
        .mean()
        .reset_index()
        .rename(columns={"seller_price_per_stem": "avg_price"})
    )
    daily["date"] = pd.to_datetime(daily["date"])

    # Plot
    fig = plt.figure()
    plt.plot(daily["date"], daily["avg_price"])

    title_parts = [f"Variety: {variety}"]
    if shop:
        title_parts.append(f"Shop: {shop}")
    if size:
        title_parts.append(f"Size: {size}")

    plt.title(" | ".join(title_parts))
    plt.xlabel("Date")
    plt.ylabel("Avg price per stem (LKR)")
    plt.xticks(rotation=30)
    plt.tight_layout()

    # Return as base64 png
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=140)
    plt.close(fig)
    buf.seek(0)

    b64 = base64.b64encode(buf.read()).decode("utf-8")
    return {
        "filters": {
            "start_date": start_date,
            "end_date": end_date,
            "variety": variety,
            "shop": shop,
            "size": size,
        },
        "points": int(len(df)),
        "image_base64_png": b64,
    }