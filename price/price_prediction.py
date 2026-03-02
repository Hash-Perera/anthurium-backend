from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Any

import joblib
import numpy as np
import pandas as pd
import tensorflow as tf


@dataclass
class PricePredictor:
    df: pd.DataFrame
    seq_len: int = 8

    rf_path: Path = Path("artifacts/price_prediction/price_recommend_model.pkl")
    prep_path: Path = Path("artifacts/price_prediction/price_recommend_preprocessor.pkl")
    lstm_path: Path = Path("artifacts/price_prediction/price_recommend_lstm_model.keras")

    def __post_init__(self) -> None:
        self.rf_model = joblib.load(self.rf_path)
        self.preprocessor = joblib.load(self.prep_path)
        self.lstm = tf.keras.models.load_model(self.lstm_path, compile=False)

    @staticmethod
    def round_to_half(x: float) -> float:
        return round(float(x) * 2) / 2

    def build_sequence_from_prices(self, prices: np.ndarray) -> np.ndarray:
        prices = prices.astype("float32")
        seq = np.zeros((self.seq_len, 5), dtype="float32")

        for i in range(self.seq_len):
            p = float(prices[i])
            lag1 = float(prices[i - 1]) if i - 1 >= 0 else p
            lag2 = float(prices[i - 2]) if i - 2 >= 0 else p
            lag4 = float(prices[i - 4]) if i - 4 >= 0 else p
            ema4 = float(pd.Series(prices[: i + 1]).ewm(span=4, adjust=False).mean().iloc[-1])
            seq[i] = [p, lag1, lag2, lag4, ema4]

        return seq

    def predict_from_sequence(
        self,
        shop: str,
        variety: str,
        size: str,
        units_sold: float,
        seq: np.ndarray,
    ) -> float:
        if seq.shape != (self.seq_len, 5):
            raise ValueError(f"sequence must be shape ({self.seq_len}, 5). Got {seq.shape}")

        lstm_pred = float(self.lstm.predict(seq[np.newaxis, :, :], verbose=0).ravel()[0])

        lag_1 = float(seq[-1, 0])
        lag_2 = float(seq[-2, 0])
        lag_4 = float(seq[-4, 0])
        ema_4 = float(pd.Series(seq[:, 0]).ewm(span=4, adjust=False).mean().iloc[-1])

        row = pd.DataFrame([{
            "shop": shop,
            "variety": variety,
            "size": size,
            "lstm_pred": lstm_pred,
            "units_sold": float(units_sold),
            "lag_1": lag_1,
            "lag_2": lag_2,
            "lag_4": lag_4,
            "ema_4": ema_4,
        }])

        X = self.preprocessor.transform(row)
        return float(self.rf_model.predict(X)[0])

    @staticmethod
    def calculate_samis(prices: np.ndarray, predicted_price: float) -> Dict[str, Any]:
        prices = np.array(prices, dtype=float)
        mean_price = np.mean(prices) if len(prices) > 0 else 1.0
        std_price = np.std(prices) if len(prices) > 0 else 0.0

        if mean_price - std_price <= predicted_price <= mean_price + std_price:
            sustainability_score = 40
        elif mean_price - 1.5 * std_price <= predicted_price <= mean_price + 1.5 * std_price:
            sustainability_score = 30
        elif mean_price - 2 * std_price <= predicted_price <= mean_price + 2 * std_price:
            sustainability_score = 20
        else:
            sustainability_score = 10

        if sustainability_score >= 30:
            sustainability_label = "Sustainable"
        elif 20 <= sustainability_score < 30:
            sustainability_label = "Moderate"
        else:
            sustainability_label = "Not Sustainable"

        recent_prices = prices[-7:] if len(prices) >= 7 else prices
        if len(recent_prices) == 0 or recent_prices[0] == 0:
            change_pct = 0.0
        else:
            change_pct = (predicted_price - recent_prices[0]) / recent_prices[0] * 100

        if change_pct > 3:
            trend_score = 30
            trend_label = "Rising"
        elif -3 <= change_pct <= 3:
            trend_score = 15
            trend_label = "Stable"
        else:
            trend_score = 5
            trend_label = "Falling"

        cv = std_price / mean_price if mean_price != 0 else 0.0
        if cv < 0.05:
            risk_score = 30
            risk_label = "Low"
        elif 0.05 <= cv <= 0.1:
            risk_score = 20
            risk_label = "Medium"
        else:
            risk_score = 10
            risk_label = "High"

        samis_score = min(max(sustainability_score + trend_score + risk_score, 0), 100)

        return {
            "samis_score": samis_score,
            "sustainability": sustainability_label,
            "trend": {"label": trend_label, "change_percent": round(change_pct, 2)},
            "risk": {"level": risk_label, "volatility": round(cv, 4)},
        }

    def predict_price(self, date_str: str, shop: str, variety: str, size: str) -> Dict[str, Any]:
        date_str = str(date_str).strip()
        shop = str(shop).strip().lower()
        variety = str(variety).strip().lower()
        size = str(size).strip().lower()

        target_date = pd.to_datetime(date_str).normalize()

        hist = self.df[
            (self.df["shop"] == shop)
            & (self.df["variety"] == variety)
            & (self.df["size"] == size)
            & (self.df["date"] < target_date)
        ].sort_values("date")

        hist_last = hist.tail(self.seq_len)
        prices = hist_last["seller_price_per_stem"].to_numpy(dtype="float32")

        if len(prices) < self.seq_len:
            if len(prices) == 0:
                fallback_price = float(self.df["seller_price_per_stem"].mean())
                prices = np.full(self.seq_len, fallback_price, dtype="float32")
            else:
                prices = np.pad(prices, (self.seq_len - len(prices), 0), "edge")

        seq = self.build_sequence_from_prices(prices)

        units_sold = float(hist_last["units_sold"].iloc[-1]) if len(hist_last) > 0 else 10.0

        predicted_price = self.predict_from_sequence(shop, variety, size, units_sold, seq)
        price_lkr = self.round_to_half(predicted_price)

        samis = self.calculate_samis(prices, predicted_price)

        return {"price_lkr": price_lkr, "samis": samis}