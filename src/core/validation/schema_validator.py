"""JSON Schema loader and validator for Repository Intelligence Scanner."""

import json
import logging
from pathlib import Path
from typing import Dict, Any, Optional, Union
import jsonschema
from jsonschema import validate, ValidationError, SchemaError

logger = logging.getLogger(__name__)


class SchemaLoader:
    """Loads and caches JSON schemas from the filesystem."""

    def __init__(self, schemas_base_path: Optional[str] = None):
        """
        Initialize schema loader.

        Args:
            schemas_base_path: Base path to schemas directory. Defaults to docs/schemas.
        """
        if schemas_base_path is None:
            # Default to docs/schemas relative to project root
            project_root = Path(__file__).parent.parent.parent.parent
            schemas_base_path = project_root / "docs" / "schemas"

        self.schemas_base_path = Path(schemas_base_path)
        self._schema_cache: Dict[str, Dict[str, Any]] = {}
        self._load_all_schemas()

    def _load_all_schemas(self) -> None:
        """Load all available schemas into cache."""
        if not self.schemas_base_path.exists():
            logger.warning(f"Schemas directory not found: {self.schemas_base_path}")
            return

        # Load schemas from root schemas directory
        self._load_schemas_from_directory(self.schemas_base_path)

        # Load schemas from subdirectories
        for subdir in self.schemas_base_path.iterdir():
            if subdir.is_dir():
                self._load_schemas_from_directory(subdir)

    def _load_schemas_from_directory(self, directory: Path) -> None:
        """Load all .json schema files from a directory."""
        for schema_file in directory.glob("*.json"):
            try:
                with open(schema_file, 'r', encoding='utf-8') as f:
                    schema = json.load(f)

                # Use relative path as schema key
                relative_path = schema_file.relative_to(self.schemas_base_path)
                schema_key = str(relative_path).replace('\\', '/').replace('.json', '')

                self._schema_cache[schema_key] = schema
                logger.debug(f"Loaded schema: {schema_key}")

            except (json.JSONDecodeError, IOError) as e:
                logger.error(f"Failed to load schema {schema_file}: {e}")

    def get_schema(self, schema_key: str) -> Optional[Dict[str, Any]]:
        """
        Get a schema by key.

        Args:
            schema_key: Schema identifier (e.g., 'output/scan_report', 'bounty_assessment')

        Returns:
            Schema dict or None if not found
        """
        return self._schema_cache.get(schema_key)

    def list_available_schemas(self) -> Dict[str, Dict[str, Any]]:
        """
        List all available schemas with metadata.

        Returns:
            Dict mapping schema keys to schema metadata
        """
        metadata = {}
        for key, schema in self._schema_cache.items():
            metadata[key] = {
                "title": schema.get("title", "Unknown"),
                "description": schema.get("description", ""),
                "version": schema.get("$id", "").split("/")[-1] if "$id" in schema else "unknown"
            }
        return metadata


class SchemaValidator:
    """Validates JSON data against loaded schemas."""

    def __init__(self, schema_loader: Optional[SchemaLoader] = None):
        """
        Initialize schema validator.

        Args:
            schema_loader: Schema loader instance. Creates default if None.
        """
        self.schema_loader = schema_loader or SchemaLoader()

    def validate_data(self, data: Dict[str, Any], schema_key: str) -> Dict[str, Any]:
        """
        Validate JSON data against a schema.

        Args:
            data: JSON data to validate
            schema_key: Schema identifier

        Returns:
            Validation result dict
        """
        result = {
            "valid": False,
            "schema_key": schema_key,
            "errors": [],
            "warnings": []
        }

        schema = self.schema_loader.get_schema(schema_key)
        if not schema:
            result["errors"].append(f"Schema not found: {schema_key}")
            return result

        try:
            # Perform validation
            validate(instance=data, schema=schema)
            result["valid"] = True
            logger.debug(f"Data validated successfully against schema: {schema_key}")

        except ValidationError as e:
            result["errors"].append({
                "type": "validation_error",
                "message": e.message,
                "path": list(e.absolute_path) if e.absolute_path else [],
                "schema_path": list(e.absolute_schema_path) if e.absolute_schema_path else []
            })
            logger.debug(f"Validation error for {schema_key}: {e.message}")

        except SchemaError as e:
            result["errors"].append({
                "type": "schema_error",
                "message": f"Invalid schema: {e.message}"
            })
            logger.error(f"Schema error in {schema_key}: {e.message}")

        except Exception as e:
            result["errors"].append({
                "type": "unexpected_error",
                "message": f"Unexpected validation error: {str(e)}"
            })
            logger.error(f"Unexpected validation error for {schema_key}: {e}")

        return result

    def validate_file(self, file_path: Union[str, Path], schema_key: str) -> Dict[str, Any]:
        """
        Validate a JSON file against a schema.

        Args:
            file_path: Path to JSON file
            schema_key: Schema identifier

        Returns:
            Validation result dict
        """
        result = {
            "valid": False,
            "file_path": str(file_path),
            "schema_key": schema_key,
            "errors": [],
            "warnings": []
        }

        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)

            # Validate the loaded data
            validation_result = self.validate_data(data, schema_key)
            result.update(validation_result)

        except json.JSONDecodeError as e:
            result["errors"].append({
                "type": "json_error",
                "message": f"Invalid JSON: {e.msg} at line {e.lineno}, column {e.colno}"
            })
        except IOError as e:
            result["errors"].append({
                "type": "file_error",
                "message": f"Cannot read file: {e}"
            })

        return result

    def validate_multiple_files(self, file_schema_pairs: Dict[str, str]) -> Dict[str, Dict[str, Any]]:
        """
        Validate multiple files against their respective schemas.

        Args:
            file_schema_pairs: Dict mapping file paths to schema keys

        Returns:
            Dict mapping file paths to validation results
        """
        results = {}
        for file_path, schema_key in file_schema_pairs.items():
            results[file_path] = self.validate_file(file_path, schema_key)
        return results

    def get_validation_summary(self, validation_result: Dict[str, Any]) -> str:
        """
        Generate a human-readable summary of validation results.

        Args:
            validation_result: Validation result dict

        Returns:
            Formatted summary string
        """
        if validation_result["valid"]:
            return f"✅ Validation Passed: {validation_result['schema_key']}"

        errors = validation_result.get("errors", [])
        if not errors:
            return f"❌ Validation Failed: {validation_result['schema_key']} (unknown errors)"

        summary = f"❌ Validation Failed: {validation_result['schema_key']} ({len(errors)} errors)\n\n"

        for i, error in enumerate(errors[:5]):  # Show first 5 errors
            error_type = error.get("type", "unknown")
            message = error.get("message", "Unknown error")

            summary += f"**{error_type.title().replace('_', ' ')}**: {message}\n"

            if "path" in error and error["path"]:
                summary += f"  Path: {'.'.join(str(p) for p in error['path'])}\n"

            summary += "\n"

        if len(errors) > 5:
            summary += f"... and {len(errors) - 5} more errors\n"

        return summary.strip()


# Global instances for convenience
_default_schema_loader = None
_default_validator = None


def get_schema_loader() -> SchemaLoader:
    """Get the default schema loader instance."""
    global _default_schema_loader
    if _default_schema_loader is None:
        _default_schema_loader = SchemaLoader()
    return _default_schema_loader


def get_schema_validator() -> SchemaValidator:
    """Get the default schema validator instance."""
    global _default_validator
    if _default_validator is None:
        _default_validator = SchemaValidator(get_schema_loader())
    return _default_validator


def validate_against_schema(data: Dict[str, Any], schema_key: str) -> bool:
    """
    Convenience function to validate data against a schema.

    Args:
        data: JSON data to validate
        schema_key: Schema identifier

    Returns:
        True if valid, False otherwise
    """
    validator = get_schema_validator()
    result = validator.validate_data(data, schema_key)
    return result["valid"]


class SchemaCompatibilityValidator:
    """Validates schema compatibility and version constraints."""

    def __init__(self, schema_loader: Optional[SchemaLoader] = None):
        """
        Initialize schema compatibility validator.

        Args:
            schema_loader: Schema loader instance. Creates default if None.
        """
        self.schema_loader = schema_loader or get_schema_loader()

    def validate_schema_version_compatibility(self, schema_key: str, 
                                            required_version: Optional[str] = None) -> Dict[str, Any]:
        """
        Validate that a schema meets version compatibility requirements.

        Args:
            schema_key: Schema identifier
            required_version: Minimum required version (semantic versioning)

        Returns:
            Compatibility validation result
        """
        result = {
            "compatible": False,
            "schema_key": schema_key,
            "current_version": None,
            "required_version": required_version,
            "errors": []
        }

        schema = self.schema_loader.get_schema(schema_key)
        if not schema:
            result["errors"].append(f"Schema not found: {schema_key}")
            return result

        # Extract version from schema
        schema_version = self._extract_schema_version(schema)
        result["current_version"] = schema_version

        if required_version and schema_version:
            if self._is_version_compatible(schema_version, required_version):
                result["compatible"] = True
            else:
                result["errors"].append(
                    f"Schema version {schema_version} is incompatible with required {required_version}"
                )
        elif schema_version:
            # If no required version specified, any version is compatible
            result["compatible"] = True
        else:
            result["errors"].append("Schema version could not be determined")

        return result

    def validate_backward_compatibility(self, old_schema_key: str, new_schema_key: str) -> Dict[str, Any]:
        """
        Validate that a new schema version is backward compatible with an old version.

        Args:
            old_schema_key: Key for the old schema version
            new_schema_key: Key for the new schema version

        Returns:
            Backward compatibility validation result
        """
        result = {
            "backward_compatible": False,
            "old_schema": old_schema_key,
            "new_schema": new_schema_key,
            "compatibility_issues": []
        }

        old_schema = self.schema_loader.get_schema(old_schema_key)
        new_schema = self.schema_loader.get_schema(new_schema_key)

        if not old_schema:
            result["compatibility_issues"].append(f"Old schema not found: {old_schema_key}")
            return result

        if not new_schema:
            result["compatibility_issues"].append(f"New schema not found: {new_schema_key}")
            return result

        # Check for breaking changes
        issues = []

        # Check if required fields were removed
        old_required = set(old_schema.get("required", []))
        new_required = set(new_schema.get("required", []))
        removed_required = old_required - new_required
        if removed_required:
            issues.append(f"Required fields removed: {removed_required}")

        # Check if field types changed incompatibly
        old_properties = old_schema.get("properties", {})
        new_properties = new_schema.get("properties", {})

        for field_name, old_field_def in old_properties.items():
            if field_name in new_properties:
                new_field_def = new_properties[field_name]
                if self._are_types_incompatible(old_field_def, new_field_def):
                    issues.append(f"Field '{field_name}' type changed incompatibly")

        result["compatibility_issues"] = issues
        result["backward_compatible"] = len(issues) == 0

        return result

    def _extract_schema_version(self, schema: Dict[str, Any]) -> Optional[str]:
        """Extract version from schema metadata."""
        # Try different version fields
        version_fields = ["version", "$id"]
        for field in version_fields:
            if field in schema:
                value = schema[field]
                if isinstance(value, str):
                    # Extract version from $id URL if present
                    if field == "$id" and "/" in value:
                        parts = value.split("/")
                        for part in reversed(parts):
                            if self._looks_like_version(part):
                                return part
                    elif self._looks_like_version(value):
                        return value

        return None

    def _looks_like_version(self, s: str) -> bool:
        """Check if a string looks like a semantic version."""
        import re
        # Simple semver pattern: x.y.z
        return bool(re.match(r'^\d+\.\d+\.\d+', s))

    def _is_version_compatible(self, current: str, required: str) -> bool:
        """Check if current version meets required version constraint."""
        try:
            from packaging import version
            return version.parse(current) >= version.parse(required)
        except ImportError:
            # Fallback to simple string comparison
            return current >= required

    def _are_types_incompatible(self, old_def: Dict[str, Any], new_def: Dict[str, Any]) -> bool:
        """Check if two field definitions have incompatible types."""
        old_type = old_def.get("type")
        new_type = new_def.get("type")

        # If types are explicitly different, they're incompatible
        if old_type and new_type and old_type != new_type:
            return True

        # If old was required and new is not, or vice versa
        old_required = old_def.get("required", False)
        new_required = new_def.get("required", False)
        if old_required != new_required:
            return True

        return False


__all__ = [
    'SchemaLoader',
    'SchemaValidator',
    'SchemaCompatibilityValidator',
    'get_schema_loader',
    'get_schema_validator',
    'validate_against_schema'
]