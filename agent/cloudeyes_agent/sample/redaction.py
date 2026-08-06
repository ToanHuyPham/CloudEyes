"""Privacy guard for JSON evidence included in submission bundles."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any
from urllib.parse import urlsplit, urlunsplit

_SENSITIVE_KEYS = {
    "accesskey",
    "apikey",
    "authorization",
    "clientsecret",
    "cookie",
    "credential",
    "credentials",
    "password",
    "passwd",
    "privatekey",
    "proxyauthorization",
    "secret",
    "setcookie",
    "token",
}
_REDACTED = "[REDACTED]"


@dataclass(frozen=True, slots=True)
class RedactionResult:
    """Redacted JSON-compatible value and number of changed fields."""

    value: Any
    redaction_count: int


def _normalized_key(value: str) -> str:
    return "".join(character for character in value.casefold() if character.isalnum())


def _sanitize_url(value: str) -> tuple[str, int]:
    if not value.casefold().startswith(("http://", "https://")):
        return value, 0
    try:
        parsed = urlsplit(value)
        if not parsed.hostname:
            return value, 0
        port = f":{parsed.port}" if parsed.port is not None else ""
        hostname = parsed.hostname
        if ":" in hostname and not hostname.startswith("["):
            hostname = f"[{hostname}]"
        sanitized = urlunsplit((parsed.scheme, f"{hostname}{port}", parsed.path, "", ""))
    except (ValueError, UnicodeError):
        return value, 0
    return sanitized, int(sanitized != value)


def redact_json(value: Any) -> RedactionResult:
    """Redact credential-like fields and URL user/query/fragment components."""

    if isinstance(value, dict):
        output: dict[str, Any] = {}
        count = 0
        for raw_key, item in value.items():
            key = str(raw_key)
            if _normalized_key(key) in _SENSITIVE_KEYS:
                output[key] = _REDACTED
                count += 1
                continue
            result = redact_json(item)
            output[key] = result.value
            count += result.redaction_count
        return RedactionResult(output, count)
    if isinstance(value, list):
        output_items: list[Any] = []
        count = 0
        for item in value:
            result = redact_json(item)
            output_items.append(result.value)
            count += result.redaction_count
        return RedactionResult(output_items, count)
    if isinstance(value, str):
        sanitized, count = _sanitize_url(value)
        return RedactionResult(sanitized, count)
    return RedactionResult(value, 0)


__all__ = ["RedactionResult", "redact_json"]
