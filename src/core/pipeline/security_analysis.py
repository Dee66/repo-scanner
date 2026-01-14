"""Security vulnerability analysis pipeline stage."""

import logging
from typing import Dict, List, Any
from pathlib import Path

from .security_analysis import SecurityAnalyzer

logger = logging.getLogger(__name__)


def analyze_security_vulnerabilities(file_list: List[str], semantic_analysis: Dict[str, Any]) -> Dict[str, Any]:
    """
    Analyze security vulnerabilities across all files using the SecurityAnalyzer.

    This function uses the SecurityAnalyzer to detect vulnerabilities and
    synthesizes them into a comprehensive security analysis report.
    """
    logger.info("Starting security vulnerability analysis")

    # Use the SecurityAnalyzer's analyze_security_vulnerabilities method
    return analyzer.analyze_security_vulnerabilities(file_list, semantic_analysis)


def _get_language_from_path(file_path: str) -> str:
    """Determine language from file extension."""
    path = Path(file_path)
    ext = path.suffix.lower()

    language_map = {
        '.py': 'python',
        '.js': 'javascript',
        '.java': 'java',
        '.rs': 'rust',
        '.php': 'php',
        '.cpp': 'cpp',
        '.c': 'c',
        '.go': 'go',
        '.rb': 'ruby',
        '.cs': 'csharp'
    }

    return language_map.get(ext, 'unknown')

    # Limit critical findings to top 50 most severe
    unsafe_patterns["critical_findings"] = unsafe_patterns["critical_findings"][:50]

    logger.info("Security analysis completed: %d patterns found across %d languages", 
                unsafe_patterns['summary']['total_patterns'], len(languages_processed))

    return {
        "unsafe_patterns": unsafe_patterns,
        "security_posture": _assess_security_posture(unsafe_patterns),
        "recommendations": _generate_security_recommendations(unsafe_patterns)
    }


def _extract_evidence_snippet(file_path: str, pattern: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Extract evidence snippet for a security finding with provenance information."""
    evidence = []
    try:
        line_number = pattern.get("line", 0)
        if line_number > 0:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                lines = f.readlines()
            
            # Get context around the finding (3 lines before and after)
            start_line = max(0, line_number - 4)  # 0-based indexing
            end_line = min(len(lines), line_number + 3)
            
            snippet_lines = []
            byte_start = 0
            byte_end = 0
            
            for i in range(start_line, end_line):
                line_content = lines[i].rstrip('\n\r')
                if i == line_number - 1:  # The finding line (convert to 0-based)
                    # Calculate byte range for the finding line
                    byte_start = sum(len(lines[j].encode('utf-8')) for j in range(start_line, i))
                    byte_end = byte_start + len(line_content.encode('utf-8'))
                
                snippet_lines.append({
                    "line_number": i + 1,
                    "content": line_content,
                    "is_finding_line": (i + 1) == line_number
                })
            
            # Get repository commit SHA (if available)
            repo_commit = _get_repository_commit_sha()
            
            evidence.append({
                "type": "code_snippet",
                "file_path": file_path,
                "line_range": f"{start_line + 1}-{end_line}",
                "byte_range": f"{byte_start}-{byte_end}" if byte_start < byte_end else None,
                "repo_commit_sha": repo_commit,
                "evidence_snippet": snippet_lines,
                "description": f"Code snippet showing {pattern.get('type', 'security issue')} at line {line_number}"
            })
    except Exception:
        # If we can't read the file, just return minimal evidence
        evidence.append({
            "type": "metadata",
            "file_path": file_path,
            "line_range": str(pattern.get("line", 0)),
            "repo_commit_sha": _get_repository_commit_sha(),
            "description": "Security finding detected but unable to extract code snippet"
        })
    
    return evidence


def _get_repository_commit_sha() -> str:
    """Get the current repository commit SHA."""
    try:
        import subprocess
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            capture_output=True,
            text=True,
            timeout=5
        )
        if result.returncode == 0:
            return result.stdout.strip()
    except Exception:
        pass
    return "unknown"


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
            eval_count = sum(1 for p in lang_patterns if (p.get("pattern") or p.get("type")) == "dynamic_code_execution")
            if eval_count > 0:
                recommendations.append({
                    "priority": "high",
                    "action": f"Replace eval() usage in JavaScript files ({eval_count} instances)",
                    "rationale": "eval() poses significant security risks in JavaScript",
                    "effort": "medium"
                })

        elif language.lower() == "python":
            pickle_count = sum(1 for p in lang_patterns if (p.get("pattern") or p.get("type")) == "deserialization_vulnerability")
            if pickle_count > 0:
                recommendations.append({
                    "priority": "high",
                    "action": f"Replace pickle usage with safer alternatives ({pickle_count} instances)",
                    "rationale": "Pickle deserialization can lead to remote code execution",
                    "effort": "medium"
                })

        elif language.lower() == "php":
            sql_injection_count = sum(1 for p in lang_patterns if (p.get("pattern") or p.get("type")) == "sql_injection")
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