"""
Enhanced Report Generation with Executive Summaries and Risk Scoring

Generates actionable, commercial-grade reports with:
- Executive summary with overall risk score
- Top 3 critical risks with impact and remediation
- Actionable recommendations prioritized by effort and impact
- Clear risk scoring (1-10 scale)
- False positive probability per finding
"""

import logging
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime
from pathlib import Path

logger = logging.getLogger(__name__)


class EnhancedReportGenerator:
    """Generates commercial-grade reports with actionable insights."""
    
    def __init__(self):
        """Initialize report generator."""
        self.risk_thresholds = {
            'CRITICAL': (9.0, 10.0),
            'HIGH': (7.0, 8.9),
            'MEDIUM': (4.0, 6.9),
            'LOW': (1.0, 3.9)
        }
    
    def generate_report(self, analysis_results: Dict[str, Any], 
                       repository_path: str) -> str:
        """
        Generate comprehensive enhanced report.
        
        Args:
            analysis_results: Full analysis results
            repository_path: Path to analyzed repository
            
        Returns:
            Markdown formatted report
        """
        repo_name = Path(repository_path).name
        report_date = datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')
        
        # Calculate overall risk score
        risk_score, risk_level = self._calculate_overall_risk(analysis_results)
        
        # Build report sections
        sections = [
            self._generate_header(repo_name, report_date, risk_score, risk_level),
            self._generate_executive_summary(analysis_results, risk_score, risk_level),
            self._generate_top_risks(analysis_results),
            self._generate_actionable_recommendations(analysis_results),
            self._generate_detailed_findings(analysis_results),
            self._generate_metrics_dashboard(analysis_results),
            self._generate_footer()
        ]
        
        return '\n\n'.join(sections)
    
    def _calculate_overall_risk(self, results: Dict[str, Any]) -> Tuple[float, str]:
        """
        Calculate overall repository risk score.
        
        Returns:
            Tuple of (risk_score, risk_level)
            risk_score: 1.0 - 10.0 where 10 is most severe
            risk_level: CRITICAL, HIGH, MEDIUM, or LOW
        """
        # Check for malicious intent first - this overrides everything
        malicious_analysis = results.get('malicious_intent', {})
        if malicious_analysis.get('malicious_intent_detected', False):
            malicious_score = malicious_analysis.get('risk_score', 10.0)
            malicious_level = malicious_analysis.get('overall_risk', 'CRITICAL')
            
            # If malicious code detected with HIGH or CRITICAL risk, force critical status
            if malicious_level in ['CRITICAL', 'HIGH'] and malicious_score >= 7.0:
                logger.warning("Malicious code detected - forcing CRITICAL risk level")
                return 10.0, 'CRITICAL'
        
        scores = []
        
        # Security risk (weight: 40%)
        security_score = self._calculate_security_risk(results.get('security_analysis', {}))
        scores.append(('security', security_score, 0.40))
        
        # Malicious intent risk (weight: 30%)
        malicious_score = malicious_analysis.get('risk_score', 1.0)
        scores.append(('malicious_intent', malicious_score, 0.30))
        
        # Code quality risk (weight: 15%)
        quality_score = self._calculate_quality_risk(results)
        scores.append(('quality', quality_score, 0.15))
        
        # Documentation risk (weight: 10%)
        doc_score = self._calculate_documentation_risk(results)
        scores.append(('documentation', doc_score, 0.10))
        
        # Governance risk (weight: 5%)
        gov_score = self._calculate_governance_risk(results)
        scores.append(('governance', gov_score, 0.05))
        
        # Weighted average
        overall_score = sum(score * weight for _, score, weight in scores)
        
        # Determine risk level
        risk_level = 'LOW'
        for level, (min_score, max_score) in self.risk_thresholds.items():
            if min_score <= overall_score <= max_score:
                risk_level = level
                break
        
        logger.info("Overall risk score: %.2f (%s)", overall_score, risk_level)
        logger.debug("Risk component scores: %s", 
                    {name: f"{score:.2f}" for name, score, _ in scores})
        
        return overall_score, risk_level
    
    def _calculate_security_risk(self, security_analysis: Dict[str, Any]) -> float:
        """Calculate security risk score (1-10)."""
        if not security_analysis:
            return 1.0
        
        patterns = security_analysis.get('patterns_by_language', {})
        all_patterns = []
        for lang_patterns in patterns.values():
            all_patterns.extend(lang_patterns)
        
        if not all_patterns:
            return 1.0
        
        # Count by severity
        critical = sum(1 for p in all_patterns if p.get('severity') == 'critical')
        high = sum(1 for p in all_patterns if p.get('severity') == 'high')
        medium = sum(1 for p in all_patterns if p.get('severity') == 'medium')
        
        # Calculate score
        score = 1.0 + (critical * 3.0) + (high * 1.5) + (medium * 0.5)
        return min(10.0, score)
    
    def _calculate_quality_risk(self, results: Dict[str, Any]) -> float:
        """Calculate code quality risk score (1-10)."""
        # TODO: Implement based on complexity, duplication, test coverage
        return 3.0  # Placeholder
    
    def _calculate_documentation_risk(self, results: Dict[str, Any]) -> float:
        """Calculate documentation risk score (1-10)."""
        doc_analysis = results.get('documentation_analysis', {})
        if not doc_analysis:
            return 5.0  # Unknown
        
        accuracy = doc_analysis.get('accuracy_score', 0.5)
        # Lower accuracy = higher risk
        return 1.0 + (1.0 - accuracy) * 9.0
    
    def _calculate_governance_risk(self, results: Dict[str, Any]) -> float:
        """Calculate governance risk score (1-10)."""
        gov_signals = results.get('governance_signals', {})
        if not gov_signals:
            return 4.0
        
        # Good governance signals reduce risk
        has_ci = gov_signals.get('has_ci', False)
        has_tests = gov_signals.get('has_tests', False)
        has_readme = gov_signals.get('has_readme', False)
        
        score = 7.0
        if has_ci:
            score -= 1.5
        if has_tests:
            score -= 1.5
        if has_readme:
            score -= 1.0
        
        return max(1.0, score)
    
    def _generate_header(self, repo_name: str, report_date: str, 
                        risk_score: float, risk_level: str) -> str:
        """Generate report header."""
        risk_emoji = {
            'CRITICAL': '🚨',
            'HIGH': '⚠️',
            'MEDIUM': '⚡',
            'LOW': '✅'
        }.get(risk_level, '❓')
        
        return f"""# Repository Security & Quality Assessment

**Repository:** `{repo_name}`  
**Analysis Date:** {report_date}  
**Overall Risk Score:** {risk_score:.1f}/10.0 {risk_emoji}  
**Risk Level:** **{risk_level}**

---
"""
    
    def _generate_executive_summary(self, results: Dict[str, Any], 
                                   risk_score: float, risk_level: str) -> str:
        """Generate executive summary."""
        # Count findings by severity
        security = results.get('security_analysis', {})
        patterns = security.get('patterns_by_language', {})
        all_patterns = []
        for lang_patterns in patterns.values():
            all_patterns.extend(lang_patterns)
        
        critical_count = sum(1 for p in all_patterns if p.get('severity') == 'critical')
        high_count = sum(1 for p in all_patterns if p.get('severity') == 'high')
        medium_count = sum(1 for p in all_patterns if p.get('severity') == 'medium')
        
        # Malicious intent
        malicious = results.get('malicious_intent', {})
        malicious_detected = malicious.get('malicious_intent_detected', False)
        
        # Summary text
        if risk_level == 'CRITICAL':
            summary = (
                "**⚠️ CRITICAL RISKS IDENTIFIED - IMMEDIATE ACTION REQUIRED**\n\n"
                "This repository contains severe security vulnerabilities and/or malicious patterns "
                "that pose immediate risk. **Do not deploy or use this code in production** until "
                "all critical issues are resolved."
            )
        elif risk_level == 'HIGH':
            summary = (
                "**⚠️ HIGH RISK - SIGNIFICANT ISSUES REQUIRE ATTENTION**\n\n"
                "This repository has significant security or quality issues that must be addressed "
                "before production use. Manual security review is strongly recommended."
            )
        elif risk_level == 'MEDIUM':
            summary = (
                "**⚡ MODERATE RISK - REVIEW RECOMMENDED**\n\n"
                "This repository has some issues that should be addressed to improve security "
                "and quality posture. Review and remediation recommended before production deployment."
            )
        else:
            summary = (
                "**✅ LOW RISK - ACCEPTABLE WITH MINOR IMPROVEMENTS**\n\n"
                "This repository shows good security and quality practices. "
                "Minor improvements recommended but safe for production use."
            )
        
        findings_summary = f"""
### Quick Stats
- **Critical Vulnerabilities:** {critical_count}
- **High Severity Issues:** {high_count}
- **Medium Severity Issues:** {medium_count}
- **Malicious Intent Detected:** {'Yes ⚠️' if malicious_detected else 'No ✅'}
"""
        
        return f"""## 📊 Executive Summary

{summary}

{findings_summary}

**Recommendation:** {self._generate_executive_recommendation(risk_level, critical_count, malicious_detected)}
"""
    
    def _generate_executive_recommendation(self, risk_level: str, 
                                          critical_count: int, 
                                          malicious_detected: bool) -> str:
        """Generate executive recommendation."""
        if malicious_detected:
            return "**REJECT** - Malicious code detected. Do not use."
        elif risk_level == 'CRITICAL' or critical_count >= 5:
            return "**HOLD** - Address critical issues before proceeding."
        elif risk_level == 'HIGH':
            return "**REVIEW** - Security review required before approval."
        elif risk_level == 'MEDIUM':
            return "**CONDITIONAL APPROVAL** - Address issues in next iteration."
        else:
            return "**APPROVED** - Safe for production with monitoring."
    
    def _generate_top_risks(self, results: Dict[str, Any]) -> str:
        """Generate top 3 critical risks section."""
        risks = self._extract_top_risks(results)
        
        if not risks:
            return """## 🎯 Top Risks

✅ **No critical risks identified**

This repository does not have any high-priority security or quality issues.
"""
        
        risk_details = []
        for i, risk in enumerate(risks[:3], 1):
            severity_emoji = {
                'critical': '🚨',
                'high': '⚠️',
                'medium': '⚡',
                'low': '✅'
            }.get(risk['severity'], '❓')
            
            risk_text = f"""### {i}. {risk['title']} {severity_emoji}

**Severity:** {risk['severity'].upper()}  
**Impact:** {risk['impact']}  
**Confidence:** {risk['confidence']}

**Evidence:**
```
{risk['evidence']}
```

**Remediation:** {risk['remediation']}

**Effort:** {risk['effort']}  
**Priority:** {risk['priority']}
"""
            risk_details.append(risk_text)
        
        return f"""## 🎯 Top 3 Critical Risks

{chr(10).join(risk_details)}
"""
    
    def _extract_top_risks(self, results: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Extract and prioritize top risks."""
        risks = []
        
        # Extract security vulnerabilities
        security = results.get('security_analysis', {})
        patterns = security.get('patterns_by_language', {})
        for lang, lang_patterns in patterns.items():
            for pattern in lang_patterns:
                severity = pattern.get('severity', 'medium')
                confidence = pattern.get('confidence', 0.5)
                
                # Calculate priority score
                severity_weight = {
                    'critical': 10,
                    'high': 7,
                    'medium': 4,
                    'low': 2
                }.get(severity, 1)
                priority_score = severity_weight * confidence
                
                risks.append({
                    'title': pattern.get('description', 'Security Issue'),
                    'severity': severity,
                    'impact': pattern.get('impact', 'Security vulnerability'),
                    'confidence': f"{confidence:.0%}",
                    'evidence': f"{pattern.get('file', 'unknown')}:{pattern.get('line', '?')}\n{pattern.get('evidence', '')}",
                    'remediation': pattern.get('remediation', 'Review and fix'),
                    'effort': self._estimate_effort(severity),
                    'priority': 'CRITICAL' if priority_score >= 8 else 'HIGH' if priority_score >= 5 else 'MEDIUM',
                    'priority_score': priority_score
                })
        
        # Extract malicious intent patterns
        malicious = results.get('malicious_intent', {})
        top_threats = malicious.get('top_threats', [])
        for threat in top_threats:
            risks.append({
                'title': f"Malicious Pattern: {threat['description']}",
                'severity': threat['severity'].lower(),
                'impact': threat['impact'],
                'confidence': threat['confidence'],
                'evidence': threat['location'],
                'remediation': threat['remediation'],
                'effort': 'HIGH',
                'priority': 'CRITICAL',
                'priority_score': 10.0
            })
        
        # Sort by priority score
        risks.sort(key=lambda r: r['priority_score'], reverse=True)
        
        return risks
    
    def _estimate_effort(self, severity: str) -> str:
        """Estimate remediation effort."""
        return {
            'critical': 'MEDIUM',
            'high': 'LOW-MEDIUM',
            'medium': 'LOW',
            'low': 'TRIVIAL'
        }.get(severity, 'UNKNOWN')
    
    def _generate_actionable_recommendations(self, results: Dict[str, Any]) -> str:
        """Generate prioritized actionable recommendations."""
        recommendations = self._build_recommendations(results)
        
        if not recommendations:
            return """## ✅ Recommendations

No immediate actions required. Repository follows good practices.
"""
        
        # Group by priority
        critical = [r for r in recommendations if r['priority'] == 'CRITICAL']
        high = [r for r in recommendations if r['priority'] == 'HIGH']
        medium = [r for r in recommendations if r['priority'] == 'MEDIUM']
        
        sections = []
        
        if critical:
            critical_text = '\n'.join(
                f"{i}. **{r['action']}** (Effort: {r['effort']}, Impact: {r['impact']})\n   - {r['details']}"
                for i, r in enumerate(critical, 1)
            )
            sections.append(f"### 🚨 Critical Priority (Fix Immediately)\n\n{critical_text}")
        
        if high:
            high_text = '\n'.join(
                f"{i}. **{r['action']}** (Effort: {r['effort']}, Impact: {r['impact']})\n   - {r['details']}"
                for i, r in enumerate(high, 1)
            )
            sections.append(f"### ⚠️ High Priority (Fix This Sprint)\n\n{high_text}")
        
        if medium:
            medium_text = '\n'.join(
                f"{i}. **{r['action']}** (Effort: {r['effort']}, Impact: {r['impact']})\n   - {r['details']}"
                for i, r in enumerate(medium, 1)
            )
            sections.append(f"### ⚡ Medium Priority (Plan for Next Iteration)\n\n{medium_text}")
        
        return f"""## 📋 Actionable Recommendations

{chr(10).join(sections)}
"""
    
    def _build_recommendations(self, results: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Build prioritized recommendations list."""
        recommendations = []
        
        # Security recommendations
        security = results.get('security_analysis', {})
        patterns = security.get('patterns_by_language', {})
        critical_count = 0
        high_count = 0
        
        for lang_patterns in patterns.values():
            for pattern in lang_patterns:
                if pattern.get('severity') == 'critical':
                    critical_count += 1
                elif pattern.get('severity') == 'high':
                    high_count += 1
        
        if critical_count > 0:
            recommendations.append({
                'priority': 'CRITICAL',
                'action': f'Fix {critical_count} Critical Security Vulnerabilities',
                'effort': 'MEDIUM',
                'impact': 'CRITICAL',
                'details': 'Review and remediate all critical security issues before production deployment'
            })
        
        if high_count > 0:
            recommendations.append({
                'priority': 'HIGH',
                'action': f'Address {high_count} High-Severity Security Issues',
                'effort': 'LOW-MEDIUM',
                'impact': 'HIGH',
                'details': 'Fix high-severity vulnerabilities to reduce attack surface'
            })
        
        # Malicious intent recommendations
        malicious = results.get('malicious_intent', {})
        if malicious.get('malicious_intent_detected'):
            recommendations.append({
                'priority': 'CRITICAL',
                'action': 'Investigate Malicious Code Patterns',
                'effort': 'HIGH',
                'impact': 'CRITICAL',
                'details': f"{malicious.get('summary', 'Malicious patterns detected')} - Perform thorough code audit"
            })
        
        return recommendations
    
    def _generate_detailed_findings(self, results: Dict[str, Any]) -> str:
        """Generate detailed findings section."""
        sections = []
        
        # Security findings
        security_section = self._generate_security_findings_detail(results)
        if security_section:
            sections.append(security_section)
        
        # Malicious intent findings
        malicious_section = self._generate_malicious_findings_detail(results)
        if malicious_section:
            sections.append(malicious_section)
        
        if not sections:
            return "## 📝 Detailed Findings\n\nNo significant findings to report."
        
        return "## 📝 Detailed Findings\n\n" + "\n\n".join(sections)
    
    def _generate_security_findings_detail(self, results: Dict[str, Any]) -> str:
        """Generate detailed security findings."""
        security = results.get('security_analysis', {})
        patterns = security.get('patterns_by_language', {})
        
        if not patterns:
            return ""
        
        findings_by_severity = {'critical': [], 'high': [], 'medium': [], 'low': []}
        
        for lang, lang_patterns in patterns.items():
            for pattern in lang_patterns:
                severity = pattern.get('severity', 'medium')
                findings_by_severity[severity].append({
                    'language': lang,
                    'type': pattern.get('type', 'unknown'),
                    'file': pattern.get('file', 'unknown'),
                    'line': pattern.get('line', '?'),
                    'confidence': pattern.get('confidence', 0.5),
                    'description': pattern.get('description', 'No description')
                })
        
        sections = []
        for severity in ['critical', 'high', 'medium', 'low']:
            findings = findings_by_severity[severity]
            if not findings:
                continue
            
            emoji = {
                'critical': '🚨',
                'high': '⚠️',
                'medium': '⚡',
                'low': '✅'
            }.get(severity, '❓')
            
            findings_text = '\n'.join(
                f"- **{f['type']}** in `{f['file']}:{f['line']}` (Confidence: {f['confidence']:.0%})\n  {f['description']}"
                for f in findings[:10]  # Limit to 10 per severity
            )
            
            sections.append(f"#### {emoji} {severity.upper()} ({len(findings)} findings)\n\n{findings_text}")
        
        return f"### 🔒 Security Vulnerabilities\n\n" + "\n\n".join(sections)
    
    def _generate_malicious_findings_detail(self, results: Dict[str, Any]) -> str:
        """Generate detailed malicious intent findings."""
        malicious = results.get('malicious_intent', {})
        
        if not malicious or not malicious.get('malicious_intent_detected'):
            return ""
        
        by_category = malicious.get('by_category', {})
        category_text = '\n'.join(
            f"- **{cat.replace('_', ' ').title()}:** {count} detection(s)"
            for cat, count in by_category.items()
        )
        
        return f"""### 🎭 Malicious Intent Analysis

**Overall Assessment:** {malicious.get('overall_risk', 'UNKNOWN')}  
**Summary:** {malicious.get('summary', 'No summary')}

**Detections by Category:**
{category_text}

Review the Top Risks section above for detailed remediation guidance.
"""
    
    def _generate_metrics_dashboard(self, results: Dict[str, Any]) -> str:
        """Generate metrics dashboard."""
        # TODO: Implement comprehensive metrics
        return """## 📈 Metrics Dashboard

*(Metrics dashboard available in full version)*
"""
    
    def _generate_footer(self) -> str:
        """Generate report footer."""
        return """---

**Report Generation:** This report was generated by Repository Intelligence Scanner.  
**Feedback:** Use `repo-scanner feedback` to improve detection accuracy.  
**Support:** For questions or issues, consult the documentation.
"""
