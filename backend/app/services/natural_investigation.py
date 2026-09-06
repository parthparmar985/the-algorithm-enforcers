import re
import unicodedata
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta, timezone
from ..ai.plate_utils import is_valid_indian_plate, normalize_plate


# India has used UTC+05:30 without daylight-saving transitions since 1945.
# A fixed offset avoids requiring the optional tzdata package on Windows.
INDIA_TZ = timezone(timedelta(hours=5, minutes=30), name="Asia/Kolkata")
VEHICLE_TYPES = {
    "car": "car", "cars": "car", "sedan": "car", "sedans": "car",
    "motorcycle": "motorcycle", "motorcycles": "motorcycle", "motorbike": "motorcycle", "motorbikes": "motorcycle",
    "bus": "bus", "buses": "bus", "truck": "truck", "trucks": "truck",
}
MONTHS = {name.lower(): number for number, name in enumerate(
    ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"], 1)}
MONTHS.update({name[:3]: number for name, number in list(MONTHS.items())})
GENERIC_WORDS = {"find", "show", "vehicle", "vehicles", "detected", "seen", "at", "in", "on", "by", "between", "and", "the", "a", "an", "during", "from", "to", "near", "around", "please", "me", "all"}


@dataclass
class ParseResult:
    status: str
    filters: dict
    confidence: dict
    unparsed_terms: list[str]
    warnings: list[str]
    interpretation: str
    matches: list[dict]


def clean_query(value: str) -> str:
    normalized = unicodedata.normalize("NFKC", value)
    return re.sub(r"[\x00-\x1f\x7f]", " ", normalized).strip()


def local_to_utc(value: datetime) -> datetime:
    return value.astimezone(timezone.utc).replace(tzinfo=None)


def parse_clock(value: str) -> time:
    match = re.fullmatch(r"\s*(\d{1,2})(?::(\d{2}))?\s*(am|pm)?\s*", value, re.I)
    if not match:
        raise ValueError(f"Invalid time: {value}")
    hour, minute = int(match.group(1)), int(match.group(2) or 0)
    meridiem = (match.group(3) or "").lower()
    if minute > 59 or (meridiem and not 1 <= hour <= 12) or (not meridiem and hour > 23):
        raise ValueError(f"Invalid time: {value}")
    if meridiem == "pm" and hour != 12:
        hour += 12
    if meridiem == "am" and hour == 12:
        hour = 0
    return time(hour, minute)


def date_context(query: str, now: datetime):
    lower = query.lower()
    if "yesterday" in lower:
        return now.date() - timedelta(days=1), "yesterday"
    if "today" in lower:
        return now.date(), "today"
    iso = re.search(r"\b(20\d{2})-(\d{1,2})-(\d{1,2})\b", lower)
    if iso:
        return date(int(iso.group(1)), int(iso.group(2)), int(iso.group(3))), iso.group(0)
    for pattern in (
        r"\b(\d{1,2})\s+([a-z]{3,9})(?:,?\s+(20\d{2}))?\b",
        r"\b([a-z]{3,9})\s+(\d{1,2})(?:,?\s+(20\d{2}))?\b",
    ):
        for named in re.finditer(pattern, lower):
            day_first = named.group(1).isdigit()
            day = int(named.group(1) if day_first else named.group(2))
            month_name = (named.group(2) if day_first else named.group(1)).lower()
            if month_name in MONTHS:
                return date(int(named.group(3) or now.year), MONTHS[month_name], day), named.group(0)
    return now.date(), None


def parse_time_range(query: str, now: datetime):
    lower = query.lower()
    day, date_phrase = date_context(lower, now)
    day_start = datetime.combine(day, time.min, INDIA_TZ)
    day_end = datetime.combine(day, time.max, INDIA_TZ)
    consumed = [date_phrase] if date_phrase else []

    iso_clock = r"20\d{2}-\d{1,2}-\d{1,2}[T ]\d{1,2}:\d{2}(?::\d{2})?(?:Z|[+-]\d{2}:?\d{2})?"
    explicit = re.search(rf"\b(?:from|between)\s+({iso_clock})\s+(?:to|and)\s+({iso_clock})", query, re.I)
    if explicit:
        def parse_iso(value):
            parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
            return parsed.replace(tzinfo=INDIA_TZ) if parsed.tzinfo is None else parsed
        start, end = parse_iso(explicit.group(1)), parse_iso(explicit.group(2))
        if end <= start:
            raise ValueError("Start time must be before end time")
        return local_to_utc(start), local_to_utc(end), [explicit.group(0)], "explicit date/time range"

    relative = re.search(r"\blast\s+(?:(\d+)\s+)?(hour|hours|minute|minutes)\b", lower)
    if relative:
        amount = int(relative.group(1) or 1)
        if amount <= 0 or amount > 24 * 31 * 60:
            raise ValueError("Relative time amount is outside the supported range")
        delta = timedelta(hours=amount) if relative.group(2).startswith("hour") else timedelta(minutes=amount)
        return local_to_utc(now - delta), local_to_utc(now), [relative.group(0)], f"last {amount} {relative.group(2)}"

    periods = {"this morning": (time(6), time(12)), "this afternoon": (time(12), time(17)), "this evening": (time(17), time(23, 59, 59))}
    for phrase, (start_clock, end_clock) in periods.items():
        if phrase in lower:
            return local_to_utc(datetime.combine(day, start_clock, INDIA_TZ)), local_to_utc(datetime.combine(day, end_clock, INDIA_TZ)), [phrase] + consumed, phrase

    clock = r"\d{1,2}(?::\d{2})?\s*(?:am|pm)?"
    between = re.search(rf"\bbetween\s+({clock})\s+and\s+({clock})\b", lower, re.I)
    if between:
        start = datetime.combine(day, parse_clock(between.group(1)), INDIA_TZ)
        end = datetime.combine(day, parse_clock(between.group(2)), INDIA_TZ)
        if end <= start:
            end += timedelta(days=1)
        return local_to_utc(start), local_to_utc(end), [between.group(0)] + consumed, f"{between.group(1).upper()} to {between.group(2).upper()} India time"

    after = re.search(rf"\bafter\s+({clock})\b", lower, re.I)
    if after:
        start = datetime.combine(day, parse_clock(after.group(1)), INDIA_TZ)
        if not date_phrase and start > now:
            start -= timedelta(days=1)
        end = min(day_end, now) if start.date() == now.date() else day_end
        return local_to_utc(start), local_to_utc(end), [after.group(0)] + consumed, f"after {after.group(1).upper()} India time"

    before = re.search(rf"\bbefore\s+({clock})\b", lower, re.I)
    if before:
        end = datetime.combine(day, parse_clock(before.group(1)), INDIA_TZ)
        return local_to_utc(day_start), local_to_utc(end), [before.group(0)] + consumed, f"before {before.group(1).upper()} India time"

    if date_phrase:
        end = min(day_end, now) if day == now.date() else day_end
        return local_to_utc(day_start), local_to_utc(end), consumed, date_phrase
    return None, None, [], None


def camera_resolution(query: str, cameras):
    lower = query.casefold()
    exact = []
    camera_ref = re.search(r"\bcamera\s*[-#:]?\s*(\d+)\b", lower)
    code_ref = re.search(r"\bcam\s*-?\s*0*(\d+)\b", lower)
    number = int((camera_ref or code_ref).group(1)) if (camera_ref or code_ref) else None
    if number is not None:
        exact = [camera for camera in cameras if camera.id == number or re.search(rf"0*{number}$", camera.camera_code or "", re.I)]
    code_matches = [camera for camera in cameras if camera.camera_code and camera.camera_code.casefold() in lower]
    name_matches = [camera for camera in cameras if camera.camera_name and camera.camera_name.casefold() in lower]
    location_matches = [camera for camera in cameras if camera.location and camera.location.casefold() in lower]
    candidates = {camera.id: camera for camera in exact + code_matches + name_matches + location_matches}
    matches = list(candidates.values())
    if len(matches) > 1:
        return None, None, matches, []
    if not matches:
        return None, None, [], []
    camera = matches[0]
    phrases = [phrase for phrase in [camera.camera_code, camera.camera_name, camera.location, camera_ref.group(0) if camera_ref else None, code_ref.group(0) if code_ref else None] if phrase and phrase.casefold() in lower]
    matched_location = camera.location if camera.location and camera.location.casefold() in lower else None
    return camera, matched_location, [], phrases


def parse_natural_query(query: str, cameras, now: datetime | None = None) -> ParseResult:
    query = clean_query(query)
    now = now.astimezone(INDIA_TZ) if now else datetime.now(INDIA_TZ)
    filters = {"registration_number": None, "vehicle_type": None, "camera_id": None, "camera_name": None,
               "location": None, "start_time": None, "end_time": None}
    confidence, warnings, consumed = {}, [], []

    plate_pattern = re.compile(r"\b(?:[A-Z]{2}[\s-]*\d{1,2}[\s-]*[A-Z]{1,3}[\s-]*\d{1,4}|\d{2}[\s-]*BH[\s-]*\d{4}[\s-]*[A-Z]{1,2})\b", re.I)
    for match in plate_pattern.finditer(query):
        candidate = normalize_plate(match.group(0))
        if is_valid_indian_plate(candidate):
            filters["registration_number"] = candidate
            confidence["registration_number"] = 1.0
            consumed.append(match.group(0))
            break

    words = re.findall(r"\b[A-Za-z]+\b", query)
    for word in words:
        mapped = VEHICLE_TYPES.get(word.casefold())
        if mapped:
            filters["vehicle_type"] = mapped
            confidence["vehicle_type"] = 0.95 if word.casefold() == mapped else 0.85
            consumed.append(word)
            break

    camera, location, ambiguous, camera_phrases = camera_resolution(query, cameras)
    if ambiguous:
        return ParseResult("AMBIGUOUS", filters, confidence, [], ["Multiple cameras match this reference."],
                           "Camera reference is ambiguous; select a camera explicitly.",
                           [{"id": item.id, "camera_code": item.camera_code, "camera_name": item.camera_name, "location": item.location} for item in ambiguous])
    if camera:
        filters["camera_id"] = camera.id
        filters["camera_name"] = camera.camera_name
        confidence["camera_id"] = 1.0
        consumed.extend(camera_phrases)
    if location:
        filters["location"] = location
        confidence["location"] = 1.0

    start, end, time_phrases, time_description = parse_time_range(query, now)
    if start:
        filters["start_time"], filters["end_time"] = start, end
        confidence["time_range"] = 0.95
        consumed.extend(time_phrases)

    residual = query
    for phrase in sorted(set(consumed), key=len, reverse=True):
        residual = re.sub(re.escape(phrase), " ", residual, flags=re.I)
    tokens = re.findall(r"[A-Za-z0-9_$.;='()-]+", residual)
    unparsed = [token for token in tokens if token.casefold() not in GENERIC_WORDS]
    if unparsed:
        warnings.append("Some terms are unsupported and were not used as filters: " + ", ".join(unparsed))

    parts = []
    if filters["registration_number"]:
        parts.append(f"Plate {filters['registration_number']}")
    if filters["vehicle_type"]:
        parts.append(f"Vehicle type {filters['vehicle_type']}")
    if filters["camera_id"]:
        parts.append(f"Camera {filters['camera_name']} (ID {filters['camera_id']})")
    if filters["location"]:
        parts.append(f"Location {filters['location']}")
    if time_description:
        parts.append(f"Time {time_description}; interpreted in Asia/Kolkata and converted to UTC")
    status = "PARSED" if any(value is not None for key, value in filters.items() if key != "camera_name") else "UNSUPPORTED"
    if status == "UNSUPPORTED":
        warnings.append("No supported investigation filters were found.")
    return ParseResult(status, filters, confidence, unparsed, warnings, "; ".join(parts) if parts else "No supported filters interpreted.", [])
