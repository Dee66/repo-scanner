"""
Tests for Enhanced Report Generator

Tests executive summaries, risk scoring, and actionable recommendations.
"""

import pytest
from src.core.quality.enhanced_report_generator import EnhancedReportGenerator


class TestRiskScoreCalculation:
    """Test overall risk score calculation."""
    
    def test_low_risk_repository(self):
        """Test risk calculation for safe repository."""
        results = {
            'security_analysis': {
                'patterns_by_language': {
                    'python': []
                }
            },
            'malicious_intent': {
                'risk_score': 1.0,
                'malicious_intent_detected': False
            },
            'documentation_analysis': {
                'accuracy_score': 0.95
            },
            'governance_signals': {
                'has_ci': True,
                'has_tests': True,
                'has_readme': True
            }
        }
        
        generator = EnhancedReportGenerator()
        risk_score, risk_level = generator._calculate_overall_risk(results)
        
        assert risk_score < 4.0
        assert risk_level == 'LOW'
    
    def test_critical_risk_repository(self):
        """Test risk calculation for dangerous repository."""
        results = {
            'security_analysis': {
                'patterns_by_language': {
                    'python': [
                        {'severity': 'critical', 'confidence': 0.95},
                        {'severity': 'critical', 'confidence': 0.90},
                        {'severity': 'critical', 'confidence': 0.88},
                        {'severity': 'high', 'confidence': 0.85},
                        {'severity': 'high', 'confidence': 0.80}
                    ]
                }
            },
            'malicious_intent': {
                'risk_score': 9.5,
                'malicious_intent_detected': True
            },
            'documentation_analysis': {
                'accuracy_score': 0.3
            },
            'governance_signals': {
                'has_ci': False,
                'has_tests': False,
                'has_readme': False
            }
        }
        
        generator = EnhancedReportGenerator()
        risk_score, risk_level = generator._calculate_overall_risk(results)
        
        assert risk_score >= 9.0
        assert risk_level == 'CRITICAL'
    
    def test_medium_risk_repository(self):
        """Test risk calculation for moderate risk."""
        results = {
            'security_analysis': {
                'patterns_by_language': {
                    'python': [
                        {'severity': 'medium', 'confidence': 0.70},
                        {'severity': 'medium', 'confidence': 0.65},
                        {'severity': 'low', 'confidence': 0.60}
                    ]
                }
            },
            'malicious_intent': {
                'risk_score': 4.0,
                'malicious_intent_detected': False
            },
            'documentation_analysis': {
                'accuracy_score': 0.70
            },
            'governance_signals': {
                'has_ci': True,
                'has_tests': False,
                'has_readme': True
            }
        }
        
        generator = EnhancedReportGenerator()
        risk_score, risk_level = generator._calculate_overall_risk(results)
        
        assert 4.0 <= risk_score <= 6.9
        assert risk_level == 'MEDIUM'


class TestExecutiveSummary:
    """Test executive summary generation."""
    
    def test_summary_includes_risk_info(self):
        """Test that summary includes risk information."""
        results = {
            'security_analysis': {
                'patterns_by_language': {
                    'python': [
                        {'severity': 'critical', 'confidence': 0.95}
                    ]
                }
            },
            'malicious_intent': {
                'malicious_intent_detected': True
            }
        }
        
        generator = EnhancedReportGenerator()
        summary = generator._generate_executive_summary(results, 9.0, 'CRITICAL')
        
        assert 'CRITICAL' in summary
        assert '9.0' in summary or '9.' in summary
        assert 'Critical Vulnerabilities: 1' in summary
        assert 'Malicious Intent Detected: Yes' in summary
    
    def test_summary_has_recommendation(self):
        """Test that summary includes recommendation."""
        results = {
            'security_analysis': {'patterns_by_language': {}},
            'malicious_intent': {'malicious_intent_detected': False}
        }
        
        generator = EnhancedReportGenerator()
        summary = generator._generate_executive_summary(results, 2.0, 'LOW')
        
        assert 'Recommendation:' in summary or 'APPROVED' in summary


class TestTopRisksExtraction:
    """Test top risks identification and prioritization."""
    
    def test_extract_security_risks(self):
        """Test extracting security vulnerabilities as risks."""
        results = {
            'security_analysis': {
                'patterns_by_language': {
                    'python': [
                        {
                            'pattern_id': 'SEC_001',
                            'description': 'SQL Injection',
                            'severity': 'critical',
                            'confidence': 0.95,
                            'file': 'app.py',
                            'line': 42,
                            'evidence': 'query = f"SELECT * FROM users WHERE id={user_id}"',
                            'impact': 'Data breach',
                            'remediation': 'Use parameterized queries'
                        },
                        {
                            'description': 'XSS vulnerability',
                            'severity': 'high',
                            'confidence': 0.85,
                            'file': 'web.py',
                            'line': 100,
                            'evidence': 'render(user_input)',
                            'impact': 'Session hijacking',
                            'remediation': 'Sanitize input'
                        }
                    ]
                }
            },
            'malicious_intent': {
                'top_threats': []
            }
        }
        
        generator = EnhancedReportGenerator()
        risks = generator._extract_top_risks(results)
        
        assert len(risks) >= 2
        # Highest priority first (critical with high confidence)
        assert risks[0]['severity'] == 'critical'
        assert risks[0]['priority_score'] >= risks[1]['priority_score']
    
    def test_extract_malicious_risks(self):
        """Test extracting malicious intent as risks."""
        results = {
            'security_analysis': {'patterns_by_language': {}},
            'malicious_intent': {
                'top_threats': [
                    {
                        'description': 'Environment variable exfiltration',
                        'severity': 'CRITICAL',
                        'confidence': '95%',
                        'impact': 'Complete credential compromise',
                        'location': 'evil.py:10',
                        'remediation': 'Remove external transmission'
                    }
                ]
            }
        }
        
        generator = EnhancedReportGenerator()
        risks = generator._extract_top_risks(results)
        
        assert len(risks) >= 1
        assert 'Malicious Pattern' in risks[0]['title']
        assert risks[0]['priority'] == 'CRITICAL'
    
    def test_top_3_risks_limited(self):
        """Test that top risks section shows only 3 risks."""
        results = {
            'security_analysis': {
                'patterns_by_language': {
                    'python': [
                        {'severity': 'critical', 'confidence': 0.95, 'description': f'Vuln {i}',
                         'file': f'file{i}.py', 'line': i, 'evidence': 'code',
                         'impact': 'Bad', 'remediation': 'Fix it'}
                        for i in range(10)
                    ]
                }
            },
            'malicious_intent': {'top_threats': []}
        }
        
        generator = EnhancedReportGenerator()
        top_risks_section = generator._generate_top_risks(results)
        
        # Should have 3 numbered risks
        assert '### 1.' in top_risks_section
        assert '### 2.' in top_risks_section
        assert '### 3.' in top_risks_section
        assert '### 4.' not in top_risks_section


class TestActionableRecommendations:
    """Test actionable recommendations generation."""
    
    def test_recommendations_for_vulnerabilities(self):
        """Test that vulnerabilities generate recommendations."""
        results = {
            'security_analysis': {
                'patterns_by_language': {
                    'python': [
                        {'severity': 'critical'},
                        {'severity': 'critical'},
                        {'severity': 'high'},
                        {'severity': 'high'}
                    ]
                }
            },
            'malicious_intent': {
                'malicious_intent_detected': False
            }
        }
        
        generator = EnhancedReportGenerator()
        recommendations = generator._build_recommendations(results)
        
        # Should have recommendations for critical and high issues
        assert len(recommendations) >= 2
        
        critical_rec = next(r for r in recommendations if 'Critical' in r['action'])
        assert critical_rec['priority'] == 'CRITICAL'
        assert critical_rec['impact'] == 'CRITICAL'
    
    def test_malicious_intent_recommendation(self):
        """Test that malicious intent generates critical recommendation."""
        results = {
            'security_analysis': {'patterns_by_language': {}},
            'malicious_intent': {
                'malicious_intent_detected': True,
                'summary': 'Backdoor and credential theft detected'
            }
        }
        
        generator = EnhancedReportGenerator()
        recommendations = generator._build_recommendations(results)
        
        assert len(recommendations) >= 1
        malicious_rec = next(r for r in recommendations if 'Malicious' in r['action'])
        assert malicious_rec['priority'] == 'CRITICAL'
        assert malicious_rec['effort'] == 'HIGH'
    
    def test_recommendations_grouped_by_priority(self):
        """Test that recommendations are grouped by priority."""
        results = {
            'security_analysis': {
                'patterns_by_language': {
                    'python': [
                        {'severity': 'critical'},
                        {'severity': 'high'},
                        {'severity': 'medium'}
                    ]
                }
            },
            'malicious_intent': {'malicious_intent_detected': False}
        }
        
        generator = EnhancedReportGenerator()
        recs_section = generator._generate_actionable_recommendations(results)
        
        # Should have sections for different priorities
        assert '🚨 Critical Priority' in recs_section or '⚠️ High Priority' in recs_section


class TestReportGeneration:
    """Test full report generation."""
    
    def test_complete_report_structure(self):
        """Test that complete report has all sections."""
        results = {
            'security_analysis': {
                'patterns_by_language': {
                    'python': [
                        {
                            'severity': 'high',
                            'confidence': 0.85,
                            'description': 'Test vulnerability',
                            'file': 'test.py',
                            'line': 10,
                            'evidence': 'code',
                            'impact': 'Security risk',
                            'remediation': 'Fix it',
                            'type': 'test_vuln'
                        }
                    ]
                }
            },
            'malicious_intent': {
                'malicious_intent_detected': False,
                'risk_score': 3.0,
                'top_threats': []
            },
            'documentation_analysis': {
                'accuracy_score': 0.80
            },
            'governance_signals': {
                'has_ci': True,
                'has_tests': True,
                'has_readme': True
            }
        }
        
        generator = EnhancedReportGenerator()
        report = generator.generate_report(results, '/test/repo')
        
        # Check all major sections present
        assert '# Repository Security & Quality Assessment' in report
        assert '## 📊 Executive Summary' in report
        assert '## 🎯 Top' in report  # Top Risks
        assert '## 📋 Actionable Recommendations' in report
        assert '## 📝 Detailed Findings' in report
        
        # Check metadata
        assert '/test/repo' in report or 'repo' in report
        assert 'Overall Risk Score:' in report
        assert 'Risk Level:' in report
    
    def test_report_markdown_formatting(self):
        """Test that report uses proper markdown formatting."""
        results = {
            'security_analysis': {'patterns_by_language': {}},
            'malicious_intent': {
                'malicious_intent_detected': False,
                'risk_score': 1.0
            }
        }
        
        generator = EnhancedReportGenerator()
        report = generator.generate_report(results, '/test/repo')
        
        # Check markdown formatting
        assert report.startswith('#')  # Starts with header
        assert '**' in report  # Has bold text
        assert '##' in report  # Has subheaders
        assert '---' in report  # Has separators
    
    def test_report_with_no_findings(self):
        """Test report generation when no issues found."""
        results = {
            'security_analysis': {'patterns_by_language': {}},
            'malicious_intent': {
                'malicious_intent_detected': False,
                'risk_score': 1.0,
                'top_threats': []
            }
        }
        
        generator = EnhancedReportGenerator()
        report = generator.generate_report(results, '/clean/repo')
        
        assert 'LOW' in report or 'APPROVED' in report
        assert 'No critical risks' in report or 'No immediate actions' in report


class TestEdgeCases:
    """Test edge cases and error handling."""
    
    def test_missing_security_analysis(self):
        """Test handling of missing security analysis."""
        results = {
            'malicious_intent': {
                'malicious_intent_detected': False,
                'risk_score': 1.0
            }
        }
        
        generator = EnhancedReportGenerator()
        # Should not crash
        report = generator.generate_report(results, '/test/repo')
        
        assert isinstance(report, str)
        assert len(report) > 0
    
    def test_missing_malicious_intent(self):
        """Test handling of missing malicious intent analysis."""
        results = {
            'security_analysis': {'patterns_by_language': {}}
        }
        
        generator = EnhancedReportGenerator()
        # Should not crash
        report = generator.generate_report(results, '/test/repo')
        
        assert isinstance(report, str)
        assert len(report) > 0
    
    def test_empty_results(self):
        """Test handling of completely empty results."""
        results = {}
        
        generator = EnhancedReportGenerator()
        # Should not crash
        report = generator.generate_report(results, '/test/repo')
        
        assert isinstance(report, str)
        assert '# Repository Security & Quality Assessment' in report


if __name__ == '__main__':
    pytest.main([__file__, '-v'])


class TestSecurityDataPathFix:
    """Test that report generator reads security data from correct nested path."""

    def test_security_risk_with_nested_patterns(self):
        """Patterns under unsafe_patterns.patterns_by_language should be found."""
        results = {
            'security_analysis': {
                'unsafe_patterns': {
                    'patterns_by_language': {
                        'python': [
                            {'severity': 'high', 'confidence': 0.9},
                            {'severity': 'high', 'confidence': 0.8},
                        ]
                    }
                }
            },
            'malicious_intent': {'risk_score': 1.0, 'malicious_intent_detected': False},
        }
        generator = EnhancedReportGenerator()
        score = generator._calculate_security_risk(results.get('security_analysis', {}))
        assert score > 1.0, f"Expected > 1.0, got {score}"

    def test_executive_summary_shows_nested_findings(self):
        """Executive summary should report finding counts from nested path."""
        results = {
            'security_analysis': {
                'unsafe_patterns': {
                    'summary': {'high_severity': 5, 'medium_severity': 3},
                    'patterns_by_language': {
                        'python': [
                            {'severity': 'high'},
                            {'severity': 'high'},
                        ]
                    }
                }
            },
            'malicious_intent': {'risk_score': 1.0, 'malicious_intent_detected': False},
        }
        generator = EnhancedReportGenerator()
        report = generator._generate_executive_summary(results, 3.0, 'MEDIUM')
        # Should NOT say "0" for high severity since we have findings
        assert 'High Severity Issues:** 0' not in report or 'High Severity Issues:** 2' in report or 'High Severity Issues:** 5' in report

    def test_direct_patterns_still_work(self):
        """Direct patterns_by_language (standard pipeline format) should still work."""
        results = {
            'security_analysis': {
                'patterns_by_language': {
                    'python': [
                        {'severity': 'critical', 'confidence': 0.95},
                    ]
                }
            },
            'malicious_intent': {'risk_score': 1.0, 'malicious_intent_detected': False},
        }
        generator = EnhancedReportGenerator()
        score = generator._calculate_security_risk(results.get('security_analysis', {}))
        assert score > 1.0

    def test_empty_security_analysis_graceful(self):
        """Empty security_analysis should return base score without crashing."""
        generator = EnhancedReportGenerator()
        score = generator._calculate_security_risk({})
        assert score == 1.0
