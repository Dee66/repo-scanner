# Machine-Readable Output Schemas

This directory contains JSON Schema definitions for all machine-readable outputs produced by the Repository Intelligence Scanner.

## Schema Files

### Core Analysis Outputs

- **`scan_report.json`** - Main analysis report containing executive verdict, risk assessments, evidence, and metadata
- **`evidence_bundle.json`** - Structured collection of evidence supporting analysis conclusions
- **`determinism_verification.json`** - Results of determinism verification testing

### Quality Assurance Outputs

- **`evaluation_results.json`** - Results from quality assurance evaluations (silence policy, quality bar, success criteria)

## Schema Versioning

All schemas follow JSON Schema Draft 2020-12 and include:
- `$schema` - Schema specification version
- `$id` - Unique schema identifier
- Semantic versioning in schema URIs
- Strict validation with `additionalProperties: false`

## Validation

Schemas are validated against:
- JSON Schema Draft 2020-12 compliance
- Internal consistency
- Real output compatibility

## Usage

These schemas are used for:
- Output validation in CI/CD pipelines
- API contract enforcement
- Data integrity verification
- Tool integration validation

## Maintenance

When updating schemas:
1. Increment version numbers appropriately
2. Update `$id` URIs
3. Ensure backward compatibility where possible
4. Update this README
5. Test against real outputs