"""Primary report generator for human-readable analysis output."""

import logging
from typing import Dict, List, Any, Optional
from pathlib import Path
from datetime import datetime
import json

logger = logging.getLogger(__name__)


class PrimaryReportGenerator:
    """Generates human-readable primary reports in markdown format."""

    def __init__(self):
        self.quality_grades = {
            'A': {'label': 'Exceptional', 'description': 'Surpasses enterprise standards'},
            'B': {'label': 'Strong', 'description': 'Exceeds typical expectations'},
            'C': {'label': 'Adequate', 'description': 'Meets basic requirements'},
            'D': {'label': 'Concerning', 'description': 'Requires attention'},
            'F': {'label': 'Critical', 'description': 'Immediate action required'}
        }

        self.severity_levels = {
            'critical': '🚨 CRITICAL',
            'high': '⚠️ HIGH',
            'medium': 'ℹ️ MEDIUM',
            'low': '✅ LOW',
            'info': 'ℹ️ INFO'
        }

    def generate_primary_report(self, analysis_results: Dict[str, Any],
                              repository_path: str) -> str:
        """
        Generate comprehensive primary report in markdown format.

        Args:
            analysis_results: Complete analysis pipeline results
            repository_path: Path to the analyzed repository

        Returns:
            Markdown formatted primary report
        """
        try:
            repo_name = Path(repository_path).name
            report_date = datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')

            # Build report sections
            header = self._generate_header(repo_name, report_date)
            executive_summary = self._generate_executive_summary(analysis_results)
            key_findings = self._generate_key_findings(analysis_results)
            detailed_assessments = self._generate_detailed_assessments(analysis_results)
            recommendations = self._generate_recommendations(analysis_results)
            technical_details = self._generate_technical_details(analysis_results)
            footer = self._generate_footer()

            # Combine all sections
            report = '\n\n'.join([
                header,
                executive_summary,
                key_findings,
                detailed_assessments,
                recommendations,
                technical_details,
                footer
            ])

            return report

        except Exception as e:
            logger.error(f"Error generating primary report: {e}")
            return self._generate_error_report(str(e))

    def _generate_header(self, repo_name: str, report_date: str) -> str:
        """Generate report header."""
        return f"""# Repository Intelligence Analysis Report

**Repository:** {repo_name}  
**Analysis Date:** {report_date}  
**Report Type:** Comprehensive Security & Quality Assessment

---
"""

    def _generate_executive_summary(self, results: Dict[str, Any]) -> str:
        """Generate executive summary section."""
        # Calculate overall quality grade
        overall_grade = self._calculate_overall_grade(results)

        summary_text = self._generate_summary_text(results, overall_grade)

        return f"""## Executive Summary

### Overall Assessment: {overall_grade['grade']} - {overall_grade['label']}
{overall_grade['description']}

{summary_text}

**Analysis Scope:** Complete repository assessment including security vulnerabilities, code quality, documentation accuracy, architectural patterns, and governance signals.
"""

    def _generate_key_findings(self, results: Dict[str, Any]) -> str:
        """Generate key findings section."""
        findings = []

        # Security findings
        security_findings = self._extract_security_findings(results)
        if security_findings:
            findings.extend(security_findings)

        # Quality findings
        quality_findings = self._extract_quality_findings(results)
        if quality_findings:
            findings.extend(quality_findings)

        # Documentation findings
        doc_findings = self._extract_documentation_findings(results)
        if doc_findings:
            findings.extend(doc_findings)

        if not findings:
            findings.append("✅ No critical issues identified in analysis scope.")

        findings_text = '\n'.join(f"- {finding}" for finding in findings[:10])  # Limit to top 10

        return f"""## Key Findings

{findings_text}
"""

    def _generate_detailed_assessments(self, results: Dict[str, Any]) -> str:
        """Generate detailed assessments section."""
        assessments = []

        # Security assessment
        security_assessment = self._generate_security_assessment(results)
        if security_assessment:
            assessments.append(security_assessment)

        # Code quality assessment
        quality_assessment = self._generate_quality_assessment(results)
        if quality_assessment:
            assessments.append(quality_assessment)

        # Documentation assessment
        doc_assessment = self._generate_documentation_assessment(results)
        if doc_assessment:
            assessments.append(doc_assessment)

        # Architecture assessment
        arch_assessment = self._generate_architecture_assessment(results)
        if arch_assessment:
            assessments.append(arch_assessment)

        return '\n\n'.join(assessments)

    def _generate_recommendations(self, results: Dict[str, Any]) -> str:
        """Generate recommendations section."""
        recommendations = []

        # Priority recommendations
        priority_recs = self._extract_priority_recommendations(results)
        if priority_recs:
            recommendations.extend(priority_recs)

        # General recommendations
        general_recs = self._generate_general_recommendations(results)
        recommendations.extend(general_recs)

        if not recommendations:
            recommendations.append("✅ Repository analysis complete. No immediate actions required.")

        recs_text = '\n'.join(f"**{rec['priority'].title()} Priority:** {rec['action']}" for rec in recommendations)

        return f"""## Recommendations

{recs_text}
"""

    def _generate_technical_details(self, results: Dict[str, Any]) -> str:
        """Generate technical details section."""
        details = []

        # Analysis metrics
        metrics = self._extract_analysis_metrics(results)
        if metrics:
            details.append("### Analysis Metrics")
            details.append('\n'.join(f"- {k}: {v}" for k, v in metrics.items()))

        # File statistics
        file_stats = self._extract_file_statistics(results)
        if file_stats:
            details.append("\n### Repository Statistics")
            details.append('\n'.join(f"- {k}: {v}" for k, v in file_stats.items()))

        return '\n\n'.join(details) if details else ""

    def _generate_footer(self) -> str:
        """Generate report footer."""
        return """---

**Report Generation:** Automated Repository Intelligence Scanner  
**Analysis Framework:** Deterministic, evidence-based assessment  
**Contact:** Repository maintainers or security team for questions

---
"""

    def _calculate_overall_grade(self, results: Dict[str, Any]) -> Dict[str, str]:
        """Calculate overall quality grade."""
        # Extract key metrics
        security_score = self._extract_security_score(results)
        quality_score = self._extract_quality_score(results)
        doc_score = self._extract_documentation_score(results)

        # Calculate composite score (0-1 scale)
        weights = {'security': 0.4, 'quality': 0.4, 'documentation': 0.2}
        composite_score = (
            security_score * weights['security'] +
            quality_score * weights['quality'] +
            doc_score * weights['documentation']
        )

        # Convert to grade
        if composite_score >= 0.9:
            grade = 'A'
        elif composite_score >= 0.8:
            grade = 'B'
        elif composite_score >= 0.6:
            grade = 'C'
        elif composite_score >= 0.4:
            grade = 'D'
        else:
            grade = 'F'

        return {
            'grade': grade,
            'label': self.quality_grades[grade]['label'],
            'description': self.quality_grades[grade]['description']
        }

    def _generate_summary_text(self, results: Dict[str, Any], grade: Dict[str, str]) -> str:
        """Generate summary text based on results."""
        summary_points = []

        # Security summary
        security_summary = self._generate_security_summary(results)
        if security_summary:
            summary_points.append(security_summary)

        # Quality summary
        quality_summary = self._generate_quality_summary(results)
        if quality_summary:
            summary_points.append(quality_summary)

        # Documentation summary
        doc_summary = self._generate_documentation_summary(results)
        if doc_summary:
            summary_points.append(doc_summary)

        if not summary_points:
            summary_points.append("Repository demonstrates solid foundational practices with room for enhancement.")

        return '\n\n'.join(f"• {point}" for point in summary_points)

    def _extract_security_findings(self, results: Dict[str, Any]) -> List[str]:
        """Extract critical security findings."""
        findings = []

        # Check for security analysis results
        security = results.get('security_analysis', {})
        if security and 'findings' in security:
            for finding in security['findings'][:5]:  # Top 5
                severity = finding.get('severity', 'medium')
                title = finding.get('title', 'Security issue')
                findings.append(f"{self.severity_levels.get(severity, 'ℹ️')}: {title}")

        return findings

    def _extract_quality_findings(self, results: Dict[str, Any]) -> List[str]:
        """Extract code quality findings."""
        findings = []

        # Check for code quality issues
        advanced_code = results.get('advanced_code_analysis', {})
        if advanced_code and 'findings' in advanced_code:
            for finding in advanced_code['findings'][:3]:  # Top 3
                severity = finding.get('severity', 'medium')
                title = finding.get('title', 'Code quality issue')
                findings.append(f"{self.severity_levels.get(severity, 'ℹ️')}: {title}")

        return findings

    def _extract_documentation_findings(self, results: Dict[str, Any]) -> List[str]:
        """Extract documentation findings."""
        findings = []

        # Check documentation accuracy report
        doc_report = results.get('documentation_accuracy_report', {})
        if doc_report:
            exec_summary = doc_report.get('executive_summary', {})
            critical_findings = exec_summary.get('critical_findings', [])
            for finding in critical_findings:
                findings.append(f"📝 Documentation: {finding}")

        return findings

    def _generate_security_assessment(self, results: Dict[str, Any]) -> str:
        """Generate security assessment section."""
        security = results.get('security_analysis', {})
        if not security:
            return ""

        finding_count = len(security.get('findings', []))
        critical_count = sum(1 for f in security.get('findings', [])
                           if f.get('severity') == 'critical')

        assessment = f"""### Security Assessment

**Findings:** {finding_count} total ({critical_count} critical)
**Risk Level:** {'High' if critical_count > 0 else 'Medium' if finding_count > 5 else 'Low'}

Security posture analysis identified {finding_count} potential vulnerabilities and security concerns."""

        if critical_count > 0:
            assessment += f" {critical_count} critical issues require immediate attention."

        return assessment

    def _generate_quality_assessment(self, results: Dict[str, Any]) -> str:
        """Generate code quality assessment section."""
        advanced_code = results.get('advanced_code_analysis', {})
        if not advanced_code:
            return ""

        finding_count = len(advanced_code.get('findings', []))

        assessment = f"""### Code Quality Assessment

**Analysis:** Comprehensive code quality evaluation completed
**Issues Identified:** {finding_count} areas for improvement

Code structure and quality analysis reveals {'excellent maintainability' if finding_count == 0 else f'{finding_count} opportunities for enhancement'}."""

        return assessment

    def _generate_documentation_assessment(self, results: Dict[str, Any]) -> str:
        """Generate documentation assessment section."""
        doc_report = results.get('documentation_accuracy_report', {})
        if not doc_report:
            return ""

        exec_summary = doc_report.get('executive_summary', {})
        accuracy_score = exec_summary.get('key_metrics', {}).get('accuracy_score', 0.0)
        gaps = exec_summary.get('key_metrics', {}).get('total_gaps', 0)

        assessment = f"""### Documentation Assessment

**Accuracy Score:** {accuracy_score:.1%}
**Gaps Identified:** {gaps}

Documentation quality analysis shows {'excellent alignment' if accuracy_score > 0.8 else 'moderate alignment' if accuracy_score > 0.6 else 'significant gaps requiring attention'} between documented features and implementation."""

        return assessment

    def _generate_architecture_assessment(self, results: Dict[str, Any]) -> str:
        """Generate architecture assessment section."""
        structure = results.get('structure', {})
        semantic = results.get('semantic', {})

        assessment = """### Architecture Assessment

**Analysis:** Repository structure and architectural patterns evaluated
**Languages:** Multiple technology stacks detected and analyzed

Architectural assessment indicates {'well-structured codebase' if structure else 'basic repository structure'} with {'comprehensive semantic analysis' if semantic else 'limited semantic coverage'}."""

        return assessment

    def _extract_priority_recommendations(self, results: Dict[str, Any]) -> List[Dict[str, str]]:
        """Extract priority recommendations from analysis."""
        recommendations = []

        # Security recommendations
        security = results.get('security_analysis', {})
        if security and security.get('findings'):
            critical_count = sum(1 for f in security['findings'] if f.get('severity') == 'critical')
            if critical_count > 0:
                recommendations.append({
                    'priority': 'critical',
                    'action': f'Address {critical_count} critical security vulnerabilities immediately'
                })

        # Documentation recommendations
        doc_report = results.get('documentation_accuracy_report', {})
        if doc_report:
            exec_summary = doc_report.get('executive_summary', {})
            gaps = exec_summary.get('key_metrics', {}).get('total_gaps', 0)
            if gaps > 0:
                recommendations.append({
                    'priority': 'high',
                    'action': f'Resolve {gaps} documentation-to-implementation gaps'
                })

        return recommendations

    def _generate_general_recommendations(self, results: Dict[str, Any]) -> List[Dict[str, str]]:
        """Generate general recommendations."""
        recommendations = []

        # Code quality recommendations
        advanced_code = results.get('advanced_code_analysis', {})
        if advanced_code and advanced_code.get('findings'):
            recommendations.append({
                'priority': 'medium',
                'action': 'Review and address code quality findings for improved maintainability'
            })

        # Testing recommendations
        test_signals = results.get('test_signal_analysis', {})
        if test_signals:
            test_coverage = test_signals.get('test_coverage_score', 0.0)
            if test_coverage < 0.8:
                recommendations.append({
                    'priority': 'medium',
                    'action': 'Enhance test coverage to meet enterprise standards (target: 80%+)'
                })

        # Always include maintenance recommendation
        recommendations.append({
            'priority': 'low',
            'action': 'Schedule regular repository health assessments (quarterly recommended)'
        })

        return recommendations

    def _extract_analysis_metrics(self, results: Dict[str, Any]) -> Dict[str, Any]:
        """Extract key analysis metrics."""
        metrics = {}

        # File count
        files = results.get('files', [])
        metrics['Files Analyzed'] = len(files)

        # Analysis duration (if available)
        if 'performance' in results:
            perf = results['performance']
            if 'execution_time_seconds' in perf:
                metrics['Analysis Duration'] = '.1f'

        # Languages detected
        semantic = results.get('semantic', {})
        if 'languages' in semantic:
            metrics['Languages Detected'] = len(semantic['languages'])

        return metrics

    def _extract_file_statistics(self, results: Dict[str, Any]) -> Dict[str, Any]:
        """Extract file statistics."""
        stats = {}

        structure = results.get('structure', {})
        if 'file_types' in structure:
            file_types = structure['file_types']
            stats['Code Files'] = sum(file_types.values())

        return stats

    def _extract_security_score(self, results: Dict[str, Any]) -> float:
        """Extract security score (0-1 scale)."""
        security = results.get('security_analysis', {})
        if not security:
            return 0.5  # Neutral score

        findings = security.get('findings', [])
        critical_count = sum(1 for f in findings if f.get('severity') == 'critical')
        high_count = sum(1 for f in findings if f.get('severity') == 'high')

        # Simple scoring: fewer critical/high findings = higher score
        penalty = min((critical_count * 0.3 + high_count * 0.1), 1.0)
        return max(0.0, 1.0 - penalty)

    def _extract_quality_score(self, results: Dict[str, Any]) -> float:
        """Extract code quality score (0-1 scale)."""
        advanced_code = results.get('advanced_code_analysis', {})
        if not advanced_code:
            return 0.5

        findings = advanced_code.get('findings', [])
        issue_count = len(findings)

        # Simple scoring: fewer issues = higher score
        penalty = min(issue_count * 0.05, 1.0)
        return max(0.0, 1.0 - penalty)

    def _extract_documentation_score(self, results: Dict[str, Any]) -> float:
        """Extract documentation score (0-1 scale)."""
        doc_report = results.get('documentation_accuracy_report', {})
        if not doc_report:
            return 0.5

        exec_summary = doc_report.get('executive_summary', {})
        accuracy_score = exec_summary.get('key_metrics', {}).get('accuracy_score', 0.0)

        return accuracy_score

    def _generate_security_summary(self, results: Dict[str, Any]) -> str:
        """Generate security summary point."""
        score = self._extract_security_score(results)
        if score >= 0.9:
            return "Security posture demonstrates enterprise-grade protection measures"
        elif score >= 0.7:
            return "Security implementation meets industry standards with minor enhancements needed"
        else:
            return "Security vulnerabilities identified requiring immediate remediation"

    def _generate_quality_summary(self, results: Dict[str, Any]) -> str:
        """Generate quality summary point."""
        score = self._extract_quality_score(results)
        if score >= 0.9:
            return "Code quality exemplifies best practices and maintainable architecture"
        elif score >= 0.7:
            return "Code structure and quality meet professional standards"
        else:
            return "Code quality improvements recommended for long-term maintainability"

    def _generate_documentation_summary(self, results: Dict[str, Any]) -> str:
        """Generate documentation summary point."""
        score = self._extract_documentation_score(results)
        if score >= 0.8:
            return "Documentation accurately reflects implementation with strong alignment"
        elif score >= 0.6:
            return "Documentation provides adequate coverage with some gaps to address"
        else:
            return "Documentation requires updates to match current implementation"

    def _generate_error_report(self, error: str) -> str:
        """Generate error report when analysis fails."""
        return f"""# Repository Intelligence Analysis Report

## Analysis Error

**Error:** {error}

**Status:** Analysis could not be completed due to technical issues.

**Recommendation:** Contact system administrators or retry analysis.

---
"""


def generate_primary_report(analysis_results: Dict[str, Any],
                          repository_path: str) -> str:
    """
    Main function to generate primary human-readable report.

    Args:
        analysis_results: Complete analysis pipeline results
        repository_path: Path to the analyzed repository

    Returns:
        Markdown formatted primary report
    """
    generator = PrimaryReportGenerator()
    return generator.generate_primary_report(analysis_results, repository_path)