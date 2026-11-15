"""API-key storage backed by QGIS Authentication Manager."""

from __future__ import annotations

from typing import Protocol, Union

from qgis.core import QgsApplication, QgsAuthMethodConfig, QgsSettings

AUTH_CONFIG_ID_KEY = "GeoUtilityCopilot/anthropicAuthConfigId"


class SecretStoreError(RuntimeError):
    """Raised when QGIS cannot store or retrieve an API key."""


class SecretStore(Protocol):
    """Minimal secret-storage interface consumed by the settings UI."""

    def has_api_key(self) -> bool:
        """Return whether an API key is stored."""

    def get_api_key(self) -> str:
        """Return the stored API key or an empty string."""

    def set_api_key(self, api_key: str) -> None:
        """Store a non-empty API key."""


AuthResult = Union[bool, tuple[bool, QgsAuthMethodConfig]]


class AuthManagerSecretStore:
    """Store the API key in QGIS's encrypted authentication database."""

    def has_api_key(self) -> bool:
        """Return whether a retrievable API key exists."""
        return bool(self.get_api_key())

    def get_api_key(self) -> str:
        """Load the API key without writing it to logs or settings."""
        auth_id = QgsSettings().value(AUTH_CONFIG_ID_KEY, "", type=str)
        if not auth_id:
            return ""
        config = QgsAuthMethodConfig()
        ok, loaded = _auth_result(
            QgsApplication.authManager().loadAuthenticationConfig(auth_id, config, True), config
        )
        if not ok:
            return ""
        return loaded.config("password", "")

    def set_api_key(self, api_key: str) -> None:
        """Create or update the encrypted authentication configuration.

        Args:
            api_key: Anthropic API key. Empty values are rejected.
        """
        if not api_key.strip():
            raise SecretStoreError("API key cannot be empty.")
        settings = QgsSettings()
        auth_id = settings.value(AUTH_CONFIG_ID_KEY, "", type=str)
        config = self._existing_config(auth_id)
        config.setName("GeoUtility AI Copilot — Anthropic")
        config.setConfig("username", "anthropic-api-key")
        config.setConfig("password", api_key.strip())
        ok, stored = _auth_result(
            QgsApplication.authManager().storeAuthenticationConfig(config, bool(auth_id)), config
        )
        if not ok or not stored.id():
            raise SecretStoreError(
                "QGIS Authentication Manager could not store the API key. "
                "Unlock or initialize the authentication database and try again."
            )
        settings.setValue(AUTH_CONFIG_ID_KEY, stored.id())

    @staticmethod
    def _existing_config(auth_id: str) -> QgsAuthMethodConfig:
        config = QgsAuthMethodConfig("Basic")
        if not auth_id:
            return config
        ok, loaded = _auth_result(
            QgsApplication.authManager().loadAuthenticationConfig(auth_id, config, True), config
        )
        if not ok:
            raise SecretStoreError(
                "The saved QGIS authentication configuration could not be loaded."
            )
        return loaded


def _auth_result(
    result: AuthResult, fallback: QgsAuthMethodConfig
) -> tuple[bool, QgsAuthMethodConfig]:
    """Normalize SIP return styles used across supported QGIS versions."""
    if isinstance(result, tuple):
        return bool(result[0]), result[1]
    return bool(result), fallback
