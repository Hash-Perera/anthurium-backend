import json
import os

from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

# Lazy initialization to avoid startup errors if API key is missing
_client = None


def get_client():
    """Get or create OpenAI client"""
    global _client
    if _client is None:
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("OPENAI_API_KEY environment variable is not set")
        _client = OpenAI(api_key=api_key)
    return _client


def build_anthurium_prompt(current: dict, required: dict, flower_name: str) -> str:
    current_json = json.dumps(current, indent=2, sort_keys=True)
    required_json = json.dumps(required, indent=2, sort_keys=True)

    return (
    f"You are a senior tropical plant agronomist specializing in commercial {flower_name} cultivation. "
    "Your task is to analytically compare the current soil and environmental conditions "
    f"with the required optimal target conditions for {flower_name} growth.\n\n"

    "You must:\n"
    "• Detect only meaningful deviations (ignore small variations within tolerance).\n"
    "• Use tolerance ranges:\n"
    "   - soilMoisture ±5\n"
    "   - humidity ±5\n"
    "   - temperature ±2\n"
    "   - nutrients ±5\n\n"

    "For each deviation:\n"
    "1. Clearly explain the agronomic issue.\n"
    f"2. Explain the potential physiological impact on {flower_name} "
    "(e.g., root rot, leaf yellowing, slow flowering, nutrient lockout).\n"
    "3. Provide precise, practical corrective actions suitable for growers.\n"
    "   - If moisture is low → explain irrigation method (deep watering, frequency).\n"
    "   - If moisture is high → explain drainage correction and root protection.\n"
    "   - If nutrients are low → suggest balanced fertilizer type and application method.\n"
    "   - If temperature is high → suggest shading or cooling strategies.\n"
    "   - If humidity is low → suggest misting or humidifier strategies.\n"
    "Be concise but technically accurate.\n\n"

    "If all values are within acceptable tolerance, return empty arrays.\n\n"

    "Return JSON with this exact structure:\n"
    "{\n"
    "  \"issues\": [\"string\", ...],\n"
    "  \"recommendations\": [\"string\", ...]\n"
    "}\n\n"

    "Current soil conditions:\n"
    f"{current_json}\n\n"
    "Required soil conditions:\n"
    f"{required_json}\n"
)



def generate_anthurium_recommendations(current: dict, required: dict, flower_name: str = "Anthurium") -> dict:
    client = get_client()
    prompt = build_anthurium_prompt(current, required, flower_name)

    response = client.chat.completions.create(
        model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
        messages=[
            {"role": "system", "content": "Return only valid JSON."},
            {"role": "user", "content": prompt},
        ],
        temperature=0.2,
        response_format={"type": "json_object"},
    )

    text = (response.choices[0].message.content or "").strip()
    if not text:
        raise ValueError("Model response was empty")
    try:
        return json.loads(text)
    except json.JSONDecodeError as exc:
        raise ValueError("Model response was not valid JSON") from exc

def calculate_suitability_score(current: dict, required: dict) -> dict:
    """
    Calculate suitability score (0-100)
    """
    comparison_fields = ["soilMoisture", "humidity", "temperature", "nitrogen", "phosphorus", "potassium"]
    tolerance = {
        "soilMoisture": 5,
        "humidity": 5,
        "temperature": 2,
        "nitrogen": 5,
        "phosphorus": 5,
        "potassium": 5,
    }
    
    within_tolerance_count = 0
    
    for field in comparison_fields:
        if field in current and field in required:
            current_val = current[field]
            required_val = required[field]
            field_tolerance = tolerance.get(field, 5)
            is_within_tolerance = abs(current_val - required_val) <= field_tolerance
            
            if is_within_tolerance:
                within_tolerance_count += 1
    
    # Calculate overall suitability score (0-100)
    base_score = (within_tolerance_count / len(comparison_fields)) * 100
    suitability_score = max(0, min(100, round(base_score)))
    
    return suitability_score


def generate_suitability_and_deviations(current: dict, required: dict, flower_name: str) -> dict:
    """
    Use LLM to generate suitability score explanation and deviations with percentages
    """
    # First calculate the score
    score = calculate_suitability_score(current, required)
    
    # Calculate deviations for each field
    comparison_fields = ["soilMoisture", "humidity", "temperature", "nitrogen", "phosphorus", "potassium"]
    tolerance = {
        "soilMoisture": 5,
        "humidity": 5,
        "temperature": 2,
        "nitrogen": 5,
        "phosphorus": 5,
        "potassium": 5,
    }
    
    deviations_data = []
    
    for field in comparison_fields:
        if field in current and field in required:
            current_val = current[field]
            required_val = required[field]
            
            # Calculate percentage deviation
            if required_val != 0:
                deviation_percent = ((current_val - required_val) / required_val) * 100
            else:
                deviation_percent = 0
            
            field_tolerance = tolerance.get(field, 5)
            is_within_tolerance = abs(current_val - required_val) <= field_tolerance
            
            deviations_data.append({
                "field": field,
                "current": current_val,
                "required": required_val,
                "deviation_percent": round(deviation_percent, 1),
                "is_within_tolerance": is_within_tolerance
            })
    
    # Build prompt for LLM to generate sentences
    deviations_json = json.dumps(deviations_data, indent=2)
    
    prompt = (
        f"You are a senior tropical plant agronomist specializing in {flower_name} cultivation.\n\n"
        f"Based on the deviations data, generate simple sentences for each parameter showing the deviation percentage.\n\n"
        f"Deviation data:\n{deviations_json}\n\n"
        "Return JSON with this exact structure:\n"
        "{\n"
        '  "suitability_score_explanation": "string explaining the overall score and status",\n'
        '  "deviations": [\n'
        '    "Field Name deviation: +56.5% (current: X, required: Y)",\n'
        '    "Another Field deviation: -5.6% (current: X, required: Y)"\n'
        "  ]\n"
        "}\n\n"
        "Format: Use + for positive deviations, - for negative. Include current and required values in parentheses.\n"
        "If deviation is within tolerance, mention it's acceptable."
    )
    
    client = get_client()
    response = client.chat.completions.create(
        model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
        messages=[
            {"role": "system", "content": "Return only valid JSON."},
            {"role": "user", "content": prompt},
        ],
        temperature=0.2,
        response_format={"type": "json_object"},
    )
    
    text = (response.choices[0].message.content or "").strip()
    if not text:
        raise ValueError("Model response was empty")
    try:
        result = json.loads(text)
        return {
            "suitability_score": score,
            "deviations": result.get("deviations", [])
        }
    except json.JSONDecodeError as exc:
        raise ValueError("Model response was not valid JSON") from exc


def get_required_conditions(flower_name: str) -> dict:
    
    conditions = {
        "flamingo flower": {
            "soilMoisture": 75.2,
            "humidity": 70,
            "temperature": 28,
            "nitrogen": 50,
            "phosphorus": 30,
            "potassium": 65,
        },
        "pigtail flower": {
            "soilMoisture": 60.5,
            "humidity": 65,
            "temperature": 26,
            "nitrogen": 45,
            "phosphorus": 28,
            "potassium": 60,
        },
        "black velvet": {
            "soilMoisture": 55.0,
            "humidity": 68,
            "temperature": 27,
            "nitrogen": 52,
            "phosphorus": 25,
            "potassium": 62,
        },
        "purple heart": {
            "soilMoisture": 80.2,
            "humidity": 75,
            "temperature": 29,
            "nitrogen": 55,
            "phosphorus": 32,
            "potassium": 70,
        },
        "crystal anthurium": {
            "soilMoisture": 65.0,
            "humidity": 60,
            "temperature": 24,
            "nitrogen": 47,
            "phosphorus": 28,
            "potassium": 63,
        },
       
    }
    
    flower_key = flower_name.lower().strip()
    if flower_key in conditions:
        return conditions[flower_key]
    else:
        raise ValueError(f"Unknown flower variety: {flower_name}. Supported: {', '.join(conditions.keys())}")