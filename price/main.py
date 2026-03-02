# =========================
# ✅ FIX 2: main.py (modified)
# - Make fluctuation import LAZY so it can’t break price prediction
# - Everything else stays the same
# =========================

from fastapi import FastAPI, HTTPException
from pathlib import Path
from pydantic import BaseModel
import pandas as pd

from price_prediction import PricePredictor

app = FastAPI(title="Vinuri Flower API")

DATA_PATH = Path("data/prices.csv")
SEQ_LEN = 8

if not DATA_PATH.exists():
    raise RuntimeError("Dataset not found. Put your CSV here: data/prices.csv")

df = pd.read_csv(DATA_PATH)

required_cols = ["date", "shop", "variety", "size", "seller_price_per_stem", "units_sold"]
missing = [c for c in required_cols if c not in df.columns]
if missing:
    raise RuntimeError(f"prices.csv missing columns: {missing}")

df["date"] = pd.to_datetime(df["date"], errors="coerce", dayfirst=True)
df = df.dropna(subset=["date"]).copy()

df["shop"] = df["shop"].astype(str).str.strip().str.lower()
df["variety"] = df["variety"].astype(str).str.strip().str.lower()
df["size"] = df["size"].astype(str).str.strip().str.lower()

shops = sorted(df["shop"].unique().tolist())

try:
    price_predictor = PricePredictor(df=df, seq_len=SEQ_LEN)
except Exception as e:
    raise RuntimeError(f"Failed to load price prediction models: {e}")

# ✅ Lazy-load fluctuation module so it never breaks price API
fluct_detector = None
try:
    from fluctuatuion_graph import FluctuationGraphDetector, prepare_df_for_fluctuation

    df_fluct = prepare_df_for_fluctuation(df)
    fluct_detector = FluctuationGraphDetector(df=df_fluct)
except Exception as e:
    fluct_detector = None
    import traceback
    print("⚠️ FluctuationGraphDetector not loaded:")
    print(traceback.format_exc())


class PriceRequest(BaseModel):
    date: str
    shop: str
    variety: str
    size: str


class FluctuationRequest(BaseModel):
    start_date: str
    end_date: str
    shop: str | None = None
    variety: str
    size: str | None = None


@app.get("/health")
def health():
    return {
        "status": "ok",
        "data_rows": int(len(df)),
        "min_date": str(df["date"].min().date()) if len(df) else None,
        "max_date": str(df["date"].max().date()) if len(df) else None,
        "shops_count": len(shops),
        "price_model_loaded": True,
        "fluctuation_model_loaded": bool(fluct_detector is not None),
    }


@app.get("/shops")
def list_shops():
    return {"shops": shops}


@app.post("/get_price_per_flower")
def get_price_per_flower(payload: PriceRequest):
    try:
        date_str = str(payload.date).strip()
        shop = str(payload.shop).strip().lower()
        variety = str(payload.variety).strip().lower()
        size = str(payload.size).strip().lower()
    except Exception:
        raise HTTPException(status_code=400, detail="Payload must include: date, shop, variety, size")

    try:
        result = price_predictor.predict_price(
            date_str=date_str,
            shop=shop,
            variety=variety,
            size=size,
        )
        if result is None:
            raise RuntimeError("predict_price returned None. Check price_prediction.py return statement.")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Price prediction failed: {e}")

    msg = (
        f"💐 Price per flower on {date_str} for {shop}, {variety} ({size}) is Rs. {result['price_lkr']:.2f}\n"
        f"SAMIS Score: {result['samis']['samis_score']} ({result['samis']['sustainability']})\n"
        f"Trend: {result['samis']['trend']['label']} ({result['samis']['trend']['change_percent']}%)\n"
        f"Risk Level: {result['samis']['risk']['level']} (volatility {result['samis']['risk']['volatility']})"
    )

    return {"message": msg, "data": result}


@app.post("/fluctuations")
def fluctuations(payload: FluctuationRequest):
    if fluct_detector is None:
        raise HTTPException(
            status_code=500,
            detail="Fluctuation model not loaded. Fix fluctuatuion_graph.py backend (matplotlib must be Agg).",
        )

    try:
        return fluct_detector.detect(
            start_date=payload.start_date,
            end_date=payload.end_date,
            shop=payload.shop,
            variety=payload.variety,
            size=payload.size,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Fluctuation detection failed: {e}")