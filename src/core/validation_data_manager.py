"""
Validation Data Versioning and Management System

Manages versioning, metadata, and lifecycle of validation datasets
used for testing and effectiveness validation.
"""

import json
import hashlib
import shutil
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any, Optional
import difflib


class ValidationDataManager:
    """
    Manages validation data versioning and lifecycle.

    Provides:
    - Version control for validation datasets
    - Metadata tracking and change history
    - Rollback capabilities
    - Data integrity verification
    - Automated cleanup of old versions
    """

    def __init__(self, validation_dir: str = "validation_data"):
        self.validation_dir = Path(validation_dir)
        self.versions_dir = self.validation_dir / "versions"
        self.metadata_dir = self.validation_dir / "metadata"
        self.backups_dir = self.validation_dir / "backups"

        # Create directories
        for dir_path in [self.versions_dir, self.metadata_dir, self.backups_dir]:
            dir_path.mkdir(exist_ok=True)

    def create_version(self, dataset_name: str, data: Dict[str, Any],
                      description: str = "", author: str = "system") -> str:
        """
        Create a new version of a validation dataset.

        Args:
            dataset_name: Name of the dataset
            data: Dataset content
            description: Description of changes
            author: Author of the version

        Returns:
            Version ID
        """
        # Generate version ID based on content hash
        content_str = json.dumps(data, sort_keys=True)
        content_hash = hashlib.sha256(content_str.encode()).hexdigest()[:16]
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        version_id = f"{dataset_name}_{timestamp}_{content_hash}"

        # Save version data
        version_file = self.versions_dir / f"{version_id}.json"
        with open(version_file, 'w') as f:
            json.dump(data, f, indent=2)

        # Create metadata
        metadata = {
            "version_id": version_id,
            "dataset_name": dataset_name,
            "created_at": datetime.now().isoformat(),
            "author": author,
            "description": description,
            "content_hash": content_hash,
            "data_size": len(content_str),
            "record_count": self._count_records(data),
            "previous_version": self._get_latest_version(dataset_name)
        }

        # Save metadata
        metadata_file = self.metadata_dir / f"{version_id}_metadata.json"
        with open(metadata_file, 'w') as f:
            json.dump(metadata, f, indent=2)

        # Update current version pointer
        self._update_current_version(dataset_name, version_id)

        return version_id

    def get_version(self, dataset_name: str, version_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Get a specific version of a dataset.

        Args:
            dataset_name: Name of the dataset
            version_id: Specific version ID, or None for latest

        Returns:
            Dataset content
        """
        if version_id is None:
            version_id = self._get_current_version(dataset_name)

        if not version_id:
            raise ValueError(f"No versions found for dataset {dataset_name}")

        version_file = self.versions_dir / f"{version_id}.json"
        if not version_file.exists():
            raise FileNotFoundError(f"Version {version_id} not found")

        with open(version_file, 'r') as f:
            return json.load(f)

    def list_versions(self, dataset_name: str) -> List[Dict[str, Any]]:
        """
        List all versions of a dataset.

        Args:
            dataset_name: Name of the dataset

        Returns:
            List of version metadata
        """
        versions = []
        for metadata_file in self.metadata_dir.glob(f"{dataset_name}_*_metadata.json"):
            try:
                with open(metadata_file, 'r') as f:
                    metadata = json.load(f)
                versions.append(metadata)
            except Exception:
                continue

        # Sort by creation time, newest first
        return sorted(versions, key=lambda v: v["created_at"], reverse=True)

    def compare_versions(self, dataset_name: str, version_id1: str, version_id2: str) -> Dict[str, Any]:
        """
        Compare two versions of a dataset.

        Args:
            dataset_name: Name of the dataset
            version_id1: First version ID
            version_id2: Second version ID

        Returns:
            Comparison results
        """
        data1 = self.get_version(dataset_name, version_id1)
        data2 = self.get_version(dataset_name, version_id2)

        # Convert to comparable strings
        str1 = json.dumps(data1, indent=2, sort_keys=True)
        str2 = json.dumps(data2, indent=2, sort_keys=True)

        # Generate diff
        diff = list(difflib.unified_diff(
            str1.splitlines(keepends=True),
            str2.splitlines(keepends=True),
            fromfile=f"{version_id1}",
            tofile=f"{version_id2}",
            lineterm=''
        ))

        return {
            "version1": version_id1,
            "version2": version_id2,
            "has_changes": len(diff) > 0,
            "diff_lines": len(diff),
            "diff": "".join(diff)
        }

    def rollback_version(self, dataset_name: str, target_version: str,
                        author: str = "system") -> str:
        """
        Rollback to a previous version.

        Args:
            target_version: Version to rollback to
            author: Author of the rollback

        Returns:
            New version ID created by rollback
        """
        # Get the target version data
        target_data = self.get_version(dataset_name, target_version)

        # Create backup of current version
        current_data = self.get_version(dataset_name)
        backup_id = self.create_version(
            f"{dataset_name}_backup",
            current_data,
            f"Backup before rollback to {target_version}",
            author
        )

        # Create new version with rolled back data
        new_version_id = self.create_version(
            dataset_name,
            target_data,
            f"Rolled back to version {target_version}",
            author
        )

        return new_version_id

    def cleanup_old_versions(self, dataset_name: str, keep_versions: int = 10) -> Dict[str, Any]:
        """
        Clean up old versions, keeping only the most recent ones.

        Args:
            dataset_name: Name of the dataset
            keep_versions: Number of versions to keep

        Returns:
            Cleanup summary
        """
        versions = self.list_versions(dataset_name)

        if len(versions) <= keep_versions:
            return {"deleted_versions": 0, "freed_space": 0}

        # Keep the most recent versions
        versions_to_keep = versions[:keep_versions]
        versions_to_delete = versions[keep_versions:]

        deleted_count = 0
        freed_space = 0

        for version in versions_to_delete:
            version_id = version["version_id"]

            # Delete version file
            version_file = self.versions_dir / f"{version_id}.json"
            if version_file.exists():
                size = version_file.stat().st_size
                freed_space += size
                version_file.unlink()
                deleted_count += 1

            # Delete metadata file
            metadata_file = self.metadata_dir / f"{version_id}_metadata.json"
            if metadata_file.exists():
                freed_space += metadata_file.stat().st_size
                metadata_file.unlink()

        return {
            "deleted_versions": deleted_count,
            "freed_space": freed_space,
            "kept_versions": len(versions_to_keep)
        }

    def validate_data_integrity(self, dataset_name: str) -> Dict[str, Any]:
        """
        Validate data integrity across all versions.

        Args:
            dataset_name: Name of the dataset

        Returns:
            Integrity validation results
        """
        versions = self.list_versions(dataset_name)
        results = {
            "total_versions": len(versions),
            "valid_versions": 0,
            "corrupted_versions": 0,
            "missing_files": 0,
            "integrity_issues": []
        }

        for version in versions:
            version_id = version["version_id"]
            expected_hash = version["content_hash"]

            version_file = self.versions_dir / f"{version_id}.json"
            if not version_file.exists():
                results["missing_files"] += 1
                results["integrity_issues"].append(f"Missing file for version {version_id}")
                continue

            try:
                with open(version_file, 'r') as f:
                    content = f.read()

                actual_hash = hashlib.sha256(content.encode()).hexdigest()[:16]
                if actual_hash == expected_hash:
                    results["valid_versions"] += 1
                else:
                    results["corrupted_versions"] += 1
                    results["integrity_issues"].append(f"Hash mismatch for version {version_id}")

            except Exception as e:
                results["corrupted_versions"] += 1
                results["integrity_issues"].append(f"Error reading version {version_id}: {str(e)}")

        return results

    def get_dataset_stats(self, dataset_name: str) -> Dict[str, Any]:
        """
        Get statistics for a dataset.

        Args:
            dataset_name: Name of the dataset

        Returns:
            Dataset statistics
        """
        versions = self.list_versions(dataset_name)

        if not versions:
            return {"dataset_name": dataset_name, "total_versions": 0}

        latest = versions[0]
        oldest = versions[-1]

        # Calculate growth rate
        if len(versions) > 1:
            time_span = (datetime.fromisoformat(latest["created_at"]) -
                        datetime.fromisoformat(oldest["created_at"])).days
            growth_rate = len(versions) / max(time_span, 1)  # versions per day
        else:
            growth_rate = 0

        return {
            "dataset_name": dataset_name,
            "total_versions": len(versions),
            "latest_version": latest["version_id"],
            "oldest_version": oldest["version_id"],
            "total_size": sum(v.get("data_size", 0) for v in versions),
            "avg_record_count": sum(v.get("record_count", 0) for v in versions) / len(versions),
            "creation_frequency": growth_rate,
            "authors": list(set(v.get("author", "unknown") for v in versions))
        }

    def _count_records(self, data: Dict[str, Any]) -> int:
        """Count records in dataset."""
        if isinstance(data, list):
            return len(data)
        elif isinstance(data, dict):
            # Try common keys that might contain records
            for key in ["records", "cases", "data", "items", "repositories"]:
                if key in data and isinstance(data[key], list):
                    return len(data[key])
            # If it's a dict of dicts, count top-level keys
            return len(data)
        else:
            return 1

    def _get_current_version(self, dataset_name: str) -> Optional[str]:
        """Get the current version ID for a dataset."""
        current_file = self.metadata_dir / f"{dataset_name}_current.txt"
        if current_file.exists():
            return current_file.read_text().strip()
        return None

    def _update_current_version(self, dataset_name: str, version_id: str):
        """Update the current version pointer."""
        current_file = self.metadata_dir / f"{dataset_name}_current.txt"
        with open(current_file, 'w') as f:
            f.write(version_id)

    def _get_latest_version(self, dataset_name: str) -> Optional[str]:
        """Get the latest version ID for a dataset."""
        versions = self.list_versions(dataset_name)
        return versions[0]["version_id"] if versions else None


# Global instance
_validation_manager: Optional[ValidationDataManager] = None


def get_validation_manager() -> ValidationDataManager:
    """Get the global validation data manager instance."""
    global _validation_manager
    if _validation_manager is None:
        _validation_manager = ValidationDataManager()
    return _validation_manager