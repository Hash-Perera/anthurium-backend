import numpy as np
import cv2
from PIL import Image

def estimate_infected_area_percent(pil_img: Image.Image) -> float:
    img = np.array(pil_img.convert("RGB"))
    bgr = cv2.cvtColor(img, cv2.COLOR_RGB2BGR)
    hsv = cv2.cvtColor(bgr, cv2.COLOR_BGR2HSV)

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
    if pct <= 50.0:
        return "Intermediate"
    return "Advanced"