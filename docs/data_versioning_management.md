# Validation Data Versioning and Management System

## Overview

The Validation Data Versioning and Management System provides comprehensive data integrity, versioning, automated maintenance, and quality monitoring capabilities for the repository scanner's validation datasets. This system ensures long-term data reliability and supports continuous effectiveness measurement.

## Architecture

### Core Components

#### ValidationDataManager (`src/core/data_management/manager.py`)
- **Version Control**: Tracks changes to validation data with semantic versioning
- **Integrity Verification**: SHA256 checksum validation for all data files
- **Quality Metrics**: Automated calculation of data quality indicators
- **Backup/Restore**: Full data backup and restoration capabilities
- **Reporting**: Comprehensive data management reports

#### AutomatedDataMaintenance (`src/core/data_management/maintenance.py`)
- **Scheduled Tasks**: Cron-like scheduling for maintenance operations
- **Task Execution**: Automated execution of data updates, integrity checks, cleanup
- **Quality Monitoring**: Continuous monitoring of data quality metrics
- **Custom Tasks**: Support for user-defined maintenance tasks

### Data Structure

```
validation_data/
├── repositories/           # Repository samples
│   ├── python/
│   ├── java/
│   ├── rust/
│   ├── javascript/
│   ├── go/
│   └── cpp/
├── versions/              # Version metadata
├── backups/               # Data backups
├── integrity/             # Integrity checksums
└── reports/               # Generated reports
```

## Usage

### Command Line Interface

The `scripts/data_management.py` script provides a comprehensive CLI for data management operations:

```bash
# Create a new data version
python3 scripts/data_management.py create-version \
    --description "Added new Python repositories" \
    --author "developer@example.com" \
    --changes "Added repo1" "Added repo2"

# Verify data integrity
python3 scripts/data_management.py verify

# Show quality metrics
python3 scripts/data_management.py quality

# Generate data report
python3 scripts/data_management.py report --output-file report.json

# Run maintenance tasks
python3 scripts/data_management.py maintenance

# Add custom maintenance task
python3 scripts/data_management.py add-task \
    --name "custom-cleanup" \
    --description "Custom cleanup task" \
    --schedule "0 2 * * *" \
    --task-type cleanup \
    --command "rm -rf /tmp/validation_cache/*"
```

### CI/CD Integration

The `ci/run_data_management.sh` script integrates data management into CI/CD pipelines:

```bash
# Run full data management cycle
./ci/run_data_management.sh

# Force maintenance run
FORCE_MAINTENANCE=true ./ci/run_data_management.sh

# Create version after changes
CREATE_VERSION=true ./ci/run_data_management.sh
```

### Python API

#### ValidationDataManager

```python
from core.data_management.manager import ValidationDataManager

manager = ValidationDataManager()

# Create version
version_id = manager.create_version(
    description="Added new repositories",
    author="developer@example.com",
    changes=["Added repo1", "Added repo2"]
)

# Verify integrity
checks = manager.verify_integrity()
valid_files = [c for c in checks if c.is_valid]

# Get quality metrics
metrics = manager.get_quality_metrics()
print(f"Total repos: {metrics.total_repositories}")

# Generate report
report_file = manager.generate_data_report("data_report.json")
```

#### AutomatedDataMaintenance

```python
from core.data_management.maintenance import AutomatedDataMaintenance

maintenance = AutomatedDataMaintenance()

# Run maintenance cycle
results = maintenance.run_maintenance_cycle()

# Add custom task
task_id = maintenance.add_custom_task(
    name="custom-backup",
    description="Custom backup task",
    schedule="0 3 * * *",
    task_type="backup",
    command="rsync -av /data /backup"
)

# Update repository data
success = maintenance.update_repository_data()

# Monitor quality
metrics = maintenance.monitor_data_quality()
```

## Version Control

### Version Format
Versions follow semantic versioning: `MAJOR.MINOR.PATCH-TIMESTAMP`

- **MAJOR**: Breaking changes to data structure
- **MINOR**: New repositories or significant updates
- **PATCH**: Bug fixes, minor updates
- **TIMESTAMP**: Creation timestamp for uniqueness

### Version Metadata
Each version includes:
- **Description**: Human-readable description of changes
- **Author**: Person or system that created the version
- **Changes**: List of specific changes made
- **Metadata**: Additional structured data (e.g., test results, metrics)
- **Checksums**: SHA256 hashes of all data files
- **Timestamp**: Creation timestamp

## Integrity Verification

### Checksum Validation
- SHA256 checksums calculated for all data files
- Integrity checks run automatically during CI/CD
- Failed checks trigger alerts and prevent deployment

### Quality Metrics
- **Repository Count**: Total number of repositories
- **Language Coverage**: Languages represented in dataset
- **Repository Types**: Distribution of repository types
- **Data Freshness**: Age of repository data
- **Validation Success Rate**: Percentage of valid repositories

## Automated Maintenance

### Built-in Tasks

#### Data Updates (`update`)
- Fetches latest repository data
- Updates repository metadata
- Refreshes validation samples

#### Integrity Checks (`verify`)
- Validates all data file checksums
- Reports integrity violations
- Triggers alerts on failures

#### Cleanup (`cleanup`)
- Removes old versions beyond retention policy
- Cleans up temporary files
- Optimizes storage usage

#### Backup (`backup`)
- Creates compressed backups of all data
- Stores backups in secure location
- Maintains backup rotation

#### Quality Monitoring (`monitor`)
- Calculates quality metrics
- Generates quality reports
- Triggers alerts on quality degradation

### Scheduling
Tasks use cron-like scheduling:
- `update`: Daily at 2 AM
- `verify`: Every 4 hours
- `cleanup`: Weekly on Sunday
- `backup`: Daily at 3 AM
- `monitor`: Hourly

### Custom Tasks
Users can add custom maintenance tasks:
```python
maintenance.add_custom_task(
    name="custom-validation",
    description="Run custom validation checks",
    schedule="0 */6 * * *",  # Every 6 hours
    task_type="custom",
    command="python3 scripts/custom_validation.py"
)
```

## Quality Monitoring

### Metrics Tracked
- Repository validity percentage
- Language coverage completeness
- Data freshness (days since last update)
- File integrity status
- Storage utilization

### Alert Thresholds
- **Critical**: <95% repository validity
- **Warning**: <98% repository validity
- **Info**: Data older than 30 days

### Reporting
- Daily quality reports generated automatically
- CI/CD integration with quality gates
- Dashboard integration for real-time monitoring

## Backup and Recovery

### Backup Strategy
- **Full Backups**: Complete data snapshots
- **Incremental Backups**: Changes since last backup
- **Offsite Storage**: Backups stored in secure location
- **Retention**: 30 days of daily backups, 12 months of monthly backups

### Recovery Process
1. Identify backup to restore from
2. Verify backup integrity
3. Restore data to temporary location
4. Validate restored data
5. Switch to restored data

## Integration Points

### Continuous Validation Pipeline
- Data management integrated into validation workflow
- Automatic version creation on successful validation runs
- Quality metrics feed into effectiveness measurements

### A/B Testing Framework
- Data versioning supports experiment isolation
- Backup/restore enables experiment rollback
- Quality monitoring ensures experiment validity

### SME Review Process
- Data integrity verification before review assignments
- Version tracking for review context
- Automated data updates for review freshness

## Configuration

### Environment Variables
- `VALIDATION_DATA_PATH`: Path to validation data directory
- `BACKUP_RETENTION_DAYS`: Days to retain backups
- `MAINTENANCE_ENABLED`: Enable/disable automated maintenance
- `QUALITY_ALERT_THRESHOLD`: Quality alert threshold percentage

### Configuration Files
- `config/data_management.json`: Data management settings
- `config/maintenance_tasks.json`: Custom maintenance tasks
- `config/quality_thresholds.json`: Quality monitoring thresholds

## Monitoring and Alerting

### Health Checks
- Data integrity status
- Maintenance task execution
- Quality metric trends
- Storage utilization

### Alerts
- Email notifications for critical issues
- Slack/Discord integration for team alerts
- Dashboard integration for visual monitoring

## Troubleshooting

### Common Issues

#### Integrity Check Failures
- **Cause**: File corruption or unauthorized modifications
- **Solution**: Restore from backup, investigate root cause
- **Prevention**: Regular integrity checks, access controls

#### Maintenance Task Failures
- **Cause**: Network issues, permission problems, resource constraints
- **Solution**: Check logs, retry manually, adjust scheduling
- **Prevention**: Monitor task execution, implement retries

#### Quality Degradation
- **Cause**: Outdated data, repository changes, validation failures
- **Solution**: Update data, review validation logic
- **Prevention**: Regular quality monitoring, automated updates

### Debug Commands

```bash
# Detailed integrity check
python3 scripts/data_management.py verify --verbose

# Force maintenance run
FORCE_MAINTENANCE=true ./ci/run_data_management.sh

# Manual quality assessment
python3 scripts/data_management.py quality --detailed
```

## Performance Considerations

### Storage Optimization
- Compression for backups and archives
- Deduplication of similar repository data
- Cleanup of old versions and temporary files

### Execution Efficiency
- Parallel processing for integrity checks
- Incremental updates for large datasets
- Caching for frequently accessed metadata

### Scalability
- Distributed processing for large-scale operations
- Database integration for metadata management
- Cloud storage integration for backups

## Security

### Access Controls
- Role-based access to data management operations
- Audit logging for all changes
- Encryption for sensitive data

### Data Protection
- Encryption at rest for backups
- Secure transmission of data updates
- Compliance with data retention policies

## Future Enhancements

### Planned Features
- **Database Integration**: Migrate metadata to database for better querying
- **Distributed Processing**: Support for processing large datasets across multiple nodes
- **Machine Learning**: Automated quality assessment using ML models
- **Real-time Monitoring**: Live dashboards and alerting
- **API Integration**: REST API for external system integration

### Research Areas
- **Data Quality Prediction**: ML models to predict data quality issues
- **Automated Curation**: Intelligent selection of validation repositories
- **Cross-validation**: Validation across different data sources
- **Anomaly Detection**: Automated detection of data anomalies