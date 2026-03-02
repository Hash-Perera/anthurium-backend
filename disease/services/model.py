import numpy as np
from PIL import Image
from core.config import IMG_SIZE, MEAN, STD, session, labels

def preprocess_image(pil_img: Image.Image) -> np.ndarray:
    img = pil_img.resize((IMG_SIZE, IMG_SIZE))
    img = np.array(img).astype(np.float32) / 255.0
    img = (img - MEAN) / STD
    img = np.transpose(img, (2, 0, 1))  # HWC -> CHW
    img = np.expand_dims(img, axis=0)   # NCHW
    return img

def predict_disease(pil_img: Image.Image):
    input_tensor = preprocess_image(pil_img)
    input_name = session.get_inputs()[0].name
    outputs = session.run(None, {input_name: input_tensor})

    probs = outputs[0][0]
    pred = int(np.argmax(probs))
    confidence = float(probs[pred])

    if isinstance(labels, dict):
        disease = labels.get(str(pred), labels.get(pred, str(pred)))
    else:
        disease = labels[pred] if pred < len(labels) else str(pred)

    return disease, confidence