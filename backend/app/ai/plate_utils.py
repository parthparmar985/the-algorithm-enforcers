import re


STANDARD_INDIAN_PLATE = re.compile(r"^[A-Z]{2}[0-9]{1,2}[A-Z]{1,3}[0-9]{1,4}$")
BHARAT_SERIES_PLATE = re.compile(r"^[0-9]{2}BH[0-9]{4}[A-Z]{1,2}$")
INDIAN_STATE_CODES = {
    "AN", "AP", "AR", "AS", "BR", "CG", "CH", "DD", "DL", "DN", "GA", "GJ", "HP", "HR",
    "JH", "JK", "KA", "KL", "LA", "LD", "MH", "ML", "MN", "MP", "MZ", "NL", "OD", "OR",
    "PB", "PY", "RJ", "SK", "TN", "TR", "TS", "UK", "UP", "WB",
}


def normalize_plate(value: str | None) -> str | None:
    """Remove spacing/punctuation while preserving every recognized character."""
    if not value:
        return None
    normalized = re.sub(r"[^A-Z0-9]", "", value.upper())
    return normalized or None


def is_valid_indian_plate(value: str | None) -> bool:
    normalized = normalize_plate(value)
    return bool(normalized and ((normalized[:2] in INDIAN_STATE_CODES and STANDARD_INDIAN_PLATE.fullmatch(normalized)) or BHARAT_SERIES_PLATE.fullmatch(normalized)))


def normalize_ocr_plate(value: str | None, confidence: float) -> str | None:
    """Apply position-aware ambiguity fixes only to a high-confidence, common 10-character format."""
    normalized = normalize_plate(value)
    if not normalized or confidence < 0.80 or len(normalized) != 10:
        return normalized
    characters = list(normalized)
    numeric_positions = (2, 3, 6, 7, 8, 9)
    numeric_ambiguities = {"O": "0", "Q": "0", "D": "0", "I": "1", "L": "1"}
    for position in numeric_positions:
        characters[position] = numeric_ambiguities.get(characters[position], characters[position])
    return "".join(characters)


def plates_match(left: str | None, right: str | None) -> bool:
    return normalize_plate(left) == normalize_plate(right) if left and right else False
