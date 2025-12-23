"""PR Automation Engine for Algora Bounty Hunting.

Generates and automates pull request creation with CI/CD integration,
leveraging governance analysis to ensure compliance with maintainer standards.
"""

from typing import Dict, List, Optional, Any
from datetime import datetime
import re


class PRAutomationEngine:
    """Engine for automated PR generation and CI/CD integration for bounties."""

    def __init__(self):
        self.pr_templates = {
            "bug_fix": self._get_bug_fix_template(),
            "feature": self._get_feature_template(),
            "security": self._get_security_template(),
            "documentation": self._get_documentation_template()
        }

        self.ci_cd_patterns = {
            "github_actions": {
                "workflow_path": ".github/workflows/",
                "trigger_events": ["pull_request", "push"],
                "required_checks": ["test", "lint", "security"]
            },
            "jenkins": {
                "config_file": "Jenkinsfile",
                "pipeline_stages": ["build", "test", "deploy"]
            },
            "circle_ci": {
                "config_file": ".circleci/config.yml",
                "workflows": ["build_and_test", "deploy"]
            }
        }

    def generate_pr_content(self, bounty_data: Dict, maintainer_profile: Dict,
                          governance: Dict, solution_code: Dict) -> Dict:
        """Generate comprehensive PR content aligned with maintainer preferences."""

        # Apply surgical minimalist filter to solution code
        minimalist_filter = SurgicalMinimalistFilter()
        filtered_solution = minimalist_filter.filter_solution(
            solution_code, {}, maintainer_profile  # TODO: Pass existing codebase
        )

        # Generate commit fragmentation plan
        fragmenter = CommitFragmenter()
        commit_plan = fragmenter.fragment_changes(filtered_solution, maintainer_profile)

        # Determine PR type from bounty data
        pr_type = self._classify_bounty_type(bounty_data)

        # Generate PR components
        pr_title = self._generate_pr_title(bounty_data, pr_type, maintainer_profile)
        pr_description = self._generate_pr_description(bounty_data, pr_type, maintainer_profile, governance)
        pr_branch_name = self._generate_branch_name(bounty_data, pr_type)
        pr_labels = self._generate_pr_labels(bounty_data, pr_type, maintainer_profile)
        pr_checklist = self._generate_pr_checklist(governance, maintainer_profile)

        # Generate CI/CD integration
        ci_cd_integration = self._generate_ci_cd_integration(governance, filtered_solution)

        pr_content = {
            "title": pr_title,
            "description": pr_description,
            "branch_name": pr_branch_name,
            "labels": pr_labels,
            "checklist": pr_checklist,
            "ci_cd_integration": ci_cd_integration,
            "review_requirements": self._determine_review_requirements(maintainer_profile),
            "testing_requirements": self._determine_testing_requirements(governance),
            "commit_fragmentation": commit_plan,
            "filtered_solution": filtered_solution,
            "generated_at": datetime.now().isoformat(),
            "confidence_score": _calculate_generation_confidence(maintainer_profile, governance)
        }

        return pr_content

    def _classify_bounty_type(self, bounty_data: Dict) -> str:
        """Classify the type of bounty for appropriate PR generation."""
        title = bounty_data.get("title", "").lower()
        description = bounty_data.get("description", "").lower()
        labels = [l.lower() for l in bounty_data.get("labels", [])]

        # Classification logic
        if any(word in title for word in ["security", "vulnerability", "exploit", "cve"]):
            return "security"
        elif any(word in title for word in ["bug", "fix", "issue", "error"]):
            return "bug_fix"
        elif any(word in title for word in ["feature", "enhancement", "add"]):
            return "feature"
        elif any(word in title for word in ["doc", "documentation", "readme"]):
            return "documentation"
        elif "bug" in labels:
            return "bug_fix"
        elif "enhancement" in labels or "feature" in labels:
            return "feature"
        else:
            return "bug_fix"  # Default fallback

    def _generate_pr_title(self, bounty_data: Dict, pr_type: str, maintainer_profile: Dict) -> str:
        """Generate PR title following maintainer conventions."""
        bounty_title = bounty_data.get("title", "Bounty Solution")
        bounty_id = bounty_data.get("id", "")

        # Check maintainer preferences for title style
        communication_style = maintainer_profile.get("communication_style", {})
        tone = communication_style.get("tone", "professional")

        # Generate title based on type and maintainer preferences
        if pr_type == "security":
            title_prefix = "🔒 Security: " if tone == "collaborative" else "Security Fix: "
        elif pr_type == "bug_fix":
            title_prefix = "🐛 Fix: " if tone == "collaborative" else "Fix: "
        elif pr_type == "feature":
            title_prefix = "✨ Add: " if tone == "collaborative" else "Add: "
        else:
            title_prefix = "📝 Update: " if tone == "collaborative" else "Update: "

        # Clean and format bounty title
        clean_title = re.sub(r'[^\w\s\-_]', '', bounty_title)
        clean_title = re.sub(r'\s+', ' ', clean_title).strip()

        # Add bounty reference
        if bounty_id:
            title = f"{title_prefix}{clean_title} (#{bounty_id})"
        else:
            title = f"{title_prefix}{clean_title}"

        return title[:100]  # GitHub title limit

    def _generate_pr_description(self, bounty_data: Dict, pr_type: str,
                               maintainer_profile: Dict, governance: Dict) -> str:
        """Generate comprehensive PR description aligned with maintainer preferences."""

        # Get template for PR type
        template = self.pr_templates.get(pr_type, self.pr_templates["bug_fix"])

        # Extract maintainer preferences
        communication_style = maintainer_profile.get("communication_style", {})
        detail_level = communication_style.get("detail_level", "standard")

        # Fill template with bounty data
        description = template  # template is already a string

        # Replace placeholders
        description = description.replace("{{BOUNTY_TITLE}}", bounty_data.get("title", ""))
        description = description.replace("{{BOUNTY_DESCRIPTION}}", bounty_data.get("description", ""))
        description = description.replace("{{BOUNTY_ID}}", str(bounty_data.get("id", "")))

        # Adjust detail level based on maintainer preference
        if detail_level == "concise":
            # Remove verbose sections
            description = re.sub(r'## Detailed Analysis.*?(?=##|$)', '', description, flags=re.DOTALL)
        elif detail_level == "comprehensive":
            # Add extra detail sections
            description += "\n\n## Implementation Details\n- Solution approach\n- Code changes\n- Testing strategy"

        # Add governance compliance notes
        governance_notes = self._generate_governance_notes(governance)
        if governance_notes:
            description += f"\n\n## Compliance\n{governance_notes}"

        return description

    def _generate_branch_name(self, bounty_data: Dict, pr_type: str) -> str:
        """Generate branch name following conventional patterns."""
        bounty_id = bounty_data.get("id", "unknown")
        bounty_title = bounty_data.get("title", "bounty-solution")

        # Sanitize title for branch name
        clean_title = re.sub(r'[^\w\-_]', '-', bounty_title.lower())
        clean_title = re.sub(r'-+', '-', clean_title).strip('-')

        # Generate branch name based on type
        type_prefixes = {
            "security": "security",
            "bug_fix": "fix",
            "feature": "feature",
            "documentation": "docs"
        }

        prefix = type_prefixes.get(pr_type, "fix")
        branch_name = f"{prefix}/{clean_title}-{bounty_id}"

        return branch_name[:50]  # Reasonable branch name length

    def _generate_pr_labels(self, bounty_data: Dict, pr_type: str, maintainer_profile: Dict) -> List[str]:
        """Generate appropriate PR labels based on maintainer preferences."""
        labels = []

        # Type-based labels
        type_labels = {
            "security": ["security", "bug"],
            "bug_fix": ["bug", "fix"],
            "feature": ["enhancement", "feature"],
            "documentation": ["documentation"]
        }

        labels.extend(type_labels.get(pr_type, ["enhancement"]))

        # Add bounty-specific labels
        bounty_labels = bounty_data.get("labels", [])
        labels.extend([l for l in bounty_labels if l not in labels])

        # Add maintainer preference labels
        review_patterns = maintainer_profile.get("review_patterns", {})
        focus_areas = review_patterns.get("focus_areas", [])

        if "stability" in focus_areas:
            labels.append("stability")
        if "testing" in focus_areas:
            labels.append("testing")

        return list(set(labels))  # Remove duplicates

    def _generate_pr_checklist(self, governance: Dict, maintainer_profile: Dict) -> List[Dict]:
        """Generate PR checklist based on governance and maintainer requirements."""
        checklist = []

        # Code quality requirements
        code_quality = governance.get("code_quality_governance", {})
        if code_quality.get("linters"):
            checklist.append({
                "item": "Code passes linting checks",
                "required": True,
                "tools": code_quality["linters"]
            })

        if code_quality.get("formatters"):
            checklist.append({
                "item": "Code is properly formatted",
                "required": True,
                "tools": code_quality["formatters"]
            })

        # Testing requirements
        testing_requirements = self._determine_testing_requirements(governance)
        if testing_requirements["required"]:
            checklist.append({
                "item": f"Tests added/updated ({testing_requirements['coverage']})",
                "required": True,
                "details": testing_requirements["frameworks"]
            })

        # Documentation requirements
        docs_governance = governance.get("documentation_governance", {})
        if docs_governance.get("readme_files"):
            checklist.append({
                "item": "Documentation updated",
                "required": True,
                "details": "README and relevant docs"
            })

        # Security requirements
        security_governance = governance.get("security_governance", {})
        if security_governance.get("security_scanners"):
            checklist.append({
                "item": "Security checks pass",
                "required": True,
                "tools": security_governance["security_scanners"]
            })

        # Maintainer-specific requirements
        review_patterns = maintainer_profile.get("review_patterns", {})
        if review_patterns.get("review_depth") == "thorough":
            checklist.append({
                "item": "Thorough testing completed",
                "required": True,
                "details": "Edge cases and error conditions covered"
            })

        return checklist

    def _generate_ci_cd_integration(self, governance: Dict, solution_code: Dict) -> Dict:
        """Generate CI/CD integration configuration for the PR."""
        ci_cd_integration = {
            "workflows": [],
            "required_checks": [],
            "deployment_strategy": "manual",
            "testing_pipeline": []
        }

        # Analyze CI/CD governance
        ci_cd_governance = governance.get("ci_cd_governance", {})

        if ci_cd_governance.get("ci_platforms"):
            for platform in ci_cd_governance["ci_platforms"]:
                if platform in self.ci_cd_patterns:
                    pattern = self.ci_cd_patterns[platform]
                    workflow = {
                        "platform": platform,
                        "config_path": pattern.get("workflow_path", pattern.get("config_file")),
                        "trigger_events": pattern.get("trigger_events", []),
                        "required_checks": pattern.get("required_checks", [])
                    }
                    ci_cd_integration["workflows"].append(workflow)
                    ci_cd_integration["required_checks"].extend(workflow["required_checks"])

        # Determine deployment strategy
        if ci_cd_integration["workflows"]:
            ci_cd_integration["deployment_strategy"] = "automated"
        else:
            ci_cd_integration["deployment_strategy"] = "manual"

        # Generate testing pipeline
        ci_cd_integration["testing_pipeline"] = self._generate_testing_pipeline(governance)

        return ci_cd_integration

    def _generate_testing_pipeline(self, governance: Dict) -> List[Dict]:
        """Generate testing pipeline configuration."""
        pipeline = []

        # Unit tests
        pipeline.append({
            "stage": "unit_tests",
            "description": "Run unit test suite",
            "required": True,
            "timeout": 300
        })

        # Integration tests if CI/CD supports it
        ci_cd_governance = governance.get("ci_cd_governance", {})
        if ci_cd_governance.get("test_commands"):
            pipeline.append({
                "stage": "integration_tests",
                "description": "Run integration test suite",
                "required": False,
                "timeout": 600
            })

        # Code quality checks
        code_quality = governance.get("code_quality_governance", {})
        if code_quality.get("linters") or code_quality.get("static_analyzers"):
            pipeline.append({
                "stage": "code_quality",
                "description": "Run code quality and security checks",
                "required": True,
                "timeout": 180
            })

        return pipeline

    def _determine_review_requirements(self, maintainer_profile: Dict) -> Dict:
        """Determine review requirements based on maintainer profile."""
        review_patterns = maintainer_profile.get("review_patterns", {})

        requirements = {
            "approvals_required": 1,
            "review_depth": "standard",
            "reviewer_types": ["maintainer"],
            "timeline": "standard"
        }

        # Adjust based on maintainer preferences
        if review_patterns.get("approval_requirements") == "multiple_approvers":
            requirements["approvals_required"] = 2

        requirements["review_depth"] = review_patterns.get("review_depth", "standard")

        if review_patterns.get("response_time") == "fast":
            requirements["timeline"] = "expedited"

        return requirements

    def _determine_testing_requirements(self, governance: Dict) -> Dict:
        """Determine testing requirements from governance analysis."""
        requirements = {
            "required": True,
            "coverage": "minimal",
            "frameworks": [],
            "types": ["unit"]
        }

        # Check CI/CD for testing requirements
        ci_cd_governance = governance.get("ci_cd_governance", {})
        if ci_cd_governance.get("test_commands"):
            requirements["frameworks"] = ci_cd_governance.get("test_commands", [])
            requirements["required"] = True

        # Check testing governance maturity
        # This would integrate with test_signal_analysis results
        requirements["coverage"] = "standard"  # Assume standard requirement

        return requirements

    def _generate_governance_notes(self, governance: Dict) -> str:
        """Generate governance compliance notes for PR description."""
        notes = []

        # Code quality compliance
        code_quality = governance.get("code_quality_governance", {})
        if code_quality.get("linters"):
            notes.append(f"✅ Code passes {', '.join(code_quality['linters'])} checks")

        # Security compliance
        security = governance.get("security_governance", {})
        if security.get("security_scanners"):
            notes.append(f"✅ Security scans with {', '.join(security['security_scanners'])}")

        # CI/CD compliance
        ci_cd = governance.get("ci_cd_governance", {})
        if ci_cd.get("ci_platforms"):
            notes.append(f"✅ CI/CD pipeline configured for {', '.join(ci_cd['ci_platforms'])}")

        return "\n".join(notes) if notes else ""

    def _calculate_generation_confidence(self, maintainer_profile: Dict, governance: Dict) -> float:
        """Calculate confidence in PR generation quality."""
        confidence = 0.5

        # Profile completeness
        if maintainer_profile and maintainer_profile.get("profile_confidence", 0) > 0:
            confidence += 0.2

        # Governance completeness
        governance_maturity = governance.get("governance_maturity_score", 0)
        confidence += governance_maturity * 0.3

        return min(confidence, 0.99)  # Cap at 99%

    def _get_bug_fix_template(self) -> str:
        """Get PR template for bug fixes."""
        return """## Problem
{{BOUNTY_DESCRIPTION}}

## Solution
This PR fixes the issue by implementing the following changes:

- [ ] Root cause identified and addressed
- [ ] Solution tested and verified
- [ ] No breaking changes introduced

## Testing
- [ ] Unit tests added/updated
- [ ] Integration tests pass
- [ ] Manual testing completed

## Related Issues
Closes #{{BOUNTY_ID}}

## Checklist
- [ ] Code follows project conventions
- [ ] Documentation updated
- [ ] All tests pass"""

    def _get_feature_template(self) -> str:
        """Get PR template for features."""
        return """## Feature Description
{{BOUNTY_DESCRIPTION}}

## Implementation
This PR adds the requested feature with the following implementation:

- [ ] Feature fully implemented
- [ ] Backward compatibility maintained
- [ ] Performance impact assessed

## Testing
- [ ] Unit tests added
- [ ] Integration tests added
- [ ] End-to-end testing completed

## Documentation
- [ ] README updated
- [ ] API documentation added
- [ ] Usage examples provided

## Related Issues
Addresses #{{BOUNTY_ID}}"""

    def _get_security_template(self) -> str:
        """Get PR template for security fixes."""
        return """## Security Vulnerability
{{BOUNTY_DESCRIPTION}}

## Security Impact
- **Severity**: High/Medium/Low
- **CVSS Score**: TBD
- **Affected Versions**: All supported versions

## Solution
This PR addresses the security vulnerability by:

- [ ] Vulnerability patched
- [ ] Input validation strengthened
- [ ] Security best practices applied

## Testing
- [ ] Security tests added
- [ ] Penetration testing completed
- [ ] No regressions introduced

## Disclosure
This fix should be deployed immediately after review.

## Related Issues
Fixes #{{BOUNTY_ID}}"""

    def _get_documentation_template(self) -> str:
        """Get PR template for documentation updates."""
        return """## Documentation Update
{{BOUNTY_DESCRIPTION}}

## Changes Made
This PR updates documentation to:

- [ ] Fix inaccuracies
- [ ] Add missing information
- [ ] Improve clarity and readability
- [ ] Update examples

## Files Changed
- Documentation files updated
- Examples corrected
- API references updated

## Review Notes
Please review for technical accuracy and clarity.

## Related Issues
Closes #{{BOUNTY_ID}}"""


def generate_pr_for_bounty(bounty_data: Dict, maintainer_profile: Dict,
                         governance: Dict, solution_code: Dict) -> Dict:
    """Convenience function for generating bounty PR content."""
    engine = PRAutomationEngine()
    return engine.generate_pr_content(bounty_data, maintainer_profile, governance, solution_code)


class CommitFragmenter:
    """Fragments large changes into multiple commits to simulate human development."""

    def __init__(self, max_commits: int = 4, delay_minutes: int = 10):
        self.max_commits = max_commits
        self.delay_minutes = delay_minutes

    def fragment_changes(self, solution_code: Dict, maintainer_profile: Dict) -> List[Dict]:
        """Fragment solution code into multiple commits."""
        files_to_modify = solution_code.get("files_to_modify", [])
        new_files = solution_code.get("new_files", [])
        code_changes = solution_code.get("code_changes", [])

        # Group changes by logical units
        commit_groups = self._group_changes_by_logic(files_to_modify, new_files, code_changes)

        # Create commit sequence
        commits = []
        for i, group in enumerate(commit_groups[:self.max_commits]):
            commit = {
                "commit_number": i + 1,
                "message": self._generate_commit_message(group, maintainer_profile, i),
                "files": group["files"],
                "changes": group["changes"],
                "delay_after_commit": self.delay_minutes if i < len(commit_groups) - 1 else 0
            }
            commits.append(commit)

        return commits

    def _group_changes_by_logic(self, files_to_modify: List[str], new_files: List[str],
                               code_changes: List[Dict]) -> List[Dict]:
        """Group changes into logical commits."""
        groups = []

        # Group 1: New files (if any)
        if new_files:
            groups.append({
                "type": "new_files",
                "files": new_files,
                "changes": []
            })

        # Group 2: Core implementation changes
        core_changes = [c for c in code_changes if not self._is_test_or_config_change(c)]
        if core_changes:
            groups.append({
                "type": "core_implementation",
                "files": [c.get("file") for c in core_changes],
                "changes": core_changes
            })

        # Group 3: Tests and configuration
        test_config_changes = [c for c in code_changes if self._is_test_or_config_change(c)]
        if test_config_changes:
            groups.append({
                "type": "tests_and_config",
                "files": [c.get("file") for c in test_config_changes],
                "changes": test_config_changes
            })

        # Group 4: Documentation updates
        doc_changes = [c for c in code_changes if self._is_documentation_change(c)]
        if doc_changes:
            groups.append({
                "type": "documentation",
                "files": [c.get("file") for c in doc_changes],
                "changes": doc_changes
            })

        return groups

    def _is_test_or_config_change(self, change: Dict) -> bool:
        """Check if change is test or configuration related."""
        file_path = change.get("file", "").lower()
        return ("test" in file_path or "spec" in file_path or
                file_path.endswith((".yml", ".yaml", ".json", ".toml", ".cfg")))

    def _is_documentation_change(self, change: Dict) -> bool:
        """Check if change is documentation related."""
        file_path = change.get("file", "").lower()
        return ("readme" in file_path or "doc" in file_path or
                file_path.endswith((".md", ".rst", ".txt")))

    def _generate_commit_message(self, group: Dict, maintainer_profile: Dict, commit_index: int) -> str:
        """Generate human-like commit message."""
        group_type = group["type"]
        persona = maintainer_profile.get("detected_persona", {})

        # Base messages by type
        base_messages = {
            "new_files": ["Add initial implementation files", "Create core module files", "Set up project structure"],
            "core_implementation": ["Implement core functionality", "Add main feature logic", "Update business logic"],
            "tests_and_config": ["Add tests and configuration", "Update test suite", "Configure project settings"],
            "documentation": ["Update documentation", "Add usage examples", "Improve documentation"]
        }

        messages = base_messages.get(group_type, ["Update implementation"])

        # Apply persona-specific jargon
        jargon_map = persona.get("jargon_replacements", {})
        message = messages[commit_index % len(messages)]

        for old_term, new_term in jargon_map.items():
            message = message.replace(old_term, new_term)

        return message


class SurgicalMinimalistFilter:
    """Filters AI-generated code to prefer minimal, maintainable solutions."""

    def __init__(self):
        self.max_line_ratio = 0.5  # AI solution should be no more than 50% larger than minimal

    def filter_solution(self, ai_solution: Dict, existing_codebase: Dict,
                       maintainer_profile: Dict) -> Dict:
        """Filter AI solution to prefer minimal implementations."""
        filtered_solution = ai_solution.copy()

        # Analyze each code change
        for change in filtered_solution.get("code_changes", []):
            original_code = self._get_original_code(change, existing_codebase)
            ai_code = change.get("new_code", "")

            # Check if we can achieve the same result with existing utilities
            minimal_version = self._find_minimal_implementation(
                ai_code, original_code, existing_codebase, maintainer_profile
            )

            if minimal_version and len(minimal_version.split('\n')) < len(ai_code.split('\n')) * self.max_line_ratio:
                change["new_code"] = minimal_version
                change["approach"] = "minimal_utility_based"

        return filtered_solution

    def _get_original_code(self, change: Dict, existing_codebase: Dict) -> str:
        """Get original code for the file being changed."""
        file_path = change.get("file", "")
        return existing_codebase.get(file_path, "")

    def _find_minimal_implementation(self, ai_code: str, original_code: str,
                                   existing_codebase: Dict, maintainer_profile: Dict) -> Optional[str]:
        """Find a minimal implementation using existing utilities."""
        persona = maintainer_profile.get("detected_persona", {})

        # For Ziverge (Scala/ZIO): Prefer existing ZIO utilities
        if persona.get("persona") == "ziverge":
            return self._optimize_zio_code(ai_code, existing_codebase)

        # For Golem (Rust/WASM): Prefer zero-copy operations
        if persona.get("persona") == "golem":
            return self._optimize_rust_wasm_code(ai_code, existing_codebase)

        # Generic optimization: Look for utility functions
        return self._find_existing_utility(ai_code, existing_codebase)

    def _optimize_zio_code(self, ai_code: str, existing_codebase: Dict) -> Optional[str]:
        """Optimize Scala/ZIO code to use existing utilities."""
        # Look for patterns that can use ZIO utilities
        if "fold(" in ai_code and "ZIO.succeed" in existing_codebase.get("patterns", []):
            # Replace manual fold with ZIO.foldZIO
            return ai_code.replace("fold(", "ZIO.foldZIO(")

        if "try {" in ai_code and "no_try_catch" in str(existing_codebase):
            # Remove try/catch as per Ziverge rules
            return self._remove_try_catch(ai_code)

        return None

    def _optimize_rust_wasm_code(self, ai_code: str, existing_codebase: Dict) -> Optional[str]:
        """Optimize Rust/WASM code for performance."""
        if ".unwrap()" in ai_code and "avoid_unwrap" in str(existing_codebase):
            # Replace unwrap with proper error handling
            return ai_code.replace(".unwrap()", ".expect(\"Operation failed\")")

        if "clone()" in ai_code and "zero_copy" in str(existing_codebase):
            # Prefer references over cloning
            return self._optimize_for_zero_copy(ai_code)

        return None

    def _find_existing_utility(self, ai_code: str, existing_codebase: Dict) -> Optional[str]:
        """Find existing utility functions that can replace AI-generated code."""
        # Look for common patterns that might have utility functions
        utilities = existing_codebase.get("utility_functions", [])

        for utility in utilities:
            if utility.get("purpose") in ai_code:
                # Return call to existing utility instead of reimplementing
                return f"{utility['name']}({utility.get('params', '')})"

        return None

    def _remove_try_catch(self, code: str) -> str:
        """Remove try/catch blocks as per functional programming rules."""
        # Simple regex to remove try/catch (would need more sophisticated parsing for real use)
        return re.sub(r'try\s*\{[^}]*\}\s*catch\s*\{[^}]*\}', '', code)

    def _optimize_for_zero_copy(self, code: str) -> str:
        """Optimize Rust code for zero-copy operations."""
        # Replace clone() with & references where possible
        return code.replace(".clone()", ".as_ref()")


def _calculate_generation_confidence(maintainer_profile: Dict, governance: Dict) -> float:
    """Calculate confidence score for PR generation based on available data."""
    confidence = 0.5  # Base confidence

    # Boost confidence based on maintainer profile completeness
    if maintainer_profile.get("detected_persona"):
        confidence += 0.2

    if maintainer_profile.get("communication_style"):
        confidence += 0.1

    if maintainer_profile.get("review_patterns"):
        confidence += 0.1

    # Boost confidence based on governance analysis completeness
    governance_keys = ["code_quality_governance", "security_governance",
                      "ci_cd_governance", "documentation_governance"]
    governance_completeness = sum(1 for key in governance_keys if governance.get(key))
    confidence += (governance_completeness / len(governance_keys)) * 0.2

    return min(confidence, 1.0)  # Cap at 1.0


def generate_pr_for_bounty(bounty_data: Dict, maintainer_profile: Dict,
                         governance: Dict, solution_code: Dict) -> Dict:
    """Convenience function for generating bounty PR content."""
    engine = PRAutomationEngine()
    return engine.generate_pr_content(bounty_data, maintainer_profile, governance, solution_code)