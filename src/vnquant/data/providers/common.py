from __future__ import annotations

from collections.abc import Mapping
from datetime import date
from enum import Enum
import json
from typing import Any

import pandas as pd

from ..base import CANONICAL_COLUMNS


class ProviderConfigurationError(RuntimeError):
    """Raised before I/O when an authorized provider contract is unavailable."""


class DataProviderErrorCode(str, Enum):
    """Stable failure taxonomy exposed by the provider/data boundary."""

    HTTP_ERROR = "DATA_PROVIDER_HTTP_ERROR"
    HTML_RESPONSE = "DATA_PROVIDER_HTML_RESPONSE"
    INVALID_JSON = "DATA_PROVIDER_INVALID_JSON"
    SCHEMA_ERROR = "DATA_PROVIDER_SCHEMA_ERROR"
    DATA_STALE = "DATA_STALE"
    SOURCE_MISMATCH = "DATA_SOURCE_MISMATCH"
    DATA_UNAVAILABLE = "DATA_UNAVAILABLE"


class ProviderResponseError(RuntimeError):
    """Raised when a remote response cannot be mapped without guessing."""

    def __init__(
        self,
        message: str,
        *,
        code: DataProviderErrorCode = DataProviderErrorCode.SCHEMA_ERROR,
        provider_id: str | None = None,
        status_code: int | None = None,
    ) -> None:
        self.code = code
        self.provider_id = provider_id
        self.status_code = status_code
        super().__init__(f"{code.value}: {message}")


def _response_body_text(response: Any) -> str | None:
    """Read a response body without invoking JSON parsing."""
    content = getattr(response, "content", None)
    if isinstance(content, bytes):
        return content.decode("utf-8", errors="replace")
    if isinstance(content, str):
        return content
    text = getattr(response, "text", None)
    return text if isinstance(text, str) else None


def _content_type(response: Any) -> str | None:
    headers = getattr(response, "headers", None)
    if not isinstance(headers, Mapping):
        return None
    value = headers.get("Content-Type") or headers.get("content-type")
    return str(value).lower() if value is not None else None


def _looks_like_html(body: str | None) -> bool:
    if body is None:
        return False
    prefix = body.lstrip().lower()[:256]
    return (
        prefix.startswith("<!doctype html")
        or prefix.startswith("<html")
        or "<html" in prefix
        or "<head" in prefix
    )


def decode_provider_json_response(response: Any, *, provider_id: str) -> Any:
    """Decode a provider response without ever blindly assuming JSON.

    SDK/test doubles may return already-decoded mappings/lists. HTTP-like
    responses are validated in fail-safe order: status, content type/body,
    then JSON parsing. The helper deliberately does not perform provider-
    specific schema validation; adapters do that after decoding.
    """
    if isinstance(response, (Mapping, list)):
        return response

    if isinstance(response, (bytes, bytearray, str)):
        body = response.decode("utf-8", errors="replace") if isinstance(response, (bytes, bytearray)) else response
        if _looks_like_html(body):
            raise ProviderResponseError(
                "provider returned HTML instead of market-data JSON",
                code=DataProviderErrorCode.HTML_RESPONSE,
                provider_id=provider_id,
            )
        try:
            return json.loads(body)
        except (TypeError, ValueError, json.JSONDecodeError) as exc:
            raise ProviderResponseError(
                "provider response body is not valid JSON",
                code=DataProviderErrorCode.INVALID_JSON,
                provider_id=provider_id,
            ) from exc

    status = getattr(response, "status_code", None)
    if status is not None:
        try:
            status_int = int(status)
        except (TypeError, ValueError):
            status_int = None
        if status_int is not None and not 200 <= status_int < 300:
            raise ProviderResponseError(
                f"provider returned HTTP {status_int}",
                code=DataProviderErrorCode.HTTP_ERROR,
                provider_id=provider_id,
                status_code=status_int,
            )

    body = _response_body_text(response)
    content_type = _content_type(response)
    if _looks_like_html(body) or (content_type and "text/html" in content_type):
        raise ProviderResponseError(
            "provider returned HTML instead of market-data JSON",
            code=DataProviderErrorCode.HTML_RESPONSE,
            provider_id=provider_id,
            status_code=int(status) if str(status).isdigit() else None,
        )

    if content_type and "json" not in content_type:
        raise ProviderResponseError(
            f"provider response Content-Type is not JSON ({content_type.split(';', 1)[0]})",
            code=DataProviderErrorCode.INVALID_JSON,
            provider_id=provider_id,
            status_code=int(status) if str(status).isdigit() else None,
        )

    if body is not None:
        try:
            return json.loads(body)
        except (TypeError, ValueError, json.JSONDecodeError) as exc:
            raise ProviderResponseError(
                "provider response body is not valid JSON",
                code=DataProviderErrorCode.INVALID_JSON,
                provider_id=provider_id,
                status_code=int(status) if str(status).isdigit() else None,
            ) from exc

    json_method = getattr(response, "json", None)
    if callable(json_method):
        try:
            return json_method()
        except Exception as exc:
            raise ProviderResponseError(
                "provider JSON decoder rejected the response",
                code=DataProviderErrorCode.INVALID_JSON,
                provider_id=provider_id,
                status_code=int(status) if str(status).isdigit() else None,
            ) from exc

    raise ProviderResponseError(
        "provider response exposes neither decoded data nor a JSON body",
        code=DataProviderErrorCode.INVALID_JSON,
        provider_id=provider_id,
    )


def canonical_frame(
    records: list[Mapping[str, Any]],
    *,
    field_map: Mapping[str, str],
    provider_id: str,
    price_multiplier: float,
) -> pd.DataFrame:
    """Map explicitly named provider fields into the existing canonical frame."""
    required = {"trading_date", "open", "high", "low", "close", "volume"}
    missing_mapping = required.difference(field_map)
    if missing_mapping:
        raise ProviderConfigurationError(
            f"field mapping is incomplete: {sorted(missing_mapping)}"
        )

    rows: list[dict[str, Any]] = []
    for record in records:
        try:
            row = {
                canonical: record[provider_field]
                for canonical, provider_field in field_map.items()
                if canonical in set(CANONICAL_COLUMNS) - {"provider"}
            }
        except KeyError as exc:
            raise ProviderResponseError(
                f"mapped response field is absent: {exc.args[0]}",
                code=DataProviderErrorCode.SCHEMA_ERROR,
                provider_id=provider_id,
            ) from exc
        row["provider"] = provider_id
        rows.append(row)

    frame = pd.DataFrame(rows)
    if frame.empty:
        return pd.DataFrame(columns=CANONICAL_COLUMNS)
    if "symbol" not in frame:
        raise ProviderResponseError(
            "response has no mapped symbol field",
            code=DataProviderErrorCode.SCHEMA_ERROR,
            provider_id=provider_id,
        )
    try:
        frame["trading_date"] = pd.to_datetime(frame["trading_date"], errors="raise").dt.date
        for column in ("open", "high", "low", "close"):
            frame[column] = pd.to_numeric(frame[column], errors="raise") * price_multiplier
        frame["volume"] = pd.to_numeric(frame["volume"], errors="raise")
        if "value" not in frame:
            frame["value"] = pd.NA
        else:
            frame["value"] = pd.to_numeric(frame["value"], errors="raise")
    except (TypeError, ValueError) as exc:
        raise ProviderResponseError(
            "provider OHLCV fields cannot be normalized to the canonical schema",
            code=DataProviderErrorCode.SCHEMA_ERROR,
            provider_id=provider_id,
        ) from exc
    return frame[CANONICAL_COLUMNS]


def unix_seconds(value: date) -> int:
    return int(pd.Timestamp(value, tz="UTC").timestamp())
