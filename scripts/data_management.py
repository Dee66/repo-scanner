#!/usr/bin/env python3
"""
Validation Data Management CLI
Command-line interface for managing validation data versioning and maintenance
"""

import argparse
import json
import sys
from pathlib import Path
from datetime import datetime

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / 'src'))

from core.data_management.manager import ValidationDataManager
from core.data_management.maintenance import AutomatedDataMaintenance


def create_version(args):
    """Create a new version of validation data"""
    manager = ValidationDataManager()

    changes = args.changes if args.changes else ["Manual version creation"]

    version_id = manager.create_version(
        description=args.description,
        author=args.author,
        changes=changes,
        metadata=args.metadata if args.metadata else {}
    )

    print(f"✅ Created validation data version: {version_id}")
    return version_id


def verify_integrity(args):
    """Verify data integrity"""
    manager = ValidationDataManager()

    checks = manager.verify_integrity(args.version_id if args.version_id else None)

    valid_count = len([c for c in checks if c.is_valid])
    total_count = len(checks)

    print(f"🔍 Data Integrity Check Results:")
    print(f"   Valid files: {valid_count}/{total_count}")

    if checks:
        failed_checks = [c for c in checks if not c.is_valid]
        if failed_checks:
            print("\n❌ Integrity Issues:")
            for check in failed_checks:
                print(f"   - {check.file_path}: {check.error_message}")
            sys.exit(1)
        else:
            print("✅ All files passed integrity check")
    else:
        print("ℹ️  No files to check")


def show_quality_metrics(args):
    """Show data quality metrics"""
    manager = ValidationDataManager()

    metrics = manager.get_quality_metrics()

    print("📊 Validation Data Quality Metrics:")
    print(f"   Total Repositories: {metrics.total_repositories}")
    print(f"   Valid Repositories: {metrics.valid_repositories}")
    print(f"   Invalid Repositories: {metrics.invalid_repositories}")
    print(f"   Languages Covered: {', '.join(metrics.languages_covered)}")
    print(f"   Repository Types: {metrics.repository_types}")
    print(f"   Average File Count: {metrics.average_file_count:.1f}")
    print(f"   Total File Size: {metrics.total_file_size_mb:.1f} MB")
    print(f"   Quality Score: {metrics.quality_score:.1f}%")
    print(f"   Last Updated: {metrics.last_updated.isoformat()}")


def generate_report(args):
    """Generate data management report"""
    manager = ValidationDataManager()

    report_file = manager.generate_data_report(args.output_file)
    print(f"📋 Generated data management report: {report_file}")


def run_maintenance(args):
    """Run automated maintenance tasks"""
    maintenance = AutomatedDataMaintenance()

    print("🔧 Running automated maintenance tasks...")

    results = maintenance.run_maintenance_cycle()

    if results:
        print(f"✅ Executed {len(results)} maintenance tasks:")

        for task_id, result in results.items():
            status = "✅" if result.success else "❌"
            duration = ".1f" if result.duration_seconds else "N/A"
            print(f"   {status} {task_id}: {duration}s")

            if not result.success and result.error_message:
                print(f"      Error: {result.error_message}")
    else:
        print("ℹ️  No maintenance tasks were due to run")


def add_maintenance_task(args):
    """Add a custom maintenance task"""
    maintenance = AutomatedDataMaintenance()

    task_id = maintenance.add_custom_task(
        name=args.name,
        description=args.description,
        schedule=args.schedule,
        task_type=args.task_type,
        command=args.command,
        enabled=not args.disabled,
        max_runtime=args.max_runtime
    )

    print(f"✅ Added maintenance task: {task_id}")


def update_data(args):
    """Update repository data"""
    maintenance = AutomatedDataMaintenance()

    success = maintenance.update_repository_data()

    if success:
        print("✅ Repository data updated successfully")
    else:
        print("❌ Repository data update failed")
        sys.exit(1)


def cleanup_data(args):
    """Clean up old data"""
    manager = ValidationDataManager()

    removed_versions = manager.cleanup_old_data(args.keep_versions)

    if removed_versions:
        print(f"🧹 Cleaned up {len(removed_versions)} old versions:")
        for version_id in removed_versions:
            print(f"   - {version_id}")
    else:
        print("ℹ️  No old versions to clean up")


def backup_data(args):
    """Create data backup"""
    maintenance = AutomatedDataMaintenance()

    success = maintenance.backup_data()

    if success:
        print("💾 Data backup created successfully")
    else:
        print("❌ Data backup failed")
        sys.exit(1)


def monitor_quality(args):
    """Monitor data quality"""
    maintenance = AutomatedDataMaintenance()

    metrics = maintenance.monitor_data_quality()

    if "error" in metrics:
        print(f"❌ Quality monitoring failed: {metrics['error']}")
        sys.exit(1)

    print("📊 Data Quality Monitoring Results:")
    print(f"   Repository Validity: {metrics.get('validity_rate', 0):.1f}%")
    print(f"   Repository Count: {metrics.get('valid_repositories', 0)}")
    print(f"   Language Coverage: {len(metrics.get('languages_covered', []))}")

    alerts = metrics.get('alerts', [])
    if alerts:
        print("\n⚠️  Quality Alerts:")
        for alert in alerts:
            print(f"   - {alert}")
    else:
        print("✅ No quality issues detected")


def main():
    parser = argparse.ArgumentParser(description="Validation Data Management CLI")
    subparsers = parser.add_subparsers(dest='command', help='Available commands')

    # Create version
    create_parser = subparsers.add_parser('create-version', help='Create a new data version')
    create_parser.add_argument('--description', required=True, help='Version description')
    create_parser.add_argument('--author', required=True, help='Version author')
    create_parser.add_argument('--changes', nargs='+', help='List of changes')
    create_parser.add_argument('--metadata', help='JSON metadata file')

    # Verify integrity
    verify_parser = subparsers.add_parser('verify', help='Verify data integrity')
    verify_parser.add_argument('--version-id', help='Specific version to verify')

    # Quality metrics
    quality_parser = subparsers.add_parser('quality', help='Show quality metrics')

    # Generate report
    report_parser = subparsers.add_parser('report', help='Generate data management report')
    report_parser.add_argument('--output-file', help='Output file path')

    # Run maintenance
    maintenance_parser = subparsers.add_parser('maintenance', help='Run maintenance tasks')

    # Add maintenance task
    add_task_parser = subparsers.add_parser('add-task', help='Add custom maintenance task')
    add_task_parser.add_argument('--name', required=True, help='Task name')
    add_task_parser.add_argument('--description', required=True, help='Task description')
    add_task_parser.add_argument('--schedule', required=True, help='Schedule (cron format)')
    add_task_parser.add_argument('--task-type', required=True,
                                choices=['update', 'cleanup', 'verify', 'backup', 'monitor'],
                                help='Task type')
    add_task_parser.add_argument('--command', required=True, help='Command to execute')
    add_task_parser.add_argument('--disabled', action='store_true', help='Create disabled task')
    add_task_parser.add_argument('--max-runtime', type=int, default=300, help='Max runtime seconds')

    # Update data
    update_parser = subparsers.add_parser('update', help='Update repository data')

    # Cleanup data
    cleanup_parser = subparsers.add_parser('cleanup', help='Clean up old data')
    cleanup_parser.add_argument('--keep-versions', type=int, default=20, help='Versions to keep')

    # Backup data
    backup_parser = subparsers.add_parser('backup', help='Create data backup')

    # Monitor quality
    monitor_parser = subparsers.add_parser('monitor', help='Monitor data quality')

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    if args.command == 'create-version':
        create_version(args)
    elif args.command == 'verify':
        verify_integrity(args)
    elif args.command == 'quality':
        show_quality_metrics(args)
    elif args.command == 'report':
        generate_report(args)
    elif args.command == 'maintenance':
        run_maintenance(args)
    elif args.command == 'add-task':
        add_maintenance_task(args)
    elif args.command == 'update':
        update_data(args)
    elif args.command == 'cleanup':
        cleanup_data(args)
    elif args.command == 'backup':
        backup_data(args)
    elif args.command == 'monitor':
        monitor_quality(args)


if __name__ == '__main__':
    main()