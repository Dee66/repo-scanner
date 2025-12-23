"""Command-line interface for Repository Intelligence Scanner."""

import argparse
import json
import sys
from pathlib import Path

from src.core.exceptions import ScannerError, RepositoryDiscoveryError, AnalysisError, OutputGenerationError, ValidationError
from src.core.pipeline.analysis import execute_pipeline
from src.core.quality.output_contract import generate_primary_report, generate_machine_output, generate_executive_verdict


def main():
    """Main entry point for the CLI."""
    try:
        parser = argparse.ArgumentParser(
            description="Repository Intelligence Scanner - Decision-grade repository analysis"
        )
        parser.add_argument(
            "repository_path",
            type=str,
            help="Path to the repository to scan"
        )
        parser.add_argument(
            "--output-dir",
            type=str,
            default=".",
            help="Directory to write output files (default: current directory)"
        )
        parser.add_argument(
            "--format",
            choices=["markdown", "json", "both"],
            default="both",
            help="Output format (default: both)"
        )
        parser.add_argument(
            "--report-type",
            choices=["comprehensive", "verdict", "both"],
            help="Type of report to generate (comprehensive: full analysis, verdict: executive verdict, both: both reports). Takes precedence over --format if both are specified."
        )

        args = parser.parse_args()

        # Validate inputs
        if not args.repository_path or not args.repository_path.strip():
            raise ValidationError("Repository path cannot be empty")
        
        if not args.output_dir or not args.output_dir.strip():
            raise ValidationError("Output directory cannot be empty")

        repo_path = Path(args.repository_path)
        output_dir = Path(args.output_dir)

        # Validate repository path
        if not repo_path.exists():
            raise ValidationError(f"Repository path {repo_path} does not exist", {"path": str(repo_path)})
        
        if not repo_path.is_dir():
            raise ValidationError(f"Repository path {repo_path} is not a directory", {"path": str(repo_path)})

        # Create output directory
        try:
            output_dir.mkdir(parents=True, exist_ok=True)
        except OSError as e:
            raise OutputGenerationError(f"Cannot create output directory {output_dir}: {e}", {"directory": str(output_dir), "error": str(e)})

        # Execute the analysis pipeline
        try:
            analysis_result = execute_pipeline(str(repo_path))
        except Exception as e:
            raise AnalysisError(f"Analysis pipeline failed: {e}", {"error": str(e)}) from e

        # Determine report type and output format
        if args.report_type is not None:
            report_type = args.report_type
            # For new report-type system, always include JSON
            include_json = True
        else:
            # Backward compatibility with --format
            if args.format == "markdown":
                report_type = "comprehensive"
                include_json = False
            elif args.format == "json":
                report_type = None  # No reports, just JSON
                include_json = True
            else:  # both
                report_type = "comprehensive"
                include_json = True

        # Generate outputs based on report type
        try:
            if report_type and report_type in ["comprehensive", "both"]:
                report_path = output_dir / "scan_report.md"
                report_content = generate_primary_report(analysis_result, str(repo_path))
                report_path.write_text(report_content)
                print(f"Comprehensive report written to {report_path}")

            if report_type and report_type in ["verdict", "both"]:
                verdict_path = output_dir / "verdict_report.md"
                verdict_content = generate_executive_verdict(analysis_result, str(repo_path))
                verdict_path.write_text(verdict_content)
                print(f"Executive verdict report written to {verdict_path}")

            if include_json:
                json_path = output_dir / "scan_report.json"
                json_data = generate_machine_output(analysis_result, str(repo_path))
                with open(json_path, 'w') as f:
                    json.dump(json_data, f, indent=2, sort_keys=True)
                print(f"Machine-readable output written to {json_path}")

        except Exception as e:
            raise OutputGenerationError(f"Output generation failed: {e}", {"error": str(e)}) from e

        print("Scan completed successfully")
        
    except ValidationError as e:
        print(f"Validation error: {e.message}", file=sys.stderr)
        if e.details:
            print(f"Details: {e.details}", file=sys.stderr)
        sys.exit(1)
    except RepositoryDiscoveryError as e:
        print(f"Repository discovery error: {e.message}", file=sys.stderr)
        if e.details:
            print(f"Details: {e.details}", file=sys.stderr)
        sys.exit(1)
    except AnalysisError as e:
        print(f"Analysis error: {e.message}", file=sys.stderr)
        if e.details:
            print(f"Details: {e.details}", file=sys.stderr)
        sys.exit(1)
    except OutputGenerationError as e:
        print(f"Output generation error: {e.message}", file=sys.stderr)
        if e.details:
            print(f"Details: {e.details}", file=sys.stderr)
        sys.exit(1)
    except ScannerError as e:
        print(f"Scanner error: {e.message}", file=sys.stderr)
        if e.details:
            print(f"Details: {e.details}", file=sys.stderr)
        sys.exit(1)
    except KeyboardInterrupt:
        print("Operation cancelled by user", file=sys.stderr)
        sys.exit(130)
    except Exception as e:
        print(f"Unexpected error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
