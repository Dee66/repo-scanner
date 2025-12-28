# Optional Features for Repository Intelligence Scanner

This directory contains **optional features** that extend the core scanner functionality but may violate the core product specification requirements for offline operation and no external services.

## ⚠️ Important Warning

These features are **not part of the core spec-compliant implementation**. They introduce:
- External service dependencies
- Web server components
- Production deployment capabilities
- Network connectivity beyond controlled Git cloning

**Use at your own risk** - these features may conflict with the product's core principles of offline operation and controlled network access.

## Available Optional Features

### 1. Web API Server (`api_server.py`)
- **Purpose**: RESTful API for remote repository scanning
- **Use Case**: CI/CD integration, web dashboards, programmatic access
- **Spec Conflict**: Introduces web server (not offline-only)
- **Enable**: `--enable-api-server` or `REPO_SCANNER_ENABLE_API=true`

### 2. Health Monitoring (`monitoring.py`)
- **Purpose**: 99.999% uptime tracking and SLA compliance
- **Use Case**: Production service monitoring
- **Spec Conflict**: Assumes 24/7 operation (not offline-only)
- **Enable**: `--enable-health-monitoring` or `REPO_SCANNER_ENABLE_HEALTH=true`

### 3. Circuit Breakers (`circuit_breaker.py`)
- **Purpose**: Protection against external service failures
- **Use Case**: Robust external API interactions
- **Spec Conflict**: Enables external services (forbidden in spec)
- **Enable**: `--enable-circuit-breakers` or `REPO_SCANNER_ENABLE_CIRCUIT_BREAKERS=true`

### 4. Bounty Service (`bounty/`)
- **Purpose**: Bounty opportunity analysis and solution generation
- **Use Case**: Automated bounty hunting and solution creation
- **Spec Conflict**: External API calls to bounty platforms
- **Enable**: `--enable-bounties` or `REPO_SCANNER_ENABLE_BOUNTIES=true`

### 5. Error Handling (`error_handling.py`)
- **Purpose**: Comprehensive error recovery and classification
- **Use Case**: Production-grade error management
- **Spec Conflict**: May introduce external logging/monitoring
- **Enable**: `--enable-error-handling` or `REPO_SCANNER_ENABLE_ERROR_HANDLING=true`

### 6. Graceful Degradation (`recovery_strategies.py`)
- **Purpose**: Continue operation when components fail
- **Use Case**: High-availability production deployments
- **Spec Conflict**: Assumes multi-component architecture
- **Enable**: `--enable-degradation` or `REPO_SCANNER_ENABLE_DEGRADATION=true`

## Usage

### CLI Flags
```bash
# Enable individual features
python -m src.cli scan /path/to/repo --enable-api-server --enable-health-monitoring

# Start API server
python -m src.cli api --host 0.0.0.0 --port 8080

# Run bounty analysis
python -m src.cli bounty /path/to/repo --enable-bounties --bounty-data bounties.json
```

### Environment Variables
```bash
export REPO_SCANNER_ENABLE_API=true
export REPO_SCANNER_ENABLE_HEALTH=true
export REPO_SCANNER_ENABLE_BOUNTIES=true
export REPO_SCANNER_API_HOST=0.0.0.0
export REPO_SCANNER_API_PORT=8080
```

### Configuration
Features can be configured via `src/optional/optional_config.py` or environment variables.

## Architecture

```
repo_scanner/
├── core/                    # Spec-compliant core (CLI, offline analysis)
├── optional/                # Extended features (may violate spec)
│   ├── api_server.py       # Web API
│   ├── monitoring.py        # Health tracking
│   ├── circuit_breaker.py   # External service protection
│   ├── error_handling.py    # Advanced error management
│   ├── recovery_strategies.py # Graceful degradation
│   ├── bounty/              # Bounty analysis
│   └── optional_config.py   # Feature configuration
└── cli.py                   # Main entry point (core + optional)
```

## Development Notes

- **Core First**: Always ensure core functionality works without optional features
- **Backward Compatibility**: Optional features should not break core operation
- **Clear Warnings**: Users should be informed about spec compliance issues
- **Modular Design**: Features should be independently enableable/disableable

## Future Considerations

These optional features represent potential future directions for the product:
- **Enterprise Deployment**: API server for large organizations
- **Commercial Services**: Bounty analysis as a paid feature
- **Cloud Integration**: Health monitoring for hosted solutions
- **Advanced Analytics**: Performance tracking and optimization

However, any move toward these features should involve updating the core product specification to maintain architectural integrity.