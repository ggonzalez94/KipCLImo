"""CLI state container."""

from __future__ import annotations

from dataclasses import dataclass

from .auth import AuthManager
from .cache import CacheBackend
from .client import GarminService, ServiceOptions
from .config import AppConfig
from .schema import SchemaRegistry


@dataclass(slots=True)
class GlobalOptions:
    output: str
    no_cache: bool
    refresh: bool
    fields: list[str]
    verbose: bool


@dataclass
class AppState:
    options: GlobalOptions
    config: AppConfig
    cache: CacheBackend
    auth: AuthManager
    registry: SchemaRegistry
    _service: GarminService | None = None

    @property
    def service_options(self) -> ServiceOptions:
        return ServiceOptions(no_cache=self.options.no_cache, refresh=self.options.refresh)

    def service(self) -> GarminService:
        if self._service is None:
            self._service = GarminService(
                auth=self.auth,
                cache=self.cache,
                config=self.config,
            )
        return self._service
