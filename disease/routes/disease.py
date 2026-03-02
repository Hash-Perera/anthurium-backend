import io
from PIL import Image
from fastapi import APIRouter, File, UploadFile, Form
from fastapi.responses import JSONResponse

from services.model import predict_disease
from services.analysis import estimate_infected_area_percent, get_stage
from services.rules import recovery_days, spread_risk, treatment_tips

router = APIRouter(tags=["disease"])

def read_image_or_400(upload: UploadFile):
    try:
        return Image.open(io.BytesIO(upload.file.read())).convert("RGB")
    except Exception:
        return None

@router.post("/predict-disease")
async def predict(image: UploadFile = File(...)):
    try:
        img = Image.open(io.BytesIO(await image.read())).convert("RGB")
    except Exception:
        return JSONResponse(
            status_code=400,
            content={"success": False, "message": "Uploaded image is not supported. Please upload a clear leaf photo."},
        )

    try:
        d, c = predict_disease(img)
        return {"success": True, "disease": d, "confidence": round(c, 4)}
    except Exception:
        return JSONResponse(status_code=500, content={"success": False, "message": "Disease detection failed. Please try again."})

@router.post("/stage")
async def stage(image: UploadFile = File(...)):
    try:
        img = Image.open(io.BytesIO(await image.read())).convert("RGB")
    except Exception:
        return JSONResponse(status_code=400, content={"success": False, "message": "Invalid image file."})

    pct = estimate_infected_area_percent(img)
    st = get_stage(pct)
    return {"success": True, "infected_area_percent": round(pct, 2), "stage": st}

@router.post("/recovery")
async def recovery(
    image: UploadFile = File(...),
    treatment_quality: str = Form("normal"),
    humidity: str = Form("medium"),
):
    try:
        img = Image.open(io.BytesIO(await image.read())).convert("RGB")
    except Exception:
        return JSONResponse(status_code=400, content={"success": False, "message": "Invalid image file."})

    d, c = predict_disease(img)
    pct = estimate_infected_area_percent(img)
    st = get_stage(pct)
    rec = recovery_days(d, st, treatment_quality, humidity)

    return {"success": True, "disease": d, "confidence": round(c, 4), "stage": st, "recovery_days": rec}

@router.post("/risk")
async def risk(image: UploadFile = File(...), humidity: str = Form("medium")):
    try:
        img = Image.open(io.BytesIO(await image.read())).convert("RGB")
    except Exception:
        return JSONResponse(status_code=400, content={"success": False, "message": "Invalid image file."})

    d, c = predict_disease(img)
    pct = estimate_infected_area_percent(img)
    st = get_stage(pct)
    r = spread_risk(d, st, humidity)

    return {
        "success": True,
        "disease": d,
        "confidence": round(c, 4),
        "infected_area_percent": round(pct, 2),
        "stage": st,
        "spread_risk": r,
    }

@router.get("/treatment/{disease}")
def treatment(disease: str):
    return {"success": True, **treatment_tips(disease)}