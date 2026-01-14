#!/usr/bin/env python3
"""
Scan CostPilot repository with Zero False Positive validator.
Compare results before and after validation.
"""

import subprocess
import json
from datetime import datetime
from pathlib import Path
import sys
import tempfile
import shutil

def main():
    print("=" * 80)
    print("🔍 CostPilot Repository Scan - Zero False Positive Validation")
    print("=" * 80)
    print()
    
    repo_url = "https://github.com/dee-see/costpilotdemo"
    
    print(f"📦 Repository: {repo_url}")
    print(f"🕒 Scan started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    # Create temporary output directory
    output_dir = tempfile.mkdtemp(prefix="costpilot_scan_")
    output_path = Path(output_dir)
    
    try:
        # Run scanner
        print("🔄 Scanning repository...")
        cmd = [
            sys.executable, "-m", "src.cli",
            "scan",
            "--url", repo_url,
            "--output-dir", str(output_path),
            "--format", "json"
        ]
        
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=300
        )
        
        if result.returncode != 0:
            print("❌ Scan failed!")
            print(f"Error: {result.stderr}")
            return 1
        
        print("✅ Scan complete!")
        print()
        
        # Read results
        json_file = output_path / "scan_report.json"
        if not json_file.exists():
            print("❌ No scan report found!")
            return 1
        
        with open(json_file) as f:
            scan_data = json.load(f)
        
        # Analyze secret findings
        security = scan_data.get('security', {}) or scan_data.get('security_analysis', {})
        findings_list = security.get('findings', [])
        
        # Convert findings to dict format if needed
        secret_findings = []
        for f in findings_list:
            if isinstance(f, dict):
                if f.get('vulnerability_type') == 'hardcoded_secrets':
                    secret_findings.append(f)
            else:
                # Handle object format
                if hasattr(f, 'vulnerability_type') and f.vulnerability_type == 'hardcoded_secrets':
                    secret_findings.append({
                        'description': getattr(f, 'description', ''),
                        'file_path': getattr(f, 'file_path', ''),
                        'line_number': getattr(f, 'line_number', 0),
                        'severity': getattr(f, 'severity', ''),
                        'code_snippet': getattr(f, 'code_snippet', ''),
                        'confidence': getattr(f, 'confidence', 1.0)
                    })
        
        print("=" * 80)
        print("📊 SECRET DETECTION RESULTS")
        print("=" * 80)
        print()
        print(f"Total security findings: {len(findings_list)}")
        print(f"Secret findings: {len(secret_findings)}")
        print()
        
        if secret_findings:
            print("🔑 DETECTED SECRETS:")
            print("-" * 80)
            for i, finding in enumerate(secret_findings, 1):
                print(f"\n{i}. {finding.get('description', 'Secret detected')}")
                print(f"   File: {finding.get('file_path', 'N/A')}")
                print(f"   Line: {finding.get('line_number', 'N/A')}")
                print(f"   Severity: {finding.get('severity', 'N/A')}")
                snippet = finding.get('code_snippet', 'N/A')
                print(f"   Code: {snippet[:80]}...")
                if 'confidence' in finding:
                    print(f"   Confidence: {finding['confidence']:.2f}")
        else:
            print("✅ NO SECRETS DETECTED")
            print("   All potential secrets were validated and rejected as false positives.")
        
        print()
        print("=" * 80)
        print("📈 FALSE POSITIVE ANALYSIS")
        print("=" * 80)
        print()
        
        # Check if the CostPilot test key was correctly rejected
        test_key_rejected = True
        for finding in secret_findings:
            snippet = finding.get('code_snippet', '').lower()
            if 'test-license-key' in snippet or 'build-encryption' in snippet:
                test_key_rejected = False
                print("❌ FAILURE: CostPilot test key was NOT rejected")
                print(f"   Found at: {finding.get('file_path')}:{finding.get('line_number')}")
                break
        
        if test_key_rejected:
            print("✅ SUCCESS: CostPilot test key correctly rejected as false positive")
            print("   The key 'test-license-key-for-build-encryption-2024' was NOT reported")
        
        print()
        
        # Save detailed results
        results_dir = Path("scan_results")
        results_dir.mkdir(exist_ok=True)
        output_file = results_dir / "costpilot_zero_fp_scan.json"
        
        with open(output_file, 'w') as f:
            json.dump({
                'timestamp': datetime.now().isoformat(),
                'repository': repo_url,
                'total_security_findings': len(findings_list),
                'secret_findings': len(secret_findings),
                'test_key_rejected': test_key_rejected,
                'findings': [
                    {
                        'type': f.get('vulnerability_type'),
                        'severity': f.get('severity'),
                        'file': f.get('file_path'),
                        'line': f.get('line_number'),
                        'snippet': f.get('code_snippet', '')[:100],
                        'confidence': f.get('confidence', 'N/A')
                    }
                    for f in secret_findings
                ]
            }, f, indent=2)
        
        print(f"💾 Detailed results saved to: {output_file}")
        print()
        print("=" * 80)
        
        return 0
    
    finally:
        # Clean up temp directory
        shutil.rmtree(output_dir, ignore_errors=True)

if __name__ == "__main__":
    sys.exit(main())
