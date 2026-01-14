#!/usr/bin/env python3
"""
Test the zero false positive secret validator on sample code.
"""

import sys
sys.path.insert(0, 'src')

from core.pipeline.security_analysis import SecurityAnalyzer
from pathlib import Path
import tempfile
import os

def create_test_files():
    """Create test files with various secret patterns."""
    test_dir = tempfile.mkdtemp(prefix="zero_fp_validation_")
    
    # Test file 1: CostPilot-like false positive (should be REJECTED)
    test_file1 = Path(test_dir) / "build.rs"
    test_file1.write_text('const LICENSE_KEY: &str = "test-license-key-for-build-encryption-2024";\n'
                          'const BUILD_TIMESTAMP: &str = "2024-01-15";\n'
                          '\n'
                          'fn main() {\n'
                          '    println!("Building with key: {}", LICENSE_KEY);\n'
                          '}\n')
    
    # Test file 2: Real secret (should be DETECTED)
    test_file2 = Path(test_dir) / "config.py"
    test_file2.write_text('API_KEY = "sk_live_51H7f2hg8k9m2p5x7q1w4e3r5t6y7u8i9o0"\n'
                          'DATABASE_URL = "postgres://user:pass@localhost/db"\n')
    
    # Test file 3: Test file with secret (should be REJECTED due to file path)
    test_file3 = Path(test_dir) / "tests" / "test_auth.py"
    test_file3.parent.mkdir(exist_ok=True)
    test_file3.write_text('import pytest\n'
                          '\n'
                          'def test_api_key():\n'
                          '    api_key = "sk_test_12345678901234567890"\n'
                          '    assert len(api_key) > 0\n')
    
    # Test file 4: Weak password (should be REJECTED)
    test_file4 = Path(test_dir) / "app.py"
    test_file4.write_text('# Application\n'
                          'password = "password123"\n'
                          'secret = "admin"\n')
    
    # Test file 5: GitHub PAT (should be DETECTED)
    test_file5 = Path(test_dir) / "github_config.py"
    test_file5.write_text('GITHUB_TOKEN = "ghp_a8f3k9m2p5x7q1w4e3r5t6y7u8i9o0p1q2r3"\n'
                          'REPO_URL = "https://github.com/user/repo"\n')
    
    return test_dir, [test_file1, test_file2, test_file3, test_file4, test_file5]

def main():
    print("🔬 Testing Zero False Positive Secret Validator\n")
    print("=" * 70)
    
    # Create test files
    test_dir, test_files = create_test_files()
    print(f"✅ Created test directory: {test_dir}\n")
    
    # Initialize analyzer
    analyzer = SecurityAnalyzer()
    if not analyzer.secret_validator:
        print("❌ SecretValidator not available!")
        return 1
    
    print(f"✅ SecretValidator initialized\n")
    print("=" * 70)
    
    # Analyze each test file
    total_findings = 0
    expected_results = {
        "build.rs": ("REJECT", "CostPilot test key"),
        "config.py": ("DETECT", "Real Stripe API key"),
        "test_auth.py": ("REJECT", "Test file with test prefix"),
        "app.py": ("REJECT", "Weak passwords"),
        "github_config.py": ("DETECT", "Real GitHub PAT"),
    }
    
    results = {}
    
    for test_file in test_files:
        file_name = test_file.name
        print(f"\n📄 {file_name}")
        print("-" * 70)
        
        # Debug: show file contents
        content = test_file.read_text()
        print(f"File has {len(content.splitlines())} lines")
        
        findings = analyzer._analyze_file(str(test_file))
        secret_findings = [f for f in findings if f.vulnerability_type == 'hardcoded_secrets']
        
        print(f"Total findings: {len(findings)}, Secret findings: {len(secret_findings)}")
        
        expected_action, description = expected_results.get(file_name, ("UNKNOWN", ""))
        
        if expected_action == "DETECT":
            if secret_findings:
                print(f"✅ CORRECT: Secret DETECTED ({len(secret_findings)} finding(s))")
                for finding in secret_findings:
                    print(f"   Line {finding.line_number}: {finding.code_snippet[:60]}...")
                results[file_name] = "PASS"
            else:
                print(f"❌ WRONG: Secret NOT detected (expected detection)")
                print(f"   Expected: {description}")
                results[file_name] = "FAIL"
        else:  # REJECT
            if not secret_findings:
                print(f"✅ CORRECT: False positive REJECTED")
                print(f"   Reason: {description}")
                results[file_name] = "PASS"
            else:
                print(f"❌ WRONG: False positive NOT rejected ({len(secret_findings)} finding(s))")
                for finding in secret_findings:
                    print(f"   Line {finding.line_number}: {finding.code_snippet[:60]}...")
                results[file_name] = "FAIL"
        
        total_findings += len(secret_findings)
    
    # Summary
    print("\n" + "=" * 70)
    print("📊 SUMMARY")
    print("=" * 70)
    
    passed = sum(1 for r in results.values() if r == "PASS")
    failed = sum(1 for r in results.values() if r == "FAIL")
    
    print(f"\nTest Results:")
    for file_name, result in results.items():
        status = "✅ PASS" if result == "PASS" else "❌ FAIL"
        print(f"  {status}: {file_name}")
    
    print(f"\nTotal: {passed}/{len(results)} tests passed")
    print(f"Total secret findings reported: {total_findings}")
    
    # Expected: 2 secrets detected (config.py, github_config.py)
    # Expected: 3 false positives rejected (build.rs, test_auth.py, app.py)
    expected_detections = 2
    if total_findings == expected_detections and failed == 0:
        print(f"\n🎉 SUCCESS: All tests passed!")
        print(f"   - {expected_detections} real secrets detected")
        print(f"   - 3 false positives correctly rejected")
        return_code = 0
    else:
        print(f"\n⚠️  ISSUES DETECTED:")
        if total_findings != expected_detections:
            print(f"   - Expected {expected_detections} detections, got {total_findings}")
        if failed > 0:
            print(f"   - {failed} test(s) failed")
        return_code = 1
    
    # Cleanup
    import shutil
    shutil.rmtree(test_dir)
    print(f"\n✅ Cleaned up test directory")
    
    return return_code

if __name__ == "__main__":
    sys.exit(main())
