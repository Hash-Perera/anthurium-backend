from fastapi import FastAPI, File, UploadFile, Form
from fastapi.responses import JSONResponse
import onnxruntime as ort
import numpy as np
from PIL import Image
import json
import cv2
import io
import os

app = FastAPI()

# -----------------------------
# PATHS (artifacts folder)
# -----------------------------
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ARTIFACTS_DIR = os.path.join(BASE_DIR, "artifacts", "leafguard_artifacts")

MODEL_PATH = os.path.join(ARTIFACTS_DIR, "leafguard_classifier.onnx")
LABELS_PATH = os.path.join(ARTIFACTS_DIR, "labels.json")
PREPROCESS_PATH = os.path.join(ARTIFACTS_DIR, "preprocess.json")

# -----------------------------
# LOAD ARTIFACT FILES
# -----------------------------
if not os.path.exists(MODEL_PATH):
    raise FileNotFoundError(f"Model not found: {MODEL_PATH}")

# Use CPU by default (works on all machines)
session = ort.InferenceSession(MODEL_PATH, providers=["CPUExecutionProvider"])

if not os.path.exists(LABELS_PATH):
    raise FileNotFoundError(f"labels.json not found: {LABELS_PATH}")
with open(LABELS_PATH, "r", encoding="utf-8") as f:
    labels = json.load(f)

if not os.path.exists(PREPROCESS_PATH):
    raise FileNotFoundError(f"preprocess.json not found: {PREPROCESS_PATH}")
with open(PREPROCESS_PATH, "r", encoding="utf-8") as f:
    preprocess_cfg = json.load(f)

IMG_SIZE = int(preprocess_cfg["img_size"])
MEAN = np.array(preprocess_cfg["normalize_mean"], dtype=np.float32).reshape(1, 1, 3)
STD = np.array(preprocess_cfg["normalize_std"], dtype=np.float32).reshape(1, 1, 3)

# -----------------------------
# PREPROCESS
# -----------------------------
def preprocess_image(pil_img: Image.Image) -> np.ndarray:
    img = pil_img.resize((IMG_SIZE, IMG_SIZE))
    img = np.array(img).astype(np.float32) / 255.0
    img = (img - MEAN) / STD
    img = np.transpose(img, (2, 0, 1))  # HWC -> CHW
    img = np.expand_dims(img, axis=0)   # -> NCHW
    return img

# -----------------------------
# PREDICT DISEASE
# -----------------------------
def predict_disease(pil_img: Image.Image):
    input_tensor = preprocess_image(pil_img)
    input_name = session.get_inputs()[0].name

    outputs = session.run(None, {input_name: input_tensor})

    # Expecting [1, num_classes]
    probs = outputs[0][0]
    pred = int(np.argmax(probs))
    confidence = float(probs[pred])

    # labels.json might be {"0":"healthy", ...} OR ["healthy", ...]
    if isinstance(labels, dict):
        disease = labels.get(str(pred), labels.get(pred, str(pred)))
    else:
        disease = labels[pred] if pred < len(labels) else str(pred)

    return disease, confidence

# -----------------------------
# INFECTED AREA % (v1 approximate)
# -----------------------------
def estimate_infected_area_percent(pil_img: Image.Image) -> float:
    img = np.array(pil_img.convert("RGB"))
    bgr = cv2.cvtColor(img, cv2.COLOR_RGB2BGR)
    hsv = cv2.cvtColor(bgr, cv2.COLOR_BGR2HSV)

    # brown-ish + very dark lesions
    mask1 = cv2.inRange(hsv, (0, 40, 20), (30, 255, 180))
    mask2 = cv2.inRange(hsv, (0, 0, 0), (180, 255, 80))
    lesion = cv2.bitwise_or(mask1, mask2)

    kernel = np.ones((5, 5), np.uint8)
    lesion = cv2.morphologyEx(lesion, cv2.MORPH_OPEN, kernel, iterations=1)
    lesion = cv2.morphologyEx(lesion, cv2.MORPH_CLOSE, kernel, iterations=2)

    gray = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)
    leaf_mask = cv2.threshold(gray, 10, 255, cv2.THRESH_BINARY)[1]

    leaf_pixels = int(np.count_nonzero(leaf_mask))
    if leaf_pixels == 0:
        return 0.0

    lesion_pixels = int(np.count_nonzero(cv2.bitwise_and(lesion, lesion, mask=leaf_mask)))
    pct = (lesion_pixels / leaf_pixels) * 100.0
    return float(np.clip(pct, 0.0, 100.0))

def get_stage(pct: float) -> str:
    if pct < 20.0:
        return "Early"
    elif pct <= 50.0:
        return "Intermediate"
    else:
        return "Advanced"

# -----------------------------
# RECOVERY TIME
# -----------------------------
BASE = {"healthy": 0, "leaf_spot": 7, "anthracnose": 10, "bacterial_blight": 14}
SEV = {"Early": 1.0, "Intermediate": 1.5, "Advanced": 2.2}
TREAT = {"good": 0.9, "normal": 1.0, "poor": 1.3}
HUM = {"low": 0.95, "medium": 1.0, "high": 1.2}

def recovery_days(disease: str, stage: str, treatment: str, humidity: str):
    disease = disease.strip().lower()
    treatment = treatment.strip().lower()
    humidity = humidity.strip().lower()

    if disease == "healthy":
        return {"min": 0, "max": 0}

    base = BASE.get(disease, 10)
    sev = SEV.get(stage, 1.5)
    tr = TREAT.get(treatment, 1.0)
    hum = HUM.get(humidity, 1.0)

    days = base * sev * tr * hum
    return {"min": max(1, int(days * 0.85)), "max": max(1, int(days * 1.15))}

# -----------------------------
# SPREAD RISK
# -----------------------------
def spread_risk(disease: str, stage: str, humidity: str):
    disease = disease.strip().lower()
    humidity = humidity.strip().lower()

    d = {"healthy": 0.0, "leaf_spot": 0.5, "anthracnose": 0.6, "bacterial_blight": 0.8}.get(disease, 0.5)
    s = {"Early": 0.2, "Intermediate": 0.5, "Advanced": 0.8}.get(stage, 0.5)
    h = {"low": 0.1, "medium": 0.3, "high": 0.6}.get(humidity, 0.3)

    score = 0.4 * d + 0.4 * s + 0.2 * h

    if score <= 0.3:
        level = "LOW"
    elif score <= 0.6:
        level = "MEDIUM"
    else:
        level = "HIGH"

    return {"level": level, "score": round(float(score), 2)}

# -----------------------------
# ENDPOINTS
# -----------------------------
@app.get("/health")
def health():
    return {
        "status": "ok",
        "model_path": MODEL_PATH,
        "labels_loaded": True,
        "img_size": IMG_SIZE
    }

@app.post("/predict-disease")
async def disease(image: UploadFile = File(...)):
    try:
        img = Image.open(io.BytesIO(await image.read())).convert("RGB")
    except Exception:
        return JSONResponse({"error": "Invalid image file"}, status_code=400)

    d, c = predict_disease(img)
    return {"disease": d, "confidence": round(c, 4)}

@app.post("/stage")
async def stage(image: UploadFile = File(...)):
    try:
        img = Image.open(io.BytesIO(await image.read())).convert("RGB")
    except Exception:
        return JSONResponse({"error": "Invalid image file"}, status_code=400)

    pct = estimate_infected_area_percent(img)
    st = get_stage(pct)
    return {"infected_area_percent": round(pct, 2), "stage": st}

@app.post("/recovery")
async def recovery(
    image: UploadFile = File(...),
    treatment_quality: str = Form("normal"),
    humidity: str = Form("medium")
):
    try:
        img = Image.open(io.BytesIO(await image.read())).convert("RGB")
    except Exception:
        return JSONResponse({"error": "Invalid image file"}, status_code=400)

    d, c = predict_disease(img)
    pct = estimate_infected_area_percent(img)
    st = get_stage(pct)
    rec = recovery_days(d, st, treatment_quality, humidity)

    return {"disease": d, "confidence": round(c, 4), "stage": st, "recovery_days": rec}

@app.post("/risk")
async def risk(
    image: UploadFile = File(...),
    humidity: str = Form("medium")
):
    try:
        img = Image.open(io.BytesIO(await image.read())).convert("RGB")
    except Exception:
        return JSONResponse({"error": "Invalid image file"}, status_code=400)

    d, c = predict_disease(img)
    pct = estimate_infected_area_percent(img)
    st = get_stage(pct)
    r = spread_risk(d, st, humidity)

    return {
        "disease": d,
        "confidence": round(c, 4),
        "infected_area_percent": round(pct, 2),
        "stage": st,
        "spread_risk": r
    }

@app.get("/treatment/{disease}")
def treatment(disease: str):
    disease = disease.strip().lower()
    tips = {
        "healthy": ["Maintain airflow and monitor regularly"],
        "leaf_spot": ["Remove infected leaves", "Avoid overhead watering"],
        "anthracnose": ["Prune infected parts", "Reduce humidity"],
        "bacterial_blight": ["Isolate plant", "Avoid splashing water"]
    }
    return {"disease": disease, "guidance": tips.get(disease, [])}