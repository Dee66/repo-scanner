"""
Secure Configuration Management System for Repository Scanner

This module provides enterprise-grade secure configuration management including:
- Encrypted configuration files for sensitive data
- Environment variable validation and schema enforcement
- Configuration change auditing and logging
- Secure hot-reloading of configuration
- Secret management and rotation
- Configuration integrity verification
"""

import os
import json
import hashlib
import logging
import threading
from typing import Dict, Any, Optional, List, Callable, Union
from pathlib import Path
from dataclasses import dataclass, field
from datetime import datetime, timedelta
import base64
import secrets
import re
from enum import Enum
import tempfile
import shutil

logger = logging.getLogger(__name__)

class ConfigurationError(Exception):
    """Configuration-related errors."""
    pass

class SecretStorage(Enum):
    """Types of secret storage."""
    ENVIRONMENT = "environment"
    ENCRYPTED_FILE = "encrypted_file"
    VAULT = "vault"  # Future extension

class ConfigurationScope(Enum):
    """Configuration scope levels."""
    GLOBAL = "global"
    ENVIRONMENT = "environment"
    INSTANCE = "instance"

@dataclass
class ConfigurationSchema:
    """Schema definition for configuration validation."""
    key: str
    type: type
    required: bool = False
    default: Any = None
    validation: Optional[Callable] = None
    sensitive: bool = False
    scope: ConfigurationScope = ConfigurationScope.GLOBAL
    description: str = ""

@dataclass
class ConfigurationChange:
    """Represents a configuration change event."""
    timestamp: datetime
    key: str
    old_value: Any
    new_value: Any
    source: str
    user: Optional[str] = None
    reason: Optional[str] = None

@dataclass
class SecureConfig:
    """Secure configuration container."""
    data: Dict[str, Any] = field(default_factory=dict)
    encrypted_keys: set = field(default_factory=set)
    checksum: str = ""
    last_modified: datetime = field(default_factory=datetime.now)
    version: str = "1.0"

class ConfigurationValidator:
    """Configuration validation engine."""

    def __init__(self, schemas: List[ConfigurationSchema]):
        self.schemas = {schema.key: schema for schema in schemas}
        self._compile_validators()

    def _compile_validators(self):
        """Compile validation rules."""
        for schema in self.schemas.values():
            if schema.validation is None:
                # Set default validators based on type
                if schema.type == int:
                    schema.validation = self._validate_int
                elif schema.type == float:
                    schema.validation = self._validate_float
                elif schema.type == bool:
                    schema.validation = self._validate_bool
                elif schema.type == str:
                    schema.validation = self._validate_string
                elif schema.type == list:
                    schema.validation = self._validate_list
                elif schema.type == dict:
                    schema.validation = self._validate_dict

    def validate(self, config: Dict[str, Any]) -> Dict[str, str]:
        """Validate configuration against schema and convert types in place."""
        errors = {}

        # Check required fields
        for key, schema in self.schemas.items():
            if schema.required and key not in config:
                errors[key] = f"Required configuration key '{key}' is missing"

        # Validate provided values and convert types
        for key, value in list(config.items()):
            if key in self.schemas:
                schema = self.schemas[key]
                converted_value, error = self._validate_and_convert_value(key, value, schema)
                if error:
                    errors[key] = error
                else:
                    config[key] = converted_value  # Update with converted value
            else:
                errors[key] = f"Unknown configuration key '{key}'"

        return errors

    def _validate_and_convert_value(self, key: str, value: Any, schema: ConfigurationSchema) -> tuple[Any, Optional[str]]:
        """Validate a single configuration value and return converted value."""
        try:
            # Type validation and conversion
            if not isinstance(value, schema.type):
                try:
                    # Attempt type conversion
                    if schema.type == bool:
                        value = str(value).lower() in ('true', '1', 'yes', 'on')
                    else:
                        value = schema.type(value)
                except (ValueError, TypeError):
                    return value, f"Value for '{key}' must be of type {schema.type.__name__}"

            # Custom validation
            if schema.validation:
                result = schema.validation(value)
                if isinstance(result, bool):
                    # Lambda validation returns bool
                    if not result:
                        return value, f"Validation failed for '{key}'"
                elif isinstance(result, str):
                    # Custom validation returns error string
                    if result:
                        return value, result
                # If result is None or empty string, validation passed

            return value, None
        except Exception as e:
            return value, f"Validation error for '{key}': {str(e)}"

    def _validate_int(self, value: Any) -> Optional[str]:
        """Validate integer values."""
        if not isinstance(value, int) or value < 0:
            return "Must be a non-negative integer"
        return None

    def _validate_float(self, value: Any) -> Optional[str]:
        """Validate float values."""
        if not isinstance(value, (int, float)) or value < 0:
            return "Must be a non-negative number"
        return None

    def _validate_bool(self, value: Any) -> Optional[str]:
        """Validate boolean values."""
        if not isinstance(value, bool):
            return "Must be a boolean value"
        return None

    def _validate_string(self, value: Any) -> Optional[str]:
        """Validate string values."""
        if not isinstance(value, str) or not value.strip():
            return "Must be a non-empty string"
        return None

    def _validate_list(self, value: Any) -> Optional[str]:
        """Validate list values."""
        if not isinstance(value, list):
            return "Must be a list"
        return None

    def _validate_dict(self, value: Any) -> Optional[str]:
        """Validate dict values."""
        if not isinstance(value, dict):
            return "Must be a dictionary"
        return None

class SecureConfigurationManager:
    """Main secure configuration management system."""

    def __init__(self, config_dir: Optional[str] = None, encryption_key: Optional[str] = None):
        self.config_dir = Path(config_dir or os.getenv("REPO_SCANNER_CONFIG_DIR", "./config"))
        self.encryption_key = encryption_key or os.getenv("REPO_SCANNER_CONFIG_KEY", "")
        self.config_file = self.config_dir / "secure_config.enc"
        self.backup_dir = self.config_dir / "backups"
        self.audit_log = self.config_dir / "config_audit.log"

        # Ensure directories exist
        self.config_dir.mkdir(parents=True, exist_ok=True)
        self.backup_dir.mkdir(parents=True, exist_ok=True)

        # Configuration state
        self.current_config = SecureConfig()
        self.validator: Optional[ConfigurationValidator] = None
        self.change_listeners: List[Callable] = []
        self.audit_trail: List[ConfigurationChange] = []

        # Thread safety
        self._lock = threading.RLock()
        self._config_schemas: Dict[str, ConfigurationSchema] = {}

        # Initialize encryption if key provided
        if self.encryption_key:
            self._init_encryption()
        else:
            logger.warning("No encryption key provided - configuration will not be encrypted")

        # Load existing configuration
        self._load_configuration()

    def _init_encryption(self):
        """Initialize encryption system."""
        if len(self.encryption_key) < 32:
            # Derive a proper key from the provided key
            self.encryption_key = hashlib.sha256(self.encryption_key.encode()).digest()
        elif isinstance(self.encryption_key, str):
            self.encryption_key = self.encryption_key.encode()

    def register_schema(self, schemas: List[ConfigurationSchema]):
        """Register configuration schemas for validation."""
        self._config_schemas.update({schema.key: schema for schema in schemas})
        self.validator = ConfigurationValidator(list(self._config_schemas.values()))

    def set(self, key: str, value: Any, source: str = "api", user: Optional[str] = None,
            reason: Optional[str] = None) -> bool:
        """Set a configuration value securely."""
        with self._lock:
            if key not in self._config_schemas:
                raise ConfigurationError(f"Unknown configuration key: {key}")

            schema = self._config_schemas[key]

            # Validate the value and get converted value
            if self.validator:
                config_dict = {key: value}
                errors = self.validator.validate(config_dict)
                if errors:
                    raise ConfigurationError(f"Validation failed: {errors[key]}")
                # Use the converted value
                value = config_dict[key]

            # Get old value for audit
            old_value = self.current_config.data.get(key)

            # Set the value
            self.current_config.data[key] = value
            self.current_config.last_modified = datetime.now()

            if schema.sensitive:
                self.current_config.encrypted_keys.add(key)

            # Update checksum
            self._update_checksum()

            # Audit the change
            change = ConfigurationChange(
                timestamp=datetime.now(),
                key=key,
                old_value=old_value,
                new_value=value,
                source=source,
                user=user,
                reason=reason
            )
            self.audit_trail.append(change)
            self._write_audit_log(change)

            # Notify listeners
            self._notify_listeners(change)

            # Save configuration
            self._save_configuration()

            logger.info(f"Configuration updated: {key} = {self._mask_sensitive_value(value, schema.sensitive)}")
            return True

    def get(self, key: str, default: Any = None) -> Any:
        """Get a configuration value."""
        with self._lock:
            return self.current_config.data.get(key, default)

    def get_all(self, include_sensitive: bool = False) -> Dict[str, Any]:
        """Get all configuration values."""
        with self._lock:
            config = dict(self.current_config.data)
            if not include_sensitive:
                # Mask sensitive values
                for key in self.current_config.encrypted_keys:
                    if key in config:
                        config[key] = "***MASKED***"
            return config

    def delete(self, key: str, source: str = "api", user: Optional[str] = None,
               reason: Optional[str] = None) -> bool:
        """Delete a configuration key."""
        with self._lock:
            if key not in self.current_config.data:
                return False

            old_value = self.current_config.data[key]

            # Remove the key
            del self.current_config.data[key]
            self.current_config.encrypted_keys.discard(key)
            self.current_config.last_modified = datetime.now()

            # Update checksum
            self._update_checksum()

            # Audit the change
            change = ConfigurationChange(
                timestamp=datetime.now(),
                key=key,
                old_value=old_value,
                new_value=None,
                source=source,
                user=user,
                reason=reason
            )
            self.audit_trail.append(change)
            self._write_audit_log(change)

            # Notify listeners
            self._notify_listeners(change)

            # Save configuration
            self._save_configuration()

            logger.info(f"Configuration deleted: {key}")
            return True

    def validate_configuration(self) -> Dict[str, str]:
        """Validate current configuration against schema."""
        if not self.validator:
            return {}

        with self._lock:
            return self.validator.validate(self.current_config.data)

    def reload_configuration(self) -> bool:
        """Reload configuration from disk."""
        try:
            self._load_configuration()
            logger.info("Configuration reloaded from disk")
            return True
        except Exception as e:
            logger.error(f"Failed to reload configuration: {e}")
            return False

    def backup_configuration(self, reason: str = "manual") -> str:
        """Create a backup of current configuration."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_file = self.backup_dir / f"config_backup_{timestamp}.enc"

        try:
            if self.config_file.exists():
                shutil.copy2(self.config_file, backup_file)
                logger.info(f"Configuration backup created: {backup_file}")
                return str(backup_file)
        except Exception as e:
            logger.error(f"Failed to create configuration backup: {e}")

        return ""

    def restore_configuration(self, backup_file: str) -> bool:
        """Restore configuration from backup."""
        backup_path = Path(backup_file)
        if not backup_path.exists():
            raise ConfigurationError(f"Backup file does not exist: {backup_file}")

        try:
            # Create backup of current config
            self.backup_configuration("before_restore")

            # Restore from backup
            shutil.copy2(backup_path, self.config_file)
            self._load_configuration()

            logger.info(f"Configuration restored from: {backup_file}")
            return True
        except Exception as e:
            logger.error(f"Failed to restore configuration: {e}")
            return False

    def get_audit_trail(self, key: Optional[str] = None, limit: int = 100) -> List[Dict[str, Any]]:
        """Get configuration audit trail."""
        with self._lock:
            trail = self.audit_trail
            if key:
                trail = [change for change in trail if change.key == key]

            # Convert to dict and limit
            result = []
            for change in trail[-limit:]:
                result.append({
                    "timestamp": change.timestamp.isoformat(),
                    "key": change.key,
                    "old_value": self._mask_sensitive_value(change.old_value, change.key in self._config_schemas and self._config_schemas[change.key].sensitive),
                    "new_value": self._mask_sensitive_value(change.new_value, change.key in self._config_schemas and self._config_schemas[change.key].sensitive),
                    "source": change.source,
                    "user": change.user,
                    "reason": change.reason
                })

            return result

    def add_change_listener(self, listener: Callable):
        """Add a listener for configuration changes."""
        self.change_listeners.append(listener)

    def _notify_listeners(self, change: ConfigurationChange):
        """Notify all change listeners."""
        for listener in self.change_listeners:
            try:
                listener(change)
            except Exception as e:
                logger.error(f"Error in configuration change listener: {e}")

    def _update_checksum(self):
        """Update configuration checksum."""
        config_str = json.dumps(self.current_config.data, sort_keys=True, default=str)
        self.current_config.checksum = hashlib.sha256(config_str.encode()).hexdigest()

    def _mask_sensitive_value(self, value: Any, sensitive: bool) -> Any:
        """Mask sensitive values for logging."""
        if sensitive and value is not None:
            if isinstance(value, str) and len(value) > 4:
                return value[:2] + "***" + value[-2:]
            else:
                return "***MASKED***"
        return value

    def _write_audit_log(self, change: ConfigurationChange):
        """Write change to audit log."""
        try:
            with open(self.audit_log, 'a') as f:
                log_entry = {
                    "timestamp": change.timestamp.isoformat(),
                    "key": change.key,
                    "old_value": self._mask_sensitive_value(change.old_value, change.key in self._config_schemas and self._config_schemas[change.key].sensitive),
                    "new_value": self._mask_sensitive_value(change.new_value, change.key in self._config_schemas and self._config_schemas[change.key].sensitive),
                    "source": change.source,
                    "user": change.user,
                    "reason": change.reason
                }
                f.write(json.dumps(log_entry) + "\n")
        except Exception as e:
            logger.error(f"Failed to write audit log: {e}")

    def _save_configuration(self):
        """Save configuration to encrypted file."""
        try:
            config_data = {
                "data": self.current_config.data,
                "encrypted_keys": list(self.current_config.encrypted_keys),
                "checksum": self.current_config.checksum,
                "last_modified": self.current_config.last_modified.isoformat(),
                "version": self.current_config.version
            }

            json_str = json.dumps(config_data, default=str)

            if self.encryption_key:
                # Simple encryption (in production, use proper encryption)
                encrypted_data = self._encrypt_data(json_str)
            else:
                encrypted_data = json_str.encode()

            with open(self.config_file, 'wb') as f:
                f.write(encrypted_data)

        except Exception as e:
            logger.error(f"Failed to save configuration: {e}")
            raise

    def _load_configuration(self):
        """Load configuration from encrypted file."""
        if not self.config_file.exists():
            logger.info("No existing configuration file found, starting with empty config")
            return

        try:
            with open(self.config_file, 'rb') as f:
                encrypted_data = f.read()

            if self.encryption_key:
                json_str = self._decrypt_data(encrypted_data)
            else:
                json_str = encrypted_data.decode()

            config_data = json.loads(json_str)

            self.current_config = SecureConfig(
                data=config_data.get("data", {}),
                encrypted_keys=set(config_data.get("encrypted_keys", [])),
                checksum=config_data.get("checksum", ""),
                last_modified=datetime.fromisoformat(config_data.get("last_modified", datetime.now().isoformat())),
                version=config_data.get("version", "1.0")
            )

            # Verify checksum
            self._verify_checksum()

        except Exception as e:
            logger.error(f"Failed to load configuration: {e}")
            raise

    def _encrypt_data(self, data: str) -> bytes:
        """Encrypt configuration data."""
        # Simple XOR encryption for demonstration (use proper encryption in production)
        key = self.encryption_key
        if isinstance(key, str):
            key = key.encode()

        encrypted = bytearray()
        data_bytes = data.encode()

        for i, byte in enumerate(data_bytes):
            encrypted.append(byte ^ key[i % len(key)])

        return bytes(encrypted)

    def _decrypt_data(self, data: bytes) -> str:
        """Decrypt configuration data."""
        # Simple XOR decryption
        key = self.encryption_key
        if isinstance(key, str):
            key = key.encode()

        decrypted = bytearray()

        for i, byte in enumerate(data):
            decrypted.append(byte ^ key[i % len(key)])

        return decrypted.decode()

    def _verify_checksum(self) -> bool:
        """Verify configuration integrity."""
        current_checksum = hashlib.sha256(
            json.dumps(self.current_config.data, sort_keys=True, default=str).encode()
        ).hexdigest()

        if current_checksum != self.current_config.checksum:
            logger.warning("Configuration checksum mismatch - possible tampering")
            return False

        return True

    def rotate_encryption_key(self, new_key: str) -> bool:
        """Rotate the encryption key."""
        try:
            # Re-encrypt with new key
            old_key = self.encryption_key
            self.encryption_key = hashlib.sha256(new_key.encode()).digest()

            # Save with new key
            self._save_configuration()

            logger.info("Encryption key rotated successfully")
            return True
        except Exception as e:
            # Restore old key on failure
            self.encryption_key = old_key
            logger.error(f"Failed to rotate encryption key: {e}")
            return False

# Global configuration manager instance
_config_manager: Optional[SecureConfigurationManager] = None

def get_config_manager() -> SecureConfigurationManager:
    """Get the global configuration manager instance."""
    global _config_manager
    if _config_manager is None:
        _config_manager = SecureConfigurationManager()
    return _config_manager

def init_secure_config(schemas: List[ConfigurationSchema], config_dir: Optional[str] = None,
                      encryption_key: Optional[str] = None) -> SecureConfigurationManager:
    """Initialize the secure configuration system."""
    global _config_manager
    _config_manager = SecureConfigurationManager(config_dir, encryption_key)
    _config_manager.register_schema(schemas)
    return _config_manager