"""
Configuration Schema Definitions for Repository Scanner

This module defines the complete configuration schema for secure configuration management,
including validation rules, sensitivity flags, and default values.
"""

from .secure_config import ConfigurationSchema, ConfigurationScope, init_secure_config
import os

# Core Configuration Schemas
CONFIG_SCHEMAS = [
    # API Server Configuration
    ConfigurationSchema(
        key="api_server.enabled",
        type=bool,
        required=False,
        default=False,
        scope=ConfigurationScope.ENVIRONMENT,
        description="Enable the web API server for remote access"
    ),
    ConfigurationSchema(
        key="api_server.host",
        type=str,
        required=False,
        default="localhost",
        validation=lambda x: len(x) > 0 and len(x) <= 253,
        scope=ConfigurationScope.INSTANCE,
        description="API server host address"
    ),
    ConfigurationSchema(
        key="api_server.port",
        type=int,
        required=False,
        default=8000,
        validation=lambda x: 1024 <= x <= 65535,
        scope=ConfigurationScope.INSTANCE,
        description="API server port number"
    ),
    ConfigurationSchema(
        key="api_server.workers",
        type=int,
        required=False,
        default=1,
        validation=lambda x: 1 <= x <= 16,
        scope=ConfigurationScope.INSTANCE,
        description="Number of API server worker processes"
    ),

    # Health Monitoring Configuration
    ConfigurationSchema(
        key="health_monitoring.enabled",
        type=bool,
        required=False,
        default=False,
        scope=ConfigurationScope.ENVIRONMENT,
        description="Enable health monitoring and uptime tracking"
    ),
    ConfigurationSchema(
        key="health_monitoring.uptime_sla_target",
        type=float,
        required=False,
        default=99.999,
        validation=lambda x: 90.0 <= x <= 100.0,
        scope=ConfigurationScope.GLOBAL,
        description="Target uptime SLA percentage"
    ),
    ConfigurationSchema(
        key="health_monitoring.health_check_interval",
        type=int,
        required=False,
        default=30,
        validation=lambda x: 10 <= x <= 300,
        scope=ConfigurationScope.INSTANCE,
        description="Health check interval in seconds"
    ),

    # Circuit Breaker Configuration
    ConfigurationSchema(
        key="circuit_breaker.enabled",
        type=bool,
        required=False,
        default=False,
        scope=ConfigurationScope.ENVIRONMENT,
        description="Enable circuit breaker protection"
    ),
    ConfigurationSchema(
        key="circuit_breaker.failure_threshold",
        type=int,
        required=False,
        default=5,
        validation=lambda x: 1 <= x <= 20,
        scope=ConfigurationScope.INSTANCE,
        description="Number of failures before opening circuit"
    ),
    ConfigurationSchema(
        key="circuit_breaker.recovery_timeout",
        type=int,
        required=False,
        default=60,
        validation=lambda x: 10 <= x <= 600,
        scope=ConfigurationScope.INSTANCE,
        description="Recovery timeout in seconds"
    ),

    # Bounty Service Configuration
    ConfigurationSchema(
        key="bounty_service.enabled",
        type=bool,
        required=False,
        default=False,
        scope=ConfigurationScope.ENVIRONMENT,
        description="Enable bounty scanning and analysis"
    ),
    ConfigurationSchema(
        key="bounty_service.api_url",
        type=str,
        required=False,
        default="https://api.algora.io",
        validation=lambda x: x.startswith(('http://', 'https://')) and len(x) <= 2048,
        scope=ConfigurationScope.GLOBAL,
        description="Bounty service API URL"
    ),
    ConfigurationSchema(
        key="bounty_service.api_key",
        type=str,
        required=False,
        default="",
        sensitive=True,
        scope=ConfigurationScope.INSTANCE,
        description="Bounty service API key"
    ),
    ConfigurationSchema(
        key="bounty_service.cache_ttl",
        type=int,
        required=False,
        default=3600,
        validation=lambda x: 300 <= x <= 86400,
        scope=ConfigurationScope.INSTANCE,
        description="Bounty data cache TTL in seconds"
    ),

    # Error Handling Configuration
    ConfigurationSchema(
        key="error_handling.enabled",
        type=bool,
        required=False,
        default=False,
        scope=ConfigurationScope.ENVIRONMENT,
        description="Enable advanced error handling and recovery"
    ),
    ConfigurationSchema(
        key="error_handling.max_retries",
        type=int,
        required=False,
        default=3,
        validation=lambda x: 0 <= x <= 10,
        scope=ConfigurationScope.INSTANCE,
        description="Maximum number of retry attempts"
    ),
    ConfigurationSchema(
        key="error_handling.retry_delay",
        type=float,
        required=False,
        default=1.0,
        validation=lambda x: 0.1 <= x <= 60.0,
        scope=ConfigurationScope.INSTANCE,
        description="Delay between retry attempts in seconds"
    ),

    # Graceful Degradation Configuration
    ConfigurationSchema(
        key="graceful_degradation.enabled",
        type=bool,
        required=False,
        default=False,
        scope=ConfigurationScope.ENVIRONMENT,
        description="Enable graceful degradation for component failures"
    ),
    ConfigurationSchema(
        key="graceful_degradation.timeout",
        type=int,
        required=False,
        default=300,
        validation=lambda x: 30 <= x <= 3600,
        scope=ConfigurationScope.INSTANCE,
        description="Degradation timeout in seconds"
    ),

    # Metrics Configuration
    ConfigurationSchema(
        key="metrics.enabled",
        type=bool,
        required=False,
        default=False,
        scope=ConfigurationScope.ENVIRONMENT,
        description="Enable Prometheus-compatible metrics collection"
    ),
    ConfigurationSchema(
        key="metrics.collection_interval",
        type=int,
        required=False,
        default=60,
        validation=lambda x: 10 <= x <= 300,
        scope=ConfigurationScope.INSTANCE,
        description="Metrics collection interval in seconds"
    ),
    ConfigurationSchema(
        key="metrics.retention_period",
        type=int,
        required=False,
        default=3600,
        validation=lambda x: 300 <= x <= 86400,
        scope=ConfigurationScope.INSTANCE,
        description="Metrics retention period in seconds"
    ),

    # Tracing Configuration
    ConfigurationSchema(
        key="tracing.enabled",
        type=bool,
        required=False,
        default=False,
        scope=ConfigurationScope.ENVIRONMENT,
        description="Enable distributed tracing"
    ),
    ConfigurationSchema(
        key="tracing.service_name",
        type=str,
        required=False,
        default="repo-scanner",
        validation=lambda x: len(x) > 0 and len(x) <= 100,
        scope=ConfigurationScope.INSTANCE,
        description="Service name for tracing"
    ),

    # Alerting Configuration
    ConfigurationSchema(
        key="alerting.enabled",
        type=bool,
        required=False,
        default=False,
        scope=ConfigurationScope.ENVIRONMENT,
        description="Enable alerting system"
    ),
    ConfigurationSchema(
        key="alerting.notification_email",
        type=str,
        required=False,
        default="",
        validation=lambda x: not x or "@" in x,
        scope=ConfigurationScope.INSTANCE,
        description="Email address for alerts"
    ),

    # Dashboard Configuration
    ConfigurationSchema(
        key="dashboard.enabled",
        type=bool,
        required=False,
        default=False,
        scope=ConfigurationScope.ENVIRONMENT,
        description="Enable web dashboard"
    ),
    ConfigurationSchema(
        key="dashboard.refresh_interval",
        type=int,
        required=False,
        default=30,
        validation=lambda x: 5 <= x <= 300,
        scope=ConfigurationScope.INSTANCE,
        description="Dashboard refresh interval in seconds"
    ),

    # Logging Configuration
    ConfigurationSchema(
        key="logging.level",
        type=str,
        required=False,
        default="INFO",
        validation=lambda x: x.upper() in ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
        scope=ConfigurationScope.INSTANCE,
        description="Logging level"
    ),
    ConfigurationSchema(
        key="logging.max_file_size",
        type=int,
        required=False,
        default=10485760,  # 10MB
        validation=lambda x: 1024 <= x <= 1073741824,  # 1KB to 1GB
        scope=ConfigurationScope.INSTANCE,
        description="Maximum log file size in bytes"
    ),

    # Security Configuration
    ConfigurationSchema(
        key="security.rate_limit_per_minute",
        type=int,
        required=False,
        default=100,
        validation=lambda x: 1 <= x <= 1000,
        scope=ConfigurationScope.INSTANCE,
        description="Rate limit requests per minute"
    ),
    ConfigurationSchema(
        key="security.rate_limit_burst",
        type=int,
        required=False,
        default=20,
        validation=lambda x: 1 <= x <= 100,
        scope=ConfigurationScope.INSTANCE,
        description="Rate limit burst allowance"
    ),
    ConfigurationSchema(
        key="security.session_timeout",
        type=int,
        required=False,
        default=3600,
        validation=lambda x: 300 <= x <= 86400,
        scope=ConfigurationScope.INSTANCE,
        description="Session timeout in seconds"
    ),

    # Database Configuration (if applicable)
    ConfigurationSchema(
        key="database.url",
        type=str,
        required=False,
        default="",
        sensitive=True,
        validation=lambda x: not x or x.startswith(('sqlite://', 'postgresql://', 'mysql://')),
        scope=ConfigurationScope.INSTANCE,
        description="Database connection URL"
    ),
    ConfigurationSchema(
        key="database.pool_size",
        type=int,
        required=False,
        default=5,
        validation=lambda x: 1 <= x <= 50,
        scope=ConfigurationScope.INSTANCE,
        description="Database connection pool size"
    ),

    # Cache Configuration
    ConfigurationSchema(
        key="cache.enabled",
        type=bool,
        required=False,
        default=False,
        scope=ConfigurationScope.ENVIRONMENT,
        description="Enable caching"
    ),
    ConfigurationSchema(
        key="cache.ttl",
        type=int,
        required=False,
        default=300,
        validation=lambda x: 60 <= x <= 3600,
        scope=ConfigurationScope.INSTANCE,
        description="Cache TTL in seconds"
    ),
    ConfigurationSchema(
        key="cache.max_size",
        type=int,
        required=False,
        default=1000,
        validation=lambda x: 100 <= x <= 10000,
        scope=ConfigurationScope.INSTANCE,
        description="Maximum cache size"
    ),

    # Repository Scanning Configuration
    ConfigurationSchema(
        key="scanning.max_file_size",
        type=int,
        required=False,
        default=10485760,  # 10MB
        validation=lambda x: 1024 <= x <= 1073741824,  # 1KB to 1GB
        scope=ConfigurationScope.GLOBAL,
        description="Maximum file size for scanning in bytes"
    ),
    ConfigurationSchema(
        key="scanning.timeout",
        type=int,
        required=False,
        default=300,
        validation=lambda x: 30 <= x <= 3600,
        scope=ConfigurationScope.INSTANCE,
        description="Repository scanning timeout in seconds"
    ),
    ConfigurationSchema(
        key="scanning.max_concurrent",
        type=int,
        required=False,
        default=3,
        validation=lambda x: 1 <= x <= 10,
        scope=ConfigurationScope.INSTANCE,
        description="Maximum concurrent repository scans"
    ),

    # Output Configuration
    ConfigurationSchema(
        key="output.format",
        type=str,
        required=False,
        default="json",
        validation=lambda x: x.lower() in ["json", "xml", "yaml", "text"],
        scope=ConfigurationScope.INSTANCE,
        description="Output format for reports"
    ),
    ConfigurationSchema(
        key="output.compression",
        type=bool,
        required=False,
        default=False,
        scope=ConfigurationScope.INSTANCE,
        description="Enable output compression"
    ),
]

def initialize_secure_configuration():
    """Initialize the secure configuration system with all schemas."""
    config_dir = os.getenv("REPO_SCANNER_CONFIG_DIR")
    encryption_key = os.getenv("REPO_SCANNER_CONFIG_KEY")

    config_manager = init_secure_config(CONFIG_SCHEMAS, config_dir, encryption_key)

    # Load default values from environment variables
    for schema in CONFIG_SCHEMAS:
        env_key = f"REPO_SCANNER_{schema.key.replace('.', '_').upper()}"
        env_value = os.getenv(env_key)

        if env_value is not None:
            try:
                # Convert string value to appropriate type
                if schema.type == bool:
                    env_value = env_value.lower() in ('true', '1', 'yes', 'on')
                else:
                    env_value = schema.type(env_value)

                # Set the value if it doesn't exist
                if config_manager.get(schema.key) is None:
                    config_manager.set(schema.key, env_value, source="environment")

            except (ValueError, TypeError) as e:
                logger = logging.getLogger(__name__)
                logger.warning(f"Invalid environment value for {schema.key}: {env_value} ({e})")

    return config_manager

def get_secure_config_manager():
    """Get the initialized secure configuration manager."""
    from .secure_config import get_config_manager
    return get_config_manager()