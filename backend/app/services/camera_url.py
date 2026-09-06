import ipaddress
import os
from urllib.parse import urlsplit


ALLOWED_STREAM_SCHEMES = {"rtsp", "http", "https"}


def validate_stream_url(value: str | None) -> str | None:
    """Validate a camera stream URL without opening it."""
    if value is None or not value.strip():
        return None
    value = value.strip()
    if len(value) > 500 or any(ord(char) < 32 for char in value):
        raise ValueError("Invalid stream URL")
    parsed = urlsplit(value)
    if parsed.scheme.lower() not in ALLOWED_STREAM_SCHEMES:
        raise ValueError("Invalid stream URL scheme. Use rtsp://, http://, or https://")
    if not parsed.hostname:
        raise ValueError("Stream URL must include a host")
    hostname = parsed.hostname.casefold().rstrip(".")
    allow_loopback = os.getenv("CAMERA_HEALTH_ALLOW_LOOPBACK", "false").lower() == "true"
    if (hostname == "localhost" or hostname.endswith(".localhost") or hostname.isdigit()
            or hostname.startswith("0x")) and not allow_loopback:
        raise ValueError("Loopback stream URLs are disabled")
    try:
        address = ipaddress.ip_address(parsed.hostname.strip("[]"))
    except ValueError:
        address = None
    if address and (address.is_unspecified or address.is_multicast or address.is_link_local):
        raise ValueError("Stream URL host is not permitted")
    if address and address.is_loopback and not allow_loopback:
        raise ValueError("Loopback stream URLs are disabled")
    return value


def normalized_capture_url(value: str) -> str:
    if value.endswith(":8080") or value.endswith(":8080/"):
        return value.rstrip("/") + "/video"
    return value
