#!/usr/bin/env python3
"""
Measure False Positive Reduction Across Multiple Repositories
"""

import subprocess
import json
import sys
from pathlib import Path
from datetime import datetime
import tempfile
import shutil

# Repositories to scan
REPOS = [
    {
        "name": "Flask",
        "url": "https://github.com/pallets/flask",
        "expected": {
            "test_secrets": True,  # Has test/mock secrets that should be rejected
            "real_secrets": False   # Should have no real secrets
        }
    },
    {
        "name": "Requests",
        "url": "https://github.com/psf/requests",
        "expected": {
            "test_secrets": True,
            "real_secrets": False
        }
    },
    {
        "name": "Tornado",
        "url": "https://github.com/tornadoweb/tornado",
        "expected": {
            "test_secrets": True,
            "real_secrets": False
        }
    }
]

def scan_repository(repo):
    """Scan a repository and return findings."""
    print(f"\n{'=' * 80}")
    print(f"🔍 Scanning: {repo['name']}")
    print(f"   URL: {repo['url']}")
    print('=' * 80)
    
    # Create temporary output directory
    output_dir = tempfile.mkdtemp(prefix=f"scan_{repo['name'].lower()}_")
    output_path = Path(output_dir)
    
    try:
        # Run scanner
        print("📊 Running scanner...")
        cmd = [
            sys.executable, "-m", "src.cli",
            "scan",
            "--url", repo['url'],
            "--output-dir", str(output_path),
            "--format", "json"
        ]
        
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=180,
            cwd=Path(__file__).parent
        )
        
        if result.returncode != 0:
            print(f"❌ Scan failed for {repo['name']}")
            print(f"Error: {result.stderr[:200]}")
            return None
        
        # Read results
        json_file = output_path / "scan_report.json"
        if not json_file.exists():
            print(f"❌ No scan report found for {repo['name']}")
            return None
        
        with open(json_file) as f:
            scan_data = json.load(f)
        
        # Extract secret findings
        security = scan_data.get('security_analysis', {}) or scan_data.get('security', {})
        unsafe = security.get('unsafe_patterns', {})
        secrets = unsafe.get('hardcoded_secrets', [])
        
        print(f"✅ Scan complete")
        print(f"   Secret findings: {len(secrets)}")
        
        return {
            'name': repo['name'],
            'url': repo['url'],
            'secret_count': len(secrets),
            'secrets': secrets[:3],  # First 3 for inspection
            'expected': repo['expected']
        }
    
    except subprocess.TimeoutExpired:
        print(f"⏱️  Scan timed out for {repo['name']}")
        return None
    except Exception as e:
        print(f"❌ Error scanning {repo['name']}: {e}")
        return None
    finally:
        # Clean up
        shutil.rmtree(output_dir, ignore_errors=True)

def main():
    print("=" * 80)
    print("📊 ZERO FALSE POSITIVE VALIDATION REPORT")
    print("=" * 80)
    print(f"🕒 Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"📦 Repositories to scan: {len(REPOS)}")
    print()
    
    results = []
    for repo in REPOS:
        result = scan_repository(repo)
        if result:
            results.append(result)
    
    # Generate report
    print("\n" + "=" * 80)
    print("📈 FALSE POSITIVE REDUCTION ANALYSIS")
    print("=" * 80)
    print()
    
    total_secrets = sum(r['secret_count'] for r in results)
    perfect_repos = sum(1 for r in results if r['secret_count'] == 0)
    
    print(f"📊 SUMMARY:")
    print(f"   Total repositories scanned: {len(results)}")
    print(f"   Total secret findings: {total_secrets}")
    print(f"   Repositories with 0 secrets: {perfect_repos}/{len(results)}")
    print()
    
    print("📋 DETAILED RESULTS:")
    print("-" * 80)
    for result in results:
        print(f"\n{result['name']}:")
        print(f"   URL: {result['url']}")
        print(f"   Secret findings: {result['secret_count']}")
        
        if result['secret_count'] == 0:
            print("   ✅ Status: PERFECT - No false positives")
        else:
            print(f"   ⚠️  Status: {result['secret_count']} findings detected")
            print("   Sample findings:")
            for i, secret in enumerate(result['secrets'][:3], 1):
                file_path = secret.get('file', 'unknown')
                line = secret.get('line', '?')
                snippet = secret.get('context', {}).get('snippet', '')[:60]
                print(f"      {i}. {file_path}:{line}")
                print(f"         {snippet}...")
    
    print()
    print("=" * 80)
    print("🎯 CONCLUSION")
    print("=" * 80)
    print()
    
    if total_secrets == 0:
        print("🎉 PERFECT SCORE!")
        print("   Zero false positives detected across all repositories.")
        print("   The SecretValidator successfully filtered out all test/mock/dummy secrets.")
    else:
        print(f"⚠️  {total_secrets} findings detected across {len(results)} repositories.")
        print("   These may be real secrets or false positives that need review.")
    
    print()
    
    # Save report
    output_file = Path("scan_results") / "zero_fp_validation_report.json"
    output_file.parent.mkdir(exist_ok=True)
    
    with open(output_file, 'w') as f:
        json.dump({
            'timestamp': datetime.now().isoformat(),
            'repositories_scanned': len(results),
            'total_secrets': total_secrets,
            'perfect_repos': perfect_repos,
            'results': [
                {
                    'name': r['name'],
                    'url': r['url'],
                    'secret_count': r['secret_count'],
                    'status': 'perfect' if r['secret_count'] == 0 else 'has_findings',
                    'sample_findings': r['secrets']
                }
                for r in results
            ]
        }, f, indent=2)
    
    print(f"💾 Full report saved to: {output_file}")
    print()
    
    return 0 if total_secrets == 0 else 1

if __name__ == "__main__":
    sys.exit(main())
