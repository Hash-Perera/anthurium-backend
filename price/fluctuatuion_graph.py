import base64
import io
from dataclasses import dataclass
from typing import Optional, Dict, Any

import pandas as pd

# IMPORTANT: must be set BEFORE importing pyplot
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt


def prepare_df_for_fluctuation(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df["date"] = pd.to_datetime(df["date"], errors="coerce", dayfirst=True)
    df = df.dropna(subset=["date"]).copy()

    df["shop"] = df["shop"].astype(str).str.strip().str.lower()
    df["variety"] = df["variety"].astype(str).str.strip().str.lower()
    df["size"] = df["size"].astype(str).str.strip().str.lower()

    df["seller_price_per_stem"] = pd.to_numeric(df["seller_price_per_stem"], errors="coerce")
    df = df.dropna(subset=["seller_price_per_stem"]).copy()

    return df


def _parse_date(d: str) -> pd.Timestamp:
    # expects DD-MM-YYYY
    return pd.to_datetime(d, format="%d-%m-%Y", errors="raise").normalize()


@dataclass
class FluctuationGraphDetector:
    df: pd.DataFrame

    def detect(
        self,
        start_date: str,
        end_date: str,
        variety: str,
        shop: Optional[str] = None,
        size: Optional[str] = None,
    ) -> Dict[str, Any]:
        start = _parse_date(start_date)
        end = _parse_date(end_date)
        if end < start:
            raise ValueError("end_date must be after start_date")

        variety_n = str(variety).strip().lower()
        shop_n = str(shop).strip().lower() if shop else None
        size_n = str(size).strip().lower() if size else None

        dff = self.df[self.df["variety"] == variety_n].copy()

        if shop_n:
            dff = dff[dff["shop"] == shop_n]
        if size_n:
            dff = dff[dff["size"] == size_n]

        dff = dff[(dff["date"] >= start) & (dff["date"] <= end)].sort_values("date")

        if dff.empty:
            raise ValueError("No data found for given filters")

        daily = (
            dff.groupby(dff["date"].dt.date)["seller_price_per_stem"]
            .mean()
            .reset_index()
            .rename(columns={"seller_price_per_stem": "avg_price"})
        )
        daily["date"] = pd.to_datetime(daily["date"])

        fig = plt.figure()
        plt.plot(daily["date"], daily["avg_price"])

        title_parts = [f"Variety: {variety_n}"]
        if shop_n:
            title_parts.append(f"Shop: {shop_n}")
        if size_n:
            title_parts.append(f"Size: {size_n}")

        plt.title(" | ".join(title_parts))
        plt.xlabel("Date")
        plt.ylabel("Avg price per stem (LKR)")
        plt.xticks(rotation=30)
        plt.tight_layout()

        buf = io.BytesIO()
        fig.savefig(buf, format="png", dpi=140)
        plt.close(fig)
        buf.seek(0)

        b64 = base64.b64encode(buf.read()).decode("utf-8")

        return {
            "filters": {
                "start_date": start_date,
                "end_date": end_date,
                "variety": variety_n,
                "shop": shop_n,
                "size": size_n,
            },
            "points": int(len(dff)),
            "image_base64_png": b64,
        }