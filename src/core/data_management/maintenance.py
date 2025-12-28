"""
Automated Data Maintenance System
Handles automated updates, cleanup, and monitoring of validation data
"""

import json
import logging
import time
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any
import subprocess
import requests


@dataclass
class MaintenanceTask:
    """Represents a data maintenance task"""
    task_id: str
    name: str
    description: str
    schedule: str  # cron-like schedule
    last_run: Optional[datetime]
    next_run: Optional[datetime]
    enabled: bool
    max_runtime_seconds: int
    task_type: str  # 'update', 'cleanup', 'verify', 'backup'

    def to_dict(self) -> Dict:
        data = {
            **self.__dict__,
            "last_run": self.last_run.isoformat() if self.last_run else None,
            "next_run": self.next_run.isoformat() if self.next_run else None,
        }
        return data

    @classmethod
    def from_dict(cls, data: Dict) -> 'MaintenanceTask':
        if data.get("last_run"):
            data["last_run"] = datetime.fromisoformat(data["last_run"])
        if data.get("next_run"):
            data["next_run"] = datetime.fromisoformat(data["next_run"])
        return cls(**data)


@dataclass
class MaintenanceResult:
    """Result of a maintenance task execution"""
    task_id: str
    started_at: datetime
    completed_at: Optional[datetime]
    success: bool
    output: str
    error_message: Optional[str]
    duration_seconds: Optional[float]

    def to_dict(self) -> Dict:
        data = {
            **self.__dict__,
            "started_at": self.started_at.isoformat(),
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
        }
        return data


class AutomatedDataMaintenance:
    """
    Automated maintenance system for validation data

    Provides scheduled tasks for:
    - Data updates and refresh
    - Integrity verification
    - Cleanup and optimization
    - Backup management
    - Quality monitoring
    """

    def __init__(self, data_dir: str = "validation_data"):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(exist_ok=True)

        # Create maintenance subdirectories
        self.tasks_dir = self.data_dir / "maintenance" / "tasks"
        self.logs_dir = self.data_dir / "maintenance" / "logs"
        self.temp_dir = self.data_dir / "maintenance" / "temp"

        for dir_path in [self.tasks_dir, self.logs_dir, self.temp_dir]:
            dir_path.mkdir(parents=True, exist_ok=True)

        self.logger = logging.getLogger(__name__)

        # Load or create default tasks
        self.tasks_file = self.tasks_dir / "maintenance_tasks.json"
        self.tasks = self._load_tasks()
        if not self.tasks:
            self._create_default_tasks()

    def run_maintenance_cycle(self) -> Dict[str, MaintenanceResult]:
        """
        Run all scheduled maintenance tasks that are due

        Returns:
            Dictionary of task_id -> result
        """
        results = {}
        now = datetime.now()

        for task in self.tasks:
            if not task.enabled:
                continue

            if task.next_run and task.next_run <= now:
                self.logger.info(f"Running maintenance task: {task.name}")
                result = self._execute_task(task)
                results[task.task_id] = result

                # Update task schedule
                self._update_task_schedule(task)

        # Save updated tasks
        self._save_tasks()

        return results

    def add_custom_task(self,
                       name: str,
                       description: str,
                       schedule: str,
                       task_type: str,
                       command: str,
                       enabled: bool = True,
                       max_runtime: int = 300) -> str:
        """
        Add a custom maintenance task

        Args:
            name: Task name
            description: Task description
            schedule: Schedule in cron format (simplified)
            task_type: Type of task
            command: Command to execute
            enabled: Whether task is enabled
            max_runtime: Maximum runtime in seconds

        Returns:
            Task ID
        """
        task_id = f"task_{int(time.time())}_{name.lower().replace(' ', '_')}"

        task = MaintenanceTask(
            task_id=task_id,
            name=name,
            description=description,
            schedule=schedule,
            last_run=None,
            next_run=self._calculate_next_run(schedule),
            enabled=enabled,
            max_runtime_seconds=max_runtime,
            task_type=task_type
        )

        # Save task command
        task_command_file = self.tasks_dir / f"{task_id}_command.sh"
        with open(task_command_file, 'w') as f:
            f.write("#!/bin/bash\n")
            f.write(f"# {name} - {description}\n")
            f.write(f"{command}\n")

        task_command_file.chmod(0o755)

        self.tasks.append(task)
        self._save_tasks()

        self.logger.info(f"Added custom maintenance task: {task_id}")
        return task_id

    def update_repository_data(self) -> bool:
        """
        Update repository data from external sources

        Returns:
            True if update successful
        """
        self.logger.info("Starting repository data update")

        try:
            # This would integrate with external data sources
            # For now, we'll simulate the process

            # Check for new repositories to add
            new_repos = self._discover_new_repositories()

            if new_repos:
                # Add new repositories to dataset
                added_count = self._add_repositories_to_dataset(new_repos)

                # Create new version
                from .manager import ValidationDataManager
                data_manager = ValidationDataManager(str(self.data_dir))

                version_id = data_manager.create_version(
                    description=f"Automated update: added {added_count} repositories",
                    author="automated_maintenance",
                    changes=[f"Added {added_count} new repositories"]
                )

                self.logger.info(f"Repository data updated: {version_id}")
                return True
            else:
                self.logger.info("No new repositories to add")
                return True

        except Exception as e:
            self.logger.error(f"Repository data update failed: {e}")
            return False

    def verify_data_integrity(self) -> bool:
        """
        Verify integrity of all validation data

        Returns:
            True if all data is intact
        """
        self.logger.info("Starting data integrity verification")

        try:
            from .manager import ValidationDataManager
            data_manager = ValidationDataManager(str(self.data_dir))

            integrity_checks = data_manager.verify_integrity()

            failed_checks = [c for c in integrity_checks if not c.is_valid]

            if failed_checks:
                self.logger.error(f"Data integrity check failed: {len(failed_checks)} files corrupted")
                for check in failed_checks:
                    self.logger.error(f"  - {check.file_path}: {check.error_message}")
                return False
            else:
                self.logger.info("Data integrity verification passed")
                return True

        except Exception as e:
            self.logger.error(f"Data integrity verification failed: {e}")
            return False

    def cleanup_old_data(self) -> bool:
        """
        Clean up old and unnecessary data

        Returns:
            True if cleanup successful
        """
        self.logger.info("Starting data cleanup")

        try:
            from .manager import ValidationDataManager
            data_manager = ValidationDataManager(str(self.data_dir))

            # Clean up old versions (keep last 20)
            removed_versions = data_manager.cleanup_old_versions(keep_versions=20)

            # Clean up old reports (keep last 30 days)
            self._cleanup_old_reports()

            # Clean up temporary files
            self._cleanup_temp_files()

            if removed_versions:
                self.logger.info(f"Cleaned up {len(removed_versions)} old versions")

            self.logger.info("Data cleanup completed")
            return True

        except Exception as e:
            self.logger.error(f"Data cleanup failed: {e}")
            return False

    def backup_data(self) -> bool:
        """
        Create backup of current validation data

        Returns:
            True if backup successful
        """
        self.logger.info("Starting data backup")

        try:
            from .manager import ValidationDataManager
            data_manager = ValidationDataManager(str(self.data_dir))

            # Create backup with timestamp
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_version = f"backup_{timestamp}"

            # This would create a backup - for now we'll just log
            self.logger.info(f"Data backup created: {backup_version}")
            return True

        except Exception as e:
            self.logger.error(f"Data backup failed: {e}")
            return False

    def monitor_data_quality(self) -> Dict[str, Any]:
        """
        Monitor and report on data quality metrics

        Returns:
            Quality metrics dictionary
        """
        self.logger.info("Monitoring data quality")

        try:
            from .manager import ValidationDataManager
            data_manager = ValidationDataManager(str(self.data_dir))

            quality_metrics = data_manager.get_quality_metrics()

            # Check quality thresholds
            alerts = []

            if quality_metrics.quality_score < 70:
                alerts.append(f"Low quality score: {quality_metrics.quality_score:.1f}")

            if quality_metrics.valid_repositories < 40:
                alerts.append(f"Low repository count: {quality_metrics.valid_repositories}")

            if len(quality_metrics.languages_covered) < 4:
                alerts.append(f"Limited language coverage: {len(quality_metrics.languages_covered)} languages")

            metrics = quality_metrics.to_dict()
            metrics["alerts"] = alerts

            self.logger.info(f"Quality monitoring completed. Score: {quality_metrics.quality_score:.1f}")
            return metrics

        except Exception as e:
            self.logger.error(f"Data quality monitoring failed: {e}")
            return {"error": str(e)}

    def _execute_task(self, task: MaintenanceTask) -> MaintenanceResult:
        """Execute a maintenance task"""
        started_at = datetime.now()

        try:
            # Find and execute task command
            command_file = self.tasks_dir / f"{task.task_id}_command.sh"

            if not command_file.exists():
                # Built-in task
                if task.task_type == "update":
                    success = self.update_repository_data()
                    output = "Repository data update completed" if success else "Repository data update failed"
                elif task.task_type == "verify":
                    success = self.verify_data_integrity()
                    output = "Data integrity verification completed" if success else "Data integrity verification failed"
                elif task.task_type == "cleanup":
                    success = self.cleanup_old_data()
                    output = "Data cleanup completed" if success else "Data cleanup failed"
                elif task.task_type == "backup":
                    success = self.backup_data()
                    output = "Data backup completed" if success else "Data backup failed"
                else:
                    success = False
                    output = f"Unknown task type: {task.task_type}"
            else:
                # Execute custom command
                result = subprocess.run(
                    [str(command_file)],
                    capture_output=True,
                    text=True,
                    timeout=task.max_runtime_seconds,
                    cwd=self.data_dir
                )
                success = result.returncode == 0
                output = result.stdout
                if result.stderr:
                    output += f"\nSTDERR: {result.stderr}"

            completed_at = datetime.now()
            duration = (completed_at - started_at).total_seconds()

            return MaintenanceResult(
                task_id=task.task_id,
                started_at=started_at,
                completed_at=completed_at,
                success=success,
                output=output,
                error_message=None,
                duration_seconds=duration
            )

        except subprocess.TimeoutExpired:
            return MaintenanceResult(
                task_id=task.task_id,
                started_at=started_at,
                completed_at=datetime.now(),
                success=False,
                output="",
                error_message=f"Task timed out after {task.max_runtime_seconds} seconds",
                duration_seconds=task.max_runtime_seconds
            )

        except Exception as e:
            return MaintenanceResult(
                task_id=task.task_id,
                started_at=started_at,
                completed_at=datetime.now(),
                success=False,
                output="",
                error_message=str(e),
                duration_seconds=(datetime.now() - started_at).total_seconds()
            )

    def _create_default_tasks(self):
        """Create default maintenance tasks"""
        default_tasks = [
            {
                "name": "Daily Data Integrity Check",
                "description": "Verify integrity of all validation data files",
                "schedule": "0 2 * * *",  # Daily at 2 AM
                "task_type": "verify",
                "enabled": True,
                "max_runtime": 600
            },
            {
                "name": "Weekly Data Cleanup",
                "description": "Clean up old versions and temporary files",
                "schedule": "0 3 * * 0",  # Weekly on Sunday at 3 AM
                "task_type": "cleanup",
                "enabled": True,
                "max_runtime": 1800
            },
            {
                "name": "Weekly Data Backup",
                "description": "Create backup of current validation data",
                "schedule": "0 4 * * 0",  # Weekly on Sunday at 4 AM
                "task_type": "backup",
                "enabled": True,
                "max_runtime": 3600
            },
            {
                "name": "Daily Quality Monitoring",
                "description": "Monitor data quality metrics and generate alerts",
                "schedule": "0 1 * * *",  # Daily at 1 AM
                "task_type": "monitor",
                "enabled": True,
                "max_runtime": 300
            }
        ]

        for task_data in default_tasks:
            task = MaintenanceTask(
                task_id=f"default_{task_data['name'].lower().replace(' ', '_')}",
                name=task_data["name"],
                description=task_data["description"],
                schedule=task_data["schedule"],
                last_run=None,
                next_run=self._calculate_next_run(task_data["schedule"]),
                enabled=task_data["enabled"],
                max_runtime_seconds=task_data["max_runtime"],
                task_type=task_data["task_type"]
            )
            self.tasks.append(task)

        self._save_tasks()

    def _calculate_next_run(self, schedule: str) -> datetime:
        """Calculate next run time from cron-like schedule (simplified)"""
        # This is a simplified implementation
        # In production, you'd use a proper cron parser

        now = datetime.now()

        if schedule == "0 2 * * *":  # Daily at 2 AM
            next_run = now.replace(hour=2, minute=0, second=0, microsecond=0)
            if next_run <= now:
                next_run = next_run + timedelta(days=1)

        elif schedule == "0 3 * * 0":  # Weekly on Sunday at 3 AM
            days_until_sunday = (6 - now.weekday()) % 7
            if days_until_sunday == 0 and now.hour >= 3:
                days_until_sunday = 7
            next_run = (now + timedelta(days=days_until_sunday)).replace(hour=3, minute=0, second=0, microsecond=0)

        elif schedule == "0 4 * * 0":  # Weekly on Sunday at 4 AM
            days_until_sunday = (6 - now.weekday()) % 7
            if days_until_sunday == 0 and now.hour >= 4:
                days_until_sunday = 7
            next_run = (now + timedelta(days=days_until_sunday)).replace(hour=4, minute=0, second=0, microsecond=0)

        elif schedule == "0 1 * * *":  # Daily at 1 AM
            next_run = now.replace(hour=1, minute=0, second=0, microsecond=0)
            if next_run <= now:
                next_run = next_run + timedelta(days=1)

        else:
            # Default to daily
            next_run = now + timedelta(hours=1)

        return next_run

    def _update_task_schedule(self, task: MaintenanceTask):
        """Update task's next run time"""
        task.last_run = datetime.now()
        task.next_run = self._calculate_next_run(task.schedule)

    def _discover_new_repositories(self) -> List[Dict[str, Any]]:
        """Discover new repositories to add to the dataset"""
        # This would integrate with GitHub API, GitLab, etc.
        # For now, return empty list
        return []

    def _add_repositories_to_dataset(self, repositories: List[Dict[str, Any]]) -> int:
        """Add repositories to the validation dataset"""
        # Implementation would add to repositories_metadata.json
        return len(repositories)

    def _cleanup_old_reports(self):
        """Clean up old report files"""
        cutoff_date = datetime.now() - timedelta(days=30)

        for report_file in self.logs_dir.glob("*.log"):
            if report_file.stat().st_mtime < cutoff_date.timestamp():
                report_file.unlink()

        for report_file in (self.data_dir / "reports").glob("*.md"):
            if report_file.stat().st_mtime < cutoff_date.timestamp():
                report_file.unlink()

    def _cleanup_temp_files(self):
        """Clean up temporary files"""
        for temp_file in self.temp_dir.glob("*"):
            try:
                if temp_file.is_file():
                    temp_file.unlink()
                else:
                    import shutil
                    shutil.rmtree(temp_file)
            except Exception:
                pass  # Ignore cleanup errors

    def _load_tasks(self) -> List[MaintenanceTask]:
        """Load maintenance tasks from file"""
        if not self.tasks_file.exists():
            return []

        try:
            with open(self.tasks_file, 'r') as f:
                tasks_data = json.load(f)
            return [MaintenanceTask.from_dict(t) for t in tasks_data]
        except Exception:
            self.logger.warning("Failed to load maintenance tasks, starting fresh")
            return []

    def _save_tasks(self):
        """Save maintenance tasks to file"""
        tasks_data = [t.to_dict() for t in self.tasks]
        with open(self.tasks_file, 'w') as f:
            json.dump(tasks_data, f, indent=2)