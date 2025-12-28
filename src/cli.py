"""Command-line interface for Repository Intelligence Scanner."""

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path
from urllib.parse import urlparse
import re

from src.core.exceptions import ScannerError, RepositoryDiscoveryError, AnalysisError, OutputGenerationError, ValidationError
from src.core.pipeline.analysis import execute_pipeline
from src.core.quality.output_contract import generate_primary_report, generate_machine_output, generate_executive_verdict
from src.core.quality import schema_validator
from src.services.bounty_service import BountyService


def validate_git_url(url: str) -> bool:
    """Validate Git URL for security."""
    ALLOWED_DOMAINS = ["github.com", "gitlab.com", "bitbucket.org"]
    try:
        parsed = urlparse(url)
        if parsed.scheme not in ["https", "http", "git"]:
            return False
        if not any(domain in parsed.netloc for domain in ALLOWED_DOMAINS):
            return False
        # Prevent shell injection
        if re.search(r'[;&|`$]', url):
            return False
        return True
    except Exception:
        return False


def check_repo_limits(repo_path: Path, max_files: int = 10000, max_size_mb: int = 500) -> None:
    """Check repository size limits to prevent abuse."""
    from src.core.system_config import DATA_USAGE_CONFIG
    
    # Use config values if not specified
    if max_files == 10000 and max_size_mb == 500:  # Default values, use config
        is_ci = os.getenv('CI') == 'true' or os.getenv('GITHUB_ACTIONS') == 'true'
        limits = DATA_USAGE_CONFIG["limits"]["automated_scans" if is_ci else "manual_scans"]
        max_files = limits["max_files"]
        max_size_mb = limits["max_size_mb"]
    
    total_files = 0
    total_size = 0
    large_files = []
    
    for root, dirs, files in os.walk(repo_path):
        # Skip .git directory
        if '.git' in dirs:
            dirs.remove('.git')

        for file in files:
            total_files += 1
            if total_files > max_files:
                raise ValidationError(f"Repository exceeds maximum file limit of {max_files}")

            file_path = Path(root) / file
            try:
                file_size = file_path.stat().st_size
                total_size += file_size
                
                # Track files over threshold
                threshold = DATA_USAGE_CONFIG["monitoring"]["track_large_files_threshold_mb"] * 1024 * 1024
                if file_size > threshold:
                    large_files.append((str(file_path.relative_to(repo_path)), file_size / (1024*1024)))
                
                if total_size > max_size_mb * 1024 * 1024:
                    raise ValidationError(f"Repository exceeds maximum size limit of {max_size_mb}MB")
            except OSError:
                # Skip files we can't stat
                continue
    
    # Log data usage for monitoring
    size_mb = total_size / (1024 * 1024)
    print(f"Repository stats: {total_files} files, {size_mb:.2f}MB")
    if large_files:
        print(f"Warning: Large files detected: {large_files}")
    
    # Additional check for automated processes
    if DATA_USAGE_CONFIG["monitoring"]["ci_stricter_limits"]:
        is_ci = os.getenv('CI') == 'true' or os.getenv('GITHUB_ACTIONS') == 'true'
        if is_ci:
            ci_limits = DATA_USAGE_CONFIG["limits"]["automated_scans"]
            if size_mb > ci_limits["max_size_mb"]:
                raise ValidationError(f"Repository too large for automated scanning: {size_mb:.2f}MB (limit: {ci_limits['max_size_mb']}MB)")
            if total_files > ci_limits["max_files"]:
                raise ValidationError(f"Repository has too many files for automated scanning: {total_files} (limit: {ci_limits['max_files']})")


def main():
    """Main entry point for the CLI."""
    try:
        parser = argparse.ArgumentParser(
            description="Repository Intelligence Scanner - Decision-grade repository analysis"
        )

        # Create subparsers for different commands
        subparsers = parser.add_subparsers(dest='command', help='Available commands')

        # Repository scanning command (original functionality)
        scan_parser = subparsers.add_parser('scan', help='Scan a repository')
        scan_parser.add_argument(
            "repository_path",
            type=str,
            nargs='?',
            help="Path to the repository to scan (optional if --url is provided)"
        )
        scan_parser.add_argument(
            "--url",
            type=str,
            help="Git URL to clone and scan remotely (e.g., https://github.com/owner/repo)"
        )
        scan_parser.add_argument(
            "--output-dir",
            type=str,
            default=".",
            help="Directory to write output files (default: current directory)"
        )
        scan_parser.add_argument(
            "--format",
            choices=["markdown", "json", "both"],
            default="both",
            help="Output format (default: both)"
        )
        scan_parser.add_argument(
            "--report-type",
            choices=["comprehensive", "verdict", "both"],
            help="Type of report to generate (comprehensive: full analysis, verdict: executive verdict, both: both reports). Takes precedence over --format if both are specified."
        )

        # Bounty analysis command
        bounty_parser = subparsers.add_parser('bounty', help='Analyze bounty opportunities')
        bounty_parser.add_argument(
            "repository_path",
            type=str,
            nargs='?',
            help="Path to the repository to analyze (optional when fetching from Algora)"
        )
        bounty_parser.add_argument(
            "--bounty-data",
            type=str,
            help="JSON string or file path containing bounty data (not required with --fetch-algora-bounties)"
        )
        bounty_parser.add_argument(
            "--output-dir",
            type=str,
            default=".",
            help="Directory to write output files (default: current directory)"
        )
        bounty_parser.add_argument(
            "--generate-solution",
            action="store_true",
            help="Generate complete bounty solution including PR content"
        )
        bounty_parser.add_argument(
            "--solution-code",
            type=str,
            help="JSON string or file path containing solution code data (required with --generate-solution)"
        )
        bounty_parser.add_argument(
            "--batch",
            action="store_true",
            help="Process multiple bounties in parallel for better performance"
        )
        bounty_parser.add_argument(
            "--batch-id",
            type=str,
            help="Custom batch ID for tracking parallel processing (auto-generated if not provided)"
        )
        bounty_parser.add_argument(
            "--fetch-algora-bounties",
            action="store_true",
            help="Fetch bounties from Algora.io instead of providing bounty data"
        )
        bounty_parser.add_argument(
            "--org",
            type=str,
            help="Algora organization name (required with --fetch-algora-bounties)"
        )
        bounty_parser.add_argument(
            "--fetch-github-issues",
            action="store_true",
            help="Fetch bounties from GitHub Issues instead of providing bounty data"
        )
        bounty_parser.add_argument(
            "--repo",
            type=str,
            help="GitHub repository in owner/repo format (required with --fetch-github-issues)"
        )
        bounty_parser.add_argument(
            "--labels",
            type=str,
            default="bounty",
            help="Comma-separated labels to filter issues (default: bounty)"
        )
        bounty_parser.add_argument(
            "--limit",
            type=int,
            default=10,
            help="Maximum number of bounties/issues to fetch (default: 10)"
        )
        bounty_parser.add_argument(
            "--status",
            type=str,
            default="active",
            choices=["active", "inactive"],
            help="Bounty status to fetch (default: active)"
        )

        # Bounty validation command
        validate_parser = subparsers.add_parser('validate', help='Validate bounty prediction accuracy')
        validate_parser.add_argument(
            "--output-dir",
            type=str,
            default=".",
            help="Directory to write validation report (default: current directory)"
        )

        args = parser.parse_args()

        # Handle different commands
        if args.command == 'scan' or args.command is None:
            # Default to scan command for backward compatibility
            handle_scan_command(args)
        elif args.command == 'bounty':
            handle_bounty_command(args)
        elif args.command == 'validate':
            handle_validate_command(args)
        else:
            parser.print_help()
            sys.exit(1)
        
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


def handle_scan_command(args):
    """Handle repository scanning command."""
    # Validate inputs
    if args.url:
        if not validate_git_url(args.url):
            raise ValidationError("Invalid or unsafe Git URL")
    elif not args.repository_path or not args.repository_path.strip():
        raise ValidationError("Repository path cannot be empty (or provide --url)")
    
    if not args.output_dir or not args.output_dir.strip():
        raise ValidationError("Output directory cannot be empty")

    # Determine repo path
    if args.url:
        # Clone the repo
        import tempfile
        import git
        temp_dir = tempfile.mkdtemp()
        try:
            repo = git.Repo.clone_from(args.url, temp_dir, depth=1)
            repo_path = Path(temp_dir)
        except Exception as e:
            import shutil
            shutil.rmtree(temp_dir, ignore_errors=True)
            raise ValidationError(f"Failed to clone repository: {e}")
    else:
        repo_path = Path(args.repository_path)
        temp_dir = None

    output_dir = Path(args.output_dir)

    # Validate repository path
    if not repo_path.exists():
        raise ValidationError(f"Repository path {repo_path} does not exist", {"path": str(repo_path)})
    
    if not repo_path.is_dir():
        raise ValidationError(f"Repository path {repo_path} is not a directory", {"path": str(repo_path)})

    # Check repo limits if cloned
    if args.url:
        check_repo_limits(repo_path)

    # Create output directory
    try:
        output_dir.mkdir(parents=True, exist_ok=True)
    except OSError as e:
        if temp_dir:
            import shutil
            shutil.rmtree(temp_dir, ignore_errors=True)
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
            # Validate machine output against schema; raise ValidationError on failure
            try:
                schema_validator.validate_scan_report(str(json_path))
            except Exception as e:
                raise ValidationError(f"Schema validation failed for scan_report.json: {e}", {"path": str(json_path), "error": str(e)}) from e

    except Exception as e:
        raise OutputGenerationError(f"Output generation failed: {e}", {"error": str(e)}) from e

    # Cleanup temp directory if used
    if temp_dir:
        import shutil
        shutil.rmtree(temp_dir, ignore_errors=True)

    print("Scan completed successfully")


def handle_bounty_command(args):
    """Handle bounty analysis command."""
    # Validate inputs
    if args.fetch_algora_bounties:
        if not args.org:
            raise ValidationError("--org is required when using --fetch-algora-bounties")
        if args.generate_solution:
            raise ValidationError("Solution generation not supported when fetching bounties")
    elif args.fetch_github_issues:
        if not args.repo:
            raise ValidationError("--repo is required when using --fetch-github-issues")
        if args.generate_solution:
            raise ValidationError("Solution generation not supported when fetching issues")
    else:
        if not args.repository_path or not args.repository_path.strip():
            raise ValidationError("Repository path cannot be empty")
        if not args.bounty_data or not args.bounty_data.strip():
            raise ValidationError("Bounty data cannot be empty")
        if args.generate_solution and (not args.solution_code or not args.solution_code.strip()):
            raise ValidationError("Solution code is required when generating solution")

    if args.fetch_algora_bounties:
        bounty_service = BountyService()
        bounties = bounty_service.fetch_bounties(args.org, args.limit, args.status)
        
        results = []
        for bounty in bounties:
            repo_name = bounty.get('repo_name')
            if not repo_name:
                print(f"Skipping bounty {bounty['id']}: no repo_name")
                continue
            repo_path = Path(repo_name)
            if not repo_path.exists() or not repo_path.is_dir():
                print(f"Skipping bounty {bounty['id']}: repo {repo_name} not found locally")
                continue
            
            # Execute repository analysis
            try:
                analysis_result = execute_pipeline(str(repo_path))
                if analysis_result is None:
                    analysis_result = {}
            except Exception as e:
                print(f"Analysis failed for {repo_name}: {e}")
                continue
            
            # Analyze bounty
            repository_url = f"file://{repo_path.absolute()}"
            try:
                assessment = bounty_service.analyze_bounty_opportunity(repository_url, bounty, analysis_result)
                results.append(assessment)
            except Exception as e:
                print(f"Bounty analysis failed for {bounty['id']}: {e}")
                continue
        
        # Output results
        output_dir = Path(args.output_dir)
        try:
            output_dir.mkdir(parents=True, exist_ok=True)
        except OSError as e:
            raise OutputGenerationError(f"Cannot create output directory {output_dir}: {e}", {"directory": str(output_dir), "error": str(e)})
        
        batch_path = output_dir / "algora_bounties_results.json"
        with open(batch_path, 'w') as f:
            json.dump({
                "org": args.org,
                "fetched_at": datetime.now().isoformat(),
                "total_bounties": len(bounties),
                "analyzed_bounties": len(results),
                "results": results
            }, f, indent=2, sort_keys=True)
        print(f"Algora bounties analysis written to {batch_path}")
        return
    elif args.fetch_github_issues:
        bounty_service = BountyService()
        bounties = bounty_service.fetch_github_issues(args.repo, args.labels, args.limit)
        
        results = []
        for bounty in bounties:
            repo_name = bounty.get('repo_name')
            if not repo_name:
                print(f"Skipping issue {bounty['id']}: no repo_name")
                continue
            repo_path = Path(repo_name)
            if not repo_path.exists() or not repo_path.is_dir():
                print(f"Skipping issue {bounty['id']}: repo {repo_name} not found locally")
                continue
            
            # Execute repository analysis
            try:
                analysis_result = execute_pipeline(str(repo_path))
                if analysis_result is None:
                    analysis_result = {}
            except Exception as e:
                print(f"Analysis failed for {repo_name}: {e}")
                continue
            
            # Analyze bounty
            repository_url = f"file://{repo_path.absolute()}"
            try:
                assessment = bounty_service.analyze_bounty_opportunity(repository_url, bounty, analysis_result)
                results.append(assessment)
            except Exception as e:
                print(f"Issue analysis failed for {bounty['id']}: {e}")
                continue
        
        # Output results
        output_dir = Path(args.output_dir)
        try:
            output_dir.mkdir(parents=True, exist_ok=True)
        except OSError as e:
            raise OutputGenerationError(f"Cannot create output directory {output_dir}: {e}", {"directory": str(output_dir), "error": str(e)})
        
        batch_path = output_dir / "github_issues_results.json"
        with open(batch_path, 'w') as f:
            json.dump({
                "repo": args.repo,
                "fetched_at": datetime.now().isoformat(),
                "total_issues": len(bounties),
                "analyzed_issues": len(results),
                "results": results
            }, f, indent=2, sort_keys=True)
        print(f"GitHub issues analysis written to {batch_path}")
        return

    # Validate repository path
    if not repo_path.exists():
        raise ValidationError(f"Repository path {repo_path} does not exist", {"path": str(repo_path)})

    if not repo_path.is_dir():
        raise ValidationError(f"Repository path {repo_path} is not a directory", {"path": str(repo_path)})

    # Parse bounty data - handle both single and batch
    try:
        bounty_data = parse_json_input(args.bounty_data)
    except Exception as e:
        raise ValidationError(f"Invalid bounty data format: {e}", {"bounty_data": args.bounty_data})

    # Determine if this is batch processing
    is_batch = args.batch or (isinstance(bounty_data, list) and len(bounty_data) > 1)
    if is_batch and not isinstance(bounty_data, list):
        bounty_data = [bounty_data]  # Convert single item to list for batch processing
    elif not is_batch and isinstance(bounty_data, list):
        if len(bounty_data) > 1:
            is_batch = True  # Auto-detect batch from data
        else:
            bounty_data = bounty_data[0]  # Single item in list

    # Validate bounty data structure
    if is_batch:
        if not isinstance(bounty_data, list):
            raise ValidationError("Batch processing requires bounty data to be a list", {"bounty_data": bounty_data})
        for i, item in enumerate(bounty_data):
            required_bounty_fields = ["id", "title", "description"]
            for field in required_bounty_fields:
                if field not in item:
                    raise ValidationError(f"Bounty item {i} missing required field: {field}", {"missing_field": field, "item_index": i, "bounty_data": item})
    else:
        required_bounty_fields = ["id", "title", "description"]
        for field in required_bounty_fields:
            if field not in bounty_data:
                raise ValidationError(f"Bounty data missing required field: {field}", {"missing_field": field, "bounty_data": bounty_data})

    # Parse solution code if provided
    solution_code = None
    if args.solution_code:
        try:
            solution_code = parse_json_input(args.solution_code)
        except Exception as e:
            raise ValidationError(f"Invalid solution code format: {e}", {"solution_code": args.solution_code})

    # Create output directory
    try:
        output_dir.mkdir(parents=True, exist_ok=True)
    except OSError as e:
        raise OutputGenerationError(f"Cannot create output directory {output_dir}: {e}", {"directory": str(output_dir), "error": str(e)})

    # Execute repository analysis first
    try:
        analysis_result = execute_pipeline(str(repo_path))
        if analysis_result is None:
            analysis_result = {}
    except Exception as e:
        raise AnalysisError(f"Repository analysis failed: {e}", {"error": str(e)}) from e

    # Execute bounty analysis
    try:
        bounty_service = BountyService()
        repository_url = f"file://{repo_path.absolute()}"  # Mock URL for local repo

        if is_batch:
            # Batch processing
            print(f"Processing {len(bounty_data)} bounties in parallel...")
            bounty_assessments = bounty_service.analyze_bounty_batch(
                repository_url, bounty_data, analysis_result, args.batch_id
            )
            bounty_solution = None  # Batch solution generation not supported yet
        else:
            # Single bounty processing
            bounty_assessment = bounty_service.analyze_bounty_opportunity(
                repository_url, bounty_data, analysis_result
            )
            bounty_assessments = [bounty_assessment]  # Wrap in list for consistent handling

            # Generate solution if requested
            if args.generate_solution and solution_code:
                maintainer_profile = bounty_assessment["components"]["maintainer_profile"]
                governance = analysis_result.get("governance", {})

                # Generate ADR analysis for the repository
                from src.core.bounty.adr_engine import ADREngine
                adr_engine = ADREngine()
                adr_analysis = adr_engine.analyze_repository_adrs(str(repo_path))

                bounty_solution = bounty_service.generate_bounty_solution(
                    bounty_data, maintainer_profile, governance, solution_code,
                    adr_analysis, None, str(repo_path)
                )
            else:
                bounty_solution = None

    except Exception as e:
        raise AnalysisError(f"Bounty analysis failed: {e}", {"error": str(e)}) from e

    # Generate outputs
    try:
        if is_batch:
            # Write batch results
            batch_path = output_dir / "bounty_batch_results.json"
            with open(batch_path, 'w') as f:
                json.dump({
                    "batch_id": args.batch_id or f"batch_{int(datetime.now().timestamp())}",
                    "repository_url": repository_url,
                    "total_bounties": len(bounty_assessments),
                    "results": bounty_assessments,
                    "processing_stats": bounty_service.get_performance_stats()
                }, f, indent=2, sort_keys=True)
            print(f"Batch bounty results written to {batch_path}")
        else:
            # Write single bounty assessment
            assessment_path = output_dir / "bounty_assessment.json"
            with open(assessment_path, 'w') as f:
                json.dump(bounty_assessments[0], f, indent=2, sort_keys=True)
            print(f"Bounty assessment written to {assessment_path}")
            try:
                schema_validator.validate_bounty_assessment(str(assessment_path))
            except Exception as e:
                raise ValidationError(f"Schema validation failed for bounty_assessment.json: {e}", {"path": str(assessment_path), "error": str(e)}) from e

            # Write bounty solution if generated
            if bounty_solution:
                solution_path = output_dir / "bounty_solution.json"
                with open(solution_path, 'w') as f:
                    json.dump(bounty_solution, f, indent=2, sort_keys=True)
                print(f"Bounty solution written to {solution_path}")
                try:
                    schema_validator.validate_bounty_solution(str(solution_path))
                except Exception as e:
                    raise ValidationError(f"Schema validation failed for bounty_solution.json: {e}", {"path": str(solution_path), "error": str(e)}) from e

                # Write PR content separately for easy access
                pr_path = output_dir / "pr_content.md"
                pr_content = generate_pr_markdown(bounty_solution["pr_content"])
                pr_path.write_text(pr_content)
                print(f"PR content written to {pr_path}")

    except Exception as e:
        raise OutputGenerationError(f"Output generation failed: {e}", {"error": str(e)}) from e

    print("Bounty analysis completed successfully")


def handle_validate_command(args):
    """Handle bounty validation command."""
    output_dir = Path(args.output_dir)

    # Create output directory
    try:
        output_dir.mkdir(parents=True, exist_ok=True)
    except OSError as e:
        raise OutputGenerationError(f"Cannot create output directory {output_dir}: {e}", {"directory": str(output_dir), "error": str(e)})

    # Execute validation
    try:
        bounty_service = BountyService()
        validation_results = bounty_service.validate_bounty_accuracy()

    except Exception as e:
        raise AnalysisError(f"Validation failed: {e}", {"error": str(e)}) from e

    # Generate validation report
    try:
        report_path = output_dir / "bounty_accuracy_report.md"
        report_content = validation_results.get("report", "No report generated")
        report_path.write_text(report_content)
        print(f"Accuracy report written to {report_path}")

        # Write validation metrics
        metrics_path = output_dir / "bounty_accuracy_metrics.json"
        metrics_dict = validation_results.get("metrics", {})
        if hasattr(metrics_dict, '__dict__'):
            # Convert dataclass to dict
            metrics_dict = {
                'total_predictions': metrics_dict.total_predictions,
                'correct_predictions': metrics_dict.correct_predictions,
                'false_positives': metrics_dict.false_positives,
                'false_negatives': metrics_dict.false_negatives,
                'accuracy_percentage': metrics_dict.accuracy_percentage,
                'precision': metrics_dict.precision,
                'recall': metrics_dict.recall,
                'f1_score': metrics_dict.f1_score,
                'confidence_distribution': metrics_dict.confidence_distribution
            }
        with open(metrics_path, 'w') as f:
            json.dump({
                "metrics": metrics_dict,
                "validation": validation_results.get("validation", {}),
                "errors": validation_results.get("errors", {})
            }, f, indent=2, sort_keys=True)
        print(f"Accuracy metrics written to {metrics_path}")

    except Exception as e:
        raise OutputGenerationError(f"Report generation failed: {e}", {"error": str(e)}) from e

    print("Validation completed successfully")


def parse_json_input(input_str: str) -> dict:
    """Parse JSON input from string or file path."""
    # Try to parse as JSON string first
    try:
        return json.loads(input_str)
    except json.JSONDecodeError:
        pass

    # Try to read as file path
    try:
        with open(input_str, 'r') as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        raise ValueError(f"Invalid JSON input: {input_str}")


def generate_pr_markdown(pr_content: dict) -> str:
    """Generate markdown representation of PR content."""
    title = pr_content.get("title", "Bounty Solution")
    description = pr_content.get("description", "")
    branch = pr_content.get("branch_name", "")
    labels = pr_content.get("labels", [])

    markdown = f"""# {title}

**Branch:** {branch}
**Labels:** {', '.join(labels)}

## Description

{description}

## Checklist

"""

    checklist = pr_content.get("checklist", [])
    for item in checklist:
        checked = "x" if item.get("required", False) else " "
        markdown += f"- [{checked}] {item.get('item', '')}\n"

    return markdown


if __name__ == "__main__":
    main()
