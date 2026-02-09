"""
Configuration validation tests.

These tests verify configuration loading and validation logic.
Note: These tests use monkeypatch to set environment variables for testing
configuration logic, but all integration tests use actual credentials.
"""

import pytest
from collibra_client import CollibraConfig


class TestCollibraConfig:
    """Test suite for CollibraConfig."""

    def test_config_from_env_variables(self, monkeypatch):
        """Test loading configuration from environment variables."""
        monkeypatch.setenv("COLLIBRA_BASE_URL", "https://test.collibra.com")
        monkeypatch.setenv("COLLIBRA_CLIENT_ID", "test_client_id")
        monkeypatch.setenv("COLLIBRA_CLIENT_SECRET", "test_client_secret")
        
        config = CollibraConfig.from_env()
        
        assert config.base_url == "https://test.collibra.com"
        assert config.client_id == "test_client_id"
        assert config.client_secret == "test_client_secret"
        assert config.timeout == 30  # default

    def test_config_with_custom_timeout(self, monkeypatch):
        """Test configuration with custom timeout."""
        monkeypatch.setenv("COLLIBRA_BASE_URL", "https://test.collibra.com")
        monkeypatch.setenv("COLLIBRA_CLIENT_ID", "test_client_id")
        monkeypatch.setenv("COLLIBRA_CLIENT_SECRET", "test_client_secret")
        
        config = CollibraConfig.from_env(timeout=60)
        
        assert config.timeout == 60

    def test_config_direct_initialization(self):
        """Test direct configuration initialization."""
        config = CollibraConfig(
            base_url="https://test.collibra.com",
            client_id="test_client_id",
            client_secret="test_client_secret",
            timeout=45,
        )
        
        assert config.base_url == "https://test.collibra.com"
        assert config.client_id == "test_client_id"
        assert config.client_secret == "test_client_secret"
        assert config.timeout == 45

    def test_config_missing_base_url(self, monkeypatch):
        """Test that missing base_url raises ValueError."""
        monkeypatch.delenv("COLLIBRA_BASE_URL", raising=False)
        monkeypatch.setenv("COLLIBRA_CLIENT_ID", "test_client_id")
        monkeypatch.setenv("COLLIBRA_CLIENT_SECRET", "test_client_secret")
        
        with pytest.raises(ValueError, match="base URL"):
            CollibraConfig.from_env()

    def test_config_missing_client_id(self, monkeypatch):
        """Test that missing client_id raises ValueError."""
        monkeypatch.setenv("COLLIBRA_BASE_URL", "https://test.collibra.com")
        monkeypatch.delenv("COLLIBRA_CLIENT_ID", raising=False)
        monkeypatch.setenv("COLLIBRA_CLIENT_SECRET", "test_client_secret")
        
        with pytest.raises(ValueError, match="client ID"):
            CollibraConfig.from_env()

    def test_config_missing_client_secret(self, monkeypatch):
        """Test that missing client_secret raises ValueError."""
        monkeypatch.setenv("COLLIBRA_BASE_URL", "https://test.collibra.com")
        monkeypatch.setenv("COLLIBRA_CLIENT_ID", "test_client_id")
        monkeypatch.delenv("COLLIBRA_CLIENT_SECRET", raising=False)
        
        with pytest.raises(ValueError, match="client secret"):
            CollibraConfig.from_env()

    def test_config_parameter_override_env(self, monkeypatch):
        """Test that direct parameters override environment variables."""
        monkeypatch.setenv("COLLIBRA_BASE_URL", "https://env.collibra.com")
        monkeypatch.setenv("COLLIBRA_CLIENT_ID", "env_client_id")
        monkeypatch.setenv("COLLIBRA_CLIENT_SECRET", "env_secret")
        
        config = CollibraConfig(
            base_url="https://param.collibra.com",
            client_id="param_client_id",
            client_secret="param_secret",
        )
        
        assert config.base_url == "https://param.collibra.com"
        assert config.client_id == "param_client_id"
        assert config.client_secret == "param_secret"

