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

def treatment_tips(disease: str):
    disease = disease.strip().lower()
    tips = {
        "healthy": ["Maintain airflow and monitor regularly"],
        "leaf_spot": ["Remove infected leaves", "Avoid overhead watering"],
        "anthracnose": ["Prune infected parts", "Reduce humidity"],
        "bacterial_blight": ["Isolate plant", "Avoid splashing water"],
    }
    return {"disease": disease, "guidance": tips.get(disease, [])}