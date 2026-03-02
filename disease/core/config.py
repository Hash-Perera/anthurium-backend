import os
import json
import numpy as np
import onnxruntime as ort

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_DIR = os.path.dirname(BASE_DIR)
ARTIFACTS_DIR = os.path.join(PROJECT_DIR, "artifacts")

MODEL_PATH = os.path.join(ARTIFACTS_DIR, "leafguard_classifier.onnx")
LABELS_PATH = os.path.join(ARTIFACTS_DIR, "labels.json")
PREPROCESS_PATH = os.path.join(ARTIFACTS_DIR, "preprocess.json")

def _load_json(path: str):
    if not os.path.exists(path):
        raise FileNotFoundError(f"File not found: {path}")
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

labels = _load_json(LABELS_PATH)
preprocess_cfg = _load_json(PREPROCESS_PATH)

IMG_SIZE = int(preprocess_cfg["img_size"])
MEAN = np.array(preprocess_cfg["normalize_mean"], dtype=np.float32).reshape(1, 1, 3)
STD = np.array(preprocess_cfg["normalize_std"], dtype=np.float32).reshape(1, 1, 3)

if not os.path.exists(MODEL_PATH):
    raise FileNotFoundError(f"Model not found: {MODEL_PATH}")

session = ort.InferenceSession(MODEL_PATH, providers=["CPUExecutionProvider"])