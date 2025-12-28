"""
Validation Data Versioning and Management System
Manages versioning, integrity, and maintenance of validation datasets
"""

import json
import hashlib
import os
import shutil
from dataclasses import dataclass, asdict
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
import logging


@dataclass
class DataVersion:
    """Represents a version of validation data"""
    version_id: str
    timestamp: datetime
    description: str
    author: str
    parent_version: Optional[str]
    checksums: Dict[str, str]  # file_path -> checksum
    metadata: Dict[str, Any]
    changes: List[str]

    def to_dict(self) -> Dict:
        data = asdict(self)
        data["timestamp"] = self.timestamp.isoformat()
        return data

    @classmethod
    def from_dict(cls, data: Dict) -> 'DataVersion':
        data["timestamp"] = datetime.fromisoformat(data["timestamp"])
        return cls(**data)


@dataclass
class DataIntegrityCheck:
    """Result of data integrity verification"""
    file_path: str
    expected_checksum: str
    actual_checksum: str
    is_valid: bool
    checked_at: datetime
    error_message: Optional[str] = None

    def to_dict(self) -> Dict:
        data = asdict(self)
        data["checked_at"] = self.checked_at.isoformat()
        return data


@dataclass
class DataQualityMetrics:
    """Quality metrics for validation data"""
    total_repositories: int
    valid_repositories: int
    invalid_repositories: int
    languages_covered: List[str]
    repository_types: Dict[str, int]
    average_file_count: float
    total_file_size_mb: float
    last_updated: datetime
    quality_score: float  # 0-100

    def to_dict(self) -> Dict:
        data = asdict(self)
        data["last_updated"] = self.last_updated.isoformat()
        return data


class ValidationDataManager:
    """
    Manages versioning, integrity, and maintenance of validation datasets

    Provides comprehensive data management capabilities including:
    - Version control for datasets
    - Integrity verification
    - Automated maintenance
    - Quality monitoring
    - Backup and recovery
    """

    def __init__(self, data_dir: str = "validation_data"):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(exist_ok=True)

        # Create management subdirectories
        self.versions_dir = self.data_dir / "versions"
        self.backups_dir = self.data_dir / "backups"
        self.reports_dir = self.data_dir / "reports"
        self.temp_dir = self.data_dir / "temp"

        for dir_path in [self.versions_dir, self.backups_dir, self.reports_dir, self.temp_dir]:
            dir_path.mkdir(exist_ok=True)

        self.logger = logging.getLogger(__name__)

        # Load or create version history
        self.version_history_file = self.versions_dir / "version_history.json"
        self.version_history = self._load_version_history()

    def create_version(self,
                      description: str,
                      author: str,
                      changes: List[str],
                      metadata: Optional[Dict[str, Any]] = None) -> str:
        """
        Create a new version of the validation data

        Args:
            description: Description of this version
            author: Author of the changes
            changes: List of changes made
            metadata: Additional metadata

        Returns:
            Version ID
        """
        if metadata is None:
            metadata = {}

        # Generate version ID
        timestamp = datetime.now()
        version_id = f"v{timestamp.strftime('%Y%m%d_%H%M%S')}"

        # Calculate checksums for all data files
        checksums = self._calculate_data_checksums()

        # Create version object
        parent_version = self.version_history[-1].version_id if self.version_history else None

        version = DataVersion(
            version_id=version_id,
            timestamp=timestamp,
            description=description,
            author=author,
            parent_version=parent_version,
            checksums=checksums,
            metadata=metadata,
            changes=changes
        )

        # Save version to history
        self.version_history.append(version)
        self._save_version_history()

        # Create backup of current state
        self._create_backup(version_id)

        self.logger.info(f"Created validation data version: {version_id}")
        return version_id

    def verify_integrity(self, version_id: Optional[str] = None) -> List[DataIntegrityCheck]:
        """
        Verify integrity of validation data

        Args:
            version_id: Specific version to check (default: current)

        Returns:
            List of integrity check results
        """
        if version_id:
            version = next((v for v in self.version_history if v.version_id == version_id), None)
            if not version:
                raise ValueError(f"Version {version_id} not found")
        else:
            version = self.version_history[-1] if self.version_history else None
            if not version:
                return []  # No versions to check

        checks = []
        for file_path, expected_checksum in version.checksums.items():
            full_path = self.data_dir / file_path

            if not full_path.exists():
                check = DataIntegrityCheck(
                    file_path=file_path,
                    expected_checksum=expected_checksum,
                    actual_checksum="",
                    is_valid=False,
                    checked_at=datetime.now(),
                    error_message="File not found"
                )
            else:
                actual_checksum = self._calculate_file_checksum(full_path)
                is_valid = actual_checksum == expected_checksum

                check = DataIntegrityCheck(
                    file_path=file_path,
                    expected_checksum=expected_checksum,
                    actual_checksum=actual_checksum,
                    is_valid=is_valid,
                    checked_at=datetime.now(),
                    error_message=None if is_valid else "Checksum mismatch"
                )

            checks.append(check)

        return checks

    def get_quality_metrics(self) -> DataQualityMetrics:
        """Calculate quality metrics for the current validation data"""
        repositories_file = self.data_dir / "repositories" / "repositories_metadata.json"

        if not repositories_file.exists():
            return DataQualityMetrics(
                total_repositories=0,
                valid_repositories=0,
                invalid_repositories=0,
                languages_covered=[],
                repository_types={},
                average_file_count=0.0,
                total_file_size_mb=0.0,
                last_updated=datetime.now(),
                quality_score=0.0
            )

        with open(repositories_file, 'r') as f:
            metadata = json.load(f)

        total_repos = len(metadata)
        valid_repos = 0
        languages = set()
        repo_types = {}
        total_files = 0
        total_size = 0

        for repo_data in metadata.values():
            if repo_data.get('validation_status') == 'collected':
                valid_repos += 1

                # Language coverage
                lang = repo_data.get('language', 'unknown')
                languages.add(lang)

                # Repository types
                repo_type = repo_data.get('type', 'unknown')
                repo_types[repo_type] = repo_types.get(repo_type, 0) + 1

                # File statistics
                total_files += repo_data.get('file_count', 0)
                total_size += repo_data.get('total_size_bytes', 0)

        average_files = total_files / valid_repos if valid_repos > 0 else 0
        total_size_mb = total_size / (1024 * 1024)

        # Calculate quality score (0-100)
        quality_score = self._calculate_quality_score(
            total_repos, valid_repos, len(languages), len(repo_types)
        )

        return DataQualityMetrics(
            total_repositories=total_repos,
            valid_repositories=valid_repos,
            invalid_repositories=total_repos - valid_repos,
            languages_covered=sorted(list(languages)),
            repository_types=repo_types,
            average_file_count=average_files,
            total_file_size_mb=total_size_mb,
            last_updated=datetime.now(),
            quality_score=quality_score
        )

    def _calculate_quality_score(self, total: int, valid: int, languages: int, types: int) -> float:
        """Calculate overall quality score"""
        if total == 0:
            return 0.0

        # Base score from validity
        validity_score = (valid / total) * 40  # 40% weight

        # Language coverage (6 languages = 100%)
        language_score = min(languages / 6 * 30, 30)  # 30% weight

        # Repository type diversity
        type_score = min(types / 5 * 20, 20)  # 20% weight

        # Minimum repository count
        count_score = min(total / 50 * 10, 10)  # 10% weight

        return validity_score + language_score + type_score + count_score

    def cleanup_old_versions(self, keep_versions: int = 10) -> List[str]:
        """
        Clean up old versions, keeping only the most recent ones

        Args:
            keep_versions: Number of recent versions to keep

        Returns:
            List of removed version IDs
        """
        if len(self.version_history) <= keep_versions:
            return []

        # Keep most recent versions
        versions_to_remove = self.version_history[:-keep_versions]
        removed_ids = [v.version_id for v in versions_to_remove]

        # Remove from history
        self.version_history = self.version_history[-keep_versions:]
        self._save_version_history()

        # Remove backup files
        for version_id in removed_ids:
            backup_file = self.backups_dir / f"{version_id}.tar.gz"
            if backup_file.exists():
                backup_file.unlink()

        self.logger.info(f"Cleaned up {len(removed_ids)} old versions")
        return removed_ids

    def restore_version(self, version_id: str) -> bool:
        """
        Restore validation data to a specific version

        Args:
            version_id: Version ID to restore

        Returns:
            True if restoration successful
        """
        backup_file = self.backups_dir / f"{version_id}.tar.gz"
        if not backup_file.exists():
            raise ValueError(f"Backup for version {version_id} not found")

        # Create current backup before restoration
        current_version = self.version_history[-1] if self.version_history else None
        if current_version:
            self._create_backup(f"{current_version.version_id}_pre_restore")

        # Extract backup
        import tarfile
        with tarfile.open(backup_file, 'r:gz') as tar:
            # Remove current data (except management dirs)
            for item in self.data_dir.iterdir():
                if item.name not in ['versions', 'backups', 'reports', 'temp']:
                    if item.is_file():
                        item.unlink()
                    else:
                        shutil.rmtree(item)

            # Extract backup
            tar.extractall(self.data_dir)

        self.logger.info(f"Restored validation data to version: {version_id}")
        return True

    def generate_data_report(self, output_file: Optional[str] = None) -> str:
        """Generate comprehensive data management report"""
        if output_file is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_file = self.reports_dir / f"data_management_report_{timestamp}.md"

        report_path = Path(output_file)
        report_path.parent.mkdir(exist_ok=True)

        # Get current metrics
        quality_metrics = self.get_quality_metrics()
        integrity_checks = self.verify_integrity()

        with open(report_path, 'w') as f:
            f.write("# Validation Data Management Report\n")
            f.write(f"**Generated:** {datetime.now().isoformat()}\n\n")

            f.write("## Data Quality Metrics\n")
            f.write(f"- **Total Repositories:** {quality_metrics.total_repositories}\n")
            f.write(f"- **Valid Repositories:** {quality_metrics.valid_repositories}\n")
            f.write(f"- **Invalid Repositories:** {quality_metrics.invalid_repositories}\n")
            f.write(f"- **Languages Covered:** {', '.join(quality_metrics.languages_covered)}\n")
            f.write(f"- **Repository Types:** {quality_metrics.repository_types}\n")
            f.write(".1f")
            f.write(".1f")
            f.write(".1f")
            f.write("\n")

            f.write("## Data Integrity Status\n")
            valid_checks = len([c for c in integrity_checks if c.is_valid])
            total_checks = len(integrity_checks)

            if total_checks > 0:
                integrity_percentage = (valid_checks / total_checks) * 100
                f.write(".1f")
                f.write(f"- **Valid Files:** {valid_checks}/{total_checks}\n")

                if integrity_checks:
                    f.write("\n### Integrity Issues\n")
                    for check in integrity_checks:
                        if not check.is_valid:
                            f.write(f"- ❌ **{check.file_path}**: {check.error_message}\n")
            else:
                f.write("No integrity checks performed (no version history)\n")

            f.write("\n## Version History\n")
            if self.version_history:
                for version in reversed(self.version_history[-5:]):  # Show last 5 versions
                    f.write(f"### {version.version_id}\n")
                    f.write(f"- **Date:** {version.timestamp.isoformat()}\n")
                    f.write(f"- **Author:** {version.author}\n")
                    f.write(f"- **Description:** {version.description}\n")
                    f.write(f"- **Changes:** {len(version.changes)}\n")
                    f.write("\n")
            else:
                f.write("No version history available\n")

        return str(report_path)

    def _calculate_data_checksums(self) -> Dict[str, str]:
        """Calculate checksums for all validation data files"""
        checksums = {}

        # Walk through data directory
        for root, dirs, files in os.walk(self.data_dir):
            # Skip management directories
            dirs[:] = [d for d in dirs if d not in ['versions', 'backups', 'reports', 'temp']]

            for file in files:
                file_path = Path(root) / file
                relative_path = file_path.relative_to(self.data_dir)
                checksums[str(relative_path)] = self._calculate_file_checksum(file_path)

        return checksums

    def _calculate_file_checksum(self, file_path: Path) -> str:
        """Calculate SHA256 checksum of a file"""
        hash_sha256 = hashlib.sha256()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_sha256.update(chunk)
        return hash_sha256.hexdigest()

    def _create_backup(self, version_id: str):
        """Create a backup of current validation data"""
        import tarfile

        backup_file = self.backups_dir / f"{version_id}.tar.gz"

        with tarfile.open(backup_file, 'w:gz') as tar:
            # Add all data files (except management dirs)
            for item in self.data_dir.iterdir():
                if item.name not in ['versions', 'backups', 'reports', 'temp']:
                    tar.add(item, arcname=item.name)

    def _load_version_history(self) -> List[DataVersion]:
        """Load version history from file"""
        if not self.version_history_file.exists():
            return []

        try:
            with open(self.version_history_file, 'r') as f:
                history_data = json.load(f)
            return [DataVersion.from_dict(v) for v in history_data]
        except Exception:
            self.logger.warning("Failed to load version history, starting fresh")
            return []

    def _save_version_history(self):
        """Save version history to file"""
        history_data = [v.to_dict() for v in self.version_history]
        with open(self.version_history_file, 'w') as f:
            json.dump(history_data, f, indent=2)