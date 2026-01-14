"""Tests for schema compatibility validation."""

import pytest
from src.core.validation.schema_validator import SchemaCompatibilityValidator


class TestSchemaCompatibilityValidator:
    """Test schema compatibility validation functionality."""

    def test_schema_version_compatibility_valid(self):
        """Test that valid schema versions pass compatibility check."""
        validator = SchemaCompatibilityValidator()

        # Test with scan_report schema (should have version 1.0.0)
        result = validator.validate_schema_version_compatibility("scan_report.schema", "1.0.0")

        assert result["compatible"] is True
        assert result["schema_key"] == "scan_report.schema"
        assert result["current_version"] is not None
        assert not result["errors"]

    def test_schema_version_compatibility_invalid_version(self):
        """Test that incompatible versions fail compatibility check."""
        validator = SchemaCompatibilityValidator()

        # Test with version requirement that's too high
        result = validator.validate_schema_version_compatibility("scan_report.schema", "2.0.0")

        assert result["compatible"] is False
        assert "incompatible" in " ".join(result["errors"])

    def test_schema_not_found(self):
        """Test handling of non-existent schemas."""
        validator = SchemaCompatibilityValidator()

        result = validator.validate_schema_version_compatibility("nonexistent_schema", "1.0.0")

        assert result["compatible"] is False
        assert "not found" in " ".join(result["errors"])

    def test_backward_compatibility_same_schema(self):
        """Test backward compatibility with identical schemas."""
        validator = SchemaCompatibilityValidator()

        result = validator.validate_backward_compatibility("scan_report.schema", "scan_report.schema")

        assert result["backward_compatible"] is True
        assert result["old_schema"] == "scan_report.schema"
        assert result["new_schema"] == "scan_report.schema"
        assert not result["compatibility_issues"]

    def test_backward_compatibility_nonexistent_schema(self):
        """Test backward compatibility with non-existent schemas."""
        validator = SchemaCompatibilityValidator()

        result = validator.validate_backward_compatibility("nonexistent_old", "nonexistent_new")

        assert result["backward_compatible"] is False
        assert len(result["compatibility_issues"]) >= 1