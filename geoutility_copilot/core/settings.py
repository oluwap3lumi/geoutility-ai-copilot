"""Typed user preferences stored in QgsSettings."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional

from qgis.core import QgsSettings

SETTINGS_GROUP = "GeoUtilityCopilot"


@dataclass(frozen=True)
class CopilotSettings:
    """Persisted provider and privacy preferences."""

    provider: str = "claude"
    model: str = "claude-sonnet-5-5"
    never_send_samples: bool = True
    metric_crs: str = "EPSG:32631"
    privacy_notice_seen: bool = False


def load_settings(store: Optional[Any] = None) -> CopilotSettings:
    """Load settings with safe defaults.

    Args:
        store: QgsSettings-compatible store, primarily for tests.
    """
    settings = store or QgsSettings()
    defaults = CopilotSettings()
    return CopilotSettings(
        provider=settings.value(_key("provider"), defaults.provider, type=str),
        model=settings.value(_key("model"), defaults.model, type=str),
        never_send_samples=settings.value(
            _key("neverSendSamples"), defaults.never_send_samples, type=bool
        ),
        metric_crs=settings.value(_key("metricCrs"), defaults.metric_crs, type=str),
        privacy_notice_seen=settings.value(
            _key("privacyNoticeSeen"), defaults.privacy_notice_seen, type=bool
        ),
    )


def save_settings(values: CopilotSettings, store: Optional[Any] = None) -> None:
    """Persist non-secret settings.

    Args:
        values: Settings snapshot to save.
        store: QgsSettings-compatible store, primarily for tests.
    """
    settings = store or QgsSettings()
    settings.setValue(_key("provider"), values.provider)
    settings.setValue(_key("model"), values.model)
    settings.setValue(_key("neverSendSamples"), values.never_send_samples)
    settings.setValue(_key("metricCrs"), values.metric_crs)
    settings.setValue(_key("privacyNoticeSeen"), values.privacy_notice_seen)


def mark_privacy_notice_seen(store: Optional[Any] = None) -> None:
    """Persist dismissal of the first-run privacy notice.

    Args:
        store: QgsSettings-compatible store, primarily for tests.
    """
    current = load_settings(store)
    save_settings(
        CopilotSettings(
            provider=current.provider,
            model=current.model,
            never_send_samples=current.never_send_samples,
            metric_crs=current.metric_crs,
            privacy_notice_seen=True,
        ),
        store,
    )


def _key(name: str) -> str:
    return f"{SETTINGS_GROUP}/{name}"
