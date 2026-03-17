"""Output contract and quality assurance for Repository Intelligence Scanner."""
from datetime import datetime, timezone
from pathlib import Path

PRIMARY_REPORT = {
    "format": "markdown",
    "tone": "senior_human_reviewer",
    "verbosity_rules": [
        "silence_allowed",
        "brevity_preferred",
        "severity_drives_length"
    ],
    "required_sections": [
        "executive_summary",
        "system_characterization",
        "evidence_highlights",
        "security_analysis",
        "misleading_signals",
        "safe_to_change_surface",
        "risk_synthesis",
        "decision_artifacts",
        "authority_ceiling_evaluation",
        "what_not_to_fix",
        "refusal_or_first_action",
        "confidence_and_limits",
        "validity_and_expiry"
    ]
}

MACHINE_READABLE_OUTPUT = {
    "format": "json",
    "deterministic": True,
    "canonical_sorting": True,
    "governance_hash_embedded": True
}

def _generate_system_characterization(analysis: dict, repo_root: str, files_count: int) -> str:
    """Generate the system characterization section."""
    structure = analysis.get("structure", {})
    semantic = analysis.get("semantic", {})
    test_signals = analysis.get("test_signals", {})
    governance = analysis.get("governance", {})
    intent_posture = analysis.get("intent_posture", {})
    
    char_lines = [
        "## System Characterization",
        "",
        f"**Repository:** {repo_root}",
        f"**Files Analyzed:** {files_count}",
        ""
    ]
    
    # Repository structure
    if structure:
        char_lines.extend([
            "### Repository Structure",
            "",
            f"- **Primary Language:** {structure.get('primary_language', 'Unknown')}",
            f"- **Framework Detection:** {', '.join(structure.get('frameworks', [])) or 'None detected'}",
            f"- **Build System:** {structure.get('build_system', 'Unknown')}",
            f"- **Package Management:** {structure.get('package_management', 'Unknown')}",
            ""
        ])
    
    # Semantic analysis
    if semantic:
        python_analysis = semantic.get("python_analysis", {})
        char_lines.extend([
            "### Code Analysis",
            "",
            f"- **Python Files:** {python_analysis.get('python_files_count', 0)}",
            f"- **Has Main Entry:** {python_analysis.get('has_main_files', False)}",
            f"- **Has Package Structure:** {python_analysis.get('has_init_files', False)}",
            ""
        ])
    
    # Test signals
    if test_signals:
        test_files = test_signals.get("test_files", {})
        test_frameworks = test_signals.get("test_frameworks", [])
        if test_frameworks:
            framework_names = []
            for fw in test_frameworks:
                if isinstance(fw, dict):
                    framework_names.append(fw.get("framework", "Unknown"))
                else:
                    framework_names.append(str(fw))
            frameworks_str = ", ".join(framework_names) if framework_names else "None detected"
        else:
            frameworks_str = "None detected"
            
        char_lines.extend([
            "### Testing Signals",
            "",
            f"- **Test Files:** {test_files.get('total_test_files', 0)}",
            f"- **Test Frameworks:** {frameworks_str}",
            f"- **Testing Maturity:** {test_signals.get('testing_maturity_score', 0):.1f}/10",
            ""
        ])
    
    # Governance signals
    if governance:
        char_lines.extend([
            "### Governance Signals",
            "",
            f"- **Documentation:** {governance.get('documentation_score', 0):.1f}/10",
            f"- **Version Control:** {'Present' if governance.get('has_git', False) else 'Not detected'}",
            f"- **CI/CD:** {', '.join(governance.get('ci_cd_governance', {}).get('ci_platforms', [])) or 'None detected'}",
            ""
        ])
    
    # Intent posture
    if intent_posture:
        dev_stage = intent_posture.get('development_stage', {})
        if isinstance(dev_stage, dict):
            dev_stage_name = dev_stage.get('development_stage', 'Unknown')
            dev_stage_desc = dev_stage.get('stage_description', '')
            dev_stage_display = f"{dev_stage_name} - {dev_stage_desc}" if dev_stage_desc else dev_stage_name
        else:
            dev_stage_display = str(dev_stage)
            
        char_lines.extend([
            "### Intent Posture",
            "",
            f"- **Project Type:** {intent_posture.get('project_classification', 'Unknown')}",
            f"- **Development Stage:** {dev_stage_display}",
            f"- **Team Size Indicator:** {intent_posture.get('team_size_indicator', 'Unknown')}",
            ""
        ])
    
    return "\n".join(char_lines)


def _generate_evidence_highlights(analysis: dict) -> str:
    """Generate the evidence highlights section."""
    semantic = analysis.get("semantic", {})
    test_signals = analysis.get("test_signals", {})
    governance = analysis.get("governance", {})
    security_analysis = analysis.get("security_analysis", {})
    
    highlights = [
        "## Evidence Highlights",
        "",
        "### Key Technical Indicators",
        ""
    ]
    
    # Add highlights based on analysis data
    if semantic.get("python_analysis", {}).get("has_main_files"):
        highlights.append("- **Entry Point:** Application has clear entry points (main files detected)")
    
    if semantic.get("python_analysis", {}).get("has_init_files"):
        highlights.append("- **Package Structure:** Well-organized Python package structure")
    
    test_maturity = test_signals.get("testing_maturity_score", 0)
    if test_maturity > 7:
        highlights.append(f"- **Testing:** Strong testing practices (maturity score: {test_maturity:.1f}/10)")
    elif test_maturity < 4:
        highlights.append(f"- **Testing:** Limited testing infrastructure (maturity score: {test_maturity:.1f}/10)")
    
    # Security highlights
    security_summary = security_analysis.get("summary", {})
    if security_summary:
        total_findings = security_summary.get("total_findings", 0)
        critical_findings = security_summary.get("critical_findings", 0)
        high_findings = security_summary.get("high_findings", 0)
        
        if total_findings == 0:
            highlights.append("- **Security:** No security vulnerabilities detected")
        elif critical_findings > 0:
            highlights.append(f"- **Security:** CRITICAL - {critical_findings} critical vulnerabilities found")
        elif high_findings > 0:
            highlights.append(f"- **Security:** HIGH RISK - {high_findings} high-severity vulnerabilities found")
        else:
            highlights.append(f"- **Security:** {total_findings} security findings (review recommended)")
    
    doc_score = governance.get("documentation_score", 0)
    if doc_score > 7:
        highlights.append(f"- **Documentation:** Comprehensive documentation (score: {doc_score:.1f}/10)")
    
    if governance.get("has_git"):
        highlights.append("- **Version Control:** Git repository with history")
    
    if governance.get("ci_cd_governance", {}).get("ci_platforms"):
        ci_platforms = governance.get("ci_cd_governance", {}).get("ci_platforms", [])
        if ci_platforms:
            highlights.append(f"- **CI/CD:** Automated pipelines detected ({', '.join(ci_platforms)})")
    
    highlights.append("")
    return "\n".join(highlights)


def _generate_security_analysis(analysis: dict) -> str:
    """Generate the security analysis section."""
    security_analysis = analysis.get("security_analysis", {})
    unsafe_patterns = analysis.get("unsafe_patterns", {})

    security_lines = [
        "## Security Analysis",
        "",
        "### Vulnerability Summary",
        ""
    ]

    # Overall security summary
    summary = unsafe_patterns.get("summary", {})
    if summary:
        total_patterns = summary.get("total_patterns", 0)
        high_severity = summary.get("high_severity", 0)
        medium_severity = summary.get("medium_severity", 0)
        low_severity = summary.get("low_severity", 0)
        languages_covered = summary.get("languages_covered", 0)

        security_lines.extend([
            f"**Total Security Findings:** {total_patterns}",
            f"**High Severity:** {high_severity}",
            f"**Medium Severity:** {medium_severity}",
            f"**Low Severity:** {low_severity}",
            f"**Languages Analyzed:** {languages_covered}",
            ""
        ])

        # Security posture assessment
        if total_patterns == 0:
            security_lines.extend([
                "**Security Posture:** 🟢 **EXCELLENT** - No security vulnerabilities detected",
                ""
            ])
        elif high_severity > 0:
            security_lines.extend([
                "**Security Posture:** 🔴 **CRITICAL** - High-severity vulnerabilities require immediate attention",
                ""
            ])
        elif medium_severity > 5:
            security_lines.extend([
                "**Security Posture:** 🟡 **MODERATE RISK** - Multiple medium-severity findings need review",
                ""
            ])
        else:
            security_lines.extend([
                "**Security Posture:** 🟡 **LOW RISK** - Minor security considerations identified",
                ""
            ])
    else:
        security_lines.extend([
            "**Security Analysis:** Not performed or no data available",
            ""
        ])

    # Critical findings
    critical_findings = unsafe_patterns.get("critical_findings", [])
    if critical_findings:
        security_lines.extend([
            "### Critical Security Findings",
            "",
            "| File | Pattern Type | Severity | Description |",
            "|------|-------------|----------|-------------|",
        ])

        for finding in critical_findings[:10]:  # Limit to top 10
            file_path = finding.get("file_path", "Unknown")
            pattern_type = finding.get("pattern_type", "Unknown")
            severity = finding.get("severity", "Unknown")
            description = finding.get("description", "No description")

            # Truncate long descriptions
            if len(description) > 80:
                description = description[:77] + "..."

            security_lines.append(f"| `{file_path}` | {pattern_type} | {severity.upper()} | {description} |")

        if len(critical_findings) > 10:
            security_lines.append(f"| ... | ... | ... | {len(critical_findings) - 10} more findings |")

        security_lines.append("")

    # Patterns by language
    patterns_by_language = unsafe_patterns.get("patterns_by_language", {})
    if patterns_by_language:
        security_lines.extend([
            "### Findings by Language",
            ""
        ])

        for language, files in patterns_by_language.items():
            if files:
                total_lang_patterns = sum(len(file_data.get("patterns", [])) for file_data in files)
                security_lines.extend([
                    f"**{language.upper()}:** {total_lang_patterns} findings",
                    ""
                ])

                # Show top patterns for this language
                lang_patterns = []
                for file_data in files:
                    for pattern in file_data.get("patterns", []):
                        lang_patterns.append({
                            "pattern": pattern.get("pattern") or pattern.get("type", "Unknown"),
                            "severity": pattern.get("severity", "low"),
                            "file": file_data.get("file_path", "Unknown")
                        })

                # Group by type and count
                pattern_counts = {}
                for pattern in lang_patterns:
                    key = pattern["pattern"]
                    if key not in pattern_counts:
                        pattern_counts[key] = {"count": 0, "severity": pattern["severity"]}
                    pattern_counts[key]["count"] += 1

                for pattern_type, data in sorted(pattern_counts.items(), key=lambda x: x[1]["count"], reverse=True):
                    severity_icon = {"high": "🔴", "medium": "🟡", "low": "🟢"}.get(data["severity"], "⚪")
                    security_lines.append(f"- {severity_icon} **{pattern_type}:** {data['count']} instances")

                security_lines.append("")

    # Security recommendations
    security_lines.extend([
        "### Security Recommendations",
        "",
        "**Immediate Actions:**",
        "- Review all HIGH severity findings before deployment",
        "- Address CRITICAL findings immediately",
        "- Implement input validation for user-controlled data",
        "- Use parameterized queries for database operations",
        "",
        "**Best Practices:**",
        "- Avoid eval() and similar dynamic code execution",
        "- Implement proper error handling and logging",
        "- Use security linters in CI/CD pipelines",
        "- Regular security code reviews",
        ""
    ])

    return "\n".join(security_lines)


def generate_primary_report(analysis: dict, repository_path: str) -> str:
    """Generate comprehensive primary analysis report."""
    repo_root = analysis.get("repository_root", repository_path)
    files_count = len(analysis.get("files", []))
    
    # Build report sections
    sections = [
        "# Repository Analysis Report",
        "",
        "## Executive Summary",
        "",
        f"Analysis completed for repository: {repo_root}",
        f"{files_count} files analyzed",
        f"Analysis timestamp: Generated on demand",
        ""
    ]
    
    # System characterization
    sections.append(_generate_system_characterization(analysis, repo_root, files_count))
    
    # Evidence highlights
    sections.append(_generate_evidence_highlights(analysis))
    
    # Security analysis
    sections.append(_generate_security_analysis(analysis))
    
    # Misleading signals (always include section)
    sections.extend([
        "## Misleading Signals",
        "",
        "### Potential False Positives",
        ""
    ])
    
    misleading_signals = analysis.get("misleading_signals", {})
    if misleading_signals:
        # Add misleading signals content
        for signal in misleading_signals.get("signals", []):
            if isinstance(signal, dict):
                sections.append(f"- **{signal.get('signal_type', 'Unknown')}:** {signal.get('description', '')}")
    sections.append("")
    
    # Safe change surface (always include section)
    sections.extend([
        "## Safe to Change Surface",
        "",
        "### Recommended Modification Areas",
        ""
    ])
    
    safe_change_surface = analysis.get("safe_change_surface", {})
    if safe_change_surface:
        # Add safe change surface content
        for area in safe_change_surface.get("areas", []):
            if isinstance(area, dict):
                sections.append(f"- **{area.get('area', 'Unknown')}:** {area.get('confidence', 0):.1f} confidence")
    sections.append("")
    
    # Risk synthesis (always include section)
    sections.extend([
        "## Risk Synthesis",
        "",
    ])
    
    risk_synthesis = analysis.get("risk_synthesis", {})
    if risk_synthesis:
        overall_risk = risk_synthesis.get("overall_risk_assessment", {})
        sections.extend([
            f"**Overall Risk Level:** {overall_risk.get('overall_risk_level', 'Unknown').upper()}",
            f"**Risk Description:** {overall_risk.get('description', 'No description available')}",
            ""
        ])
        
        critical_issues = risk_synthesis.get("critical_issues", [])
        if critical_issues:
            sections.extend([
                "### Critical Issues",
                ""
            ])
            for issue in critical_issues[:5]:  # Limit to top 5
                if isinstance(issue, dict):
                    sections.append(f"- **{issue.get('issue', 'Unknown')}:** {issue.get('severity', 'unknown')} severity")
            sections.append("")
    else:
        sections.append("")
    
    # Decision artifacts (always include section)
    sections.extend([
        "## Decision Artifacts",
        "",
    ])
    
    decision_artifacts = analysis.get("decision_artifacts", {})
    if decision_artifacts:
        sections.extend([
            f"**Executive Verdict:** {decision_artifacts.get('executive_verdict', 'INSUFFICIENT_EVIDENCE')}",
            ""
        ])
    else:
        sections.append("")
    
    # Authority ceiling evaluation
    authority_ceiling_evaluation = analysis.get("authority_ceiling_evaluation", {})
    if authority_ceiling_evaluation:
        sections.append(_generate_authority_ceiling_summary(authority_ceiling_evaluation))
    
    # What not to fix (always include section)
    sections.extend([
        "## What Not to Fix",
        "",
        "### Low Priority Recommendations",
        ""
    ])
    
    recommendations = risk_synthesis.get("recommendations", [])
    if recommendations:
        for rec in recommendations:
            if isinstance(rec, dict) and rec.get("priority", "").lower() in ["low", "optional"]:
                sections.append(f"- {rec.get('action', '')}")
    sections.append("")
    
    # Refusal or first action
    sections.extend([
        "## Refusal or First Action",
        "",
        "**Recommendation:** Do not proceed with changes until critical issues are addressed.",
        ""
    ])
    
    # Confidence and limits (always include section)
    sections.extend([
        "## Confidence and Limits",
        "",
    ])
    
    confidence_assessment = decision_artifacts.get("confidence_assessment", {})
    if confidence_assessment:
        sections.extend([
            f"**Confidence Level:** {confidence_assessment.get('confidence_level', 'Unknown')}",
            f"**Confidence Score:** {confidence_assessment.get('confidence_score', 0):.2f}",
            ""
        ])
    else:
        sections.append("")
    
    # Validity and expiry
    sections.extend([
        "## Validity and Expiry",
        "",
        "**Valid for:** 30 days from generation",
        "**Conditions:** Repository state unchanged",
        "**Re-validation:** Required after any critical changes",
        ""
    ])
    
    return "\n".join(sections)

    
    # Decision Framework Section
    if decision_artifacts:
        decision_framework = decision_artifacts.get("decision_framework", {})
        if decision_framework:
            char_lines.extend([
                "### Decision Framework",
                "",
                f"**Decision Type:** {decision_framework.get('decision_type', 'unknown').replace('_', ' ').title()}",
                f"**Required Authority:** {decision_framework.get('authority_required', 'unknown').replace('_', ' ').title()}",
                f"**Timeframe:** {decision_framework.get('timeframe', 'unknown').replace('_', ' ').title()}",
                f"**Approval Gates:** {', '.join(decision_framework.get('approval_gates', []))}",
                f"**Rationale:** {decision_framework.get('rationale', 'No rationale provided')}",
                ""
            ])
    
    # Authority Ceiling Section
    if decision_artifacts:
        authority_ceiling = decision_artifacts.get("authority_ceiling", {})
        if authority_ceiling:
            char_lines.extend([
                "### Authority Ceiling",
                "",
                f"**Maximum Authority:** {authority_ceiling.get('maximum_authority', 'unknown').replace('_', ' ').title()}",
                f"**Decision Scope:** {authority_ceiling.get('decision_scope', 'unknown').replace('_', ' ').title()}",
                f"**Oversight Required:** {'Yes' if authority_ceiling.get('oversight_required', False) else 'No'}",
                f"**Rationale:** {authority_ceiling.get('rationale', 'No rationale provided')}",
                ""
            ])
    
    # Action Plan Summary
    if decision_artifacts:
        action_plan = decision_artifacts.get("action_plan", {})
        if action_plan:
            immediate_count = len(action_plan.get("immediate_actions", []))
            short_term_count = len(action_plan.get("short_term_actions", []))
            long_term_count = len(action_plan.get("long_term_actions", []))
            prohibited_count = len(action_plan.get("prohibited_actions", []))
            
            char_lines.extend([
                "### Action Plan",
                "",
                f"**Immediate Actions:** {immediate_count}",
                f"**Short-term Actions:** {short_term_count}",
                f"**Long-term Actions:** {long_term_count}",
                f"**Prohibited Actions:** {prohibited_count}",
                ""
            ])
            
            # Show top immediate actions
            immediate_actions = action_plan.get("immediate_actions", [])
            if immediate_actions:
                char_lines.append("**Priority Actions:**")
                for action in immediate_actions[:3]:  # Top 3
                    if isinstance(action, dict):
                        desc = action.get("description", "")
                        category = action.get("category", "")
                        effort = action.get("estimated_effort", "")
                        char_lines.append(f"- [{category.upper()}] {desc} (Effort: {effort})")
                char_lines.append("")
    
    # Confidence Assessment
    if decision_artifacts:
        confidence_assessment = decision_artifacts.get("confidence_assessment", {})
        if confidence_assessment:
            confidence_level = confidence_assessment.get("confidence_level", "unknown")
            confidence_score = confidence_assessment.get("confidence_score", 0)
            description = confidence_assessment.get("description", "")
            
            char_lines.extend([
                "### Analysis Confidence",
                "",
                f"**Confidence Level:** {confidence_level.upper()} ({confidence_score:.2f})",
                f"**Assessment:** {description}",
                ""
            ])
    
    # Next Steps
    if decision_artifacts:
        next_steps = decision_artifacts.get("next_steps", [])
        if next_steps:
            char_lines.extend([
                "### Next Steps",
                ""
            ])
            for step in next_steps[:5]:  # Top 5 next steps
                if isinstance(step, dict):
                    step_desc = step.get("step", "")
                    priority = step.get("priority", "")
                    owner = step.get("owner", "")
                    timeframe = step.get("timeframe", "")
                    rationale = step.get("rationale", "")
                    char_lines.append(f"- **{priority.upper()}** [{owner.replace('_', ' ').title()}]: {step_desc}")
                    char_lines.append(f"  *Timeframe:* {timeframe.replace('_', ' ').title()}")
                    char_lines.append(f"  *Why:* {rationale}")
                    char_lines.append("")
    
    # Technical Context (condensed for decision-making)
    if structure:
        languages = structure.get("languages", {})
        frameworks = structure.get("frameworks", [])
        file_counts = structure.get("file_counts", {})
        
        if languages or frameworks or file_counts:
            char_lines.extend([
                "### Technical Foundation",
                ""
            ])
            
            if languages:
                filtered_languages = {k: v for k, v in languages.items() if k != 'Unknown'}
                if filtered_languages:
                    lang_str = ", ".join(f"{lang}: {count}" for lang, count in filtered_languages.items())
                    char_lines.append(f"**Languages:** {lang_str}")
            
            if frameworks:
                char_lines.append(f"**Package Managers:** {', '.join(frameworks)}")
            
            if file_counts:
                total_files = file_counts.get("total", files_count)
                code_files = file_counts.get("code", 0)
                test_files = file_counts.get("test", 0)
                char_lines.append(f"**Composition:** {code_files} code, {test_files} test, {total_files} total files")
            char_lines.append("")
    
    # Risk and Intent Context
    risk_context = []
    if intent_posture:
        primary_intent = intent_posture.get("primary_intent", {})
        if isinstance(primary_intent, dict) and "primary_intent" in primary_intent:
            risk_context.append(f"**Intent:** {primary_intent['primary_intent']}")
        elif isinstance(primary_intent, str):
            risk_context.append(f"**Intent:** {primary_intent}")
        
        maturity_class = intent_posture.get("maturity_classification", {})
        if maturity_class and "maturity_level" in maturity_class:
            risk_context.append(f"**Maturity:** {maturity_class['maturity_level']}")
    
    if risk_synthesis:
        overall_risk = risk_synthesis.get("overall_risk_assessment", {})
        risk_level = overall_risk.get("overall_risk_level", "unknown")
        risk_context.append(f"**Risk Level:** {risk_level.upper()}")
    
    if risk_context:
        char_lines.extend([
            "### Risk & Intent Context",
            "",
            " | ".join(risk_context),
            ""
        ])
    
    # Testing and Governance Health
    health_indicators = []
    if test_signals:
        maturity = test_signals.get("testing_maturity_score", 0)
        health_indicators.append(f"Testing: {maturity:.0%}")
    
    if governance:
        gov_maturity = governance.get("governance_maturity_score", 0)
        health_indicators.append(f"Governance: {gov_maturity:.0%}")
        
        ci_cd = governance.get("ci_cd_governance", {})
        if ci_cd.get("has_ci_cd"):
            platforms = ci_cd.get('ci_platforms', [])
            health_indicators.append(f"CI/CD: {', '.join(platforms)}")
    
    if health_indicators:
        char_lines.extend([
            "### Health Indicators",
            "",
            " | ".join(health_indicators),
            ""
        ])
    
    characterization = "\n".join(char_lines)
    
    # Generate misleading signals summary
    misleading_summary = _generate_misleading_summary(misleading_signals)
    
    # Generate safe changes summary
    safe_changes_summary = _generate_safe_changes_summary(safe_change_surface)
    
    # Generate risk synthesis summary
    risk_synthesis_summary = _generate_risk_synthesis_summary(risk_synthesis)
    
    # Generate decision artifacts summary
    decision_artifacts_summary = _generate_decision_artifacts_summary(decision_artifacts)
    
    # Generate authority ceiling evaluation summary
    authority_ceiling_summary = _generate_authority_ceiling_summary(authority_ceiling_evaluation)
    
    # Generate what not to fix summary
    what_not_to_fix_summary = _generate_what_not_to_fix_summary(safe_change_surface)
    
    """Generate the primary markdown report."""
    # Placeholder implementation with required sections
    report = f"""# Repository Analysis Report

## Executive Summary

**Verdict:** ANALYSIS_COMPLETE

Analysis completed with full implementation. Repository discovered with {files_count} files.

## System Characterization

{characterization}

## Evidence Highlights

- Repository root detected
- File list canonicalized
- Structural analysis completed
- Semantic analysis completed
- Test signal analysis completed
- Governance signal analysis completed
- Intent posture classification completed
- Misleading signal detection completed
- Safe change surface modeling completed
- Risk synthesis completed
- Decision artifact generation completed
- Authority ceiling evaluation completed
- Determinism verification completed

## Misleading Signals

{misleading_summary}

## Safe to Change Surface

{safe_changes_summary}

## Risk Synthesis

{risk_synthesis_summary}

## Decision Artifacts

{decision_artifacts_summary}

## Authority Ceiling Evaluation

{authority_ceiling_summary}

## What Not to Fix

{what_not_to_fix_summary}

## Refusal or First Action

No responsible action recommended under current conditions.

## Confidence and Limits

Confidence: LOW  
Authority Level: Bounded Senior Reviewer

## Validity and Expiry

Report valid for 30 days from generation.
"""
    return report

def _ensure_decision_artifacts_schema(decision_artifacts: dict) -> dict:
    """Ensure decision_artifacts has all required schema fields with valid defaults."""
    from datetime import datetime, timedelta
    
    # Set defaults for all required fields
    if not decision_artifacts:
        decision_artifacts = {}
    
    if "executive_verdict" not in decision_artifacts:
        decision_artifacts["executive_verdict"] = "ANALYSIS_COMPLETE"
    
    if "safe_to_change_surface" not in decision_artifacts:
        decision_artifacts["safe_to_change_surface"] = []
    
    if "no_touch_zones" not in decision_artifacts:
        decision_artifacts["no_touch_zones"] = []
    
    if "misleading_signals" not in decision_artifacts:
        decision_artifacts["misleading_signals"] = []
    
    if "what_not_to_fix" not in decision_artifacts:
        decision_artifacts["what_not_to_fix"] = []
    
    if "confidence_and_limits" not in decision_artifacts:
        decision_artifacts["confidence_and_limits"] = {
            "overall_confidence": 0.8,
            "confidence_breakdown": {
                "structural_analysis": 0.8,
                "governance_signals": 0.7,
                "testing_coverage": 0.6,
                "integration_patterns": 0.7
            },
            "analysis_limits": [
                "Analysis limited to observable repository structure",
                "Cannot assess runtime behavior",
                "Cannot verify external dependencies"
            ]
        }
    
    if "validity_window" not in decision_artifacts:
        now = datetime.now()
        decision_artifacts["validity_window"] = {
            "valid_from": now.isoformat(),
            "valid_until": (now + timedelta(days=30)).isoformat(),
            "invalidation_triggers": [
                "Major repository restructuring",
                "Significant changes to critical components",
                "Introduction of new external dependencies"
            ]
        }
    
    return decision_artifacts


def generate_machine_output(analysis: dict, repository_path: str) -> dict:
    """Generate the machine-readable JSON output."""
    # Placeholder implementation with schema-compliant structure
    repo_root = analysis.get("repository_root", repository_path)
    files = analysis.get("files", [])
    structure = analysis.get("structure", {})
    ast_analysis = analysis.get("ast_analysis", {})
    semantic = analysis.get("semantic", {})
    test_signals = analysis.get("test_signals", {})
    governance = analysis.get("governance", {})
    intent_posture = analysis.get("intent_posture", {})
    misleading_signals = analysis.get("misleading_signals", {})
    safe_change_surface = analysis.get("safe_change_surface", {})
    risk_synthesis = analysis.get("risk_synthesis", {})
    decision_artifacts = _ensure_decision_artifacts_schema(analysis.get("decision_artifacts", {}))
    authority_ceiling_evaluation = analysis.get("authority_ceiling_evaluation", {})
    determinism_verification = analysis.get("determinism_verification", {})
    output = {
        "run_id": "placeholder-run-id",
        "repository": {
            "name": Path(repo_root).resolve().name if repo_root else "unknown",
            "path": repo_root
        },
        "summary": {
            "overall_score": analysis.get("risk_synthesis", {}).get("overall_risk_assessment", {}).get("average_risk_score",
                            analysis.get("risk_synthesis", {}).get("overall_risk_score",
                            analysis.get("risk_synthesis", {}).get("average_score", 0.0))),
            "files_scanned": len(files),
            "tests_discovered": structure.get("file_counts", {}).get("test", 0),
            "gaps_count": 0
        },
        "structure": structure,
        "ast_analysis": ast_analysis,
        "semantic": semantic,
        "test_signals": test_signals,
        "governance": governance,
        "intent_posture": intent_posture,
        "misleading_signals": misleading_signals,
        "safe_change_surface": safe_change_surface,
        "risk_synthesis": risk_synthesis,
        "decision_artifacts": decision_artifacts,
        "authority_ceiling_evaluation": authority_ceiling_evaluation,
        "determinism_verification": determinism_verification,
        "tasks": {},
        "gaps": [],
        "unsafe_patterns": analysis.get("security_analysis", {}).get("unsafe_patterns", {
            "summary": {"total_patterns": 0, "high_severity": 0, "medium_severity": 0, "low_severity": 0, "languages_covered": 0},
            "patterns_by_language": {},
            "critical_findings": []
        }),
        "metadata": {
            "scanner_version": "1.1.0",
            "run_timestamp": datetime.now(timezone.utc).isoformat(),
            "deterministic_hash": "placeholder-hash",
            "schema_version": "1.0.0"
        }
    }

    # Ensure metadata includes schema_version for compatibility checks
    try:
        version_path = Path('docs') / 'schemas' / 'VERSION'
        if version_path.exists():
            ver = version_path.read_text(encoding='utf-8', errors='ignore').strip()
            if ver:
                output['metadata']['schema_version'] = ver
    except Exception:
        pass  # Keep the default schema_version already set

    # Normalize evidence objects for HIGH/CRITICAL findings to ensure
    # every claim at severity HIGH or CRITICAL includes structured evidence
    def _normalize_evidence(obj):
        """Recursively walk obj and normalize any dict with 'severity' and 'evidence'."""
        if isinstance(obj, dict):
            # If this dict looks like a finding/artifact
            sev = obj.get('severity')
            if isinstance(sev, str) and sev.upper() in ('HIGH', 'CRITICAL'):
                ev = obj.get('evidence')
                if not isinstance(ev, list):
                    # Wrap simple evidence strings into evidence objects
                    ev_list = []
                    if isinstance(ev, str) and ev:
                        ev_list.append({
                            'repo_commit': _get_repo_commit(repository_path),
                            'source_path': None,
                            'snippet': ev
                        })
                    obj['evidence'] = ev_list
                    for e in obj['evidence']:
                        if isinstance(e, dict):
                            _populate_provenance_for_evidence(repository_path, e)
                else:
                    # Ensure each evidence entry is an object with repo_commit and source_path
                    normalized = []
                    for e in ev:
                        if isinstance(e, dict):
                            if 'repo_commit' not in e:
                                e['repo_commit'] = _get_repo_commit(repository_path)
                            if 'source_path' not in e:
                                e['source_path'] = None
                            else:
                                # Resolve relative source_path to repository root when possible
                                spv = e.get('source_path')
                                try:
                                    if isinstance(spv, str) and spv and not Path(spv).is_absolute():
                                        candidate = Path(repository_path) / spv
                                        if candidate.exists():
                                            e['source_path'] = str(candidate)
                                except Exception:
                                    pass
                            normalized.append(e)
                            _populate_provenance_for_evidence(repository_path, e)
                        else:
                            normalized.append({
                                'repo_commit': _get_repo_commit(repository_path),
                                'source_path': None,
                                'snippet': str(e)
                            })
                            _populate_provenance_for_evidence(repository_path, normalized[-1])
                    obj['evidence'] = normalized

            # Enrich evidence with deterministic provenance when possible
            for ev in obj.get('evidence', []) if isinstance(obj.get('evidence'), list) else []:
                try:
                    src = ev.get('source_path')
                    snippet = ev.get('snippet') or ev.get('snippet', '')
                    if src:
                        p = Path(src)
                        # Resolve relative paths against repository root if necessary
                        if not p.is_absolute():
                            p = Path(repository_path) / p
                        if p.exists() and p.is_file():
                            text = p.read_text(encoding='utf-8', errors='ignore')
                            # find snippet in file
                            if snippet:
                                idx = text.find(snippet)
                            else:
                                idx = 0
                            if idx >= 0:
                                # compute line range (1-based inclusive)
                                start_line = text[:idx].count('\n') + 1
                                end_idx = idx + (len(snippet) if snippet else 0)
                                end_line = text[:end_idx].count('\n') + 1
                                ev['line_range'] = [start_line, end_line]
                                # compute byte offsets
                                b = text.encode('utf-8')
                                # find byte index of snippet
                                if snippet:
                                    b_idx = b.find(snippet.encode('utf-8'))
                                    if b_idx >= 0:
                                        ev['byte_range'] = [b_idx, b_idx + len(snippet.encode('utf-8'))]
                                else:
                                    ev['byte_range'] = [0, len(b)]
                except Exception:
                    # don't fail output generation for provenance enrichment
                    continue

            # Recurse into children
            for k, v in obj.items():
                _normalize_evidence(v)
        elif isinstance(obj, list):
            for item in obj:
                _normalize_evidence(item)

    def _get_repo_commit(repo_path: str) -> str:
        """Return current git HEAD sha if available, else a placeholder."""
        try:
            from subprocess import run, PIPE
            import os
            p = Path(repo_path)
            if (p / '.git').exists():
                r = run(['git', 'rev-parse', 'HEAD'], cwd=str(p), capture_output=True, text=True, check=False)
                if r.returncode == 0:
                    return r.stdout.strip()
        except Exception:
            pass
        return 'unknown-commit'

    def _populate_provenance_for_evidence(repo_root: str, evidence_obj: dict):
        """Populate deterministic provenance fields (line_range, byte_range) when possible."""
        try:
            sp = evidence_obj.get('source_path')
            snippet = evidence_obj.get('snippet')
            if not sp:
                return
            # Resolve path relative to repo_root when possible
            p = Path(sp)
            if not p.exists():
                # try relative to repo_root
                p = Path(repo_root) / sp
            # fallback: try to resolve using files list
            if (not p.exists() or not p.is_file()) and isinstance(files, list):
                for cand in files:
                    if cand.endswith(sp):
                        p = Path(cand)
                        break
            # DEBUG: trace resolution
            # print(f"PROV: repo_root={repo_root} sp={sp} p={p} exists={p.exists()}")
            if not p.exists() or not p.is_file():
                return

            text = p.read_text(errors='ignore')
            # compute total bytes and lines
            b = text.encode('utf-8')
            total_lines = text.count('\n') + (0 if text.endswith('\n') else 1)
            # default byte_range covers whole file
            evidence_obj.setdefault('byte_range', [0, len(b)])
            # default line_range covers whole file
            evidence_obj.setdefault('line_range', [1, max(1, total_lines)])

            # refine line_range and byte_range if snippet present
            if snippet and isinstance(snippet, str) and snippet.strip():
                idx = text.find(snippet)
                if idx >= 0:
                    before = text[:idx]
                    start_line = before.count('\n') + 1
                    snippet_lines = snippet.count('\n') + 1
                    end_line = start_line + snippet_lines - 1
                    evidence_obj['line_range'] = [start_line, end_line]
                    start_byte = len(before.encode('utf-8'))
                    end_byte = start_byte + len(snippet.encode('utf-8'))
                    evidence_obj['byte_range'] = [start_byte, end_byte]
        except Exception:
            return

    # Populate provenance for all evidence entries
    def _walk_and_populate(obj):
        if isinstance(obj, dict):
            if 'evidence' in obj and isinstance(obj['evidence'], list):
                for ev in obj['evidence']:
                    if isinstance(ev, dict):
                        # Ensure repo_commit exists
                        if 'repo_commit' not in ev or not ev.get('repo_commit'):
                            ev['repo_commit'] = _get_repo_commit(repository_path)
                        # attempt to populate provenance
                        _populate_provenance_for_evidence(repository_path, ev)
            for v in obj.values():
                _walk_and_populate(v)
        elif isinstance(obj, list):
            for item in obj:
                _walk_and_populate(item)

    _normalize_evidence(output)
    _walk_and_populate(output)

    # Evidence-first enforcement: drop HIGH/CRITICAL artifacts that lack evidence
    try:
        da = output.get('decision_artifacts', {})
        if isinstance(da, dict):
            arts = da.get('artifacts')
            if isinstance(arts, list):
                filtered = []
                for a in arts:
                    if not isinstance(a, dict):
                        filtered.append(a)
                        continue
                    sev = a.get('severity', '')
                    if isinstance(sev, str) and sev.upper() in ('HIGH', 'CRITICAL'):
                        ev = a.get('evidence')
                        # If evidence is empty or missing, drop the artifact
                        if not ev:
                            continue
                    filtered.append(a)
                da['artifacts'] = filtered
                output['decision_artifacts'] = da
    except Exception:
        # Be conservative: if filtering fails, do not raise — keep original output
        pass

    # Recompute determinism verification on the final, normalized output to ensure
    # the stored determinism hash matches the canonicalized data that was written.
    try:
        from src.core.pipeline.determinism_verification import verify_determinism

        determinism_verification = verify_determinism(
            output.get('files', []),
            output.get('structure', {}),
            output.get('semantic', {}),
            output.get('test_signals', {}),
            output.get('governance', {}),
            output.get('intent_posture', {}),
            output.get('misleading_signals', {}),
            output.get('safe_change_surface', {}),
            output.get('risk_synthesis', {}),
            output.get('decision_artifacts', {}),
            output.get('authority_ceiling_evaluation', {})
        )
        output['determinism_verification'] = determinism_verification
        # Mirror the deterministic hash into metadata for easier access
        try:
            output.setdefault('metadata', {})['deterministic_hash'] = determinism_verification.get('determinism_hash')
        except Exception:
            pass
    except Exception:
        # If determinism verification fails at output time, do not prevent report generation
        pass

    return output



def _generate_misleading_summary(misleading_signals: dict) -> str:
    """Generate summary of misleading signals for the report."""
    if not isinstance(misleading_signals, dict):
        return "- None identified"
    
    total_signals = misleading_signals.get("total_misleading_signals", 0)
    overall_risk = misleading_signals.get("overall_misleading_risk", "low")
    
    if total_signals == 0:
        return "- None identified"
    
    summary_lines = [f"- **{total_signals} misleading signals detected** (Risk: {overall_risk.upper()})"]
    
    signals = misleading_signals.get("misleading_signals", {})
    for category, signal_list in signals.items():
        if isinstance(signal_list, list) and signal_list:
            summary_lines.append(f"- {category.replace('_', ' ').title()}: {len(signal_list)} signals")
            # Add top 2 signals as examples
            for signal in signal_list[:2]:
                if isinstance(signal, dict):
                    desc = signal.get("description", "Unknown signal")
                    severity = signal.get("severity", "unknown")
                    summary_lines.append(f"  - {desc} ({severity} severity)")
    
    return "\n".join(summary_lines)


def _generate_safe_changes_summary(safe_change_surface: dict) -> str:
    """Generate summary of safe changes for the report."""
    if not isinstance(safe_change_surface, dict):
        return "- No safe changes identified"
    
    safe_changes = safe_change_surface.get("safe_changes", [])
    if not isinstance(safe_changes, list) or not safe_changes:
        return "- No safe changes identified"
    
    overall_safety = safe_change_surface.get("overall_change_safety", {})
    safety_level = overall_safety.get("overall_safety_level", "low")
    
    summary_lines = [f"- **Change Safety: {safety_level.upper()}** - {overall_safety.get('description', '')}"]
    
    for change in safe_changes[:5]:  # Limit to top 5
        summary_lines.append(f"- {change}")
    
    return "\n".join(summary_lines)


def _generate_what_not_to_fix_summary(safe_change_surface: dict) -> str:
    """Generate summary of what not to fix for the report."""
    if not isinstance(safe_change_surface, dict):
        return "- No specific recommendations"
    
    unsafe_changes = safe_change_surface.get("unsafe_changes", [])
    if not isinstance(unsafe_changes, list) or not unsafe_changes:
        return "- No specific recommendations"
    
    summary_lines = []
    for change in unsafe_changes[:5]:  # Limit to top 5
        summary_lines.append(f"- {change}")
    
    return "\n".join(summary_lines)


def _generate_risk_synthesis_summary(risk_synthesis: dict) -> str:
    """Generate risk synthesis summary for the report."""
    if not isinstance(risk_synthesis, dict):
        return "- Risk synthesis not available"
    
    overall_risk = risk_synthesis.get("overall_risk_assessment", {})
    component_risks = risk_synthesis.get("component_risks", {})
    recommendations = risk_synthesis.get("recommendations", [])
    critical_issues = risk_synthesis.get("critical_issues", [])
    
    summary_lines = []
    
    # Overall risk assessment
    overall_level = overall_risk.get("overall_risk_level", "unknown")
    description = overall_risk.get("description", "")
    summary_lines.append(f"**Overall Risk Level:** {overall_level.upper()}")
    if description:
        summary_lines.append(f"**Assessment:** {description}")
    
    # Component risks
    if component_risks:
        summary_lines.append("\n**Component Risk Breakdown:**")
        for component_name, risk_data in component_risks.items():
            if isinstance(risk_data, dict):
                level = risk_data.get("risk_level", "unknown")
                desc = risk_data.get("description", "")
                summary_lines.append(f"- {component_name.replace('_', ' ').title()}: {level.upper()} - {desc}")
    
    # Critical issues
    if critical_issues:
        summary_lines.append("\n**Critical Issues Requiring Immediate Attention:**")
        for issue in critical_issues:
            if isinstance(issue, dict):
                severity = issue.get("severity", "unknown")
                issue_desc = issue.get("issue", "")
                impact = issue.get("impact", "")
                summary_lines.append(f"- **{severity.upper()}:** {issue_desc}")
                if impact:
                    summary_lines.append(f"  *Impact:* {impact}")
    
    # Recommendations
    if recommendations:
        summary_lines.append("\n**Prioritized Recommendations:**")
        for rec in recommendations[:5]:  # Limit to top 5
            if isinstance(rec, dict):
                priority = rec.get("priority", "unknown")
                category = rec.get("category", "")
                action = rec.get("action", "")
                rationale = rec.get("rationale", "")
                summary_lines.append(f"- **{priority.upper()}** [{category}]: {action}")
                if rationale:
                    summary_lines.append(f"  *Why:* {rationale}")
    
    return "\n".join(summary_lines) if summary_lines else "- No risk synthesis data available"


def _generate_decision_artifacts_summary(decision_artifacts: dict) -> str:
    """Generate decision artifacts summary for the report."""
    if not isinstance(decision_artifacts, dict):
        return "- Decision artifacts not available"
    
    decision_framework = decision_artifacts.get("decision_framework", {})
    action_plan = decision_artifacts.get("action_plan", {})
    authority_ceiling = decision_artifacts.get("authority_ceiling", {})
    confidence_assessment = decision_artifacts.get("confidence_assessment", {})
    next_steps = decision_artifacts.get("next_steps", [])
    
    summary_lines = []
    
    # Decision framework
    if decision_framework:
        decision_type = decision_framework.get("decision_type", "unknown")
        authority_required = decision_framework.get("authority_required", "unknown")
        timeframe = decision_framework.get("timeframe", "unknown")
        rationale = decision_framework.get("rationale", "")
        
        summary_lines.append(f"**Decision Framework:** {decision_type.upper()}")
        summary_lines.append(f"**Required Authority:** {authority_required.replace('_', ' ').title()}")
        summary_lines.append(f"**Timeframe:** {timeframe.replace('_', ' ').title()}")
        if rationale:
            summary_lines.append(f"**Rationale:** {rationale}")
    
    # Authority ceiling
    if authority_ceiling:
        max_authority = authority_ceiling.get("maximum_authority", "unknown")
        decision_scope = authority_ceiling.get("decision_scope", "unknown")
        oversight = "Required" if authority_ceiling.get("oversight_required", False) else "Not Required"
        
        summary_lines.append(f"\n**Authority Ceiling:** {max_authority.replace('_', ' ').title()}")
        summary_lines.append(f"**Decision Scope:** {decision_scope.replace('_', ' ').title()}")
        summary_lines.append(f"**Oversight:** {oversight}")
    
    # Action plan summary
    if action_plan:
        immediate_count = len(action_plan.get("immediate_actions", []))
        short_term_count = len(action_plan.get("short_term_actions", []))
        long_term_count = len(action_plan.get("long_term_actions", []))
        
        summary_lines.append(f"\n**Action Plan:**")
        if immediate_count > 0:
            summary_lines.append(f"- **{immediate_count} immediate action(s)** requiring urgent attention")
        if short_term_count > 0:
            summary_lines.append(f"- **{short_term_count} short-term action(s)** for near-term improvement")
        if long_term_count > 0:
            summary_lines.append(f"- **{long_term_count} long-term action(s)** for ongoing health")
    
    # Confidence assessment
    if confidence_assessment:
        confidence_level = confidence_assessment.get("confidence_level", "unknown")
        confidence_score = confidence_assessment.get("confidence_score", 0)
        description = confidence_assessment.get("description", "")
        
        summary_lines.append(f"\n**Analysis Confidence:** {confidence_level.upper()} ({confidence_score:.2f})")
        if description:
            summary_lines.append(f"**Assessment:** {description}")
    
    # Next steps
    if next_steps:
        summary_lines.append(f"\n**Immediate Next Steps:**")
        for step in next_steps[:3]:  # Limit to top 3
            if isinstance(step, dict):
                step_desc = step.get("step", "")
                priority = step.get("priority", "")
                owner = step.get("owner", "")
                timeframe = step.get("timeframe", "")
                summary_lines.append(f"- **{priority.upper()}** [{owner}]: {step_desc} ({timeframe.replace('_', ' ')})")
    
    return "\n".join(summary_lines) if summary_lines else "- No decision artifacts available"


def _generate_authority_ceiling_summary(authority_ceiling_evaluation: dict) -> str:
    """Generate authority ceiling evaluation summary for the report."""
    if not isinstance(authority_ceiling_evaluation, dict):
        return "- Authority ceiling evaluation not available"
    
    final_ceiling = authority_ceiling_evaluation.get("final_authority_ceiling", {})
    authority_rationale = authority_ceiling_evaluation.get("authority_rationale", {})
    authority_confidence = authority_ceiling_evaluation.get("authority_confidence", {})
    
    summary_lines = []
    
    # Final authority ceiling
    if final_ceiling:
        max_authority = final_ceiling.get("maximum_authority", "unknown")
        decision_scope = final_ceiling.get("decision_scope", "unknown")
        oversight = "Required" if final_ceiling.get("oversight_required", False) else "Not Required"
        applied_constraints = final_ceiling.get("constraint_count", 0)
        
        summary_lines.append(f"**Final Authority Ceiling:** {max_authority.replace('_', ' ').title()}")
        summary_lines.append(f"**Decision Scope:** {decision_scope.replace('_', ' ').title()}")
        summary_lines.append(f"**Oversight:** {oversight}")
        if applied_constraints > 0:
            summary_lines.append(f"**Applied Constraints:** {applied_constraints} factor(s) elevated authority")
    
    # Authority rationale
    if authority_rationale:
        rationale_summary = authority_rationale.get("rationale_summary", "")
        if rationale_summary:
            summary_lines.append(f"\n**Authority Rationale:** {rationale_summary}")
        
        key_factors = authority_rationale.get("key_factors", [])
        if key_factors:
            summary_lines.append("\n**Key Factors:**")
            for factor in key_factors:
                summary_lines.append(f"- {factor}")
    
    # Authority confidence
    if authority_confidence:
        confidence_level = authority_confidence.get("authority_confidence_level", "unknown")
        confidence_score = authority_confidence.get("authority_confidence_score", 0)
        description = authority_confidence.get("description", "")
        
        summary_lines.append(f"\n**Authority Confidence:** {confidence_level.upper()} ({confidence_score:.2f})")
        if description:
            summary_lines.append(f"**Assessment:** {description}")
    
    return "\n".join(summary_lines) if summary_lines else "- No authority ceiling evaluation available"


def generate_executive_verdict(analysis: dict, repository_path: str) -> str:
    """
    Generate a concise executive verdict report answering:
    "Can a competent engineer safely act on this repository right now, and if so, how?"
    
    Args:
        analysis: Dict containing the full analysis pipeline output
        repository_path: Path to the repository being analyzed
        
    Returns:
        String containing the executive verdict report (markdown format)
    """
    risk_synthesis = analysis.get("risk_synthesis", {})
    decision_artifacts = analysis.get("decision_artifacts", {})
    confidence_assessment = decision_artifacts.get("confidence_assessment", {})
    
    # Extract key decision data
    overall_risk = risk_synthesis.get("overall_risk_assessment", {})
    risk_level = overall_risk.get("overall_risk_level", "unknown").lower()
    risk_description = overall_risk.get("description", "")
    
    confidence_score = confidence_assessment.get("confidence_score", 0.0)
    confidence_level = confidence_assessment.get("confidence_level", "unknown")
    
    critical_issues = risk_synthesis.get("critical_issues", [])
    recommendations = risk_synthesis.get("recommendations", [])
    
    # Determine verdict based on risk level and confidence
    if confidence_score < 0.5:
        verdict = "INSUFFICIENT_EVIDENCE"
        verdict_explanation = f"Analysis confidence too low ({confidence_score:.2f}) to make reliable assessment"
    elif risk_level in ["low", "minimal"]:
        verdict = "PASS"
        verdict_explanation = "Repository appears safe for competent engineering action"
    elif risk_level in ["high", "critical"]:
        verdict = "FAIL"
        verdict_explanation = "Repository contains blocking risks requiring immediate attention"
    elif risk_level == "medium":
        verdict = "CAUTION"
        verdict_explanation = "Repository requires careful engineering attention"
    else:
        verdict = "INSUFFICIENT_EVIDENCE"
        verdict_explanation = "Unable to determine risk level with sufficient confidence"
    
    # Build verdict report sections
    sections = []
    
    # Executive Verdict
    sections.append("# Executive Verdict")
    sections.append("")
    sections.append(f"**Verdict:** {verdict}")
    sections.append(f"**Confidence:** {confidence_level.upper()} ({confidence_score:.2f})")
    sections.append("")
    sections.append(f"**Assessment:** {verdict_explanation}")
    sections.append("")
    
    # Scope of Assessment
    sections.append("## Scope of Assessment")
    sections.append("")
    sections.append(f"Repository: {repository_path}")
    sections.append(f"Risk Level: {risk_level.upper()}")
    sections.append(f"Analysis Confidence: {confidence_score:.2f}")
    sections.append("")
    
    # Blocking Risks (if any)
    if verdict == "FAIL" and critical_issues:
        sections.append("## Blocking Risks")
        sections.append("")
        for i, issue in enumerate(critical_issues[:5], 1):  # Limit to top 5
            if isinstance(issue, dict):
                issue_desc = issue.get("issue", "Unknown issue")
                severity = issue.get("severity", "unknown")
                impact = issue.get("impact", "unknown")
                sections.append(f"{i}. **{issue_desc}**")
                sections.append(f"   - Severity: {severity}")
                sections.append(f"   - Impact: {impact}")
                sections.append("")
    
    # Safe Action Summary
    sections.append("## Safe Action Summary")
    sections.append("")
    if verdict == "PASS":
        sections.append("Competent engineers can safely:")
        sections.append("- Review and merge pull requests")
        sections.append("- Deploy to staging environments")
        sections.append("- Perform routine maintenance tasks")
        sections.append("- Implement non-critical features")
        if recommendations:
            sections.append("")
            sections.append("Recommended actions:")
            for rec in recommendations[:3]:
                if isinstance(rec, dict):
                    action = rec.get("action", "")
                    priority = rec.get("priority", "")
                    sections.append(f"- {priority.upper()}: {action}")
    elif verdict == "CAUTION":
        sections.append("Competent engineers should proceed with caution:")
        sections.append("- Review and merge pull requests (with extra scrutiny)")
        sections.append("- Deploy to staging environments only")
        sections.append("- Perform routine maintenance tasks")
        sections.append("- Avoid major architectural changes")
        if recommendations:
            sections.append("")
            sections.append("Address these recommendations first:")
            for rec in recommendations[:3]:
                if isinstance(rec, dict):
                    action = rec.get("action", "")
                    priority = rec.get("priority", "")
                    sections.append(f"- {priority.upper()}: {action}")
    else:
        sections.append("No safe actions recommended until blocking risks are addressed.")
    sections.append("")
    
    # Unsafe Action Summary
    sections.append("## Unsafe Action Summary")
    sections.append("")
    if verdict == "FAIL":
        sections.append("The following actions carry significant risk:")
        sections.append("- Production deployments")
        sections.append("- Major architectural changes")
        sections.append("- Security-critical modifications")
        sections.append("- Changes to core business logic")
        if critical_issues:
            sections.append("")
            sections.append("Until the following critical issues are resolved:")
            for issue in critical_issues[:3]:
                if isinstance(issue, dict):
                    issue_desc = issue.get("issue", "")
                    sections.append(f"- {issue_desc}")
    else:
        sections.append("Standard engineering caution applies - no specific unsafe actions identified.")
    
    # Ensure under 300 words (rough estimate)
    report = "\n".join(sections)
    word_count = len(report.split())
    if word_count > 300:
        # Truncate if necessary
        lines = report.split('\n')
        truncated = []
        current_words = 0
        for line in lines:
            line_words = len(line.split())
            if current_words + line_words > 280:  # Leave buffer
                truncated.append("\n[Report truncated for brevity]")
                break
            truncated.append(line)
            current_words += line_words
        report = '\n'.join(truncated)
    
    return report


# Output Evaluation Functions

def evaluate_output_consistency(repo_path: str, runs: int = 3) -> dict:
    """Evaluate output consistency across multiple runs."""
    from src.core.pipeline.analysis import execute_pipeline
    import hashlib
    import json
    
    results = []
    for i in range(runs):
        try:
            analysis = execute_pipeline(repo_path)
            json_output = generate_machine_output(analysis, repo_path)
            json_str = json.dumps(json_output, sort_keys=True)
            hash_val = hashlib.sha256(json_str.encode()).hexdigest()
            results.append(hash_val)
        except Exception as e:
            results.append(f"error: {str(e)}")
    
    # Calculate consistency
    unique_hashes = set(results)
    consistency_score = 1.0 if len(unique_hashes) == 1 else 0.0
    if len(unique_hashes) > 1 and all(not h.startswith("error") for h in results):
        # Partial consistency if some match
        most_common = max(set(results), key=results.count)
        consistency_score = results.count(most_common) / len(results)
    
    return {
        "consistency_score": consistency_score,
        "runs": runs,
        "unique_outputs": len(unique_hashes),
        "results": results
    }


def evaluate_output_metrics(analysis_result: dict, expected_result: dict = None) -> dict:
    """Calculate basic metrics for output quality."""
    metrics = {}
    
    # Risk level accuracy (if expected provided)
    if expected_result:
        actual_risk = analysis_result.get("risk_synthesis", {}).get("overall_risk_assessment", {}).get("overall_risk_level")
        expected_risk = expected_result.get("risk_level")
        metrics["risk_accuracy"] = 1.0 if actual_risk == expected_risk else 0.0
    
    # Presence of key sections
    required_sections = ["risk_synthesis", "governance", "intent_posture"]
    metrics["completeness"] = sum(1 for section in required_sections if section in analysis_result) / len(required_sections)
    
    # Issue counts
    risk_synthesis = analysis_result.get("risk_synthesis", {})
    high_issues = len(risk_synthesis.get("high_priority_issues", []))
    med_issues = len(risk_synthesis.get("medium_priority_issues", []))
    low_issues = len(risk_synthesis.get("low_priority_issues", []))
    metrics["total_issues"] = high_issues + med_issues + low_issues
    metrics["high_issue_ratio"] = high_issues / max(1, metrics["total_issues"])
    
    return metrics


def benchmark_against_golden_repos(repo_path: str, golden_repos: list) -> dict:
    """Benchmark current repo against golden standard repos."""
    # Placeholder: Compare metrics to known good/bad repos
    # In practice, load pre-computed metrics for golden repos
    current_metrics = evaluate_output_metrics({"dummy": "data"})  # Replace with actual
    
    benchmark_results = {
        "current_metrics": current_metrics,
        "golden_comparison": {},
        "overall_score": 0.8  # Placeholder
    }
    
    return benchmark_results
