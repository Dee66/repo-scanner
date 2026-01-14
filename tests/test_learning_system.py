"""
Tests for Continuous Learning System

Tests feedback recording, pattern statistics, and learning improvements.
"""

import pytest
import tempfile
import json
from pathlib import Path
from src.core.learning.learning_system import (
    LearningSystem,
    FeedbackDatabase,
    PatternStatistics,
    ScanFinding,
    get_learning_system
)


class TestFeedbackDatabase:
    """Test feedback database operations."""
    
    @pytest.fixture
    def temp_db(self):
        """Create temporary database for testing."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test_feedback.db"
            yield db_path
    
    def test_database_creation(self, temp_db):
        """Test database tables are created correctly."""
        db = FeedbackDatabase(temp_db)
        
        # Check tables exist
        tables = db.conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        ).fetchall()
        
        table_names = [t['name'] for t in tables]
        assert 'scans' in table_names
        assert 'findings' in table_names
        assert 'feedback' in table_names
        assert 'pattern_stats' in table_names
    
    def test_store_scan(self, temp_db):
        """Test storing scan results."""
        db = FeedbackDatabase(temp_db)
        
        results = {
            'security_analysis': {
                'patterns_by_language': {
                    'python': [
                        {
                            'pattern_id': 'SEC_001',
                            'type': 'hardcoded_secret',
                            'severity': 'critical',
                            'confidence': 0.95,
                            'file': 'test.py',
                            'line': 10,
                            'evidence': 'password = "admin123"',
                            'description': 'Hardcoded password'
                        }
                    ]
                }
            }
        }
        
        db.store_scan('test_scan_001', '/path/to/repo', results)
        
        # Verify scan stored
        scan = db.conn.execute(
            "SELECT * FROM scans WHERE scan_id = ?",
            ('test_scan_001',)
        ).fetchone()
        
        assert scan is not None
        assert scan['repository_path'] == '/path/to/repo'
        assert scan['total_findings'] == 1
        
        # Verify finding stored
        findings = db.get_findings_by_scan('test_scan_001')
        assert len(findings) == 1
        assert findings[0].pattern_id == 'SEC_001'
        assert findings[0].severity == 'critical'
    
    def test_record_feedback(self, temp_db):
        """Test recording user feedback."""
        db = FeedbackDatabase(temp_db)
        
        # First store a scan
        results = {
            'security_analysis': {
                'patterns_by_language': {
                    'python': [
                        {
                            'pattern_id': 'SEC_001',
                            'type': 'test',
                            'severity': 'high',
                            'confidence': 0.80,
                            'file': 'test.py',
                            'line': 1,
                            'evidence': 'code',
                            'description': 'Test finding'
                        }
                    ]
                }
            }
        }
        
        db.store_scan('scan_001', '/repo', results)
        findings = db.get_findings_by_scan('scan_001')
        finding_id = findings[0].finding_id
        
        # Record feedback
        db.record_feedback(finding_id, 'TP', 'Confirmed vulnerability')
        
        # Verify feedback recorded
        feedback = db.conn.execute(
            "SELECT * FROM feedback WHERE finding_id = ?",
            (finding_id,)
        ).fetchone()
        
        assert feedback is not None
        assert feedback['classification'] == 'TP'
        assert feedback['user_comment'] == 'Confirmed vulnerability'
    
    def test_pattern_statistics_update(self, temp_db):
        """Test pattern statistics are updated with feedback."""
        db = FeedbackDatabase(temp_db)
        
        # Store scan with finding
        results = {
            'security_analysis': {
                'patterns_by_language': {
                    'python': [
                        {
                            'pattern_id': 'SEC_001',
                            'type': 'test',
                            'severity': 'high',
                            'confidence': 0.80,
                            'file': 'test.py',
                            'line': 1,
                            'evidence': 'code',
                            'description': 'Test'
                        }
                    ]
                }
            }
        }
        
        db.store_scan('scan_001', '/repo', results)
        findings = db.get_findings_by_scan('scan_001')
        finding_id = findings[0].finding_id
        
        # Record feedback
        db.record_feedback(finding_id, 'TP')
        
        # Check pattern stats updated
        stats = db.get_pattern_stats('SEC_001')
        assert stats is not None
        assert stats.pattern_id == 'SEC_001'
        assert stats.total_reports == 1
        assert stats.true_positives == 1
        assert stats.false_positives == 0
    
    def test_false_positive_rate_calculation(self, temp_db):
        """Test false positive rate calculation."""
        db = FeedbackDatabase(temp_db)
        
        # Store multiple scans with same pattern
        for i in range(10):
            results = {
                'security_analysis': {
                    'patterns_by_language': {
                        'python': [
                            {
                                'pattern_id': 'SEC_001',
                                'type': 'test',
                                'severity': 'high',
                                'confidence': 0.80,
                                'file': f'test{i}.py',
                                'line': i,
                                'evidence': 'code',
                                'description': 'Test'
                            }
                        ]
                    }
                }
            }
            
            scan_id = f'scan_{i:03d}'
            db.store_scan(scan_id, f'/repo{i}', results)
            findings = db.get_findings_by_scan(scan_id)
            
            # 7 TP, 3 FP
            classification = 'TP' if i < 7 else 'FP'
            db.record_feedback(findings[0].finding_id, classification)
        
        # Check statistics
        stats = db.get_pattern_stats('SEC_001')
        assert stats.total_reports == 10
        assert stats.true_positives == 7
        assert stats.false_positives == 3
        assert abs(stats.false_positive_rate - 0.3) < 0.01  # 3/10 = 0.3


class TestLearningSystem:
    """Test learning system functionality."""
    
    @pytest.fixture
    def temp_learning_system(self):
        """Create temporary learning system for testing."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test_learning.db"
            learning = LearningSystem(db_path)
            yield learning
    
    def test_record_and_retrieve_scan(self, temp_learning_system):
        """Test recording and retrieving scan results."""
        learning = temp_learning_system
        
        results = {
            'security_analysis': {
                'patterns_by_language': {
                    'python': [
                        {
                            'pattern_id': 'SEC_001',
                            'type': 'vulnerability',
                            'severity': 'critical',
                            'confidence': 0.95,
                            'file': 'app.py',
                            'line': 42,
                            'evidence': 'vulnerable_code()',
                            'description': 'SQL Injection'
                        }
                    ]
                }
            }
        }
        
        learning.record_scan_result('scan_abc123', '/project/repo', results)
        
        # Retrieve findings
        findings = learning.db.get_findings_by_scan('scan_abc123')
        assert len(findings) == 1
        assert findings[0].pattern_id == 'SEC_001'
        assert findings[0].file_path == 'app.py'
    
    def test_submit_feedback(self, temp_learning_system):
        """Test submitting feedback on findings."""
        learning = temp_learning_system
        
        # Record scan
        results = {
            'security_analysis': {
                'patterns_by_language': {
                    'python': [
                        {
                            'pattern_id': 'SEC_002',
                            'type': 'xss',
                            'severity': 'high',
                            'confidence': 0.85,
                            'file': 'web.py',
                            'line': 100,
                            'evidence': 'render(user_input)',
                            'description': 'XSS vulnerability'
                        }
                    ]
                }
            }
        }
        
        learning.record_scan_result('scan_def456', '/web/app', results)
        findings = learning.db.get_findings_by_scan('scan_def456')
        finding_id = findings[0].finding_id
        
        # Submit feedback
        learning.submit_feedback(finding_id, 'FP', 'This is sanitized elsewhere')
        
        # Verify feedback recorded
        feedback = learning.db.conn.execute(
            "SELECT * FROM feedback WHERE finding_id = ?",
            (finding_id,)
        ).fetchone()
        
        assert feedback['classification'] == 'FP'
        assert 'sanitized' in feedback['user_comment']
    
    def test_adjusted_confidence_calculation(self, temp_learning_system):
        """Test that confidence is adjusted based on feedback."""
        learning = temp_learning_system
        
        # Record multiple scans and feedback
        for i in range(20):
            results = {
                'security_analysis': {
                    'patterns_by_language': {
                        'python': [
                            {
                                'pattern_id': 'SEC_003',
                                'type': 'test',
                                'severity': 'medium',
                                'confidence': 0.70,
                                'file': f'file{i}.py',
                                'line': i,
                                'evidence': 'code',
                                'description': 'Test'
                            }
                        ]
                    }
                }
            }
            
            scan_id = f'scan_{i}'
            learning.record_scan_result(scan_id, f'/repo{i}', results)
            findings = learning.db.get_findings_by_scan(scan_id)
            
            # 90% accuracy (18 TP, 2 FP)
            classification = 'FP' if i < 2 else 'TP'
            learning.submit_feedback(findings[0].finding_id, classification)
        
        # Get adjusted confidence
        adjusted_conf = learning.get_adjusted_confidence('SEC_003')
        
        # Should be higher than base (0.70) due to high accuracy
        assert adjusted_conf > 0.70
        assert adjusted_conf < 1.0
    
    def test_improvement_report_generation(self, temp_learning_system):
        """Test generating pattern improvement report."""
        learning = temp_learning_system
        
        # Create patterns with different performance
        patterns_data = [
            ('PAT_GOOD', 10, 9, 1),    # 90% accuracy - good
            ('PAT_OK', 10, 8, 2),      # 80% accuracy - ok
            ('PAT_BAD', 10, 3, 7),     # 30% accuracy - bad (70% FP rate)
        ]
        
        for pattern_id, total, tp_count, fp_count in patterns_data:
            for i in range(total):
                results = {
                    'security_analysis': {
                        'patterns_by_language': {
                            'python': [
                                {
                                    'pattern_id': pattern_id,
                                    'type': 'test',
                                    'severity': 'medium',
                                    'confidence': 0.70,
                                    'file': f'{pattern_id}_{i}.py',
                                    'line': i,
                                    'evidence': 'code',
                                    'description': 'Test'
                                }
                            ]
                        }
                    }
                }
                
                scan_id = f'{pattern_id}_{i}'
                learning.record_scan_result(scan_id, f'/repo{i}', results)
                findings = learning.db.get_findings_by_scan(scan_id)
                
                # Assign TP or FP based on counts
                classification = 'TP' if i < tp_count else 'FP'
                learning.submit_feedback(findings[0].finding_id, classification)
        
        # Generate report
        report = learning.generate_improvement_report()
        
        assert 'problematic_patterns' in report
        assert 'needs_review' in report
        assert 'performing_well' in report
        
        # PAT_BAD should be in problematic (>20% FP rate)
        problematic_ids = [p['pattern_id'] for p in report['problematic_patterns']]
        assert 'PAT_BAD' in problematic_ids
        
        # PAT_GOOD should be in performing well
        performing_ids = [p['pattern_id'] for p in report['performing_well']]
        assert 'PAT_GOOD' in performing_ids


class TestEdgeCases:
    """Test edge cases and error handling."""
    
    @pytest.fixture
    def temp_db(self):
        """Create temporary database."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test.db"
            db = FeedbackDatabase(db_path)
            yield db
    
    @pytest.fixture
    def temp_learning_system(self):
        """Create temporary learning system."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "learning.db"
            system = LearningSystem(db_path)
            yield system
    
    def test_feedback_on_nonexistent_finding(self, temp_db):
        """Test feedback on non-existent finding."""
        db = FeedbackDatabase(temp_db)
        
        # Should not crash, just create stats entry
        db.record_feedback('nonexistent_id', 'TP')
        
        # No stats should be created without valid finding
        conn = db.conn
        result = conn.execute(
            "SELECT COUNT(*) as count FROM pattern_stats"
        ).fetchone()
        
        assert result['count'] == 0
    
    def test_empty_scan_results(self, temp_db):
        """Test handling of scans with no findings."""
        db = FeedbackDatabase(temp_db)
        
        results = {
            'security_analysis': {
                'patterns_by_language': {}
            }
        }
        
        db.store_scan('empty_scan', '/repo', results)
        
        scan = db.conn.execute(
            "SELECT * FROM scans WHERE scan_id = ?",
            ('empty_scan',)
        ).fetchone()
        
        assert scan['total_findings'] == 0
    
    def test_confidence_with_insufficient_data(self, temp_learning_system):
        """Test that confidence adjustment requires minimum data."""
        learning = temp_learning_system
        
        # Only 2 reports (less than minimum of 5)
        for i in range(2):
            results = {
                'security_analysis': {
                    'patterns_by_language': {
                        'python': [
                            {
                                'pattern_id': 'SEC_NEW',
                                'type': 'test',
                                'severity': 'low',
                                'confidence': 0.60,
                                'file': f'file{i}.py',
                                'line': i,
                                'evidence': 'code',
                                'description': 'Test'
                            }
                        ]
                    }
                }
            }
            
            scan_id = f'scan_{i}'
            learning.record_scan_result(scan_id, f'/repo{i}', results)
            findings = learning.db.get_findings_by_scan(scan_id)
            learning.submit_feedback(findings[0].finding_id, 'TP')
        
        # Should return default confidence due to insufficient data
        adjusted = learning.get_adjusted_confidence('SEC_NEW')
        assert adjusted == 0.5  # Default


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
