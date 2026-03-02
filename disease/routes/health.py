from fastapi import APIRouter
from core.config import MODEL_PATH, IMG_SIZE

router = APIRouter(tags=["health"])

@router.get("/health")
def health():
    return {
        "status": "ok",
        "model_path": MODEL_PATH,
        "labels_loaded": True,
        "img_size": IMG_SIZE,
    }