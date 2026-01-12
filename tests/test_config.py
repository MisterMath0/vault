"""
Tests for vault.config module.
"""

import os
from unittest.mock import patch

import pytest
from pydantic import ValidationError

from vault.config import VaultConfig, load_config


class TestVaultConfig:
    """Tests for VaultConfig class."""

    def test_config_creation_with_kwargs(self):
        """Test creating config with keyword arguments."""
        config = VaultConfig(
            supabase_url="https://test.supabase.co",
            supabase_key="test-key-12345678901234567890"
        )
        assert config.supabase_url == "https://test.supabase.co"
        assert config.supabase_key == "test-key-12345678901234567890"
        assert config.db_schema == "public"
        assert config.auto_migrate is False
        assert config.enable_audit_log is True

    def test_config_with_all_options(self):
        """Test creating config with all options."""
        config = VaultConfig(
            supabase_url="https://test.supabase.co",
            supabase_key="test-key-12345678901234567890",
            db_schema="vault",
            supabase_anon_key="anon-key",
            jwt_secret="jwt-secret",
            auto_migrate=True,
            enable_audit_log=False,
            from_email="noreply@example.com",
            debug=True,
        )
        assert config.db_schema == "vault"
        assert config.supabase_anon_key == "anon-key"
        assert config.jwt_secret == "jwt-secret"
        assert config.auto_migrate is True
        assert config.enable_audit_log is False
        assert config.from_email == "noreply@example.com"
        assert config.debug is True

    def test_config_url_validation_valid(self):
        """Test URL validation with valid URLs."""
        valid_urls = [
            "https://test.supabase.co",
            "https://custom.supabase.in",
            "https://test.supabase.co/",
        ]
        for url in valid_urls:
            config = VaultConfig(
                supabase_url=url,
                supabase_key="test-key-12345678901234567890"
            )
            # Should strip trailing slash
            assert config.supabase_url.endswith(".supabase.co") or config.supabase_url.endswith(".supabase.in")

    def test_config_url_validation_invalid(self):
        """Test URL validation with invalid URLs."""
        invalid_urls = [
            "http://test.supabase.co",  # Must be HTTPS
            "ftp://test.supabase.co",
            "test.supabase.co",  # Missing protocol
        ]
        for url in invalid_urls:
            with pytest.raises(ValidationError):
                VaultConfig(
                    supabase_url=url,
                    supabase_key="test-key-12345678901234567890"
                )

    def test_config_key_validation_valid(self):
        """Test key validation with valid keys."""
        valid_keys = [
            "test-key-12345678901234567890",
            "a" * 50,  # Long key
        ]
        for key in valid_keys:
            config = VaultConfig(
                supabase_url="https://test.supabase.co",
                supabase_key=key
            )
            assert config.supabase_key == key

    def test_config_key_validation_invalid(self):
        """Test key validation with invalid keys."""
        invalid_keys = [
            "",  # Empty
            "short",  # Too short
            "123",  # Too short
        ]
        for key in invalid_keys:
            with pytest.raises(ValidationError):
                VaultConfig(
                    supabase_url="https://test.supabase.co",
                    supabase_key=key
                )

    @patch.dict(os.environ, {
        "VAULT_SUPABASE_URL": "https://env.supabase.co",
        "VAULT_SUPABASE_KEY": "env-key-12345678901234567890"
    })
    def test_config_from_environment(self):
        """Test loading config from environment variables."""
        config = VaultConfig()
        assert config.supabase_url == "https://env.supabase.co"
        assert config.supabase_key == "env-key-12345678901234567890"

    @patch.dict(os.environ, {
        "VAULT_SUPABASE_URL": "https://env.supabase.co",
        "VAULT_SUPABASE_KEY": "env-key-12345678901234567890",
        "VAULT_DB_SCHEMA": "vault",
        "VAULT_AUTO_MIGRATE": "true",
        "VAULT_DEBUG": "true",
    })
    def test_config_from_environment_all_options(self):
        """Test loading all config options from environment."""
        config = VaultConfig()
        assert config.supabase_url == "https://env.supabase.co"
        assert config.supabase_key == "env-key-12345678901234567890"
        assert config.db_schema == "vault"
        assert config.auto_migrate is True
        assert config.debug is True

    def test_config_kwargs_override_env(self):
        """Test that kwargs override environment variables."""
        with patch.dict(os.environ, {
            "VAULT_SUPABASE_URL": "https://env.supabase.co",
            "VAULT_SUPABASE_KEY": "env-key-12345678901234567890"
        }):
            config = VaultConfig(
                supabase_url="https://override.supabase.co",
                supabase_key="override-key-12345678901234567890"
            )
            assert config.supabase_url == "https://override.supabase.co"
            assert config.supabase_key == "override-key-12345678901234567890"


class TestLoadConfig:
    """Tests for load_config function."""

    def test_load_config_with_kwargs(self):
        """Test load_config with keyword arguments."""
        config = load_config(
            supabase_url="https://test.supabase.co",
            supabase_key="test-key-12345678901234567890"
        )
        assert isinstance(config, VaultConfig)
        assert config.supabase_url == "https://test.supabase.co"
        assert config.supabase_key == "test-key-12345678901234567890"

    @patch.dict(os.environ, {
        "VAULT_SUPABASE_URL": "https://env.supabase.co",
        "VAULT_SUPABASE_KEY": "env-key-12345678901234567890"
    })
    def test_load_config_from_env(self):
        """Test load_config from environment."""
        config = load_config()
        assert config.supabase_url == "https://env.supabase.co"
        assert config.supabase_key == "env-key-12345678901234567890"

    @patch.dict(os.environ, {
        "VAULT_SUPABASE_URL": "https://env.supabase.co",
        "VAULT_SUPABASE_KEY": "env-key-12345678901234567890"
    })
    def test_load_config_kwargs_override_env(self):
        """Test that load_config kwargs override environment."""
        config = load_config(
            supabase_url="https://override.supabase.co",
            debug=True
        )
        assert config.supabase_url == "https://override.supabase.co"
        assert config.debug is True
        # Should still use env for key
        assert config.supabase_key == "env-key-12345678901234567890"

