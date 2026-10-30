"""Service health."""

from enum import StrEnum

from .common import ApiModel


class HealthStatus(StrEnum):
    """`degraded` when a dependency (e.g. the database) is unhealthy."""

    OK = "ok"
    DEGRADED = "degraded"


class DependencyStatus(StrEnum):
    """Whether a dependency is reachable."""

    OK = "ok"
    UNAVAILABLE = "unavailable"


class ConfiguredModels(ApiModel):
    """The OpenAI models the server is configured with."""

    transcribe: str
    """Model that reads page images."""
    embed: str
    """Model that embeds page text for search."""


class Health(ApiModel):
    """Service status."""

    status: HealthStatus
    version: str
    """The running app version."""
    database: DependencyStatus
    models: ConfiguredModels
