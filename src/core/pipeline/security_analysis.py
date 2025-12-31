"""Security vulnerability analysis pipeline stage."""

import logging
from typing import Dict, List, Any
from pathlib import Path

from ..adapters.language_adapter_manager import LanguageAdapterManager

logger = logging.getLogger(__name__)


def analyze_security_vulnerabilities(file_list: List[str], semantic_analysis: Dict[str, Any]) -> Dict[str, Any]:
    """
    Analyze security vulnerabilities across all files using language-specific adapters.

    This function collects unsafe patterns detected by language adapters and
    synthesizes them into a comprehensive security analysis report.
    """
    logger.info("Starting security vulnerability analysis")

    # Initialize adapter manager
    adapter_manager = LanguageAdapterManager()

    # Collect unsafe patterns from all files
    unsafe_patterns = {
        "summary": {
            "total_patterns": 0,
            "high_severity": 0,
            "medium_severity": 0,
            "low_severity": 0,
            "languages_covered": 0
        },
        "patterns_by_language": {},
        "critical_findings": []
    }

    languages_processed = set()

    # Process each file
    for file_path in file_list:
        try:
            # Get appropriate adapter for this file
            adapter = adapter_manager.get_adapter_for_file(file_path)

            if adapter:
                # Extract AST which includes unsafe patterns
                ast_result = adapter.extract_ast(file_path)

                # Check if unsafe patterns were detected
                file_unsafe_patterns = ast_result.get("unsafe_patterns", [])

                if file_unsafe_patterns:
                    # Get language name
                    language = adapter.language_name
                    languages_processed.add(language)

                    # Initialize language entry if not exists
                    if language not in unsafe_patterns["patterns_by_language"]:
                        unsafe_patterns["patterns_by_language"][language] = []

                    # Add file patterns
                    unsafe_patterns["patterns_by_language"][language].append({
                        "file_path": file_path,
                        "language": language,
                        "patterns": file_unsafe_patterns
                    })

                    # Update summary counts
                    for pattern in file_unsafe_patterns:
                        severity = pattern.get("severity", "low")
                        unsafe_patterns["summary"]["total_patterns"] += 1

                        if severity == "high":
                            unsafe_patterns["summary"]["high_severity"] += 1
                            # Add to critical findings
                            unsafe_patterns["critical_findings"].append({
                                "file_path": file_path,
                                "pattern_type": pattern.get("type", "Unknown"),
                                "severity": severity,
                                "description": pattern.get("description", "No description"),
                                "line": pattern.get("line", 0)
                            })
                        elif severity == "medium":
                            unsafe_patterns["summary"]["medium_severity"] += 1
                        elif severity == "low":
                            unsafe_patterns["summary"]["low_severity"] += 1

        except Exception as e:
            logger.warning(f"Failed to analyze security patterns in {file_path}: {str(e)}")
            continue

    # Update languages covered count
    unsafe_patterns["summary"]["languages_covered"] = len(languages_processed)

    # Sort critical findings by severity (high first) and then by file path
    unsafe_patterns["critical_findings"].sort(key=lambda x: (
        {"high": 0, "medium": 1, "low": 2}.get(x["severity"], 3),
        x["file_path"]
    ))

    # Limit critical findings to top 50 most severe
    unsafe_patterns["critical_findings"] = unsafe_patterns["critical_findings"][:50]

    logger.info(f"Security analysis completed: {unsafe_patterns['summary']['total_patterns']} patterns found across {len(languages_processed)} languages")

    return {
        "unsafe_patterns": unsafe_patterns,
        "security_posture": _assess_security_posture(unsafe_patterns),
        "recommendations": _generate_security_recommendations(unsafe_patterns)
    }


def _assess_security_posture(unsafe_patterns: Dict[str, Any]) -> Dict[str, Any]:
    """Assess overall security posture based on findings."""
    summary = unsafe_patterns.get("summary", {})

    high_severity = summary.get("high_severity", 0)
    medium_severity = summary.get("medium_severity", 0)
    total_patterns = summary.get("total_patterns", 0)

    # Determine risk level
    if high_severity > 0:
        risk_level = "critical"
        risk_score = 9.0
        description = "Critical security vulnerabilities require immediate attention"
    elif medium_severity > 10:
        risk_level = "high"
        risk_score = 7.0
        description = "Multiple medium-severity issues need prompt resolution"
    elif total_patterns > 20:
        risk_level = "medium"
        risk_score = 5.0
        description = "Several security considerations identified"
    elif total_patterns > 0:
        risk_level = "low"
        risk_score = 2.0
        description = "Minor security improvements recommended"
    else:
        risk_level = "excellent"
        risk_score = 0.0
        description = "No security vulnerabilities detected"

    return {
        "risk_level": risk_level,
        "risk_score": risk_score,  # 0.0 = excellent, 10.0 = critical
        "description": description,
        "high_priority_actions": high_severity,
        "total_findings": total_patterns
    }


def _generate_security_recommendations(unsafe_patterns: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Generate actionable security recommendations."""
    recommendations = []
    summary = unsafe_patterns.get("summary", {})

    high_severity = summary.get("high_severity", 0)
    medium_severity = summary.get("medium_severity", 0)

    if high_severity > 0:
        recommendations.append({
            "priority": "critical",
            "action": "Address all high-severity vulnerabilities immediately",
            "rationale": f"{high_severity} critical security issues require immediate remediation",
            "effort": "high"
        })

    if medium_severity > 5:
        recommendations.append({
            "priority": "high",
            "action": "Review and fix medium-severity security issues",
            "rationale": f"{medium_severity} medium-severity issues should be addressed promptly",
            "effort": "medium"
        })

    # Language-specific recommendations
    patterns_by_language = unsafe_patterns.get("patterns_by_language", {})
    for language, files in patterns_by_language.items():
        lang_patterns = []
        for file_data in files:
            lang_patterns.extend(file_data.get("patterns", []))

        # Check for common patterns by language
        if language.lower() == "javascript":
            eval_count = sum(1 for p in lang_patterns if p.get("type") == "dynamic_code_execution")
            if eval_count > 0:
                recommendations.append({
                    "priority": "high",
                    "action": f"Replace eval() usage in JavaScript files ({eval_count} instances)",
                    "rationale": "eval() poses significant security risks in JavaScript",
                    "effort": "medium"
                })

        elif language.lower() == "python":
            pickle_count = sum(1 for p in lang_patterns if p.get("type") == "deserialization_vulnerability")
            if pickle_count > 0:
                recommendations.append({
                    "priority": "high",
                    "action": f"Replace pickle usage with safer alternatives ({pickle_count} instances)",
                    "rationale": "Pickle deserialization can lead to remote code execution",
                    "effort": "medium"
                })

        elif language.lower() == "php":
            sql_injection_count = sum(1 for p in lang_patterns if p.get("type") == "sql_injection")
            if sql_injection_count > 0:
                recommendations.append({
                    "priority": "high",
                    "action": f"Use parameterized queries instead of string concatenation ({sql_injection_count} instances)",
                    "rationale": "SQL injection vulnerabilities in PHP code",
                    "effort": "medium"
                })

    # General recommendations
    recommendations.extend([
        {
            "priority": "medium",
            "action": "Implement input validation for all user-controlled data",
            "rationale": "Prevents injection attacks and other input-based vulnerabilities",
            "effort": "medium"
        },
        {
            "priority": "medium",
            "action": "Add security-focused static analysis to CI/CD pipeline",
            "rationale": "Catches security issues early in development",
            "effort": "low"
        },
        {
            "priority": "low",
            "action": "Conduct regular security code reviews",
            "rationale": "Human review catches issues automated tools might miss",
            "effort": "medium"
        }
    ])

    return recommendations