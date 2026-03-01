# fluctuatuion_graph.py
# ============================================================
# Fluctuation detection module for Vinuri Flower API
# Loads saved artifacts INSIDE this module (not in app.py)
# Uses saved artifacts:
#   - fluctuatuion_graph_isolation_forest.pkl
#   - fluctuatuion_graph_feature_columns.pkl
#   - fluctuatuion_graph_config.pkl (optional)
# ============================================================

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Any, List, Optional

import joblib
import pandas as pd


def _norm_text(s: pd.Series) -> pd.Series:
    return s.astype(str).str.strip().str.lower()


def _norm_size(s: pd.Series) -> pd.Series:
    # match training notebook: remove spaces and hyphens
    s = s.astype(str).str.strip().str.lower()
    s = s.str.replace(r"\s+", "", regex=True).str.replace("-", "", regex=False)
    return s


@dataclass
class FluctuationArtifacts:
    # Default locations (same style as your PricePredictor paths)
    model_path: Path = Path("artifacts/fluctuatuion_graph/fluctuatuion_graph_isolation_forest.pkl")
    feature_cols_path: Path = Path("artifacts/fluctuatuion_graph/fluctuatuion_graph_feature_columns.pkl")
    config_path: Path = Path("artifacts/fluctuatuion_graph/fluctuatuion_graph_config.pkl")  

class FluctuationGraphDetector:
    """
    Detect price fluctuations (anomalies) for a given shop, variety, size, and date range,
    using a pre-trained IsolationForest artifact.
    """

    def __init__(self, df: pd.DataFrame, artifacts: Optional[FluctuationArtifacts] = None):
        self.df = df.copy()

        # Use default artifact paths if not provided
        self.artifacts = artifacts or FluctuationArtifacts()

        # Ensure artifacts exist before loading
        if not self.artifacts.model_path.exists():
            raise RuntimeError(f"IsolationForest artifact not found: {self.artifacts.model_path}")
        if not self.artifacts.feature_cols_path.exists():
            raise RuntimeError(f"Feature columns artifact not found: {self.artifacts.feature_cols_path}")

        # Load artifacts once (INSIDE THIS MODULE)
        self.model = joblib.load(self.artifacts.model_path)
        self.feature_cols: List[str] = joblib.load(self.artifacts.feature_cols_path)

        self.config: Dict[str, Any] = {}
        if self.artifacts.config_path and self.artifacts.config_path.exists():
            self.config = joblib.load(self.artifacts.config_path)

        # Ensure required feature columns exist in df
        missing_feats = [c for c in self.feature_cols if c not in self.df.columns]
        if missing_feats:
            raise RuntimeError(
                f"Dataset is missing required feature columns: {missing_feats}. "
                f"Compute them using prepare_df_for_fluctuation(df) before initializing the detector."
            )

        # Ensure normalized filter columns exist
        for col in ["date", "shop", "variety", "size"]:
            if col not in self.df.columns:
                raise RuntimeError(f"Dataset missing required column: {col}")

    def detect(
        self,
        start_date: str,
        end_date: str,
        shop: str,
        variety: str,
        size: str,
    ) -> Dict[str, Any]:
        """
        Returns:
          {
            "summary": {...},
            "rows": [ {date, price, price_diff, price_pct_change, fluctuation_score, is_fluctuation}, ...]
          }
        """
        d1 = pd.to_datetime(start_date, dayfirst=True, errors="coerce")
        d2 = pd.to_datetime(end_date, dayfirst=True, errors="coerce")
        if pd.isna(d1) or pd.isna(d2):
            raise ValueError("start_date and end_date must be valid date strings")
        if d2 < d1:
            raise ValueError("end_date must be on or after start_date")

        shop_n = str(shop).strip().lower()
        variety_n = str(variety).strip().lower()
        size_n = str(size).strip().lower().replace(" ", "").replace("-", "")

        mask = (
            (self.df["date"] >= d1) & (self.df["date"] <= d2) &
            (self.df["shop"] == shop_n) &
            (self.df["variety"] == variety_n) &
            (self.df["size"] == size_n)
        )

        sub = self.df.loc[mask].copy()
        if sub.empty:
            return {
                "summary": {
                    "start_date": str(d1.date()),
                    "end_date": str(d2.date()),
                    "shop": shop_n,
                    "variety": variety_n,
                    "size": size_n,
                    "rows": 0,
                    "fluctuations": 0,
                    "message": "No data found for given filters."
                },
                "rows": []
            }

        sub = sub.sort_values("date").reset_index(drop=True)

        feats = sub[self.feature_cols].fillna(0)

        sub["fluctuation_score"] = self.model.decision_function(feats)
        sub["is_fluctuation"] = (self.model.predict(feats) == -1).astype(int)

        cols_out = ["date", "price", "price_diff", "price_pct_change", "fluctuation_score", "is_fluctuation"]
        rows = []
        for _, r in sub[cols_out].iterrows():
            rows.append({
                "date": str(pd.to_datetime(r["date"]).date()),
                "price": float(r["price"]) if pd.notna(r["price"]) else None,
                "price_diff": float(r["price_diff"]) if pd.notna(r["price_diff"]) else 0.0,
                "price_pct_change": float(r["price_pct_change"]) if pd.notna(r["price_pct_change"]) else 0.0,
                "fluctuation_score": float(r["fluctuation_score"]),
                "is_fluctuation": int(r["is_fluctuation"]),
            })

        return {
            "summary": {
                "start_date": str(d1.date()),
                "end_date": str(d2.date()),
                "shop": shop_n,
                "variety": variety_n,
                "size": size_n,
                "rows": int(len(rows)),
                "fluctuations": int(sub["is_fluctuation"].sum()),
                "config": self.config
            },
            "rows": rows
        }


def prepare_df_for_fluctuation(df: pd.DataFrame) -> pd.DataFrame:
    """
    This matches your training notebook feature engineering.
    Call this in app.py once after loading prices.csv, then pass the output to FluctuationGraphDetector.
    """
    out = df.copy()

    # normalize columns
    out["date"] = pd.to_datetime(out["date"], errors="coerce", dayfirst=True)
    out = out.dropna(subset=["date", "seller_price_per_stem"]).copy()

    out["shop"] = _norm_text(out["shop"])
    out["variety"] = _norm_text(out["variety"])
    out["size"] = _norm_size(out["size"])

    out["price"] = pd.to_numeric(out["seller_price_per_stem"], errors="coerce")
    out = out.dropna(subset=["price"]).copy()

    out = out.sort_values(["shop", "variety", "size", "date"]).reset_index(drop=True)

    out["price_diff"] = out.groupby(["shop", "variety", "size"])["price"].diff()
    out["price_pct_change"] = out.groupby(["shop", "variety", "size"])["price"].pct_change() * 100

    out["dow"] = out["date"].dt.dayofweek
    out["month"] = out["date"].dt.month

    return out
