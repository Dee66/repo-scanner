"""
Learning System for Continuous Improvement

Enables the scanner to learn from feedback and improve detection accuracy over time.
"""

import json
import sqlite3
import logging
from pathlib import Path
from typing import Dict, Any, List, Literal, Optional
from dataclasses import dataclass
from datetime import datetime
import hashlib

logger = logging.getLogger(__name__)


@dataclass
class ScanFinding:
    """Represents a single finding from a scan."""
    finding_id: str  # Unique ID for this finding
    scan_id: str
    pattern_id: str
    pattern_type: str
    severity: str
    confidence: float
    file_path: str
    line_number: Optional[int]
    evidence: str
    description: str
    timestamp: str


@dataclass
class FindingFeedback:
    """User feedback on a finding."""
    finding_id: str
    classification: Literal["TP", "FP", "UNKNOWN"]  # True Positive, False Positive, Unknown
    user_comment: Optional[str]
    timestamp: str


@dataclass
class PatternStatistics:
    """Statistics for a detection pattern."""
    pattern_id: str
    pattern_type: str
    total_reports: int
    true_positives: int
    false_positives: int
    unknown: int
    base_confidence: float
    adjusted_confidence: float
    false_positive_rate: float
    last_updated: str


class FeedbackDatabase:
    """SQLite database for storing scan results and user feedback."""
    
    def __init__(self, db_path: Optional[Path] = None):
        """
        Initialize feedback database.
        
        Args:
            db_path: Path to SQLite database file
        """
        if db_path is None:
            db_path = Path.home() / ".repo-scanner" / "feedback.db"
        
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        
        self.conn = sqlite3.connect(str(self.db_path))
        self.conn.row_factory = sqlite3.Row
        self._create_tables()
        
    def _create_tables(self):
        """Create database tables if they don't exist."""
        self.conn.executescript("""
            CREATE TABLE IF NOT EXISTS scans (
                scan_id TEXT PRIMARY KEY,
                repository_path TEXT NOT NULL,
                scan_timestamp TEXT NOT NULL,
                total_findings INTEGER,
                scan_data TEXT  -- JSON blob with full results
            );
            
            CREATE TABLE IF NOT EXISTS findings (
                finding_id TEXT PRIMARY KEY,
                scan_id TEXT NOT NULL,
                pattern_id TEXT NOT NULL,
                pattern_type TEXT NOT NULL,
                severity TEXT NOT NULL,
                confidence REAL NOT NULL,
                file_path TEXT NOT NULL,
                line_number INTEGER,
                evidence TEXT,
                description TEXT,
                timestamp TEXT NOT NULL,
                FOREIGN KEY (scan_id) REFERENCES scans(scan_id)
            );
            
            CREATE TABLE IF NOT EXISTS feedback (
                feedback_id INTEGER PRIMARY KEY AUTOINCREMENT,
                finding_id TEXT NOT NULL,
                classification TEXT NOT NULL CHECK(classification IN ('TP', 'FP', 'UNKNOWN')),
                user_comment TEXT,
                timestamp TEXT NOT NULL,
                FOREIGN KEY (finding_id) REFERENCES findings(finding_id)
            );
            
            CREATE TABLE IF NOT EXISTS pattern_stats (
                pattern_id TEXT PRIMARY KEY,
                pattern_type TEXT NOT NULL,
                total_reports INTEGER DEFAULT 0,
                true_positives INTEGER DEFAULT 0,
                false_positives INTEGER DEFAULT 0,
                unknown INTEGER DEFAULT 0,
                base_confidence REAL NOT NULL,
                adjusted_confidence REAL NOT NULL,
                false_positive_rate REAL DEFAULT 0.0,
                last_updated TEXT NOT NULL
            );
            
            CREATE INDEX IF NOT EXISTS idx_findings_scan ON findings(scan_id);
            CREATE INDEX IF NOT EXISTS idx_findings_pattern ON findings(pattern_id);
            CREATE INDEX IF NOT EXISTS idx_feedback_finding ON feedback(finding_id);
        """)
        self.conn.commit()
        
    def store_scan(self, scan_id: str, repository_path: str, results: Dict[str, Any]):
        """Store scan results."""
        findings = self._extract_findings_from_results(scan_id, results)
        
        # Store scan metadata
        self.conn.execute("""
            INSERT OR REPLACE INTO scans (scan_id, repository_path, scan_timestamp, total_findings, scan_data)
            VALUES (?, ?, ?, ?, ?)
        """, (scan_id, repository_path, datetime.utcnow().isoformat(), 
              len(findings), json.dumps(results)))
        
        # Store individual findings
        for finding in findings:
            self.conn.execute("""
                INSERT OR REPLACE INTO findings 
                (finding_id, scan_id, pattern_id, pattern_type, severity, confidence,
                 file_path, line_number, evidence, description, timestamp)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (finding.finding_id, finding.scan_id, finding.pattern_id,
                  finding.pattern_type, finding.severity, finding.confidence,
                  finding.file_path, finding.line_number, finding.evidence,
                  finding.description, finding.timestamp))
        
        self.conn.commit()
        logger.info("Stored scan %s with %d findings", scan_id, len(findings))
        
    def _extract_findings_from_results(self, scan_id: str, results: Dict) -> List[ScanFinding]:
        """Extract findings from scan results."""
        findings = []
        security_analysis = results.get("security_analysis", {})
        patterns = security_analysis.get("patterns_by_language", {})
        
        for _language, pattern_list in patterns.items():
            for pattern in pattern_list:
                finding_id = self._generate_finding_id(scan_id, pattern)
                findings.append(ScanFinding(
                    finding_id=finding_id,
                    scan_id=scan_id,
                    pattern_id=pattern.get("pattern_id", "unknown"),
                    pattern_type=pattern.get("type", "unknown"),
                    severity=pattern.get("severity", "medium"),
                    confidence=pattern.get("confidence", 0.5),
                    file_path=pattern.get("file", "unknown"),
                    line_number=pattern.get("line"),
                    evidence=pattern.get("evidence", ""),
                    description=pattern.get("description", ""),
                    timestamp=datetime.utcnow().isoformat()
                ))
        
        return findings
        
    def _generate_finding_id(self, scan_id: str, pattern: Dict) -> str:
        """Generate unique ID for a finding."""
        content = f"{scan_id}:{pattern.get('file')}:{pattern.get('line')}:{pattern.get('type')}"
        return hashlib.sha256(content.encode()).hexdigest()[:16]
        
    def record_feedback(self, finding_id: str, classification: str, comment: Optional[str] = None):
        """Record user feedback on a finding."""
        self.conn.execute("""
            INSERT INTO feedback (finding_id, classification, user_comment, timestamp)
            VALUES (?, ?, ?, ?)
        """, (finding_id, classification, comment, datetime.utcnow().isoformat()))
        self.conn.commit()
        
        # Update pattern statistics
        finding = self.conn.execute(
            "SELECT pattern_id, confidence FROM findings WHERE finding_id = ?",
            (finding_id,)
        ).fetchone()
        
        if finding:
            self._update_pattern_stats(finding['pattern_id'], classification, finding['confidence'])
            
    def _update_pattern_stats(self, pattern_id: str, classification: str, base_confidence: float):
        """Update statistics for a pattern based on feedback."""
        # Get existing stats or create new
        stats = self.conn.execute(
            "SELECT * FROM pattern_stats WHERE pattern_id = ?",
            (pattern_id,)
        ).fetchone()
        
        if stats:
            total = stats['total_reports'] + 1
            tp = stats['true_positives'] + (1 if classification == 'TP' else 0)
            fp = stats['false_positives'] + (1 if classification == 'FP' else 0)
            unknown = stats['unknown'] + (1 if classification == 'UNKNOWN' else 0)
        else:
            total = 1
            tp = 1 if classification == 'TP' else 0
            fp = 1 if classification == 'FP' else 0
            unknown = 1 if classification == 'UNKNOWN' else 0
        
        # Calculate adjusted confidence and FP rate
        if tp + fp > 0:
            accuracy = tp / (tp + fp)
            fp_rate = fp / (tp + fp)
            # Bayesian adjustment
            adjusted_confidence = base_confidence * accuracy / (
                base_confidence * accuracy + (1 - base_confidence) * (1 - accuracy)
            )
        else:
            accuracy = 0.5
            fp_rate = 0.0
            adjusted_confidence = base_confidence
        
        self.conn.execute("""
            INSERT OR REPLACE INTO pattern_stats
            (pattern_id, pattern_type, total_reports, true_positives, false_positives,
             unknown, base_confidence, adjusted_confidence, false_positive_rate, last_updated)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (pattern_id, "security", total, tp, fp, unknown, base_confidence,
              adjusted_confidence, fp_rate, datetime.utcnow().isoformat()))
        
        self.conn.commit()
        logger.info("Updated stats for pattern %s: accuracy=%.2f%%, fp_rate=%.2f%%", 
                   pattern_id, accuracy * 100, fp_rate * 100)
        
    def get_pattern_stats(self, pattern_id: str) -> Optional[PatternStatistics]:
        """Get statistics for a pattern."""
        row = self.conn.execute(
            "SELECT * FROM pattern_stats WHERE pattern_id = ?",
            (pattern_id,)
        ).fetchone()
        
        if row:
            return PatternStatistics(**dict(row))
        return None
        
    def get_all_pattern_stats(self) -> List[PatternStatistics]:
        """Get statistics for all patterns."""
        rows = self.conn.execute("SELECT * FROM pattern_stats").fetchall()
        return [PatternStatistics(**dict(row)) for row in rows]
        
    def get_findings_by_scan(self, scan_id: str) -> List[ScanFinding]:
        """Get all findings for a scan."""
        rows = self.conn.execute(
            "SELECT * FROM findings WHERE scan_id = ?",
            (scan_id,)
        ).fetchall()
        return [ScanFinding(**dict(row)) for row in rows]


class LearningSystem:
    """Main learning system that coordinates feedback and improvements."""
    
    def __init__(self, db_path: Optional[Path] = None):
        """
        Initialize learning system.
        
        Args:
            db_path: Path to feedback database
        """
        self.db = FeedbackDatabase(db_path)
        
    def record_scan_result(self, scan_id: str, repository_path: str, results: Dict[str, Any]):
        """
        Record scan results for future feedback.
        
        Args:
            scan_id: Unique identifier for this scan
            repository_path: Path to repository that was scanned
            results: Full scan results dictionary
        """
        self.db.store_scan(scan_id, repository_path, results)
        
    def submit_feedback(self, finding_id: str, classification: Literal["TP", "FP", "UNKNOWN"],
                       comment: Optional[str] = None):
        """
        Submit user feedback on a finding.
        
        Args:
            finding_id: ID of the finding to provide feedback on
            classification: Whether finding is True Positive, False Positive, or Unknown
            comment: Optional user comment explaining the classification
        """
        self.db.record_feedback(finding_id, classification, comment)
        logger.info("Recorded feedback for finding %s: %s", finding_id, classification)
        
    def get_adjusted_confidence(self, pattern_id: str) -> float:
        """
        Get adjusted confidence for a pattern based on historical accuracy.
        
        Args:
            pattern_id: Pattern to get adjusted confidence for
            
        Returns:
            Adjusted confidence score (0.0 to 1.0)
        """
        stats = self.db.get_pattern_stats(pattern_id)
        if stats and stats.total_reports >= 5:  # Minimum reports for adjustment
            return stats.adjusted_confidence
        return 0.5  # Default confidence if insufficient data
        
    def generate_improvement_report(self) -> Dict[str, Any]:
        """
        Generate report on patterns needing improvement.
        
        Returns:
            Dictionary with improvement recommendations
        """
        all_stats = self.db.get_all_pattern_stats()
        
        problematic = []
        needs_review = []
        performing_well = []
        
        for stats in all_stats:
            if stats.total_reports < 5:
                continue  # Insufficient data
                
            if stats.false_positive_rate > 0.20:  # 20% FP rate
                problematic.append({
                    'pattern_id': stats.pattern_id,
                    'pattern_type': stats.pattern_type,
                    'fp_rate': f"{stats.false_positive_rate:.1%}",
                    'total_reports': stats.total_reports,
                    'recommendation': 'DISABLE or REFINE - High false positive rate'
                })
            elif stats.false_positive_rate > 0.10:  # 10% FP rate
                needs_review.append({
                    'pattern_id': stats.pattern_id,
                    'fp_rate': f"{stats.false_positive_rate:.1%}",
                    'recommendation': 'REVIEW - Moderate false positive rate'
                })
            else:
                performing_well.append({
                    'pattern_id': stats.pattern_id,
                    'accuracy': f"{(1 - stats.false_positive_rate):.1%}",
                    'adjusted_confidence': f"{stats.adjusted_confidence:.2f}"
                })
        
        return {
            'total_patterns_evaluated': len(all_stats),
            'problematic_patterns': problematic,
            'needs_review': needs_review,
            'performing_well': performing_well,
            'summary': {
                'high_priority_issues': len(problematic),
                'medium_priority_issues': len(needs_review),
                'well_performing': len(performing_well)
            }
        }


def get_learning_system(db_path: Optional[Path] = None) -> LearningSystem:
    """Get singleton learning system instance."""
    return LearningSystem(db_path)
