"""Domain errors and exit-code mapping."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import IntEnum
from typing import Any

try:  # pragma: no cover - exercised in plain-script bootstrap paths
    from garminconnect import (
        GarminConnectAuthenticationError,
        GarminConnectConnectionError,
        GarminConnectTooManyRequestsError,
    )
except ModuleNotFoundError:  # pragma: no cover - used when only helper scripts are run
    class GarminConnectAuthenticationError(Exception):
        pass

    class GarminConnectConnectionError(Exception):
        pass

    class GarminConnectTooManyRequestsError(Exception):
        pass


class ExitCode(IntEnum):
    """Stable process exit codes."""

    SUCCESS = 0
    GENERAL_ERROR = 1
    USAGE_ERROR = 2
    AUTH_ERROR = 3
    NOT_FOUND = 4
    RATE_LIMITED = 5


@dataclass(slots=True)
class GarminCliError(Exception):
    """A structured application error."""

    code: str
    message: str
    exit_code: int = int(ExitCode.GENERAL_ERROR)
    metadata: dict[str, Any] = field(default_factory=dict)

    def __str__(self) -> str:
        return self.message


def usage_error(message: str, **metadata: Any) -> GarminCliError:
    return GarminCliError(
        code="USAGE_ERROR",
        message=message,
        exit_code=int(ExitCode.USAGE_ERROR),
        metadata=metadata,
    )


def auth_error(message: str, **metadata: Any) -> GarminCliError:
    return GarminCliError(
        code="AUTH_ERROR",
        message=message,
        exit_code=int(ExitCode.AUTH_ERROR),
        metadata=metadata,
    )


def not_found_error(message: str, **metadata: Any) -> GarminCliError:
    return GarminCliError(
        code="NOT_FOUND",
        message=message,
        exit_code=int(ExitCode.NOT_FOUND),
        metadata=metadata,
    )


def rate_limited_error(message: str, **metadata: Any) -> GarminCliError:
    return GarminCliError(
        code="RATE_LIMITED",
        message=message,
        exit_code=int(ExitCode.RATE_LIMITED),
        metadata=metadata,
    )


def general_error(message: str, **metadata: Any) -> GarminCliError:
    return GarminCliError(
        code="GENERAL_ERROR",
        message=message,
        exit_code=int(ExitCode.GENERAL_ERROR),
        metadata=metadata,
    )


def _extract_http_status(exc: BaseException | None) -> int | None:
    current = exc
    while current is not None:
        response = getattr(current, "response", None)
        status = getattr(response, "status_code", None)
        if isinstance(status, int):
            return status
        wrapped = getattr(current, "error", None)
        wrapped_response = getattr(wrapped, "response", None)
        status = getattr(wrapped_response, "status_code", None)
        if isinstance(status, int):
            return status
        current = current.__cause__
    return None


def map_exception(exc: Exception) -> GarminCliError:
    """Translate library and runtime errors into stable CLI errors."""

    if isinstance(exc, GarminCliError):
        return exc
    if isinstance(exc, GarminConnectAuthenticationError):
        return auth_error("Token expired or invalid. Run `garmin login`.")
    if isinstance(exc, GarminConnectTooManyRequestsError):
        return rate_limited_error("Garmin rate limited the request. Retry later.")
    if isinstance(exc, GarminConnectConnectionError):
        status = _extract_http_status(exc)
        if status == 404:
            return not_found_error("The requested Garmin resource was not found.")
        return general_error(str(exc))
    if isinstance(exc, FileNotFoundError):
        return auth_error("No Garmin token store was found. Run `garmin login`.")
    if isinstance(exc, ValueError):
        return usage_error(str(exc))
    return general_error(str(exc))
